"""CLI: corre um conjunto de tarefas e grava um trace JSON por tarefa.

    agentic-profiling configs/ollama.yaml tasks/smoke.yaml
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import yaml

from .agent import run_task
from .llm import LLM


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def llm_from_config(cfg: dict) -> LLM:
    return LLM(base_url=cfg["base_url"], model=cfg["model"], api_key=cfg.get("api_key", "unused"),
               temperature=cfg.get("temperature", 0.0), max_tokens=cfg.get("max_tokens", 512),
               seed=cfg.get("seed", 0))


def run_meta(cfg: dict, tasks_file: str, stamp: str) -> dict:
    return {
        "config": cfg,
        "tasks_file": tasks_file,
        "started_utc": stamp,
        "git_commit": _git_commit(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "openai_version": version("openai"),
    }


def _check(answer: str | None, expected: list[str]) -> bool:
    """Acerto simples: alguma das respostas esperadas aparece na resposta (sem maiúsculas)."""
    if answer is None:
        return False
    a = answer.lower().replace(",", "")
    return any(e.lower().replace(",", "") in a for e in expected)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agentic-profiling")
    p.add_argument("config", type=Path, help="YAML com servidor/modelo/parâmetros")
    p.add_argument("tasks", type=Path, help="YAML com a lista de tarefas")
    p.add_argument("--out", type=Path, help="pasta dos traces (default: traces/<config>-<tasks>-<data>)")
    args = p.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    tasks = yaml.safe_load(args.tasks.read_text(encoding="utf-8"))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or Path("traces") / f"{args.config.stem}-{args.tasks.stem}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    llm = llm_from_config(cfg)
    meta = run_meta(cfg, str(args.tasks), stamp)
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    n_ok = 0
    for task in tasks:
        trace = run_task(llm, task["id"], task["question"], max_steps=cfg.get("max_steps", 8))
        ok = _check(trace.answer, task.get("expected", []))
        n_ok += ok
        record = {"meta": meta, "expected": task.get("expected"), "correct": ok, **trace.to_dict()}
        (out / f"{task['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
        tools = [s.tool for s in trace.steps if s.tool]
        print(f"[{'OK ' if ok else 'ERR'}] {task['id']:<12} {len(trace.steps)} passos "
              f"{trace.total_s:6.1f}s  ferramentas={tools}  resposta={trace.answer!r}")

    print(f"\n{n_ok}/{len(tasks)} corretas — traces em {out}")
