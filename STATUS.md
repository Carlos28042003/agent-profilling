# Backend status

Last updated: 18 Oct 2026.
Goal: repository + 4-page report on profiling agentic LLM workloads, for the PhD
application (deadline 15 Dec 2026, submit by 10 Dec). The web UI has its own repository
and status file (`../frontend/STATUS.md`).

| Week | Topic | State |
|---|---|---|
| 1 | Agent, tools, instrumentation, smoke tests | ✅ Done |
| 2 | HotpotQA + GSM8K, 100 tasks each, proper grading | 🔄 Code done; benchmark **running** (HotpotQA resumed at 27/100, then GSM8K) |
| 3 | Characterization (time, context growth, prefix reuse, latency) | 🔄 Tooling done (`agentic-analyze`); waiting for Week 2 data |
| 4 | Prefix caching on vs. off | 🔄 Tooling done (llama.cpp installed, configs, `agentic-compare`); runs after Week 2 |
| 5 | Concurrent agents + context truncation | 🔄 Tooling done (`--concurrency`, `history_window`); runs after Week 4 |
| 6 | Report + final numbers | ⏳ After the experiments (the results page is in the frontend repository) |

---

## 1. Folder layout on this PC

```
C:\dev\agentic-profiling\
├── backend\     this repository (GitHub: Carlos28042003/agent-profilling)
└── frontend\    React + Tailwind repository (new GitHub repository)
```

The parent folder is not a Git repository; each subfolder has its own `.git`.

---

## 2. How to run

PowerShell; copy only the commands, not the `PS C:\...>` prompt.

### First time

```powershell
cd C:\dev\agentic-profiling\backend
uv sync                                       # creates .venv with exact versions
ollama pull llama3.2:3b
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
uv run pytest                                 # expect: 22 passed
```

If `uv` or `ollama` is not recognized, close and reopen the terminal.

### Web UI with the live agent

Build the frontend once (see `..\frontend\README.md`), then:

```powershell
cd C:\dev\agentic-profiling\backend
uv run agentic-ui                             # opens http://localhost:8000
```

It serves the API and the built site from `..\frontend\docs`. Stop it with `Ctrl+C`.

### Experiments

```powershell
cd C:\dev\agentic-profiling\backend

# 5 smoke tasks
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml

# Week 2 (resumable: run the same command again to continue)
uv run agentic-profiling configs/ollama.yaml tasks/hotpotqa_100.yaml --out traces/week2/hotpotqa
uv run agentic-profiling configs/ollama.yaml tasks/gsm8k_100.yaml    --out traces/week2/gsm8k

# Summaries and figures
uv run agentic-summary traces/week2/hotpotqa traces/week2/gsm8k
uv run agentic-analyze week2 traces/week2/hotpotqa traces/week2/gsm8k   # -> results/figures/week2/
```

### Send results to the frontend

```powershell
cd C:\dev\agentic-profiling\backend
uv run agentic-export week2 traces/week2/hotpotqa traces/week2/gsm8k --title "Week 2 · HotpotQA + GSM8K" --description "..."
cd ..\frontend
npm run sync-data
npm run build
```

### Publish

```powershell
cd C:\dev\agentic-profiling\backend
git add -A
git commit -m "Describe the change"
git push
```

---

## 3. Hardware

PC: 24 GB RAM, GTX 1650 (4 GB VRAM, Turing sm_75, no bf16).

| Work | Where |
|---|---|
| Weeks 1-3 with Ollama (`llama3.2:3b`, fits on the GPU) | This PC |
| Weeks 4-5 with llama.cpp (same model file as Ollama) | This PC (first `ollama stop llama3.2:3b-ctx8k`) |
| vLLM / SGLang with 7-8B models (optional extension) | Rented 24 GB GPU (~$0.3-0.7/h) |

llama.cpp build b11719 (CUDA 12.4) is installed in `C:\Users\carlo\tools\llama.cpp-b11719`.

---

## 4. Done

| Item | File | Status |
|---|---|---|
| Hand-written ReAct loop (append-only history) | `agent.py` | ✅ |
| Tools: `search` (opens a Wikipedia page), `lookup` (sentence in that page), `calculator` (validated AST + SymPy), `python` (isolated subprocess, 10 s timeout) | `tools.py` | ✅ |
| Per-benchmark tool sets (HotpotQA: search/lookup/calculator; GSM8K: calculator/python) | `benchmarks.py`, `agent.py` | ✅ |
| Streaming LLM client: TTFT, generation, tokens, cached tokens; llama.cpp server timings; `extra_body` | `llm.py` | ✅ |
| Runner: one trace per task, resumable, progress, throughput, `--limit`, `--concurrency` | `__init__.py` | ✅ |
| Network-error guard: tasks whose tools hit network errors are not saved (retried on resume); Wikipedia retries with backoff | `__init__.py`, `tools.py` | ✅ |
| Grading: HotpotQA exact match + F1 (official normalization), GSM8K numeric match | `metrics.py` | ✅ |
| Task files: `hotpotqa_100.yaml` (81 bridge + 19 comparison, all "hard"), `gsm8k_100.yaml` (seed 0) | `benchmarks.py` | ✅ |
| Prompt: worked example (search → lookup → python), short-answer rule, repeated-action guard, last-step warning | `agent.py` | ✅ |
| 8192-token context for Ollama (Modelfiles); truncation detection in summaries | `configs/ollama/`, `summarize.py` | ✅ |
| Characterization: time split, context growth, token-level prefix reuse vs. cache, latency CDF, steps | `analyze.py` | ✅ |
| Serving comparison: TTFT, latency, throughput, prefill tokens computed, cache hit | `compare.py` | ✅ |
| llama.cpp configs (cache on/off) and server script | `configs/llamacpp*.yaml`, `scripts/` | ✅ |
| Context truncation option (`history_window`) | `agent.py` | ✅ |
| Export: `results/<name>.json` + `results/data.json` for the frontend | `export.py` | ✅ |
| API: `/api/health`, `/api/ask` (Server-Sent Events); serves `../frontend/docs` (or `--site`) | `server.py` | ✅ |
| Tests: 22 (tools, ReAct loop with a fake LLM, metrics, truncation detection) | `tests/` | ✅ |
| Separate repositories: backend here, frontend in its own repository | — | ✅ |

