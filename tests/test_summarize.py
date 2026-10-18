import json

from agentic_profiling.summarize import load_steps


def _step(i, chars, tokens):
    return {"index": i, "prompt_chars": chars, "prompt_tokens": tokens}


def test_detects_context_truncation(tmp_path):
    # Valores do code_1 (llama3.2:3b, contexto 4096): a partir do passo 5 o Ollama trunca.
    steps = [_step(3, 5864, 2591), _step(4, 7691, 3612), _step(5, 9517, 3768), _step(6, 11341, 3758)]
    trace = {"task_id": "code_1", "correct": False, "finished": False, "total_s": 1.0, "steps": steps}
    (tmp_path / "code_1.json").write_text(json.dumps(trace))

    _, df = load_steps(tmp_path)

    assert df["truncated"].tolist() == [False, False, True, True]


def test_density_change_is_not_truncation(tmp_path):
    # Valores reais do combo_1: o prompt passa de instruções a texto da Wikipedia
    # (tokens/carácter desce de 0.26 para 0.23), mas não houve truncagem.
    steps = [_step(0, 968, 248), _step(1, 2591, 584)]
    trace = {"task_id": "combo_1", "correct": True, "finished": True, "total_s": 1.0, "steps": steps}
    (tmp_path / "combo_1.json").write_text(json.dumps(trace))

    _, df = load_steps(tmp_path)

    assert not df["truncated"].any()
