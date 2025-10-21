"""ElevenLabs Text-to-Speech API client."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from backend.config.settings import settings


class ElevenLabsTTSClient:
    """Client wrapper for ElevenLabs text-to-speech service."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key or settings.elevenlabs_api_key
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY must be configured to use ElevenLabs.")

        self.base_url = base_url or str(settings.elevenlabs_api_base)
        self._client = http_client or httpx.AsyncClient(base_url=self.base_url)

    async def convert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the ElevenLabs text-to-speech endpoint."""

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            "/v1/text-to-speech",
            json=payload,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    async def list_voices(self) -> Dict[str, Any]:
        """Fetch all available voices from ElevenLabs API.

        Returns both stock voices and user's custom/cloned voices.
        """
        headers = {
            "xi-api-key": self.api_key,
        }

        response = await self._client.get(
            "/v1/voices",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()


__all__ = ["ElevenLabsTTSClient"]

