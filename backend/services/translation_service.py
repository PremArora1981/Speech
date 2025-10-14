"""Translation service with colloquial and code-mixing support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.config.settings import settings

DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


@dataclass
class TranslationConfig:
    colloquial: bool = False
    formality_level: int = 50
    code_mixing_enabled: bool = False
    english_ratio: int = 30


class TranslationService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.max_retries = max_retries

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        config: Optional[TranslationConfig] = None,
    ) -> str:
        cfg = config or TranslationConfig()
        payload = {
            "text": text,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "colloquial": cfg.colloquial,
            "formality_level": cfg.formality_level,
            "code_mixing": cfg.code_mixing_enabled,
            "english_ratio": cfg.english_ratio,
        }
        data = await self._request_with_retry(payload)
        return data.get("translated_text", text)

    async def _request_with_retry(self, payload: dict) -> dict:
        headers = {"api-subscription-key": self.api_key}
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(
                    "/text/translate",
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
        raise RuntimeError("Translation request failed after retries")

    async def close(self) -> None:
        await self.client.aclose()