---

## 5. Week 1 results (smoke tests)

Three rounds, 3 runs × 2 models each (5 tasks, `temperature 0`, `seed 0`, GTX 1650).
Correct answers:

| Round | llama3.2:3b | qwen2.5:3b | Truncated steps |
|---|---|---|---|
| A. 4096 context (Ollama default) | 3, 4, 4 | 3, 2, 2 | up to 3 per run |
| B. 8192 context | 3, 3, 2 | 4, 2, 2 | 0 |
| C. 8192 context + worked example | **4, 3, 4** | 3, 3, 3 | 0 |

Conclusions:

1. **Infrastructure validated**: every task finishes, tokens and cached tokens in every step.
2. **Prefill (TTFT) is ~60% of task time**, decode ~25%, tools 7-15%, loop overhead ~0%.
3. **~80-87% of every prompt repeats the previous step**; Ollama serves ~85% of prompt
   tokens from its cache. Even step 0 is ~77% cached: every task shares the same system
   prompt and worked example.
4. **Context truncation destroys prefix caching**: past 4096 tokens Ollama cut the start of
   the conversation; cached tokens fell from 3,102 to 5 and TTFT rose 6.1 s → 26.8 s (4.4×).
5. **The worked example was the biggest accuracy fix** (`code_1` 0/6 → 6/6).
6. **`temperature 0` + `seed` does not give identical runs** on Ollama; report means.

---

## 6. Week 2 progress (running)

- HotpotQA: 27 of 100 tasks saved; the run resumes automatically, then GSM8K starts.
- HotpotQA accuracy is low for a 3B model (most tasks reach the 8-step limit). Expected:
  the original ReAct paper reports ~27-35% EM with a 540B model. The study focuses on time,
  tokens and cache.
- GSM8K pilot (6 tasks): 5/6 correct, ~4 tasks/min.

---

## 7. Known issues

| # | Issue | Impact | What to do |
|---|---|---|---|
| 1 | `pip install vllm` fails on Windows | No vLLM locally | llama.cpp for Weeks 4-5 on this PC; vLLM only on a rented Linux GPU |
| 2 | 3B models: low accuracy on multi-hop questions | Accuracy not representative | State it in the report; optional 7B run (`qwen2.5:7b`, partly in RAM, slower) |
| 3 | Wikipedia full-text search handles phrases poorly | Multi-hop failures | Mitigated by `lookup` and the "search a name" hint |
| 4 | The `python` tool is not a security sandbox | Risk with untrusted code | Fine for GSM8K; use a container before any code benchmark |
| 5 | Internet outage during the Week 2 run (3 tasks saw only DNS errors) | Those results were invalid | **Resolved:** re-run; tasks with network errors are no longer saved |
| 6 | Model answered in sentences in the first Week 2 attempt | Exact match fails | **Resolved:** short-answer rule; run restarted |
| 7 | `cached_tokens` means different things on different servers | Cross-server comparisons | Token-level reuse from consecutive steps; llama.cpp also reports `server_timings` |
| 8 | The GitHub repository name has a typo (`agent-profilling`) | Shows in links | Rename in Settings, then `git remote set-url origin <new URL>` |
| 9 | PowerShell 5.1 `echo "..." >> file` writes UTF-16 | Corrupted files | Edit in VS Code, or `Add-Content -Encoding utf8` |
| 10 | Windows: `uv sync` fails while `agentic-profiling.exe` is running | — | Run `uv sync` with no run active |
| 11 | Raw traces only live on this PC (`traces/` is git-ignored) | Detail lost if the disk fails | Summaries are in `results/` (tracked); before the report, keep a compressed copy of the final traces |
| 12 | The VS Code window was opened on `C:\dev\agentic-profiling`, which is now a plain folder with two repositories | Source control panel may show both | Open `backend` or `frontend` as the workspace, or use a multi-root workspace |

Resolved earlier: Ollama's silent 4096-token truncation (Modelfiles with 8192), old author
email (history rewritten), missing tests (22 now).

---

## 8. Next steps

1. **Week 2** (running): finish HotpotQA and GSM8K; `agentic-summary`; export.
2. **Week 3:** `agentic-analyze week2 ...`; main conclusion ("X% of prefill work is
   repeated"); figures for the report.
3. **Week 4:** stop Ollama's model, start llama.cpp (`scripts\serve_llamacpp.ps1`), run the
   same tasks with `configs/llamacpp.yaml` and `configs/llamacpp-nocache.yaml`;
   `agentic-compare week4 ...`. Short email to Prof. Zhao with first results.
4. **Week 5:** llama.cpp with `-Parallel 1/2/4/8` and matching `--concurrency`; one run with
   `history_window: 2` (truncation vs. cache reuse and accuracy).
5. **Week 6:** 4-page report (PDF); final numbers in the README and on the results page.
6. **Weeks 7-8:** email Prof. Zhao, applications (ISE + CS at Indiana), submit by 10 Dec.
