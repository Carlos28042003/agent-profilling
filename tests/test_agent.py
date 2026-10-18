from agentic_profiling import agent
from agentic_profiling.agent import _common_prefix_len, run_task
from agentic_profiling.llm import LLMResult


class FakeLLM:
    """Returns scripted replies and records the prompts it receives."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.prompts: list[list[dict]] = []

    def chat(self, messages, stop=None):
        self.prompts.append([dict(m) for m in messages])
        return LLMResult(text=self.replies.pop(0), ttft_s=0.1, total_s=0.3,
                         prompt_tokens=100, completion_tokens=10, cached_tokens=None)


def _fake_search(monkeypatch):
    calls = []

    def search(q):
        calls.append(q)
        return f"result for {q}"

    monkeypatch.setitem(agent.TOOLS, "search", (search, "search: fake"))
    return calls


def test_common_prefix_len():
    assert _common_prefix_len("abcdef", "abcxyz") == 3
    assert _common_prefix_len("", "abc") == 0
    assert _common_prefix_len("abc", "abc") == 3


def test_tool_then_final_answer(monkeypatch):
    calls = _fake_search(monkeypatch)
    llm = FakeLLM([
        "Thought: look it up\nAction: search\nAction Input: Eiffel Tower",
        "Thought: done\nFinal Answer: 1889",
    ])
    trace = run_task(llm, "t1", "When was the Eiffel Tower completed?")

    assert trace.finished and trace.answer == "1889"
    assert trace.stop_reason == "final_answer"
    assert calls == ["Eiffel Tower"]
    assert [s.tool for s in trace.steps] == ["search", None]
    assert trace.steps[0].observation == "result for Eiffel Tower"


def test_history_is_append_only(monkeypatch):
    """Each step's prompt is an exact prefix of the next one (the basis of prefix caching)."""
    _fake_search(monkeypatch)
    llm = FakeLLM([
        "Thought: a\nAction: search\nAction Input: x",
        "Thought: b\nAction: search\nAction Input: y",
        "Final Answer: z",
    ])
    trace = run_task(llm, "t2", "q")

    p0, p1, p2 = llm.prompts
    assert p1[: len(p0)] == p0 and p2[: len(p1)] == p1
    s = trace.steps
    assert s[0].shared_prefix_chars == 0
    assert s[1].shared_prefix_chars == s[0].prompt_chars
    assert s[2].shared_prefix_chars == s[1].prompt_chars


def test_repeated_action_is_not_executed(monkeypatch):
    calls = _fake_search(monkeypatch)
    llm = FakeLLM([
        "Action: search\nAction Input: Nolan",
        "Action: search\nAction Input:  nolan ",
        "Final Answer: UK",
    ])
    trace = run_task(llm, "t3", "q")

    assert calls == ["Nolan"]
    assert "already ran this exact action" in trace.steps[1].observation


def test_unknown_tool_and_unparseable_reply(monkeypatch):
    _fake_search(monkeypatch)
    llm = FakeLLM([
        "Action: None\nAction Input: None",
        "I think the answer is 5",
        "Final Answer: 5",
    ])
    trace = run_task(llm, "t4", "q")

    assert "unknown tool" in trace.steps[0].observation
    assert "could not parse" in trace.steps[1].observation
    assert trace.answer == "5"


def test_max_steps(monkeypatch):
    _fake_search(monkeypatch)
    llm = FakeLLM([f"Action: search\nAction Input: q{i}" for i in range(3)])
    trace = run_task(llm, "t5", "q", max_steps=3)

    assert not trace.finished and trace.stop_reason == "max_steps"
    assert "Only one step left" in trace.steps[1].observation
