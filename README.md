# agentic-profiling

Profiling de workloads agênticos: onde vai o tempo num agente ReAct (LLM vs. ferramentas),
como o contexto cresce por passo e quanto do prompt é prefixo repetido, para avaliar
prefix caching (vLLM / SGLang) e otimizações de serving.

## Estrutura

```
src/agentic_profiling/
  agent.py   loop ReAct escrito à mão + registo por passo (Step / Trace)
  llm.py     cliente OpenAI-compatível com streaming: TTFT, geração, tokens, cached tokens
  tools.py   search (Wikipedia), calculator (AST validada + sympy), python (subprocesso com timeout)
configs/     servidor + modelo + parâmetros (seed, temperature, max_steps)
tasks/       conjuntos de tarefas (smoke.yaml = 5 tarefas de teste)
requirements/ base.txt (local), dev.txt, gpu.txt (vLLM/SGLang, só Linux + GPU)
traces/      saída: um JSON por tarefa + run_meta.json (ignorado pelo git)
```

## Instalar e correr

```bash
uv sync
ollama pull llama3.2:3b
uv run agentic-profiling configs/ollama.yaml tasks/smoke.yaml
```

Para vLLM/SGLang (máquina Linux com GPU): `pip install -r requirements/gpu.txt`, subir o
servidor e apontar `base_url` do config para `http://<host>:8000/v1`.

## O que cada trace regista (por passo)

`llm_ttft_s`, `llm_generation_s`, `tool`, `tool_s`, `step_total_s`, `prompt_tokens`,
`completion_tokens`, `cached_tokens` (se o servidor reportar), `prompt_chars`,
`shared_prefix_chars` (prefixo igual ao prompt do passo anterior), e a conversa completa
para re-tokenizar na análise. Cada execução guarda config, commit git e versões em `run_meta.json`.

## Limitações conhecidas

- A ferramenta `python` usa um subprocesso isolado com timeout, **não** um sandbox de segurança.
  Para SWE-bench, correr dentro de um container.
- Com `llama3.2:3b` (GPU de 4 GB) a acurácia é baixa e instável (3/5 nas tarefas de teste);
  os experimentos principais usam modelos 7-8B em GPU alugada.
