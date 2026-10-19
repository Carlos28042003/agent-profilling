import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from .summarize import load_steps

ROOT = Path(__file__).resolve().parents[2]

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK_2, INK_3, GRID, SURFACE = "#0b0b0b", "#52514e", "#77766f", "#e7e6e1", "#ffffff"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_3, "ytick.color": INK_3,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False, "lines.linewidth": 2,
    "lines.solid_capstyle": "round", "text.color": INK,
})


def load(run_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    loaded = [load_steps(r) for r in run_dirs]
    tasks = pd.concat([t for t, _ in loaded], ignore_index=True)
    steps = pd.concat([s for _, s in loaded], ignore_index=True)
    steps = steps.sort_values(["run", "task_id", "index"])
    prev = steps.groupby(["run", "task_id"])[["prompt_tokens", "completion_tokens"]].shift(1)
    steps["reusable_tokens"] = np.minimum(steps["prompt_tokens"],
                                          prev["prompt_tokens"] + prev["completion_tokens"]).fillna(0)
    steps["overhead_s"] = (steps["step_total_s"] - steps["llm_total_s"] - steps["tool_s"]).clip(lower=0)
    extra = []
    for r in run_dirs:
        for f in r.glob("*.json"):
            if not f.name.startswith("run_"):
                t = json.loads(f.read_text(encoding="utf-8"))
                extra.append({"run": r.name, "task_id": t["task_id"], "f1": t.get("f1")})
    tasks = tasks.merge(pd.DataFrame(extra), on=["run", "task_id"], how="left")
    return tasks, steps


def stats(tasks: pd.DataFrame, steps: pd.DataFrame) -> dict:
    out = {}
    for run, t in tasks.groupby("run"):
        s = steps[steps["run"] == run]
        later = s[s["index"] > 0]
        total = s["step_total_s"].sum()
        growth = s.groupby("index")["prompt_tokens"].median()
        out[run] = {
            "tasks": len(t),
            "accuracy": round(t["correct"].mean(), 3),
            "f1": round(t["f1"].mean(), 3) if t["f1"].notna().any() else None,
            "finished": round(t["finished"].mean(), 3),
            "steps_mean": round(t["n_steps"].mean(), 2),
            "steps_median": float(t["n_steps"].median()),
            "task_s_p50": round(t["total_s"].quantile(0.5), 1),
            "task_s_p95": round(t["total_s"].quantile(0.95), 1),
            "time_split_%": {k: round(100 * s[c].sum() / total, 1) for k, c in
                             [("prefill (TTFT)", "llm_ttft_s"), ("decode", "llm_generation_s"),
                              ("tools", "tool_s"), ("overhead", "overhead_s")]},
            "llm_calls": len(s),
            "prompt_tokens_mean": round(s["prompt_tokens"].mean(), 0),
            "prompt_tokens_max": int(s["prompt_tokens"].max()),
            "context_growth_tokens_per_step": round(float(np.polyfit(growth.index, growth.values, 1)[0]), 0)
            if len(growth) > 1 else None,
            "repeated_prefix_%_all_calls": round(100 * s["reusable_tokens"].sum() / s["prompt_tokens"].sum(), 1),
            "repeated_prefix_%_steps_ge1": round(100 * later["reusable_tokens"].sum()
                                                 / later["prompt_tokens"].sum(), 1),
            "cached_%_all_calls": round(100 * s["cached_tokens"].sum() / s["prompt_tokens"].sum(), 1)
            if s["cached_tokens"].notna().any() else None,
            "truncated_steps": int(s["truncated"].sum()),
        }
    return out


def _save(fig, out_dir: Path, name: str) -> None:
    fig.savefig(out_dir / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_time_breakdown(st: dict, out_dir: Path) -> None:
    runs = list(st)
    parts = ["prefill (TTFT)", "decode", "tools", "overhead"]
    fig, ax = plt.subplots(figsize=(6.4, 0.6 + 0.55 * len(runs)))
    for y, run in enumerate(runs):
        left = 0.0
        for i, part in enumerate(parts):
            w = st[run]["time_split_%"][part]
            ax.barh(y, w, left=left, height=0.5, color=SERIES[i], edgecolor=SURFACE, linewidth=2,
                    label=part if y == 0 else None)
            if w >= 7:
                ax.text(left + w / 2, y, f"{w:.0f}%", ha="center", va="center", color="white", fontsize=8)
            left += w
    ax.set_yticks(range(len(runs)), runs)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of total task time (%)")
    ax.grid(axis="y", visible=False)
    ax.invert_yaxis()
    ax.set_title("Where the time goes")
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.35 if len(runs) < 3 else -0.2), fontsize=8)
    _save(fig, out_dir, "time_breakdown")


