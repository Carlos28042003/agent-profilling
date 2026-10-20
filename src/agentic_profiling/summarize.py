import argparse
import json
import sys
from pathlib import Path

import pandas as pd

TRUNCATION_TOKENS_PER_CHAR = 0.12


def load_steps(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    tasks, steps = [], []
    for f in sorted(run_dir.glob("*.json")):
        if f.name.startswith("run_"):
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        tasks.append({"run": run_dir.name, "task_id": t["task_id"], "correct": t["correct"],
                      "finished": t["finished"], "n_steps": len(t["steps"]), "total_s": t["total_s"]})
        windowed = bool(t.get("meta", {}).get("config", {}).get("history_window"))
        prev = None
        for s in t["steps"]:
            truncated = bool(not windowed and prev is not None and s["prompt_tokens"] and prev["prompt_tokens"]
                             and s["prompt_chars"] > prev["prompt_chars"]
                             and (s["prompt_tokens"] - prev["prompt_tokens"])
                             < TRUNCATION_TOKENS_PER_CHAR * (s["prompt_chars"] - prev["prompt_chars"]))
            steps.append({"run": run_dir.name, "task_id": t["task_id"], "truncated": truncated, **s})
            prev = s
    return pd.DataFrame(tasks), pd.DataFrame(steps)


def summarize(tasks: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    later = steps[steps["index"] > 0]
    by_run = steps.groupby("run")
    llm, tool, total = by_run["llm_total_s"].sum(), by_run["tool_s"].sum(), by_run["step_total_s"].sum()
    out = pd.DataFrame({
        "accuracy": tasks.groupby("run")["correct"].mean(),
        "finished": tasks.groupby("run")["finished"].mean(),
        "steps_mean": tasks.groupby("run")["n_steps"].mean(),
        "task_s_p50": tasks.groupby("run")["total_s"].median(),
        "task_s_max": tasks.groupby("run")["total_s"].max(),
        "llm_%": 100 * llm / total,
        "tool_%": 100 * tool / total,
        "overhead_%": 100 * (total - llm - tool) / total,
        "ttft_mean_s": by_run["llm_ttft_s"].mean(),
        "prompt_tok_max": by_run["prompt_tokens"].max(),
        "truncated_steps": by_run["truncated"].sum(),
        "prefix_reuse_%": 100 * later.groupby("run")["shared_prefix_chars"].sum()
        / later.groupby("run")["prompt_chars"].sum(),
        "cached_tok_%": 100 * later.groupby("run")["cached_tokens"].sum(min_count=1)
        / later.groupby("run")["prompt_tokens"].sum(),
    })
    return out.round(2)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-summary")
    p.add_argument("runs", type=Path, nargs="+", help="trace directories")
    args = p.parse_args()

    loaded = [load_steps(r) for r in args.runs]
    tasks = pd.concat([t for t, _ in loaded], ignore_index=True)
    steps = pd.concat([s for _, s in loaded], ignore_index=True)

    pd.set_option("display.width", 200)
    summary = summarize(tasks, steps)
    print(summary.to_string())
    if summary["truncated_steps"].any():
        print("\nWARNING: the server truncated the context in some steps (see truncated_steps); "
              "increase num_ctx / max-model-len.")
    print("\nCorrect answers per task (all runs):")
    print(tasks.pivot_table(index="task_id", columns="run", values="correct", aggfunc="first")
          .astype(int).to_string())
