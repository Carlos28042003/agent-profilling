# Estado do projeto — passagem para Linux

Última atualização: 18 out 2026 (fim da Semana 1 do plano de 8 semanas).
Objetivo: repositório + relatório de 4 páginas sobre profiling de workloads agênticos,
para a candidatura de PhD (prazo 15 dez 2026, submeter até 10 dez).

---

## 1. Montar o projeto no Linux

```bash
# uv (gestor de Python/dependências)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Código: a partir do bundle copiado do Windows (ou git clone, se já estiver no GitHub)
git clone agentic-profiling.bundle agentic-profiling
cd agentic-profiling
git remote remove origin          # o bundle fica como origin; trocar pelo GitHub depois

# Ambiente (Python 3.12 + dependências do uv.lock, incluindo dev)
uv sync

# Modelo local para desenvolvimento
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b

# Teste: 5 tarefas, deve terminar com "N/5 corretas — traces em traces/..."
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml
```

Verificar a GPU: `nvidia-smi`. Com >= 24 GB dá para correr vLLM com modelos 7-8B nesta
máquina; com menos, usar GPU alugada (RunPod / Vast.ai) para as Semanas 4-5.

---

## 2. O que está feito

| Item | Ficheiro | Estado |
|---|---|---|
| Loop ReAct escrito à mão (histórico só por append) | `src/agentic_profiling/agent.py` | ✅ |
| Ferramenta `search` (API da Wikipedia: resumo + excertos) | `src/agentic_profiling/tools.py` | ✅ |
| Ferramenta `calculator` (AST validada + sympy, sem `eval` livre) | `tools.py` | ✅ |
| Ferramenta `python` (subprocesso `-I`, pasta temporária, timeout 10 s) | `tools.py` | ✅ (não é sandbox) |
| Cliente LLM com streaming: TTFT, geração, tokens, cached tokens | `src/agentic_profiling/llm.py` | ✅ |
| CLI: um trace JSON por tarefa + `run_meta.json` (config, commit, versões) | `src/agentic_profiling/__init__.py` | ✅ |
| Config Ollama | `configs/ollama.yaml` | ✅ |
| 5 tarefas de teste (search, calc, code, multi-hop, combinação) | `tasks/smoke.yaml` | ✅ |
| Dependências: `pyproject.toml` + `uv.lock`; cópia legível em `requirements/` | — | ✅ |
| Git: branch `main`, `.gitignore`, `.gitattributes` (LF) | — | ✅ |

### Campos registados por passo (trace)
`t_start`, `llm_ttft_s`, `llm_generation_s`, `llm_total_s`, `tool`, `tool_input`, `tool_s`,
`step_total_s`, `prompt_tokens`, `completion_tokens`, `cached_tokens`, `prompt_chars`,
`shared_prefix_chars`, `output`, `observation`. No fim: `messages` (conversa completa,
para re-tokenizar na análise), `answer`, `correct`, `stop_reason`.

### Primeiros números (Windows, Ollama, llama3.2:3b, GTX 1650 4 GB)
Tarefa `combo_1`, 6 passos:

| passo | TTFT (s) | geração (s) | ferramenta (s) | prompt tokens | cached tokens |
|---|---|---|---|---|---|
| 0 | 2.51 | 1.03 | 1.15 | 248 | 228 |
| 1 | 4.06 | 1.26 | 1.27 | 584 | 277 |
| 2 | 4.15 | 1.67 | 1.23 | 928 | 622 |
| 3 | 4.26 | 1.40 | 1.14 | 1283 | 977 |
| 4 | 4.36 | 1.53 | 0.00 | 1635 | 1322 |
| 5 | 2.42 | 1.53 | 0.00 | 1691 | 1676 |

O contexto cresce ~350 tokens por passo e, a partir do passo 1, > 90 % do prompt é o
prompt do passo anterior: é a hipótese central do projeto. Estes números são só um
teste de funcionamento; os do relatório vêm do Linux/GPU.

---

## 3. Problemas conhecidos

