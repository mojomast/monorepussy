from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

import httpx


@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    model: str = "gpt-4"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096


class MockLLMProvider:
    def __init__(self, response: str = "") -> None:
        self.response = response
        self.requests: list[LLMRequest] = []

    def call(self, request: LLMRequest) -> str:
        self.requests.append(request)
        return self.response


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = "gpt-4",
    base_url: str = "https://api.openai.com/v1",
    api_key_env: str = "OPENAI_API_KEY",
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> str:
    api_key = os.environ.get(api_key_env, "")
    request = LLMRequest(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _call_openai_compatible(request, timeout=timeout)


def _call_openai_compatible(request: LLMRequest, timeout: float = 60.0) -> str:
    headers = {"Content-Type": "application/json"}
    if request.api_key:
        headers["Authorization"] = f"Bearer {request.api_key}"
    payload = {
        "model": request.model,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{request.base_url}/chat/completions", json=payload, headers=headers
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    return data["choices"][0]["message"]["content"]
