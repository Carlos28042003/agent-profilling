# Project status

Last updated: 18 Oct 2026. **Week 1 complete** (infrastructure validated; accuracy limited
by the 3B models, see section 3). Weeks 2-8 to do.
Current work happens on Windows; Linux is used when needed (vLLM, Docker).
Goal: repository + 4-page report on profiling agentic workloads, for the PhD application
(deadline 15 Dec 2026, submit by 10 Dec).

---

## 1. Setting up the project (Linux or Windows)

```bash
# uv (Python and dependency manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Code
git clone https://github.com/Carlos28042003/agent-profilling.git agentic-profiling
cd agentic-profiling

# Environment (Python 3.12 + dependencies from uv.lock, including dev)
uv sync

# Local model for development
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
# Variants with an 8192-token context (Ollama's default, 4096, truncates the history)
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
ollama create qwen2.5:3b-ctx8k  -f configs/ollama/qwen2.5-ctx8k.Modelfile

# Automated tests (no model or network needed, except for the real tools)
uv run pytest

# Smoke test: 5 tasks, should end with "N/5 correct — traces in traces/..."
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml
```

### Available hardware and where each stage runs

Linux machine: 24 GB RAM, GTX 1650 (4 GB VRAM, Turing sm_75, no bf16), 256 GB SSD.

| Work | Where |
|---|---|
| Weeks 1-3 (agent, 100 tasks, analysis) with Ollama | Local |
| `llama3.2:3b` (fits on the GPU) / `qwen2.5:7b` (partly in RAM, slower) | Local |
| vLLM rehearsal with Qwen2.5-0.5B (`--dtype half --max-model-len 4096`) | Local, only to test the commands |
| vLLM/SGLang measurements with 7-8B models (Weeks 4-5) | Rented 24 GB GPU (RTX 4090/A5000, ~$0.3-0.7/h, ~15-30 h) |

Disk: remove unused models (`ollama rm`, `~/.cache/huggingface`).

---

## 2. Done

| Item | File | Status |
|---|---|---|
| Hand-written ReAct loop (append-only history) | `src/agentic_profiling/agent.py` | ✅ |
| `search` tool (Wikipedia API: summary + snippets) | `src/agentic_profiling/tools.py` | ✅ |
| `calculator` tool (validated AST + SymPy, no free `eval`) | `tools.py` | ✅ |
| `python` tool (`-I` subprocess, temporary directory, 10 s timeout) | `tools.py` | ✅ (not a sandbox) |
| Streaming LLM client: TTFT, generation time, tokens, cached tokens | `src/agentic_profiling/llm.py` | ✅ |
| CLI: one JSON trace per task + `run_meta.json` (config, commit, versions) | `src/agentic_profiling/__init__.py` | ✅ |
| Ollama config | `configs/ollama.yaml` | ✅ |
| 5 smoke tasks (search, calc, code, multi-hop, combined) | `tasks/smoke.yaml` | ✅ |
| Dependencies: `pyproject.toml` + `uv.lock`; readable copy in `requirements/` | — | ✅ |
| Repeated-action guard: the same action with the same input is not run again; the model gets a warning | `agent.py` | ✅ |
| "Only one step left" warning on the second-to-last step | `agent.py` | ✅ |
| Automated tests: 16 tests (tools, loop with a fake LLM, append-only history, repetition, `max_steps`, truncation detection) | `tests/` | ✅ |
| Run summary: accuracy, steps, % time LLM/tools/overhead, prefix reuse | `src/agentic_profiling/summarize.py` (`agentic-summary`) | ✅ |
| Config to compare models: `qwen2.5:3b` | `configs/ollama-qwen.yaml` | ✅ |
| 8192-token context via Modelfile (`llama3.2:3b-ctx8k`, `qwen2.5:3b-ctx8k`) | `configs/ollama/*.Modelfile` | ✅ |
| Context-truncation detection in the summary (`truncated_steps` column + warning) | `summarize.py`, `tests/test_summarize.py` | ✅ |
| Worked example (few-shot) in the system prompt, with multi-line Python code | `agent.py` | ✅ |
| `python` tool also strips single backticks around the code | `tools.py` | ✅ |
| **Results page (React + Tailwind, no build step)** with Results / Ask / About tabs; light/dark theme; tested at 375 px | `docs/index.html` | ✅ |
| **Local interface to ask the agent** and watch each step live (SSE); saves traces to `traces/ask/` | `server.py` (`agentic-ui`) | ✅ |
| **Export** of experiments to `results/<name>.json` + update of the page's `DATA` | `export.py` (`agentic-export`) | ✅ |
| Week 1 results exported (round A with truncation and final round C) | `results/week1-*.json` | ✅ |
| Detailed README in English (for Prof. Zhao) | `README.md` | ✅ |
| Everything in English: CLI output, code comments, configs, docs | — | ✅ |
| Git: `main` branch, `.gitignore`, `.gitattributes` (LF), GitHub `Carlos28042003/agent-profilling`, author Carlos Chirindza | — | ✅ |

