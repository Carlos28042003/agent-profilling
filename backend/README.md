# agentic-profiling — backend

The Python side of the project: the ReAct agent, its tools, the instrumented LLM client,
the benchmark runner, the analysis scripts and the API server used by the web UI.
See the [main README](../README.md) for the project overview.

## Setup

```bash
uv sync                                   # Python 3.12 + exact versions from uv.lock
ollama pull llama3.2:3b
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
uv run pytest                             # automated tests
```

## Commands

| Command | What it does |
|---|---|
| `uv run agentic-profiling <config> <tasks> [--out DIR] [--limit N] [--concurrency N]` | Run tasks, write one JSON trace per task (resumable) |
| `uv run agentic-tasks hotpotqa\|gsm8k --n 100` | Build a task file from a public benchmark (fixed seed) |
| `uv run agentic-summary <trace dirs...>` | Table per run: accuracy, steps, time split, prefix reuse, truncation |
| `uv run agentic-analyze <name> <trace dirs...>` | Week 3 figures + `stats.json` in `results/figures/<name>/` |
| `uv run agentic-compare <name> <trace dirs...>` | Weeks 4-5: TTFT, latency, throughput, prefill, cache across setups |
| `uv run agentic-export <name> <trace dirs...> --title ... --description ...` | Save `results/<name>.json` and rebuild `../frontend/src/data.json` |
| `uv run agentic-ui` | API server + the built site (`../docs`) on http://localhost:8000 |

## Layout

```
src/agentic_profiling/
  agent.py       hand-written ReAct loop, per-step Step/Trace records
  tools.py       search + lookup (Wikipedia), calculator, python
  llm.py         streaming OpenAI-compatible client (TTFT, decode, tokens, cache)
  metrics.py     HotpotQA exact match / F1, numeric match
  benchmarks.py  agentic-tasks
  __init__.py    agentic-profiling (runner)
  summarize.py   agentic-summary
  analyze.py     agentic-analyze
  compare.py     agentic-compare
  export.py      agentic-export
  server.py      agentic-ui (FastAPI: /api/health, /api/ask streaming)
configs/         server + model + sampling parameters (Ollama, llama.cpp)
tasks/           task files (smoke tests, HotpotQA, GSM8K)
scripts/         serve_llamacpp.ps1 (llama.cpp server for Weeks 4-5)
requirements/    readable dependency lists; gpu.txt / sglang.txt for Linux GPU servers
results/         exported experiments (JSON) and figures — tracked by git
traces/          raw traces — local only (git-ignored)
tests/           pytest suite
```
