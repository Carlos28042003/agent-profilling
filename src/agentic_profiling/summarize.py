"""Resumo de uma ou mais pastas de traces: acurácia, passos, tempo e prefixo repetido.

    agentic-summary traces/week1/llama-run1 traces/week1/llama-run2 ...
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def load_steps(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    tasks, steps = [], []
    for f in sorted(run_dir.glob("*.json")):
        if f.name == "run_meta.json":
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        tasks.append({"run": run_dir.name, "task_id": t["task_id"], "correct": t["correct"],
                      "finished": t["finished"], "n_steps": len(t["steps"]), "total_s": t["total_s"]})
        for s in t["steps"]:
            steps.append({"run": run_dir.name, "task_id": t["task_id"], **s})
    return pd.DataFrame(tasks), pd.DataFrame(steps)


def summarize(tasks: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    later = steps[steps["index"] > 0]  # o passo 0 não tem passo anterior para reaproveitar
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
        "prefix_reuse_%": 100 * later.groupby("run")["shared_prefix_chars"].sum()
        / later.groupby("run")["prompt_chars"].sum(),
        "cached_tok_%": 100 * later.groupby("run")["cached_tokens"].sum()
        / later.groupby("run")["prompt_tokens"].sum(),
    })
    return out.round(2)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-summary")
    p.add_argument("runs", type=Path, nargs="+", help="pastas de traces")
    args = p.parse_args()

    loaded = [load_steps(r) for r in args.runs]
    tasks = pd.concat([t for t, _ in loaded], ignore_index=True)
    steps = pd.concat([s for _, s in loaded], ignore_index=True)

    pd.set_option("display.width", 200)
    print(summarize(tasks, steps).to_string())
    print("\nAcertos por tarefa (todas as execuções):")
    print(tasks.pivot_table(index="task_id", columns="run", values="correct", aggfunc="first")
          .astype(int).to_string())