### Fields recorded per step (trace)
`t_start`, `llm_ttft_s`, `llm_generation_s`, `llm_total_s`, `tool`, `tool_input`, `tool_s`,
`step_total_s`, `prompt_tokens`, `completion_tokens`, `cached_tokens`, `prompt_chars`,
`shared_prefix_chars`, `output`, `observation`. At the end: `messages` (full conversation,
for re-tokenization during analysis), `answer`, `correct`, `stop_reason`.

### First numbers (Windows, Ollama, llama3.2:3b, GTX 1650 4 GB)
Task `combo_1`, 6 steps:

| step | TTFT (s) | generation (s) | tool (s) | prompt tokens | cached tokens |
|---|---|---|---|---|---|
| 0 | 2.51 | 1.03 | 1.15 | 248 | 228 |
| 1 | 4.06 | 1.26 | 1.27 | 584 | 277 |
| 2 | 4.15 | 1.67 | 1.23 | 928 | 622 |
| 3 | 4.26 | 1.40 | 1.14 | 1283 | 977 |
| 4 | 4.36 | 1.53 | 0.00 | 1635 | 1322 |
| 5 | 2.42 | 1.53 | 0.00 | 1691 | 1676 |

The context grows ~350 tokens per step and, from step 1 on, > 90% of the prompt is the
previous step's prompt: this is the project's central hypothesis. These numbers are only a
functional check; the report's numbers come from the full benchmarks.

---

## 3. Week 1 tests

### How to run

```bash
uv run pytest                                   # 16 automated tests

for r in 1 2 3; do                              # 3 runs per model
  uv run agentic-profiling configs/ollama.yaml      tasks/smoke.yaml --out traces/week1/llama-run$r
  uv run agentic-profiling configs/ollama-qwen.yaml tasks/smoke.yaml --out traces/week1/qwen-run$r
done

uv run agentic-summary traces/week1/*           # comparison table
```

### Results

`pytest`: **16/16 pass**.

Three rounds, 3 runs × 2 models each (5 tasks, `temperature 0`, `seed 0`, GTX 1650).
Correct answers with the fixed grading ("London" does not count as a country):

| Round | Directory (local) | llama3.2:3b | qwen2.5:3b | Truncated steps |
|---|---|---|---|---|
| A. 4096 context (Ollama default) | `traces/week1-ctx4k` | 3, 4, 4 | 3, 2, 2 | up to 3 per run |
| B. 8192 context | `traces/week1-ctx8k` | 3, 3, 2 | 4, 2, 2 | 0 |
| C. 8192 context + worked example | `traces/week1` | **4, 3, 4** | 3, 3, 3 | 0 |

Round C (final), per run:

| | llama r1 | llama r2 | llama r3 | qwen r1 | qwen r2 | qwen r3 |
|---|---|---|---|---|---|---|
| Accuracy | 0.8 | 0.6 | 0.8 | 0.6 | 0.6 | 0.6 |
| Tasks finished | 100% | 100% | 100% | 100% | 100% | 100% |
| Steps (mean) | 4.0 | 5.0 | 4.2 | 4.2 | 4.2 | 4.0 |
| Time per task P50 (s) | 20.8 | 27.7 | 21.8 | 21.4 | 20.1 | 19.8 |
| Time in the LLM | 93% | 91% | 89% | 87% | 87% | 85% |
| Time in tools | 7% | 9% | 11% | 13% | 13% | 15% |
| Repeated prefix (steps ≥ 1) | 80% | 85% | 80% | 82% | 81% | 80% |
| Tokens served from cache (Ollama) | 85% | 89% | 85% | 88% | 86% | 86% |

