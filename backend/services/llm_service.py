"""LLM orchestration with guardrails and optional RAG context."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import httpx

from backend.config.settings import settings


DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class GuardrailViolation(Exception):
    """Raised when a guardrail blocks the request."""


@dataclass
class GuardrailFlags:
    safe: bool = True
    reason: Optional[str] = None
    post_checked: bool = False


@dataclass
class LLMResponse:
    text: str
    guardrail_flags: GuardrailFlags
    tokens: dict[str, int]


class LLMService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        rag_provider: Optional[Callable[[str], Awaitable[str]]] = None,
        blocked_keywords: Optional[list[str]] = None,
        max_output_tokens: int = 600,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.rag_provider = rag_provider
        self.blocked_keywords = blocked_keywords or ["medical advice", "how to make bomb"]
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries

    async def generate(
        self,
        transcript: str,
        rag_context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        self._pre_guardrail_check(transcript)

        if not rag_context and self.rag_provider:
            rag_context = await self.rag_provider(transcript)

        prompt = system_prompt or "You are a helpful AI assistant."
        if rag_context:
            prompt += f"\nKNOWLEDGE:\n{rag_context}"

        payload = {
            "model": "sarvam-m",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript},
            ],
            "temperature": 0.7,
            "max_tokens": self.max_output_tokens,
        }

        data = await self._request_with_retry(payload)
        choice = data["choices"][0]
        text = choice["message"]["content"]

        guardrail_flags = self._post_guardrail_check(text)
        return LLMResponse(
            text=text,
            guardrail_flags=guardrail_flags,
            tokens=data.get("usage") or {},
        )

    def _pre_guardrail_check(self, transcript: str) -> None:
        lowered = transcript.lower()
        for keyword in self.blocked_keywords:
            if keyword.lower() in lowered:
                raise GuardrailViolation(f"Blocked keyword detected: {keyword}")

    def _post_guardrail_check(self, text: str) -> GuardrailFlags:
        max_words = 150
        words = text.split()
        if len(words) > max_words:
            return GuardrailFlags(safe=False, reason="Response too long", post_checked=True)
        return GuardrailFlags(safe=True, post_checked=True)

    async def _request_with_retry(self, payload: dict) -> dict:
        headers = {
            "api-subscription-key": self.api_key,
        }
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(
                    "/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if attempt == self.max_retries or exc.response.status_code < 500:
                    raise
            except httpx.HTTPError:
                if attempt == self.max_retries:
                    raise
            await asyncio.sleep(delay)
            delay *= 2
        raise RuntimeError("LLM request failed after retries")

    async def close(self) -> None:
        await self.client.aclose()


