"""ASR service integrating Sarvam streaming/batch transcription."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from backend.config.settings import settings
from backend.services.interrupt_manager import InterruptManager, InterruptibleOperation
from backend.services.cost_tracker import CostTracker

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
        interrupt_manager: Optional[InterruptManager] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.max_retries = max_retries
        self.interrupt_manager = interrupt_manager
        self.cost_tracker = cost_tracker

    async def transcribe(
        self,
        audio_url: str,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> TranscriptResult:
        """
        Transcribe audio with optional interrupt support.

        Args:
            audio_url: URL or path to audio file
            session_id: Optional session ID for interrupt tracking
            turn_id: Optional turn ID for interrupt tracking

        Returns:
            TranscriptResult with transcribed text

        Raises:
            InterruptedError: If operation is interrupted
        """
        payload = {
            "audio_url": audio_url,
            "language_detection": True,
            "output_format": "segments",
        }

        # Use interruptible operation if manager and IDs provided
        if self.interrupt_manager and session_id and turn_id:
            async with InterruptibleOperation(
                self.interrupt_manager, session_id, turn_id, "asr"
            ) as op:
                op.check_or_raise()  # Check before starting
                data = await self._request_with_retry(
                    "/speech-to-text", payload, session_id, turn_id
                )
        else:
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

        # Track cost if tracker is configured
        if self.cost_tracker and segments:
            # Calculate total audio duration from segments
            total_duration_ms = max((seg.end_ms for seg in segments), default=0)
            audio_seconds = total_duration_ms / 1000.0

            await self.cost_tracker.track_asr(
                provider="sarvam",
                audio_seconds=audio_seconds,
                session_id=session_id,
                turn_id=turn_id,
                metadata={
                    "language_code": data.get("language_code", "en-IN"),
                    "confidence": float(data.get("confidence", 0.0)),
                    "segments_count": len(segments),
                },
            )

        return TranscriptResult(
            text=data.get("text", ""),
            language_code=data.get("language_code", "en-IN"),
            confidence=float(data.get("confidence", 0.0)),
            segments=segments,
        )

    async def stream_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> AsyncIterator[TranscriptSegment]:
        """
        Stream transcribe audio with optional interrupt support.

        Args:
            audio_stream: Async iterator of audio chunks
            session_id: Optional session ID for interrupt tracking
            turn_id: Optional turn ID for interrupt tracking

        Yields:
            TranscriptSegment for each recognized segment

        Raises:
            InterruptedError: If operation is interrupted
        """
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
                # Check for interrupt on each segment
                if self.interrupt_manager and session_id and turn_id:
                    if self.interrupt_manager.is_interrupted(session_id, turn_id):
                        raise InterruptedError("ASR streaming interrupted")

                if not line:
                    continue
                data = json.loads(line)
                yield TranscriptSegment(
                    text=data.get("text", ""),
                    start_ms=int(data.get("start_ms", 0)),
                    end_ms=int(data.get("end_ms", 0)),
                    confidence=float(data.get("confidence", 0.0)),
                )

    async def _request_with_retry(
        self,
        path: str,
        payload: dict,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> dict:
        """Make HTTP request with retry logic and interrupt support."""
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            # Check for interrupt before each attempt
            if self.interrupt_manager and session_id and turn_id:
                if self.interrupt_manager.is_interrupted(session_id, turn_id):
                    raise InterruptedError("ASR request interrupted")

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


