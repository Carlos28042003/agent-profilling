"""Instrumented LLM client: measures TTFT, generation time and tokens of every call.

It uses the OpenAI-compatible API, so it works with Ollama, vLLM and SGLang
by changing only `base_url`.
"""

import time
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class LLMResult:
    text: str
    ttft_s: float          # time to first token
    total_s: float         # total call time
    prompt_tokens: int | None
    completion_tokens: int | None
    cached_tokens: int | None   # prompt tokens served from cache (if the server reports it)

    @property
    def generation_s(self) -> float:
        return self.total_s - self.ttft_s


class LLM:
    def __init__(self, base_url: str, model: str, api_key: str = "unused",
                 temperature: float = 0.0, max_tokens: int = 512, seed: int | None = 0):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed

    def chat(self, messages: list[dict], stop: list[str] | None = None) -> LLMResult:
        t0 = time.perf_counter()
        ttft = None
        parts: list[str] = []
        usage = None
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            seed=self.seed,
            stop=stop,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                parts.append(chunk.choices[0].delta.content)
        total = time.perf_counter() - t0

        details = getattr(usage, "prompt_tokens_details", None) if usage else None
        return LLMResult(
            text="".join(parts),
            ttft_s=ttft if ttft is not None else total,
            total_s=total,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            cached_tokens=getattr(details, "cached_tokens", None) if details else None,
        )
