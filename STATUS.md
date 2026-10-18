# Project status

Last updated: 18 Oct 2026.
Goal: repository + 4-page report on profiling agentic LLM workloads, for the PhD
application (deadline 15 Dec 2026, submit by 10 Dec).

| Week | Topic | State |
|---|---|---|
| 1 | Agent, tools, instrumentation, smoke tests | ✅ Done |
| 2 | HotpotQA + GSM8K, 100 tasks each, proper grading | 🔄 Code done; benchmark **running** (HotpotQA resumed at 22/100, then GSM8K) |
| 3 | Characterization (time, context growth, prefix reuse, latency) | 🔄 Tooling done (`agentic-analyze`); waiting for Week 2 data |
| 4 | Prefix caching on vs. off | 🔄 Tooling done (llama.cpp installed, configs, `agentic-compare`); runs after Week 2 |
| 5 | Concurrent agents + context truncation | 🔄 Tooling done (`--concurrency`, `history_window`); runs after Week 4 |
| 6 | Report, README, results page | 🔄 **Frontend done** (React + Tailwind, separate project); report after the experiments |

---

## 1. Project structure

The project is split into two parts that talk over HTTP:

```
agentic-profiling/
├── backend/     Python: the agent, the LLM client, experiments, analysis, API server
├── frontend/    React + Tailwind CSS (Vite): results page and live "Ask the agent" UI
├── docs/        the built frontend (npm run build) — served by GitHub Pages and by the backend
├── README.md    project overview (for the professor / GitHub visitors)
└── STATUS.md    this file
```

| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Language | Python 3.12 | JavaScript (React 19) |
| Tooling | uv (`pyproject.toml`, `uv.lock`) | npm (`package.json`, `package-lock.json`), Vite 8, Tailwind 4 |
| Runs | the agent against Ollama / llama.cpp / vLLM; experiments; API on :8000 | in the browser; talks to `/api` on the backend |
| Produces | traces (`traces/`, local), results (`results/*.json`, figures) | the static site in `docs/` |
| Link between them | `agentic-export` writes `frontend/src/data.json` | `Results` reads `data.json`; `Ask` calls `/api/ask` |

---

## 2. How to run

All commands are for PowerShell on Windows (they also work in a Linux shell). Copy only
the commands, not the `PS C:\...>` prompt.

### First time (setup)

```powershell
# Backend
cd C:\dev\agentic-profiling\backend
uv sync                                       # creates backend\.venv with exact versions
ollama pull llama3.2:3b
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
ollama pull qwen2.5:3b                        # optional, for model comparisons
ollama create qwen2.5:3b-ctx8k -f configs/ollama/qwen2.5-ctx8k.Modelfile
uv run pytest                                 # expect: 22 passed

# Frontend
cd C:\dev\agentic-profiling\frontend
npm install
npm run build                                 # builds the site into ..\docs
```

If `uv` or `ollama` is not recognized, close and reopen the terminal (PATH).

### Use the web UI (results + ask the agent live)

```powershell
cd C:\dev\agentic-profiling\backend
uv run agentic-ui                             # opens http://localhost:8000
```

- **Results** tab: all exported experiments, charts and tables.
- **Ask the agent** tab: type a question, choose `ollama · llama3.2:3b-ctx8k`, click
  *Run agent*, and watch each step live. Each question is saved in `backend\traces\ask\`.
- Stop the server with `Ctrl+C`.
- Links can open a tab directly: `http://localhost:8000/#ask`. Add `?theme=light` or
  `?theme=dark` to force a theme.

### Develop the frontend (hot reload)

```powershell
# Terminal 1: backend API
cd C:\dev\agentic-profiling\backend
uv run agentic-ui --no-browser

# Terminal 2: frontend dev server (proxies /api to the backend)
cd C:\dev\agentic-profiling\frontend
npm run dev                                   # open the URL it prints (http://localhost:5173)
```

Edit files in `frontend\src\`; the browser updates on save. When done: `npm run build`.

### Run experiments (backend)

```powershell
cd C:\dev\agentic-profiling\backend

# 5 smoke tasks
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml

# Week 2 benchmarks (resumable: run the same command again to continue)
uv run agentic-profiling configs/ollama.yaml tasks/hotpotqa_100.yaml --out traces/week2/hotpotqa
uv run agentic-profiling configs/ollama.yaml tasks/gsm8k_100.yaml    --out traces/week2/gsm8k

