# Estado do projeto

Última atualização: 18 out 2026. **Semana 1 concluída** (infraestrutura validada; acurácia
limitada pelos modelos de 3B, ver secção 3). Semanas 2-8 por fazer.
Trabalho atual no Windows; o Linux fica para quando for preciso (vLLM, Docker).
Objetivo: repositório + relatório de 4 páginas sobre profiling de workloads agênticos,
para a candidatura de PhD (prazo 15 dez 2026, submeter até 10 dez).

---

## 1. Montar o projeto (Linux ou Windows)

```bash
# uv (gestor de Python/dependências)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Código
git clone https://github.com/Carlos28042003/agent-profilling.git agentic-profiling
cd agentic-profiling

# Ambiente (Python 3.12 + dependências do uv.lock, incluindo dev)
uv sync

# Modelo local para desenvolvimento
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
# Variantes com contexto de 8192 tokens (o padrão do Ollama, 4096, trunca o histórico)
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
ollama create qwen2.5:3b-ctx8k  -f configs/ollama/qwen2.5-ctx8k.Modelfile

# Testes automáticos (sem modelo nem rede, exceto as ferramentas reais)
uv run pytest

# Teste: 5 tarefas, deve terminar com "N/5 corretas — traces em traces/..."
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml
```

### Hardware disponível e onde corre cada coisa

Máquina Linux: 24 GB RAM, GTX 1650 (4 GB VRAM, Turing sm_75, sem bf16), SSD 256 GB.

| Trabalho | Onde |
|---|---|
| Semanas 1-3 (agente, 100 tarefas, análise) com Ollama | Linux local |
| `llama3.2:3b` (cabe na GPU) / `qwen2.5:7b` (parte em RAM, mais lento) | Linux local |
| Ensaio de vLLM com Qwen2.5-0.5B (`--dtype half --max-model-len 4096`) | Linux local, só para testar comandos |
| Medições vLLM/SGLang com 7-8B (Semanas 4-5) | GPU alugada 24 GB (RTX 4090/A5000, ~$0.3-0.7/h, ~15-30 h) |

Disco: limpar modelos não usados (`ollama rm`, `~/.cache/huggingface`).

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
| Proteção contra ações repetidas: a mesma ação com o mesmo input não volta a correr; o modelo recebe um aviso | `agent.py` | ✅ |
| Aviso "só falta um passo" no penúltimo passo | `agent.py` | ✅ |
| Testes automáticos: 14 testes (ferramentas, loop com LLM falso, histórico só por append, repetição, `max_steps`) | `tests/` | ✅ |
| Resumo de execuções: acurácia, passos, % tempo LLM/ferramenta/overhead, prefixo reaproveitado | `src/agentic_profiling/summarize.py` (`agentic-summary`) | ✅ |
| Config para comparar modelos: `qwen2.5:3b` | `configs/ollama-qwen.yaml` | ✅ |
| Contexto de 8192 tokens via Modelfile (`llama3.2:3b-ctx8k`, `qwen2.5:3b-ctx8k`) | `configs/ollama/*.Modelfile` | ✅ |
| Deteção de truncagem de contexto no resumo (coluna `truncated_steps` + aviso) | `summarize.py`, `tests/test_summarize.py` | ✅ |
| Exemplo resolvido (few-shot) no system prompt, com código Python em várias linhas | `agent.py` | ✅ |
| Ferramenta `python` remove também crases simples à volta do código | `tools.py` | ✅ |
| **Página de resultados (React + Tailwind, sem build)** com separadores Results / Ask / About; tema claro/escuro; testada a 375 px | `docs/index.html` | ✅ |
| **Interface local para perguntar ao agente** e ver cada passo ao vivo (SSE); grava traces em `traces/ask/` | `server.py` (`agentic-ui`) | ✅ |
| **Exportação** de experiências para `results/<nome>.json` + atualização do `DATA` da página | `export.py` (`agentic-export`) | ✅ |
| Resultados da Semana 1 exportados (ronda A com truncagem e ronda C final) | `results/week1-*.json` | ✅ |
| README em inglês e detalhado (para o Prof. Zhao) | `README.md` | ✅ |
| Git: branch `main`, `.gitignore`, `.gitattributes` (LF), GitHub `Carlos28042003/agent-profilling`, autor Carlos Chirindza | — | ✅ |

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

## 3. Testes da Semana 1

### Como correr

```bash
uv run pytest                                   # 16 testes automáticos

for r in 1 2 3; do                              # 3 execuções por modelo
  uv run agentic-profiling configs/ollama.yaml      tasks/smoke.yaml --out traces/week1/llama-run$r
  uv run agentic-profiling configs/ollama-qwen.yaml tasks/smoke.yaml --out traces/week1/qwen-run$r
done

uv run agentic-summary traces/week1/*           # tabela comparativa
```

### Resultados

