"""Sarvam Text-to-Speech API client."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from backend.config.settings import settings


class SarvamTTSClient:
    """Client wrapper for the Sarvam AI Text-to-Speech API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.base_url = base_url or str(settings.sarvam_api_base)
        self._client = http_client or httpx.AsyncClient(base_url=self.base_url)

    async def convert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the Sarvam text-to-speech endpoint."""

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            "/text-to-speech", json=payload, headers=headers, timeout=15
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()


__all__ = ["SarvamTTSClient"]