Per task (round C): `search_1`, `calc_1` and `code_1` always succeed (6/6); `combo_1` 2/6;
`multihop_1` 0/6.

### Week 1 conclusions

1. **Infrastructure validated.** Every task finishes, no truncated steps, tokens and
   `cached_tokens` present in every step.
2. **Almost all the time is spent in the LLM** (85-93%); tools take 7-15% and the loop
   overhead is ~0%. On a small GPU the LLM dominates; on a faster rented GPU the tool share
   should rise — to be measured in Week 4.
3. **~80% of every prompt repeats the previous step**, and Ollama already serves ~85% of
   prompt tokens from its cache. This is the project's central hypothesis, confirmed at small scale.
4. **Context truncation destroys prefix caching** (round A, `code_1`, llama r1): when the
   prompt passed 4096 tokens, Ollama cut the start of the conversation; cached tokens fell
   from 3102 to 5, TTFT rose from 6.1 s to 26.8 s (**4.4×**), and the agent lost the
   question. Directly related to the Week 5 optimization (context truncation vs. cost).
5. **The worked example in the prompt (round C) was the biggest improvement:** `code_1` went
   from 0/6 to 6/6 and 100% of tasks finished (80% before). For llama the P50 time per task
   dropped from ~45 s to ~22 s (fewer steps); for qwen it stayed the same or got slightly
   worse (~17 s → ~20 s).
