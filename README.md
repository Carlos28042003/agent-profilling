# agentic-profiling

**Where does the time go when an LLM agent runs, and how much of its work is repeated?**

This project profiles *agentic* LLM workloads (multi-step ReAct agents that interleave
model calls with tool calls) from a systems perspective. Every step of every task is
instrumented: time to first token, generation time, tool latency, prompt and output
tokens, and how much of each prompt is a prefix that the model has already processed.
These traces are then used to evaluate serving-side optimizations such as **prefix
caching**, under single-agent and concurrent multi-agent load.

> **Status:** Week 1 complete; Week 2 benchmarks (100 HotpotQA + 100 GSM8K tasks) running;
> analysis, serving comparison and web UI built. See the [roadmap](#roadmap).

The repository has two parts:

| Part | What it is | Tech |
|---|---|---|
| [`backend/`](backend/) | The agent and everything that runs the LLM: tools, instrumented client, benchmark runner, analysis, API server | Python 3.12, uv, FastAPI, Ollama / llama.cpp / vLLM |
| [`frontend/`](frontend/) | Results page and live "Ask the agent" UI | React 19, Tailwind CSS 4, Vite |

The frontend is built into [`docs/`](docs/), which GitHub Pages publishes and the backend
also serves locally.

---

## Table of contents

- [Motivation](#motivation)
- [Research questions](#research-questions)
- [Preliminary observation](#preliminary-observation)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Backend commands](#backend-commands)
- [Frontend](#frontend)
- [Configuration](#configuration)
- [Task files](#task-files)
- [Trace format](#trace-format)
- [Running against llama.cpp / vLLM / SGLang](#running-against-llamacpp--vllm--sglang)
- [Tools](#tools)
- [Reproducibility](#reproducibility)
- [Hardware](#hardware)
- [Roadmap](#roadmap)
- [Known limitations](#known-limitations)

---

## Motivation

LLM serving systems are mostly designed and benchmarked for single-turn chat: one
prompt in, one answer out. Agents behave differently. A ReAct agent calls the model
many times per task, and each call re-sends the entire history (system prompt, question,
every previous thought, action and tool observation) plus a small new piece. The
model's work therefore grows with the number of steps, while most of every prompt is
identical to the previous one.

This makes agents a natural target for KV-cache reuse, but it also raises systems
questions that chat benchmarks do not answer: how much time is spent in the model vs.
in tools, how fast the context grows, how much prefix caching actually helps end-to-end
latency, and what happens when many agents share one GPU.

## Research questions

1. **Time breakdown:** what fraction of an agent task's latency is LLM prefill, LLM
   decode, tool execution and framework overhead?
2. **Context growth:** how does the prompt length grow per step, and how does this
   differ between workloads (multi-hop retrieval vs. math)?
3. **Prefix reuse:** what fraction of input tokens at each step is a repeated prefix
   from earlier steps?
4. **Serving impact:** how much does prefix caching reduce TTFT and per-task latency,
   and increase throughput, for these workloads?
5. **Concurrency:** how do latency and throughput scale with several concurrent agents,
   and what does shortening the context cost when it breaks the cached prefix?

## Preliminary observation

A sanity-check run (local Ollama, `llama3.2:3b`, GTX 1650) on one smoke-test task
(`combo_1`: *"How many years passed between the founding of Google and the founding
of Microsoft?"*, 6 steps) already shows the pattern this project studies:

| Step | TTFT (s) | Decode (s) | Tool (s) | Prompt tokens | Cached prompt tokens |
|-----:|---------:|-----------:|---------:|--------------:|---------------------:|
| 0 | 2.51 | 1.03 | 1.15 |   248 |   228 |
| 1 | 4.06 | 1.26 | 1.27 |   584 |   277 |
| 2 | 4.15 | 1.67 | 1.23 |   928 |   622 |
| 3 | 4.26 | 1.40 | 1.14 | 1,283 |   977 |
| 4 | 4.36 | 1.53 | 0.00 | 1,635 | 1,322 |
| 5 | 2.42 | 1.53 | 0.00 | 1,691 | 1,676 |

The prompt grows by roughly 350 tokens per step, and from step 1 onward more than
90% of each prompt is the previous step's prompt. Across the Week 1 smoke tests,
prefill (TTFT) takes about 60% of task time and decode about 25%. These are functional
checks on a small model, not final results.

## How it works

```mermaid
flowchart LR
    Q[Question] --> P[Build prompt<br/>system + history]
    P --> L[LLM call<br/>streamed, timed]
    L -->|Action| T[Run tool<br/>search / lookup / calculator / python]
    T -->|Observation appended| P
    L -->|Final Answer| A[Answer]
    L -. per-step record .-> R[(Trace JSON)]
    T -. per-step record .-> R
```

- **Hand-written ReAct loop** (`backend/src/agentic_profiling/agent.py`). No agent
  framework, so that every millisecond and every token can be attributed.
- **Append-only history.** Messages are only ever appended, never rewritten, so the
  prompt of step *N* is an exact prefix of the prompt of step *N+1*: the property that
  prefix caching exploits and that the traces measure.
- **Instrumented LLM client** (`llm.py`). OpenAI-compatible Chat Completions API with
  streaming: TTFT is the arrival of the first content chunk; token usage (including
  cached tokens) comes from the final chunk. Works with Ollama, llama.cpp, vLLM and
  SGLang by changing `base_url`.
- **Stop sequences** (`Observation:`) prevent the model from inventing tool results.

## Repository layout

```
agentic-profiling/
├── backend/                     Python: agent, LLM client, experiments, API server
│   ├── src/agentic_profiling/   agent.py, tools.py, llm.py, metrics.py, server.py, ...
│   ├── configs/                 server + model + sampling parameters (Ollama, llama.cpp)
│   ├── tasks/                   smoke.yaml, hotpotqa_100.yaml, gsm8k_100.yaml
│   ├── results/                 exported experiments (JSON) + figures, tracked by git
│   ├── traces/                  raw traces, local only (git-ignored)
│   ├── scripts/                 serve_llamacpp.ps1
│   ├── tests/                   pytest suite
│   ├── requirements/            readable dependency lists (+ GPU servers)
│   └── pyproject.toml, uv.lock
├── frontend/                    React + Tailwind CSS (Vite)
│   ├── src/App.jsx              tabs: Results, Ask the agent, About
│   ├── src/pages/               Results.jsx, Ask.jsx, About.jsx
│   ├── src/components/          charts, tables, UI pieces
│   ├── src/data.json            experiment data, generated by `agentic-export`
│   └── package.json, vite.config.js
├── docs/                        built frontend (GitHub Pages), from `npm run build`
├── README.md                    this file
└── STATUS.md                    progress, results so far, known issues, next steps
```

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) 20+, and
[Ollama](https://ollama.com).

```bash
git clone https://github.com/Carlos28042003/agent-profilling.git
cd agent-profilling

# 1. Backend
cd backend
uv sync
ollama pull llama3.2:3b
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
uv run pytest
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml   # 5 smoke tasks

# 2. Frontend (once, and after every export)
cd ../frontend
npm install
npm run build                                                   # -> ../docs

# 3. Web UI with the live agent
cd ../backend
uv run agentic-ui                                               # http://localhost:8000
```

## Backend commands

Run inside `backend/`:

| Command | What it does |
|---|---|
| `uv run agentic-profiling <config> <tasks> [--out DIR] [--limit N] [--concurrency N]` | Run tasks and write one JSON trace per task. Resumable: tasks that already have a trace are skipped |
| `uv run agentic-tasks hotpotqa\|gsm8k --n 100` | Build a task file from a public benchmark (fixed seed) |
| `uv run agentic-summary <trace dirs...>` | Per-run table: accuracy, steps, time split, prefix reuse, truncated steps |
| `uv run agentic-analyze <name> <trace dirs...>` | Characterization figures + `stats.json` in `results/figures/<name>/` |
| `uv run agentic-compare <name> <trace dirs...>` | Serving comparison: TTFT, latency, throughput, prefill tokens, cache hit |
| `uv run agentic-export <name> <trace dirs...> --title ... --description ...` | Save `results/<name>.json` and rebuild `../frontend/src/data.json` |
| `uv run agentic-ui` | API server + built site on http://localhost:8000 |

Example output (a 6-task GSM8K pilot run):

```
[  4/6] [OK ] gsm8k_0079   3 steps   10.9s  tools=['calculator', 'calculator']  answer='70'
[  5/6] [OK ] gsm8k_0082   3 steps   10.7s  tools=['calculator', 'calculator']  answer='623'
...
5/6 correct — 6 tasks in 87s (4.1 tasks/min) — traces in traces/pilot/gsm8k
```

## Frontend

A React 19 + Tailwind CSS 4 app built with Vite, with three tabs:

- **Results:** key numbers, prompt-vs-cache chart for one task, time split (prefill /
  decode / tools / overhead), context growth, latency CDF, serving comparison and all
  runs. Everything comes from `src/data.json`.
- **Ask the agent** (needs the local backend): type any question, pick a model and watch
  the agent work live, step by step, with TTFT, tokens and cache hit per step.
- **About:** what the project measures and how to run it.

```bash
cd frontend
npm install
npm run dev        # development server with hot reload; /api is proxied to the backend on :8000
npm run build      # production build into ../docs
```

**Publishing:** `docs/` is committed. On GitHub: Settings → Pages → branch `main`,
folder `/docs`. On GitHub Pages the Ask tab shows "local only", because it needs Python
and Ollama.

**Adding results to the page:**

```bash
cd backend
uv run agentic-export <name> traces/<experiment>/* --title "Short title" --description "One paragraph"
cd ../frontend && npm run build
```

## Configuration

`backend/configs/*.yaml`:

| Key | Default | Meaning |
|-----|---------|---------|
| `base_url` | (required) | OpenAI-compatible endpoint: Ollama `http://localhost:11434/v1`, llama.cpp `http://localhost:8080/v1`, vLLM `http://localhost:8000/v1` |
| `model` | (required) | Model name as known by the server |
| `api_key` | `unused` | Only needed for hosted APIs |
| `temperature` | `0.0` | Sampling temperature |
| `seed` | `0` | Sampling seed passed to the server |
| `max_tokens` | `512` | Maximum output tokens per LLM call |
| `max_steps` | `8` | Maximum ReAct steps per task |
| `history_window` | none | Keep only the last N steps in the prompt (context truncation experiment) |
| `extra_body` | none | Server-specific request options, e.g. `{cache_prompt: false}` for llama.cpp |

## Task files

`backend/tasks/*.yaml` is a list of tasks:

```yaml
- id: hotpot_0115
  question: The Argentine PGA Championship record holder has won how many tournaments worldwide?
  expected: ['230']
  metric: hotpotqa                        # hotpotqa (EM/F1) | numeric | contains
  tools: [search, lookup, calculator]     # tools available for this task
```

`hotpotqa`: official normalized exact match and token F1. `numeric`: the last number in the
answer equals the expected number (GSM8K). `contains`: any expected string appears in the
answer (smoke tests).

## Trace format

One JSON file per task. Per-step fields:

| Field | Description |
|-------|-------------|
| `index`, `t_start` | Step number and start time (s since task start) |
| `llm_ttft_s` | Time to first token (≈ queueing + prefill) |
| `llm_generation_s` | Time from first token to end of stream (≈ decode) |
| `tool`, `tool_input`, `tool_s` | Tool called, its input and its latency |
| `step_total_s` | Whole step; `step_total_s − llm_total_s − tool_s` = overhead |
| `prompt_tokens`, `completion_tokens`, `cached_tokens` | Token usage reported by the server |
| `prompt_chars`, `shared_prefix_chars` | Prompt length and prefix shared with the previous step |
| `server_timings` | llama.cpp server-side timings (prefill/decode ms, cached tokens), when available |
| `output`, `observation` | Raw model output and tool result |

Each trace also stores the outcome (`answer`, `correct`, `em`, `f1`, `stop_reason`), the
full conversation (`messages`, for offline re-tokenization) and the run metadata (config,
git commit, versions).

## Running against llama.cpp / vLLM / SGLang

The agent code does not change: only `base_url` and `model` in the config.

**llama.cpp (Windows or Linux, any NVIDIA GPU).** Reuses Ollama's GGUF file; prompt caching
can be switched off per request, which makes a clean on/off comparison:

```powershell
cd backend
ollama stop llama3.2:3b-ctx8k            # free the GPU
.\scripts\serve_llamacpp.ps1             # or -Parallel 4 for 4 concurrent agents
uv run agentic-profiling configs/llamacpp.yaml         tasks/gsm8k_100.yaml --out traces/week4/cache-on
uv run agentic-profiling configs/llamacpp-nocache.yaml tasks/gsm8k_100.yaml --out traces/week4/cache-off
uv run agentic-compare week4 traces/week4/cache-on traces/week4/cache-off
```

**vLLM / SGLang (Linux, 24 GB GPU for 7-8B models).** Install each in its own virtual
environment (see `backend/requirements/gpu.txt` and `sglang.txt`):

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000                             # prefix caching on
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000 --no-enable-prefix-caching  # off
```

## Tools

| Tool | Input | Implementation |
|------|-------|----------------|
| `search` | Query (best: a name or title) | MediaWiki API: opens the best-matching page; returns its introduction and the titles of other matches |
| `lookup` | Keyword | Next sentence of the current page containing the keyword (as in the ReAct paper) |
| `calculator` | Arithmetic expression | Parsed with `ast` and checked against a whitelist, then evaluated with SymPy |
| `python` | Python code | Separate interpreter (`python -I -X utf8`) in a temporary directory, 10 s timeout |

HotpotQA tasks get `search`, `lookup` and `calculator`; GSM8K tasks get `calculator` and
`python`. Tool errors are returned to the agent as observations. Tasks that hit network
errors are not saved, so a resumed run retries them.

## Reproducibility

- Exact Python dependencies in `backend/uv.lock`; exact JavaScript dependencies in
  `frontend/package-lock.json`.
- `temperature: 0` and a fixed `seed`; task files built with a fixed seed.
- Every run stores its config, git commit, Python version, platform and client version.
- Full conversations are stored in each trace, so token-level metrics can be recomputed.

## Hardware

| Stage | Hardware |
|-------|----------|
| Development, benchmarks, characterization, llama.cpp experiments | Windows/Linux PC, 24 GB RAM, GTX 1650 (4 GB) |
| vLLM / SGLang measurements with 7-8B models (optional) | Rented 24 GB GPU (RTX 4090 / A5000 class) |

## Roadmap

- [x] **Week 1:** ReAct agent, tools, per-step instrumentation, trace format, smoke tests, run summary
- [ ] **Week 2:** HotpotQA and GSM8K, 100 tasks each, proper grading — *running*
- [ ] **Week 3:** Characterization: time breakdown, context growth, prefix reuse, latency CDF (tooling done)
- [ ] **Week 4:** Prefix caching on vs. off (llama.cpp; vLLM optional) (tooling done)
- [ ] **Week 5:** Concurrent agents and context truncation vs. cache reuse (tooling done)
- [ ] **Week 6:** 4-page report; README and results page with final numbers (frontend done)

## Known limitations

- **Small-model accuracy.** The 3B models used on a 4 GB GPU answer multi-hop questions
  poorly; the study focuses on systems behaviour (time, tokens, cache), not accuracy.
- **The `python` tool is not a security sandbox**: it isolates the interpreter and limits
  run time, which is enough for math tasks.
- **Ollama's default context (4096 tokens) silently truncates long agent histories**, which
  drops the cached prefix (TTFT rose 4.4× in one trace). The configs use `num_ctx 8192`
  and `agentic-summary` flags truncated steps.
- **Wikipedia search** uses full-text search, which handles natural-language queries
  poorly; `lookup` helps the agent find facts inside a page.
- **`cached_tokens` semantics differ between servers**, so prefix reuse is also computed
  from the token counts of consecutive steps.