| # | Problema | Impacto | O que fazer |
|---|---|---|---|
| 1 | `pip install vllm` falha no Windows (long paths / sem suporte) | Bloqueava o vLLM | **Resolvido com a mudança para Linux.** Instalar em venv separado (ver `requirements/gpu.txt`) |
| 2 | Acurácia instável com `llama3.2:3b`: 3/5 nas duas execuções, mas não sempre as mesmas tarefas | Modelo repete buscas até `max_steps=8` | Usar modelo 7-8B (ex.: `qwen2.5:7b` no Ollama, ou Qwen2.5-7B-Instruct no vLLM) |
| 3 | Busca de texto completo da Wikipedia é fraca com frases ("Christopher Nolan birthplace" devolve Christopher Plummer) | Falhas em multi-hop | Para HotpotQA, considerar ferramenta `lookup[termo]` dentro da página atual (como no paper ReAct) |
| 4 | Ferramenta `python` não é sandbox de segurança | Risco com código não confiável | No Linux: correr em `docker run --rm --network none` antes de usar SWE-bench |
| 5 | Verificação da resposta é por substring (`"23"` também acerta `"2023"`) | Acurácia pode ser inflacionada | Usar exact match normalizado (HotpotQA) e comparação numérica (GSM8K) |
| 6 | `cached_tokens` do Ollama ≠ semântica do vLLM | Comparações entre servidores | Calcular o prefixo repetido também offline, re-tokenizando `messages` com o tokenizer do modelo (`transformers`) |
| 7 | Servidores sem `stream_options.include_usage` devolvem `prompt_tokens = null` | Falta de tokens no trace | Fallback: contar com o tokenizer |
| 8 | Sem testes automáticos | — | Adicionar `tests/` para `calculator`, parsing ReAct e `_common_prefix_len` |
| 9 | Email do autor em `pyproject.toml` é `dticasadagloria@gmail.com` | Fica público no GitHub | Decidir antes de publicar |
| 10 | Repositório ainda sem remote no GitHub | — | Criar repo (pode começar privado) e `git push -u origin main` |

---

## 4. O que falta (plano)

- **Semana 2 (26 out-1 nov):** loader de datasets (`datasets`): HotpotQA (distractor/fullwiki)
  e GSM8K; tarefas com seed fixa; correr 100 tarefas; avaliação correta (problema #5);
  contagem de tokens offline (problema #6).
- **Semana 3 (2-8 nov):** script de análise (`pandas` + `matplotlib`): breakdown de tempo
  LLM vs. ferramenta vs. overhead, crescimento de contexto por passo, fração de prefixo
  repetido, distribuição de passos, CDF de latência (P50/P95). Conclusão principal.
- **Semana 4 (9-15 nov):** vLLM com `--enable-prefix-caching` ligado/desligado (no vLLM V1 vem
  ligado por omissão; desligar com `--no-enable-prefix-caching`). Comparar TTFT, latência por
  tarefa, throughput. SGLang se houver tempo. Mandar email curto ao Prof. Zhao com os primeiros resultados.
- **Semana 5 (16-22 nov):** 8/16/32 agentes concorrentes (cliente assíncrono) + uma otimização
  medida (ex.: ordenar pedidos para reuso de cache, ou truncar contexto vs. acurácia).
- **Semana 6-8:** relatório de 4 páginas, README com resultados e reprodução num comando,
  email e candidaturas (ISE + CS em Indiana), submeter até 10 dez.

---

## 5. Como correr com vLLM (Semana 4)

```bash
# Terminal 1 — servidor (venv separado)
source ~/venvs/vllm/bin/activate
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000                          # prefix caching ligado
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000 --no-enable-prefix-caching  # desligado

# Terminal 2 — agente: criar configs/vllm.yaml com
#   base_url: http://localhost:8000/v1
#   model: Qwen/Qwen2.5-7B-Instruct
uv run agentic-profiling configs/vllm.yaml tasks/smoke.yaml
```

O código do agente não muda: só o `base_url` e o `model` no config.