6. **The "≥ 4/5 in every run" criterion was not met** (best: llama 4, 3, 4). The remaining
   failures are reasoning errors of the 3B models: on multi-hop they drift to similar pages
   (Wally Pfister, "Christopher Nolan (author)", an Irish poet); on `combo_1` Qwen uses a
   wrong year (2010). Decision: accept Week 1 as complete and use a 7-8B model from Week 2
   on (issue #2).
7. **`temperature 0` + `seed` does not guarantee identical runs** on Ollama: the 3 runs of
   the same round give different answers. Always report means over several runs.

---

## 4. Known issues

| # | Issue | Impact | What to do |
|---|---|---|---|
| 1 | `pip install vllm` fails on Windows (long paths / not supported) | Blocked vLLM | **Resolved by moving vLLM to Linux.** Install in a separate venv (see `requirements/gpu.txt`) |
| 2 | Limited accuracy of the 3B models (best: 4, 3, 4 of 5); multi-hop always fails | Accuracy results are not very representative | **Mitigated** (repeated actions blocked, last-step warning, worked example). Weeks 2+: `qwen2.5:7b` in Ollama (partly in RAM) or 7-8B on a rented GPU |
| 3 | Wikipedia full-text search handles phrases poorly ("Christopher Nolan birthplace" returns Christopher Plummer); snippets of other results distract small models (Wally Pfister, Nolan the Irish poet) | Multi-hop failures | For HotpotQA: a `lookup[term]` tool inside the current page (as in the ReAct paper), and test without the extra snippets |
| 4 | The `python` tool is not a security sandbox | Risk with untrusted code | On Linux: run it with `docker run --rm --network none` before using SWE-bench |
| 5 | Answer checking is substring matching (`"23"` also matches `"2023"`). **It happened:** "London" graded an answer about Michael Caine as correct | Inflated accuracy | "London" removed from `smoke.yaml`. Week 2: normalized exact match (HotpotQA) and numeric comparison (GSM8K) |
| 6 | Ollama's `cached_tokens` ≠ vLLM's semantics | Cross-server comparisons | Also compute the repeated prefix offline, re-tokenizing `messages` with the model's tokenizer (`transformers`) |
| 7 | Servers without `stream_options.include_usage` return `prompt_tokens = null` | Missing tokens in the trace | Fallback: count with the tokenizer |
| 8 | ~~No automated tests~~ | — | **Resolved:** `tests/`, 16 tests |
| 9 | ~~Old author email~~ | — | **Resolved:** history rewritten, author `Carlos Chirindza <carlos.chirindza0@gmail.com>` |
| 10 | ~~No GitHub remote~~ | — | **Resolved:** `github.com/Carlos28042003/agent-profilling` |
| 11 | The GitHub repository name has a typo (`agent-profilling`, double "l") | Shows in the link sent to the professor | Rename in *Settings* to `agentic-profiling` and run `git remote set-url` |
| 12 | In PowerShell 5.1, `echo "..." >> file` writes UTF-16 (it broke the README once) | Corrupted files on GitHub | Edit in VS Code, or use `Add-Content -Encoding utf8` |
| 13 | On Windows, `uv sync` fails while `agentic-profiling.exe` is running (file locked) | — | Run `uv sync` only when no run is active |
| 14 | ~~Ollama truncates the context at 4096 tokens without warning~~ | Loses the question and the cache (TTFT 4.4×) | **Resolved:** Modelfiles with `num_ctx 8192` + automatic detection in `agentic-summary`. In vLLM: set `--max-model-len` |
| 15 | Full traces only live on the local computer (`traces/` is in `.gitignore`) | Detail is lost if the disk fails | **Partly resolved:** summaries go to `results/*.json` (in git) with `agentic-export`. Before the report: also keep the final traces, compressed |
| 16 | The page loads React, Babel and Tailwind from CDNs and compiles JSX in the browser | First load ~1-2 s slower; needs internet | Acceptable for a results page. If needed, migrate to Vite with a build step |
| 17 | The "Ask" tab was tested through the API (question → steps → answer "391" → trace saved) but not clicked in a real browser | A UI detail may need polishing | Test manually with `uv run agentic-ui` |

---

## 5. Remaining work (plan)

- **Week 2 (26 Oct-1 Nov):** dataset loader (`datasets`): HotpotQA (distractor/fullwiki)
  and GSM8K; tasks with a fixed seed; run 100 tasks; proper grading (issue #5); offline
  token counting (issue #6).
- **Week 3 (2-8 Nov):** analysis script (`pandas` + `matplotlib`): time breakdown LLM vs.
  tools vs. overhead, context growth per step, repeated-prefix fraction, step-count
  distribution, latency CDF (P50/P95). Main conclusion.
- **Week 4 (9-15 Nov):** vLLM with prefix caching on/off (on by default in vLLM V1; turn it
  off with `--no-enable-prefix-caching`). Compare TTFT, per-task latency, throughput. SGLang
  if time allows. Send a short email to Prof. Zhao with the first results.
- **Week 5 (16-22 Nov):** 8/16/32 concurrent agents (async client) + one measured
  optimization (e.g. ordering requests for cache reuse, or context truncation vs. accuracy).
- **Week 6 (23-29 Nov):** 4-page report; README with results and one-command reproduction;
  **online results page**: `docs/index.html` already exists, just export each experiment
  with `agentic-export` and enable GitHub Pages (Settings → Pages → branch `main`, folder
  `/docs`). Put the link in the email and the CV.
- **Weeks 7-8:** email Prof. Zhao, applications (ISE + CS at Indiana), submit by 10 Dec.
- **Tip from the updated plan:** export each experiment's results to JSON early
  (`agentic-export`), so the Week 6 page is ready with no extra work.

---

## 6. Web interface and results page

```powershell
uv run agentic-ui                         # opens http://localhost:8000 (Results + Ask + About)
uv run agentic-export <name> traces/<dir>/* --title "..." --description "..."
```

- **Ask the agent:** type a question, pick the model and watch the agent work step by step
  (thought, tool, result, TTFT, tokens, cache). Works locally only.
- **Results:** reads the `DATA` object in `docs/index.html`, which `agentic-export`
  generates from `results/*.json`. Never edit `DATA` by hand.
- Adding `?theme=light` or `?theme=dark` to the address forces a theme.

## 7. Running with vLLM (Week 4)

```bash
# Terminal 1 — server (separate venv)
source ~/venvs/vllm/bin/activate
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000                             # prefix caching on
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000 --no-enable-prefix-caching  # off

# Terminal 2 — agent: create configs/vllm.yaml with
#   base_url: http://localhost:8000/v1
#   model: Qwen/Qwen2.5-7B-Instruct
uv run agentic-profiling configs/vllm.yaml tasks/smoke.yaml
```

The agent code does not change: only `base_url` and `model` in the config.