`pytest`: **16/16 passam**.

Três rondas, 3 execuções × 2 modelos cada (5 tarefas, `temperature 0`, `seed 0`, GTX 1650).
Acertos com a avaliação corrigida ("London" não conta como país):

| Ronda | Pasta (local) | llama3.2:3b | qwen2.5:3b | Passos truncados |
|---|---|---|---|---|
| A. Contexto 4096 (padrão Ollama) | `traces/week1-ctx4k` | 3, 4, 4 | 3, 2, 2 | até 3 por execução |
| B. Contexto 8192 | `traces/week1-ctx8k` | 3, 3, 2 | 4, 2, 2 | 0 |
| C. Contexto 8192 + exemplo resolvido | `traces/week1` | **4, 3, 4** | 3, 3, 3 | 0 |

Ronda C (final), por execução:

| | llama r1 | llama r2 | llama r3 | qwen r1 | qwen r2 | qwen r3 |
|---|---|---|---|---|---|---|
| Acurácia | 0.8 | 0.6 | 0.8 | 0.6 | 0.6 | 0.6 |
| Tarefas terminadas | 100% | 100% | 100% | 100% | 100% | 100% |
| Passos (média) | 4.0 | 5.0 | 4.2 | 4.2 | 4.2 | 4.0 |
| Tempo por tarefa P50 (s) | 20.8 | 27.7 | 21.8 | 21.4 | 20.1 | 19.8 |
| Tempo no LLM | 93% | 91% | 89% | 87% | 87% | 85% |
| Tempo em ferramentas | 7% | 9% | 11% | 13% | 13% | 15% |
| Prefixo repetido (passos ≥ 1) | 80% | 85% | 80% | 82% | 81% | 80% |
| Tokens servidos do cache (Ollama) | 85% | 89% | 85% | 88% | 86% | 86% |

Por tarefa (ronda C): `search_1`, `calc_1` e `code_1` acertam sempre (6/6); `combo_1` 2/6;
`multihop_1` 0/6.

### Conclusões da Semana 1

1. **Infraestrutura validada.** Todas as tarefas terminam, nenhum passo truncado, tokens e
   `cached_tokens` presentes em todos os passos.
2. **O tempo é quase todo do LLM** (85-93 %); as ferramentas são 7-15 % e o overhead do
   loop é ~0 %. Numa GPU pequena o LLM domina; na GPU alugada (mais rápida) a fração
   das ferramentas deve subir — a medir na Semana 4.
3. **~80 % de cada prompt repete o passo anterior**, e o Ollama já serve ~85 % dos tokens
   do prompt a partir do cache. É a hipótese central do projeto, confirmada em pequena escala.
4. **Truncagem de contexto destrói o prefix caching** (ronda A, `code_1`, llama r1): quando o
   prompt passou os 4096 tokens, o Ollama cortou o início da conversa; os tokens em cache
   caíram de 3102 para 5 e o TTFT subiu de 6.1 s para 26.8 s (**4.4×**), e o agente perdeu a
   pergunta. Ligação direta à otimização da Semana 5 (truncar contexto vs. custo).
5. **O exemplo resolvido no prompt (ronda C) foi a maior melhoria:** `code_1` de 0/6 para 6/6
   e 100 % das tarefas terminadas (antes 80 %). No llama o tempo P50 por tarefa caiu de
   ~45 s para ~22 s (menos passos); no qwen ficou igual ou um pouco pior (~17 s → ~20 s).