# Summaries and figures
uv run agentic-summary traces/week2/hotpotqa traces/week2/gsm8k
uv run agentic-analyze week2 traces/week2/hotpotqa traces/week2/gsm8k   # -> results/figures/week2/
```

### Put new results on the page

```powershell
cd C:\dev\agentic-profiling\backend
uv run agentic-export week2 traces/week2/hotpotqa traces/week2/gsm8k --title "Week 2 · HotpotQA + GSM8K" --description "..."
cd ..\frontend
npm run build
```

### Publish

```powershell
cd C:\dev\agentic-profiling
git add -A
git commit -m "Describe the change"
git push
```

GitHub Pages (once): repository Settings → Pages → Branch `main`, folder `/docs`.
The site will be at `https://carlos28042003.github.io/agent-profilling/`.

---

## 3. Hardware and where each stage runs

PC: 24 GB RAM, GTX 1650 (4 GB VRAM, Turing sm_75, no bf16).

| Work | Where |
|---|---|
| Weeks 1-3 with Ollama (`llama3.2:3b`, fits on the GPU) | This PC |
| Weeks 4-5 with llama.cpp (same model file as Ollama) | This PC (stop Ollama's model first: `ollama stop llama3.2:3b-ctx8k`) |
| vLLM / SGLang with 7-8B models (optional extension) | Rented 24 GB GPU (~$0.3-0.7/h) |

llama.cpp build b11719 (CUDA 12.4) is installed in `C:\Users\carlo\tools\llama.cpp-b11719`.

---

## 4. Done

### Backend

| Item | File | Status |
|---|---|---|
| Hand-written ReAct loop (append-only history) | `agent.py` | ✅ |
| Tools: `search` (opens a Wikipedia page), `lookup` (sentence in that page, as in the ReAct paper), `calculator` (validated AST + SymPy), `python` (isolated subprocess, 10 s timeout) | `tools.py` | ✅ |
| Per-benchmark tool sets (HotpotQA: search/lookup/calculator; GSM8K: calculator/python) | `benchmarks.py`, `agent.py` | ✅ |
| Streaming LLM client: TTFT, generation, tokens, cached tokens; llama.cpp server timings; `extra_body` | `llm.py` | ✅ |
| Runner: one trace per task, resumable, progress, throughput, `--limit`, `--concurrency` | `__init__.py` | ✅ |
| Network-error guard: tasks whose tools hit network errors are not saved (retried on resume); Wikipedia requests retry with backoff | `__init__.py`, `tools.py` | ✅ |
| Grading: HotpotQA exact match + F1 (official normalization), GSM8K numeric match | `metrics.py` | ✅ |
| Benchmarks: `tasks/hotpotqa_100.yaml` (81 bridge + 19 comparison, all "hard"), `tasks/gsm8k_100.yaml` (seed 0) | `benchmarks.py` | ✅ |
| Prompt: worked example (search → lookup → python), short-answer rule, repeated-action guard, last-step warning | `agent.py` | ✅ |
| 8192-token context for Ollama via Modelfiles; truncation detection in summaries | `configs/ollama/`, `summarize.py` | ✅ |
| Week 3 analysis: time split (prefill/decode/tools/overhead), context growth, token-level prefix reuse vs. cache, latency CDF, steps distribution | `analyze.py` | ✅ |
| Weeks 4-5 comparison: TTFT, latency, throughput, prefill tokens computed, cache hit | `compare.py` | ✅ |
| llama.cpp configs (cache on/off) and server script | `configs/llamacpp*.yaml`, `scripts/serve_llamacpp.ps1` | ✅ |
| Context truncation option (`history_window`) for Week 5 | `agent.py` | ✅ |
| Export to `results/*.json` and `frontend/src/data.json` | `export.py` | ✅ |
| API server: `/api/health`, `/api/ask` (live steps via Server-Sent Events), serves `docs/` | `server.py` | ✅ |
| Tests: 22 (tools, ReAct loop with a fake LLM, metrics, truncation detection) | `tests/` | ✅ |

### Frontend

| Item | File | Status |
|---|---|---|
| Separate React 19 + Tailwind CSS 4 project, built with Vite 8 (no CDNs) | `frontend/` | ✅ |
| Results tab: key numbers, prompt-vs-cache chart, time split, context growth, latency CDF, serving comparison, runs table | `pages/Results.jsx`, `components/` | ✅ |
| Ask tab: live agent with steps, timings, tokens, cache | `pages/Ask.jsx` | ✅ |
| About tab | `pages/About.jsx` | ✅ |
| Light/dark theme (validated palette), linkable tabs (`#ask`), phone width | `index.css`, `App.jsx` | ✅ |
| Build into `docs/` for GitHub Pages (`.nojekyll` included) | `vite.config.js`, `public/` | ✅ |

### Repository

| Item | Status |
|---|---|
| Clean split into `backend/` and `frontend/`; old single-file page replaced by the React build | ✅ |
| Everything in English | ✅ |
| README for the project (root) and for the backend (`backend/README.md`) | ✅ |
| GitHub `Carlos28042003/agent-profilling`, author Carlos Chirindza | ✅ |

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
   tokens from its cache. Even step 0 is ~77% cached, because every task shares the same
   system prompt and worked example.
4. **Context truncation destroys prefix caching**: past 4096 tokens Ollama cut the start of
   the conversation; cached tokens fell from 3,102 to 5 and TTFT rose 6.1 s → 26.8 s (4.4×).
5. **The worked example was the biggest accuracy fix** (`code_1` 0/6 → 6/6).
6. **`temperature 0` + `seed` does not give identical runs** on Ollama; report means.

---

## 6. Week 2 progress (running)

- HotpotQA: 22 of 100 tasks saved so far; the run resumes automatically.
- Accuracy on HotpotQA is low for a 3B model (most tasks reach the 8-step limit). This is
  expected — the original ReAct paper reports ~27-35% EM with a 540B model — and the
  study focuses on time, tokens and cache, not accuracy.
- GSM8K pilot (6 tasks): 5/6 correct, ~4 tasks/min.

---

## 7. Known issues

| # | Issue | Impact | What to do |
|---|---|---|---|
| 1 | `pip install vllm` fails on Windows | No vLLM locally | Use llama.cpp for Weeks 4-5 on this PC; vLLM only on a rented Linux GPU |
| 2 | 3B models: low accuracy on multi-hop questions | Accuracy numbers not representative | State it in the report; optional 7B run (`qwen2.5:7b`, partly in RAM, slower) |
| 3 | Wikipedia full-text search handles phrases poorly | Multi-hop failures | Mitigated by `lookup` and the "search a name" hint |
| 4 | The `python` tool is not a security sandbox | Risk with untrusted code | Fine for GSM8K; use a container before any code benchmark |
| 5 | **Internet outage during the Week 2 run**: 3 HotpotQA tasks only saw DNS errors | Those 3 results were invalid | **Resolved:** deleted and re-run; tasks with network errors are no longer saved |
| 6 | First Week 2 attempt: model answered in sentences ("Both bands are from the United States") | Exact match fails | **Resolved:** short-answer rule in the prompt; run restarted |
| 7 | `cached_tokens` means different things on different servers | Cross-server comparisons | Token-level reuse computed from consecutive steps; llama.cpp also reports `server_timings` |
| 8 | The GitHub repository name has a typo (`agent-profilling`) | Shows in the link sent to the professor | Rename in Settings to `agentic-profiling`, then `git remote set-url origin https://github.com/Carlos28042003/agentic-profiling.git` |
| 9 | PowerShell 5.1 `echo "..." >> file` writes UTF-16 | Corrupted files | Edit in VS Code, or `Add-Content -Encoding utf8` |
| 10 | Windows: `uv sync` fails while `agentic-profiling.exe` is running | — | Run `uv sync` with no run active |
| 11 | Raw traces only live on this PC (`backend/traces/` is git-ignored) | Detail lost if the disk fails | Summaries go to `backend/results/` (in git); before the report, keep a compressed copy of the final traces |
| 12 | After changing results, the site must be rebuilt | Page shows old numbers | `agentic-export ...` then `cd ../frontend && npm run build` |

Resolved earlier: Ollama's silent 4096-token truncation (Modelfiles with 8192), old author
email (history rewritten), missing tests (22 now), CDN-based page (now a Vite build).

---

## 8. Next steps

1. **Week 2** (running): finish HotpotQA and GSM8K; `agentic-summary`; export to the page.
2. **Week 3:** `agentic-analyze week2 ...`; pick the main conclusion ("X% of prefill work is
   repeated"); export figures for the report.
3. **Week 4:** stop Ollama's model, start llama.cpp (`scripts\serve_llamacpp.ps1`), run the
   same tasks with `configs/llamacpp.yaml` and `configs/llamacpp-nocache.yaml`,
   `agentic-compare week4 ...`. Send a short email to Prof. Zhao with the first results.
4. **Week 5:** llama.cpp with `-Parallel 1/2/4/8` and `--concurrency` to match; one run with
   `history_window: 2` to measure truncation vs. cache reuse and accuracy.
5. **Week 6:** 4-page report (PDF); final numbers in README and on the page; enable GitHub
   Pages; push.
6. **Weeks 7-8:** email Prof. Zhao, applications (ISE + CS at Indiana), submit by 10 Dec.
