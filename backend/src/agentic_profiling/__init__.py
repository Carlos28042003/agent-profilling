"""CLI: runs a task file and writes one JSON trace per task.

    agentic-profiling configs/ollama.yaml tasks/smoke.yaml
    agentic-profiling configs/ollama.yaml tasks/hotpotqa_100.yaml --out traces/week2/hotpotqa
    agentic-profiling configs/llamacpp.yaml tasks/gsm8k_100.yaml --concurrency 4

Tasks that already have a trace in the output directory are skipped, so an interrupted
run resumes where it stopped.
"""

import argparse
import json
import platform
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import yaml

from .agent import run_task
from .llm import LLM
from .metrics import grade

NETWORK_ERROR_RE = re.compile(r"Error: (ConnectionError|ConnectTimeout|ReadTimeout|Timeout|SSLError|ChunkedEncodingError)")


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def llm_from_config(cfg: dict) -> LLM:
    return LLM(base_url=cfg["base_url"], model=cfg["model"], api_key=cfg.get("api_key", "unused"),
               temperature=cfg.get("temperature", 0.0), max_tokens=cfg.get("max_tokens", 512),
               seed=cfg.get("seed", 0), extra_body=cfg.get("extra_body"))


def run_meta(cfg: dict, tasks_file: str, stamp: str, concurrency: int = 1) -> dict:
    return {
        "config": cfg,
        "tasks_file": tasks_file,
        "concurrency": concurrency,
        "started_utc": stamp,
        "git_commit": _git_commit(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "openai_version": version("openai"),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-profiling")
    p.add_argument("config", type=Path, help="YAML with server, model and parameters")
    p.add_argument("tasks", type=Path, help="YAML with the list of tasks")
    p.add_argument("--out", type=Path, help="trace directory (default: traces/<config>-<tasks>-<timestamp>)")
    p.add_argument("--limit", type=int, help="run only the first N tasks")
    p.add_argument("--concurrency", type=int, default=1, help="number of agents running in parallel")
    args = p.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    tasks = yaml.safe_load(args.tasks.read_text(encoding="utf-8"))[: args.limit]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or Path("traces") / f"{args.config.stem}-{args.tasks.stem}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    todo = [t for t in tasks if not (out / f"{t['id']}.json").exists()]
    if len(todo) < len(tasks):
        print(f"Resuming: {len(tasks) - len(todo)} of {len(tasks)} tasks already have traces in {out}")

    meta = run_meta(cfg, str(args.tasks), stamp, args.concurrency)
    (out / f"run_meta_{stamp}.json" if todo != tasks else out / "run_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8")

    lock = threading.Lock()
    done = {"n": len(tasks) - len(todo), "infra": 0}

    def run_one(task: dict) -> None:
        trace = run_task(llm_from_config(cfg), task["id"], task["question"],
                         max_steps=cfg.get("max_steps", 8), history_window=cfg.get("history_window"),
                         allowed_tools=task.get("tools"))
        if any(s.observation and NETWORK_ERROR_RE.match(s.observation) for s in trace.steps):
            # The environment failed, not the agent: do not save, so a resumed run retries the task.
            with lock:
                done["n"] += 1
                done["infra"] += 1
                print(f"[{done['n']:>3}/{len(tasks)}] [NET] {task['id']:<12} network error in a tool; "
                      "not saved, rerun to retry", flush=True)
            return
        g = grade(trace.answer, task.get("expected", []), task.get("metric", "contains"))
        record = {"meta": meta, "expected": task.get("expected"), "metric": task.get("metric", "contains"),
                  **{k: task[k] for k in ("type", "level") if k in task}, **g, **trace.to_dict()}
        (out / f"{task['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
        tools = [s.tool for s in trace.steps if s.tool]
        with lock:
            done["n"] += 1
            print(f"[{done['n']:>3}/{len(tasks)}] [{'OK ' if g['correct'] else 'ERR'}] {task['id']:<12} "
                  f"{len(trace.steps)} steps {trace.total_s:6.1f}s  tools={tools}  answer={trace.answer!r}",
                  flush=True)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(run_one, todo))
    wall = time.perf_counter() - t0

    saved = [out / f"{t['id']}.json" for t in tasks if (out / f"{t['id']}.json").exists()]
    results = [json.loads(f.read_text(encoding="utf-8")) for f in saved]
    n_ok = sum(r["correct"] for r in results)
    line = f"\n{n_ok}/{len(results)} correct"
    f1s = [r["f1"] for r in results if r.get("f1") is not None]
    if f1s:
        line += f" (EM {n_ok / len(results):.2f}, F1 {sum(f1s) / len(f1s):.2f})"
    if todo:
        line += f" — {len(todo)} tasks in {wall:.0f}s ({60 * len(todo) / wall:.1f} tasks/min)"
        summary = {"started_utc": stamp, "tasks_run": len(todo), "wall_s": round(wall, 2),
                   "tasks_per_min": round(60 * len(todo) / wall, 3), "concurrency": args.concurrency}
        (out / f"run_summary_{stamp}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{line} — traces in {out}")
    if done["infra"]:
        print(f"{done['infra']} tasks hit network errors and were not saved: run the same command again.")