def fig_context_growth(steps: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for i, (run, s) in enumerate(steps.groupby("run")):
        q = s.groupby("index")["prompt_tokens"].quantile([0.25, 0.5, 0.75]).unstack()
        n = s.groupby("index").size()
        q = q[n >= 5]
        ax.fill_between(q.index, q[0.25], q[0.75], color=SERIES[i], alpha=0.12, linewidth=0)
        ax.plot(q.index, q[0.5], color=SERIES[i], marker="o", markersize=4, label=run)
        ax.annotate(f"{q[0.5].iloc[-1]:,.0f}", (q.index[-1], q[0.5].iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", color=INK_2, fontsize=8)
    ax.set_xlabel("Step")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("Prompt tokens")
    ax.set_title("Context grows every step (median, band = 25th-75th percentile)")
    ax.legend(loc="upper left")
    ax.set_ylim(bottom=0)
    _save(fig, out_dir, "context_growth")


def fig_prefix_reuse(steps: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for i, (run, s) in enumerate(steps.groupby("run")):
        g = s.groupby("index")
        n = g.size()
        reuse = (100 * g["reusable_tokens"].sum() / g["prompt_tokens"].sum())[n >= 5]
        cached = (100 * g["cached_tokens"].sum() / g["prompt_tokens"].sum())[n >= 5]
        axes[0].plot(reuse.index, reuse.values, color=SERIES[i], marker="o", markersize=4, label=run)
        axes[1].plot(cached.index, cached.values, color=SERIES[i], marker="o", markersize=4, label=run)
    axes[0].set_title("Repeated prefix (could be cached)")
    axes[1].set_title("Actually served from the server cache")
    for ax in axes:
        ax.set_xlabel("Step")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("% of prompt tokens")
    axes[0].legend(loc="lower right")
    _save(fig, out_dir, "prefix_reuse")


def fig_latency_cdf(tasks: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for i, (run, t) in enumerate(tasks.groupby("run")):
        x = np.sort(t["total_s"].values)
        y = np.arange(1, len(x) + 1) / len(x)
        p50, p95 = np.percentile(x, 50), np.percentile(x, 95)
        ax.step(x, 100 * y, where="post", color=SERIES[i], label=f"{run}  (P50 {p50:.0f}s, P95 {p95:.0f}s)")
        ax.plot([p50, p95], [50, 95], "o", color=SERIES[i], markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xlabel("Task latency (s)")
    ax.set_ylabel("% of tasks")
    ax.set_ylim(0, 102)
    ax.set_xlim(left=0)
    ax.set_title("Task latency CDF")
    ax.legend(loc="lower right")
    _save(fig, out_dir, "latency_cdf")


def fig_steps(tasks: pd.DataFrame, out_dir: Path) -> None:
    runs = sorted(tasks["run"].unique())
    k = np.arange(1, int(tasks["n_steps"].max()) + 1)
    w = 0.8 / len(runs)
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    for i, run in enumerate(runs):
        counts = tasks[tasks["run"] == run]["n_steps"].value_counts().reindex(k, fill_value=0)
        pct = 100 * counts / counts.sum()
        ax.bar(k + (i - (len(runs) - 1) / 2) * w, pct.values, width=w * 0.9, color=SERIES[i], label=run)
    ax.set_xticks(k)
    ax.set_xlabel("Steps per task (8 = step limit reached)")
    ax.set_ylabel("% of tasks")
    ax.set_title("How many steps tasks take")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
    _save(fig, out_dir, "steps_distribution")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-analyze")
    p.add_argument("name", help="output folder name under results/figures/")
    p.add_argument("runs", type=Path, nargs="+", help="trace directories (one per workload)")
    args = p.parse_args()

    tasks, steps = load(args.runs)
    out_dir = ROOT / "results" / "figures" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    st = stats(tasks, steps)
    (out_dir / "stats.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
    fig_time_breakdown(st, out_dir)
    fig_context_growth(steps, out_dir)
    fig_prefix_reuse(steps, out_dir)
    fig_latency_cdf(tasks, out_dir)
    fig_steps(tasks, out_dir)
    print(json.dumps(st, indent=2))
    print(f"\nFigures and stats in {out_dir.relative_to(ROOT)}")
