from __future__ import annotations

from reverseoracle.llm import LLMRequest, MockLLMProvider


def test_mock_llm_provider_records_requests():
    provider = MockLLMProvider("ok")
    request = LLMRequest(system_prompt="s", user_prompt="u")
    assert provider.call(request) == "ok"
    assert provider.requests[0].user_prompt == "u"
