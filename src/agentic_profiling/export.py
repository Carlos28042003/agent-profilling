"""Export an experiment to results/<name>.json and update DATA on the results page.

    agentic-export week1 traces/week1/* --title "..." --description "..."
    agentic-export --page-only        # only rebuild DATA in docs/index.html from results/

The page (docs/index.html) reads everything from the DATA object between the
DATA:START and DATA:END markers.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .analyze import load as load_full
from .analyze import stats as workload_stats
from .compare import compare
from .summarize import load_steps, summarize

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
PAGE = ROOT / "docs" / "index.html"
DATA_RE = re.compile(r"/\* DATA:START \*/.*?/\* DATA:END \*/", re.DOTALL)

STEP_FIELDS = ["index", "tool", "llm_ttft_s", "llm_generation_s", "tool_s",
               "prompt_tokens", "completion_tokens", "cached_tokens", "truncated"]


def _example(run_dirs: list[Path], steps: pd.DataFrame, choice: str | None) -> dict:
    """One task for the step-by-step chart: the chosen one, or the longest correct one."""
    if choice:
        run, task_id = choice.split("/")
    else:
        lengths = steps.groupby(["run", "task_id"])["index"].max().sort_values(ascending=False)
        correct = set()
        for d in run_dirs:
            for f in d.glob("*.json"):
                t = json.loads(f.read_text(encoding="utf-8"))
                if t.get("correct"):
                    correct.add((d.name, t["task_id"]))
        run, task_id = next((k for k in lengths.index if k in correct), lengths.index[0])
    path = next(d for d in run_dirs if d.name == run) / f"{task_id}.json"
    t = json.loads(path.read_text(encoding="utf-8"))
    rows = steps[(steps["run"] == run) & (steps["task_id"] == task_id)].sort_values("index")
    return {"run": run, "task_id": task_id, "question": t["question"], "answer": t["answer"],
            "correct": t.get("correct"), "model": t.get("meta", {}).get("config", {}).get("model"),
            "steps": json.loads(rows[STEP_FIELDS].to_json(orient="records"))}


def _characterization(run_dirs: list[Path]) -> dict:
    """Per-run series for the page's Week 3 charts (context growth, reuse, latency, time split)."""
    tasks, steps = load_full(run_dirs)
    growth, reuse, latency = {}, {}, {}
    for run, s in steps.groupby("run"):
        g = s.groupby("index")
        n = g.size()
        q = g["prompt_tokens"].quantile([0.25, 0.5, 0.75]).unstack()
        keep = n[n >= 5].index
        growth[run] = [{"step": int(i), "p25": round(q.loc[i, 0.25]), "p50": round(q.loc[i, 0.5]),
                        "p75": round(q.loc[i, 0.75]), "n": int(n[i])} for i in keep]
        reuse_pct = 100 * g["reusable_tokens"].sum() / g["prompt_tokens"].sum()
        cached_pct = 100 * g["cached_tokens"].sum() / g["prompt_tokens"].sum()
        reuse[run] = [{"step": int(i), "reuse_pct": round(reuse_pct[i], 1),
                       "cached_pct": None if pd.isna(cached_pct[i]) else round(cached_pct[i], 1)} for i in keep]
    for run, t in tasks.groupby("run"):
        latency[run] = sorted(round(x, 2) for x in t["total_s"])
    st = workload_stats(tasks, steps)
    return {"stats": st, "growth": growth, "reuse_by_step": reuse, "latency": latency,
            "time_split": {run: v["time_split_%"] for run, v in st.items()}}


def export(name: str, run_dirs: list[Path], title: str, description: str, example: str | None,
           with_compare: bool = False) -> Path:
    loaded = [load_steps(r) for r in run_dirs]
    tasks = pd.concat([t for t, _ in loaded], ignore_index=True)
    steps = pd.concat([s for _, s in loaded], ignore_index=True)
    summary = summarize(tasks, steps).reset_index()

    models = {}
    for r in run_dirs:
        meta_file = r / "run_meta.json"
        if meta_file.exists():
            models[r.name] = json.loads(meta_file.read_text(encoding="utf-8"))["config"]["model"]
    summary.insert(1, "model", summary["run"].map(models))

    per_task = tasks.pivot_table(index="task_id", columns="run", values="correct", aggfunc="first")
    result = {
        "id": name,
        "title": title,
        "description": description,
        "exported": date.today().isoformat(),
        "runs": json.loads(summary.to_json(orient="records")),
        "per_task": {task: {run: int(v) for run, v in row.items()} for task, row in per_task.iterrows()},
        "example": _example(run_dirs, steps, example),
        **_characterization(run_dirs),
    }
    if with_compare:
        result["compare"] = json.loads(compare(run_dirs).round(3).to_json(orient="records"))
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{name}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def update_page() -> int:
    experiments = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS.glob("*.json"))]
    data = {"updated": date.today().isoformat(), "experiments": experiments}
    block = "/* DATA:START */\nconst DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n/* DATA:END */"
    html = PAGE.read_text(encoding="utf-8")
    if not DATA_RE.search(html):
        sys.exit(f"DATA:START/DATA:END markers not found in {PAGE}")
    PAGE.write_text(DATA_RE.sub(lambda _: block, html), encoding="utf-8", newline="\n")
    return len(experiments)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-export")
    p.add_argument("name", nargs="?", help="experiment name (file results/<name>.json)")
    p.add_argument("runs", type=Path, nargs="*", help="trace directories")
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument("--example", help="task for the step chart, as run/task_id")
    p.add_argument("--compare", action="store_true", help="also export the run comparison (Weeks 4-5)")
    p.add_argument("--page-only", action="store_true", help="only update docs/index.html")
    args = p.parse_args()

    if not args.page_only:
        if not args.name or not args.runs:
            p.error("give the experiment name and trace directories (or --page-only)")
        out = export(args.name, args.runs, args.title or args.name, args.description, args.example,
                     args.compare)
        print(f"Exported: {out.relative_to(ROOT)}")
    n = update_page()
    print(f"Page updated: {PAGE.relative_to(ROOT)} ({n} experiments)")
