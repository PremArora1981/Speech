"""Tests for LLMService."""

import pytest

from backend.services.llm_service import (
    GuardrailViolation,
    GuardrailFlags,
    LLMService,
)


class MockLLMClient:
    def __init__(self, response_text="Hello", status=200):
        self.response_text = response_text
        self.status = status
        self.requests = []

    async def post(self, path, json=None, headers=None, timeout=None):
        self.requests.append(json)

        class MockResponse:
            def __init__(self, text, status):
                self.text = text
                self.status_code = status

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": self.text}},
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                }

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception("HTTP error")

        return MockResponse(self.response_text, self.status)

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_generate_blocks_keyword():
    service = LLMService(client=MockLLMClient())
    with pytest.raises(GuardrailViolation):
        await service.generate("Tell me medical advice")


@pytest.mark.asyncio
async def test_generate_includes_rag_context():
    async def fake_rag(query: str) -> str:
        return "Context"

    client = MockLLMClient()
    service = LLMService(client=client, rag_provider=fake_rag)

    result = await service.generate("Hello")

    payload = client.requests[-1]
    assert "Context" in payload["messages"][0]["content"]
    assert result.guardrail_flags.safe


@pytest.mark.asyncio
async def test_generate_post_guardrail_length():
    long_text = "word " * 160
    client = MockLLMClient(response_text=long_text)
    service = LLMService(client=client)

    result = await service.generate("Hello")
    assert not result.guardrail_flags.safe
    assert result.guardrail_flags.reason == "Response too long"