6. **Critério "≥ 4/5 em todas as execuções" não foi atingido** (melhor: llama 4, 3, 4). As
   falhas restantes são de raciocínio dos modelos de 3B: no multi-hop desviam-se para
   páginas parecidas (Wally Pfister, "Christopher Nolan (author)", poeta irlandês); no
   `combo_1` o Qwen usa um ano errado (2010). Decisão: aceitar a Semana 1 como fechada e
   usar um modelo 7-8B nas Semanas 2+ (problema #2).
7. **`temperature 0` + `seed` não garante execuções iguais** no Ollama: as 3 execuções da
   mesma ronda dão respostas diferentes. Reportar sempre médias de várias execuções.

---

## 4. Problemas conhecidos

| # | Problema | Impacto | O que fazer |
|---|---|---|---|
| 1 | `pip install vllm` falha no Windows (long paths / sem suporte) | Bloqueava o vLLM | **Resolvido com a mudança para Linux.** Instalar em venv separado (ver `requirements/gpu.txt`) |
| 2 | Acurácia limitada dos modelos de 3B (melhor: 4, 3, 4 de 5); multi-hop falha sempre | Resultados de acurácia pouco representativos | **Mitigado** (repetição bloqueada, aviso de último passo, exemplo resolvido). Semanas 2+: `qwen2.5:7b` no Ollama (parte em RAM) ou 7-8B na GPU alugada |
| 3 | Busca de texto completo da Wikipedia é fraca com frases ("Christopher Nolan birthplace" devolve Christopher Plummer); os excertos dos outros resultados distraem os modelos pequenos (Wally Pfister, Nolan poeta irlandês) | Falhas em multi-hop | Para HotpotQA: ferramenta `lookup[termo]` dentro da página atual (como no paper ReAct) e testar sem os excertos extra |
| 4 | Ferramenta `python` não é sandbox de segurança | Risco com código não confiável | No Linux: correr em `docker run --rm --network none` antes de usar SWE-bench |
| 5 | Verificação da resposta é por substring (`"23"` também acerta `"2023"`). **Aconteceu:** "London" deu como certa uma resposta sobre o Michael Caine | Acurácia inflacionada | "London" removido do `smoke.yaml`. Semana 2: exact match normalizado (HotpotQA) e comparação numérica (GSM8K) |
| 6 | `cached_tokens` do Ollama ≠ semântica do vLLM | Comparações entre servidores | Calcular o prefixo repetido também offline, re-tokenizando `messages` com o tokenizer do modelo (`transformers`) |
| 7 | Servidores sem `stream_options.include_usage` devolvem `prompt_tokens = null` | Falta de tokens no trace | Fallback: contar com o tokenizer |
| 8 | ~~Sem testes automáticos~~ | — | **Resolvido:** `tests/`, 14 testes |
| 9 | ~~Email antigo do autor~~ | — | **Resolvido:** histórico reescrito, autor `Carlos Chirindza <carlos.chirindza0@gmail.com>` |
| 10 | ~~Sem remote no GitHub~~ | — | **Resolvido:** `github.com/Carlos28042003/agent-profilling` |
| 11 | Nome do repositório no GitHub tem um erro (`agent-profilling`, dois "l") | Aparece no link enviado ao professor | Renomear em *Settings* para `agentic-profiling` e `git remote set-url` |
| 12 | No PowerShell 5.1, `echo "..." >> ficheiro` escreve em UTF-16 (estragou o README uma vez) | Ficheiros corrompidos no GitHub | Editar no VS Code, ou `Add-Content -Encoding utf8` |
| 13 | No Windows, `uv sync` falha se o `agentic-profiling.exe` estiver a correr (ficheiro bloqueado) | — | Correr `uv sync` só sem execuções ativas |
| 14 | ~~Ollama trunca o contexto aos 4096 tokens sem avisar~~ | Perde a pergunta e o cache (TTFT 4.4×) | **Resolvido:** Modelfiles com `num_ctx 8192` + deteção automática no `agentic-summary`. No vLLM: definir `--max-model-len` |
| 15 | Os traces completos ficam só no computador local (`traces/` está no `.gitignore`) | Perde-se o detalhe se o disco falhar | **Em parte resolvido:** os resumos vão para `results/*.json` (no git) com `agentic-export`. Antes do relatório: guardar também os traces finais comprimidos |
| 16 | A página carrega React, Babel e Tailwind de CDNs e compila o JSX no browser | Primeira abertura ~1-2 s mais lenta; precisa de internet | Aceitável para uma página de resultados. Se for preciso, migrar para Vite com build |
| 17 | O separador "Ask" foi testado pela API (pergunta → passos → resposta "391" → trace gravado) mas não clicado num browser real | Pode haver um detalhe de interface por afinar | Testar manualmente com `uv run agentic-ui` |

---

## 5. O que falta (plano)

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
- **Semana 6 (23-29 nov):** relatório de 4 páginas; README com resultados e reprodução num
  comando; **página de resultados online**: `docs/index.html` já existe, basta exportar cada
  experiência com `agentic-export` e ativar o GitHub Pages (Settings → Pages → branch `main`,
  pasta `/docs`). Pôr o link no email e no CV.
- **Semanas 7-8:** email ao Prof. Zhao, candidaturas (ISE + CS em Indiana), submeter até 10 dez.
- **Dica do plano novo:** exportar os resultados de cada experiência para JSON desde cedo
  (`agentic-export`), para a página da Semana 6 ficar pronta sem trabalho extra.

---

## 6. Interface web e página de resultados

```powershell
uv run agentic-ui                         # abre http://localhost:8000 (Results + Ask + About)
uv run agentic-export <nome> traces/<pasta>/* --title "..." --description "..."
```

- **Ask the agent:** escrever uma pergunta, escolher o modelo e ver o agente trabalhar passo
  a passo (pensamento, ferramenta, resultado, TTFT, tokens, cache). Só funciona localmente.
- **Results:** lê o objeto `DATA` de `docs/index.html`, que o `agentic-export` gera a partir
  de `results/*.json`. Nunca editar o `DATA` à mão.
- `?theme=light` ou `?theme=dark` no fim do endereço força o tema.

## 7. Como correr com vLLM (Semana 4)

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
