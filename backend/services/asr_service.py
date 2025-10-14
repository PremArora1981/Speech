"""ASR service integrating Sarvam streaming/batch transcription."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from backend.config.settings import settings

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


@dataclass
class TranscriptSegment:
    text: str
    start_ms: int
    end_ms: int
    confidence: float


@dataclass
class TranscriptResult:
    text: str
    language_code: str
    confidence: float
    segments: list[TranscriptSegment]


class ASRService:
    """Wrapper around Sarvam ASR API supporting batch and streaming."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.max_retries = max_retries

    async def transcribe(self, audio_url: str) -> TranscriptResult:
        payload = {
            "audio_url": audio_url,
            "language_detection": True,
            "output_format": "segments",
        }
        data = await self._request_with_retry("/speech-to-text", payload)
        segments = [
            TranscriptSegment(
                text=seg.get("text", ""),
                start_ms=int(seg.get("start_ms", 0)),
                end_ms=int(seg.get("end_ms", 0)),
                confidence=float(seg.get("confidence", 0.0)),
            )
            for seg in data.get("segments", [])
        ]
        return TranscriptResult(
            text=data.get("text", ""),
            language_code=data.get("language_code", "en-IN"),
            confidence=float(data.get("confidence", 0.0)),
            segments=segments,
        )

    async def stream_transcribe(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptSegment]:
        headers = self._headers
        async with self.client.stream(
            "POST",
            "/speech-to-text/stream",
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
            data=self._chunked_content(audio_stream),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                yield TranscriptSegment(
                    text=data.get("text", ""),
                    start_ms=int(data.get("start_ms", 0)),
                    end_ms=int(data.get("end_ms", 0)),
                    confidence=float(data.get("confidence", 0.0)),
                )

    async def _request_with_retry(self, path: str, payload: dict) -> dict:
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(
                    path,
                    json=payload,
                    headers=self._headers,
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
        raise RuntimeError("ASR request failed after retries")

    @staticmethod
    async def _chunked_content(stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        async for chunk in stream:
            yield chunk

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "api-subscription-key": self.api_key,
        }

    async def close(self) -> None:
        await self.client.aclose()


