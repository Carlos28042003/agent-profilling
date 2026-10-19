import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from .llm import LLM
from .tools import make_tools

SYSTEM_PROMPT = """You are an agent that answers questions by reasoning step by step and using tools.

Available tools:
{tools}

Use EXACTLY this format, one action per turn:

Thought: <your reasoning about what to do next>
Action: <one of: {names}>
Action Input: <the input for the tool>

After each action you will receive an "Observation:" with the result. Repeat as needed.
When you know the answer, reply with:

Thought: <short reasoning>
Final Answer: <the answer, as short as possible>

The Final Answer must be only the answer itself, not a sentence: a name, a number, a date,
or "yes"/"no" for yes/no questions (e.g. "Final Answer: United Kingdom", "Final Answer: yes").

Never write "Action: None". If a search result is not relevant, rephrase the query
(e.g. search the person's name, then read their page).

Example:

Question: How old was the author of "1984" when the book was published?
Thought: I need the author of "1984" and his birth year.
Action: search
Action Input: Nineteen Eighty-Four
Observation: [Nineteen Eighty-Four] Nineteen Eighty-Four is a novel by the English writer George Orwell. It was published on 8 June 1949...
Thought: The author is George Orwell and it was published on 8 June 1949. I need his birth date.
Action: search
Action Input: George Orwell
Observation: [George Orwell] Eric Arthur Blair, better known by his pen name George Orwell, was an English novelist and essayist...
Thought: The introduction does not give his birth date. I will look it up on this page.
Action: lookup
Action Input: born
Observation: (Result 1/2 in [George Orwell]) Eric Arthur Blair was born on 25 June 1903 in Motihari, Bihar, India.
Thought: Born 25 June 1903, book published 8 June 1949, so he was 45 (his birthday had not yet come).
Action: python
Action Input:
from datetime import date
born, published = date(1903, 6, 25), date(1949, 6, 8)
age = published.year - born.year - ((published.month, published.day) < (born.month, born.day))
print(age)
Observation: 45
Thought: The answer is 45.
Final Answer: 45"""

ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(.*)", re.DOTALL)
FINAL_RE = re.compile(r"Final Answer:\s*(.*)", re.DOTALL)


@dataclass
class Step:
    index: int
    t_start: float
    llm_ttft_s: float
    llm_generation_s: float
    llm_total_s: float
    tool: str | None
    tool_input: str | None
    tool_s: float
    step_total_s: float
    prompt_tokens: int | None
    completion_tokens: int | None
    cached_tokens: int | None
    prompt_chars: int
    shared_prefix_chars: int
    output: str
    observation: str | None
    server_timings: dict | None = None


@dataclass
class Trace:
    task_id: str
    question: str
    answer: str | None = None
    finished: bool = False
    stop_reason: str = ""
    total_s: float = 0.0
    steps: list[Step] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _render(messages: list[dict]) -> str:
    return "".join(f"<{m['role']}>{m['content']}" for m in messages)


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def run_task(llm: LLM, task_id: str, question: str, max_steps: int = 8,
             on_step: Callable[[Step], None] | None = None, history_window: int | None = None,
             allowed_tools: list[str] | None = None) -> Trace:
    tools = make_tools()
    if allowed_tools:
        tools = {name: tools[name] for name in allowed_tools}
    system = SYSTEM_PROMPT.format(
        tools="\n".join(f"- {desc}" for _, desc in tools.values()),
        names=", ".join(tools),
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Question: {question}"},
    ]
    trace = Trace(task_id=task_id, question=question)
    prev_prompt = ""
    seen_actions: set[tuple[str, str]] = set()
    t_task = time.perf_counter()

    for i in range(max_steps):
        t_step = time.perf_counter()
        view = messages
        if history_window is not None and len(messages) > 2 + 2 * history_window:
            view = messages[:2] + messages[len(messages) - 2 * history_window:]
        prompt = _render(view)
        res = llm.chat(view, stop=["\nObservation:", "Observation:"])
        output = res.text.strip()
        messages.append({"role": "assistant", "content": output})

        tool = tool_input = observation = None
        tool_s = 0.0
        final = FINAL_RE.search(output)
        action = ACTION_RE.search(output)
        if action and not (final and final.start() < action.start()):
            tool, tool_input = action.group(1).lower(), action.group(2).strip()
            key = (tool, " ".join(tool_input.lower().split()))
            t_tool = time.perf_counter()
            if key in seen_actions:
                observation = ("You already ran this exact action and got the result above. "
                               "Use that information, try a different input, or give the Final Answer.")
            elif tool in tools:
                seen_actions.add(key)
                try:
                    observation = tools[tool][0](tool_input)
                except Exception as e:  # noqa: BLE001 — network/tool failures become observations
                    observation = f"Error: {type(e).__name__}: {e}"
            else:
                observation = f"Error: unknown tool {tool!r}. Use one of: {', '.join(tools)}."
            tool_s = time.perf_counter() - t_tool
            if i == max_steps - 2:
                observation += "\n(Only one step left: give your Final Answer now.)"
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        elif final:
            trace.answer = final.group(1).strip()
            trace.finished = True
            trace.stop_reason = "final_answer"
        else:
            observation = "Error: could not parse your reply. Use the Thought/Action/Action Input format or give a Final Answer."
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        trace.steps.append(Step(
            index=i,
            t_start=t_step - t_task,
            llm_ttft_s=res.ttft_s,
            llm_generation_s=res.generation_s,
            llm_total_s=res.total_s,
            tool=tool,
            tool_input=tool_input,
            tool_s=tool_s,
            step_total_s=time.perf_counter() - t_step,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            cached_tokens=res.cached_tokens,
            prompt_chars=len(prompt),
            shared_prefix_chars=_common_prefix_len(prev_prompt, prompt),
            output=output,
            observation=observation,
            server_timings=res.server_timings,
        ))
        if on_step is not None:
            on_step(trace.steps[-1])
        prev_prompt = prompt
        if trace.finished:
            break
    else:
        trace.stop_reason = "max_steps"

    trace.total_s = time.perf_counter() - t_task
    trace.messages = messages
    return trace
