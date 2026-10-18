"""Compare runs of the same tasks under different serving setups (Weeks 4-5).

    agentic-compare week4 traces/week4/cache-on traces/week4/cache-off
    agentic-compare week5 traces/week5/c1 traces/week5/c2 traces/week5/c4 traces/week5/c8

Writes results/figures/<name>/compare.json, compare.md, ttft_vs_prompt.png and
throughput_latency.png. Run directories keep the order given (it is the x-axis).
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .analyze import INK_2, SERIES, SURFACE, load

ROOT = Path(__file__).resolve().parents[2]


def _wall(run_dir: Path) -> tuple[float | None, int | None]:
    """Total wall time and concurrency from the run_summary files of a directory."""
    summaries = [json.loads(f.read_text(encoding="utf-8")) for f in run_dir.glob("run_summary_*.json")]
    if not summaries:
        return None, None
    return sum(s["wall_s"] for s in summaries), summaries[-1]["concurrency"]


def compare(run_dirs: list[Path]) -> pd.DataFrame:
    tasks, steps = load(run_dirs)
    rows = []
    for d in run_dirs:
        t, s = tasks[tasks["run"] == d.name], steps[steps["run"] == d.name]
        timings = s["server_timings"].dropna() if "server_timings" in s else pd.Series(dtype=object)
        prefill = sum(x.get("prompt_n", 0) for x in timings) if len(timings) else None
        prefill_ms = sum(x.get("prompt_ms", 0) for x in timings) if len(timings) else None
        wall, conc = _wall(d)
        rows.append({
            "run": d.name,
            "concurrency": conc,
            "tasks": len(t),
            "accuracy": t["correct"].mean(),
            "llm_calls": len(s),
            "ttft_mean_s": s["llm_ttft_s"].mean(),
            "ttft_p50_s": s["llm_ttft_s"].median(),
            "ttft_p95_s": s["llm_ttft_s"].quantile(0.95),
            "task_p50_s": t["total_s"].median(),
            "task_p95_s": t["total_s"].quantile(0.95),
            "tasks_per_min": 60 * len(t) / wall if wall else None,
            "gen_tokens_per_s": s["completion_tokens"].sum() / wall if wall else None,
            "prompt_tokens": int(s["prompt_tokens"].sum()),
            "prefill_tokens_computed": prefill,
            "prefill_s_server": prefill_ms / 1000 if prefill_ms is not None else None,
            "cache_hit_%": 100 * s["cached_tokens"].sum() / s["prompt_tokens"].sum()
            if s["cached_tokens"].notna().any() else None,
        })
    return pd.DataFrame(rows)


def fig_ttft_vs_prompt(steps: pd.DataFrame, order: list[str], out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, run in enumerate(order[:3]):
        s = steps[steps["run"] == run]
        ax.scatter(s["prompt_tokens"], s["llm_ttft_s"], s=14, color=SERIES[i], alpha=0.55,
                   edgecolors=SURFACE, linewidths=0.6, label=run)
    ax.set_xlabel("Prompt tokens")
    ax.set_ylabel("Time to first token (s)")
    ax.set_title("TTFT vs. prompt length, one dot per LLM call")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left")
    fig.savefig(out_dir / "ttft_vs_prompt.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_throughput_latency(df: pd.DataFrame, out_dir: Path) -> None:
    if df["tasks_per_min"].isna().all():
        return
    labels = df["run"].tolist()
    x = range(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    axes[0].bar(x, df["tasks_per_min"], width=0.5, color=SERIES[0])
    for xi, v in zip(x, df["tasks_per_min"], strict=True):
        axes[0].annotate(f"{v:.1f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                         ha="center", color=INK_2, fontsize=8)
    axes[0].set_title("Throughput (tasks/min)")
    axes[1].plot(x, df["task_p50_s"], color=SERIES[0], marker="o", label="P50")
    axes[1].plot(x, df["task_p95_s"], color=SERIES[1], marker="o", label="P95")
    axes[1].set_title("Task latency (s)")
    axes[1].legend(loc="upper left")
    for ax in axes:
        ax.set_xticks(list(x), labels)
        ax.set_ylim(bottom=0)
        ax.grid(axis="x", visible=False)
    fig.savefig(out_dir / "throughput_latency.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def _markdown(df: pd.DataFrame) -> str:
    body = [["–" if pd.isna(v) else str(v) for v in row] for row in df.values.tolist()]
    rows = [list(df.columns), ["---"] * len(df.columns), *body]
    return "\n".join("| " + " | ".join(r) + " |" for r in rows) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-compare")
    p.add_argument("name", help="output folder name under results/figures/")
    p.add_argument("runs", type=Path, nargs="+", help="trace directories, in x-axis order")
    args = p.parse_args()

    out_dir = ROOT / "results" / "figures" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    df = compare(args.runs)
    (out_dir / "compare.json").write_text(df.round(3).to_json(orient="records", indent=2), encoding="utf-8")
    (out_dir / "compare.md").write_text(_markdown(df.round(2)), encoding="utf-8")
    _, steps = load(args.runs)
    fig_ttft_vs_prompt(steps, [d.name for d in args.runs], out_dir)
    fig_throughput_latency(df, out_dir)
    pd.set_option("display.width", 250)
    print(df.round(2).to_string(index=False))
    print(f"\nTable and figures in {out_dir.relative_to(ROOT)}")
