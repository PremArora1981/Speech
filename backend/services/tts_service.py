"""Text-to-Speech orchestration service."""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from backend.clients import ElevenLabsTTSClient, SarvamTTSClient
from backend.config.settings import settings
from backend.schemas import SynthesizeRequest, SynthesizeResponse, TTSMetadata
from backend.services.interrupt_manager import InterruptManager, InterruptibleOperation
from backend.services.cost_tracker import CostTracker
from backend.utils import (
    TTSCache,
    VOICE_REGISTRY,
    VoiceEntry,
    VoiceRegistry,
    metrics,
)
from backend.utils.cache import CachedAudio


@dataclass
class TTSResponse:
    audio_b64: str
    request_id: Optional[str]
    latency_ms: int
    sample_rate_hz: Optional[int]


class TTSOrchestrator:
    """Coordinates text-to-speech synthesis across providers."""

    def __init__(
        self,
        sarvam_client: Optional[SarvamTTSClient] = None,
        elevenlabs_client: Optional[ElevenLabsTTSClient] = None,
        voice_registry: Optional[VoiceRegistry] = None,
        cache: Optional[TTSCache] = None,
        interrupt_manager: Optional[InterruptManager] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        self.sarvam_client = sarvam_client or SarvamTTSClient()
        self.elevenlabs_client = elevenlabs_client
        self.voice_registry = voice_registry or VOICE_REGISTRY
        self.cache = cache or (
            TTSCache(settings.redis_url) if settings.redis_url else None
        )
        self.interrupt_manager = interrupt_manager
        self.cost_tracker = cost_tracker

    async def synthesize(
        self,
        request: SynthesizeRequest,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> SynthesizeResponse:
        """
        Generate speech audio for the provided request.

        Args:
            request: TTS synthesis request
            session_id: Optional session ID for interrupt tracking
            turn_id: Optional turn ID for interrupt tracking

        Returns:
            SynthesizeResponse with audio and metadata

        Raises:
            InterruptedError: If operation is interrupted
        """
        # Use interruptible operation if manager and IDs provided
        if self.interrupt_manager and session_id and turn_id:
            async with InterruptibleOperation(
                self.interrupt_manager, session_id, turn_id, "tts"
            ) as op:
                return await self._synthesize_internal(request, session_id, turn_id, op)
        else:
            return await self._synthesize_internal(request, session_id, turn_id)

    async def _synthesize_internal(
        self,
        request: SynthesizeRequest,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        op: Optional[InterruptibleOperation] = None,
    ) -> SynthesizeResponse:
        """Internal synthesis logic with optional interrupt checking."""
        # Check for interrupt at the start
        if op:
            op.check_or_raise()

        voice_entry, provider, fallback_source = self._resolve_voice(request)

        cache_key = self._cache_key(request, voice_entry.voice_id)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                metrics["tts_requests_total"].labels(provider=provider, cache="hit").inc()
                metrics["tts_cache_hits_total"].labels(provider=provider).inc()
                metadata = TTSMetadata(
                    provider=provider,
                    voice_id=voice_entry.voice_id,
                    language_code=request.language_code,
                    optimization_level=request.optimization_level,
                    sample_rate_hz=cached.sample_rate_hz,
                    audio_codec=cached.codec,
                    cached=True,
                    fallback_from_provider=fallback_source[0],
                    fallback_from_voice_id=fallback_source[1],
                )
                return SynthesizeResponse(
                    audio_b64=cached.audio_b64,
                    mime_type=self._infer_mime_type(cached.codec),
                    metadata=metadata,
                )

        # Check for interrupt after cache check
        if op:
            op.check_or_raise()

        try:
            if provider == "elevenlabs":
                response, payload, codec = await self._synthesize_elevenlabs(
                    request, voice_entry, op
                )
            else:
                response, payload, codec = await self._synthesize_sarvam(
                    request, voice_entry, op
                )
        except Exception as exc:  # noqa: BLE001
            metrics["tts_failures_total"].labels(provider=provider, reason=exc.__class__.__name__).inc()
            # Fallback to Sarvam if ElevenLabs fails
            if provider != "sarvam":
                metrics["tts_fallback_total"].labels(from_provider=provider, to_provider="sarvam").inc()
                fallback_entry = self._find_fallback_voice(request.language_code)
                if fallback_entry:
                    response, payload, codec = await self._synthesize_sarvam(
                        request, fallback_entry, op
                    )
                    provider = "sarvam"
                    voice_entry = fallback_entry
                else:
                    raise
            else:
                raise

        metrics["tts_requests_total"].labels(provider=provider, cache="miss").inc()
        metrics["tts_latency_seconds"].labels(provider=provider).observe(
            response.latency_ms / 1000
        )

        metadata = TTSMetadata(
            provider=provider,
            voice_id=voice_entry.voice_id,
            language_code=request.language_code,
            optimization_level=request.optimization_level,
            sample_rate_hz=response.sample_rate_hz
            or payload.get("speech_sample_rate", settings.default_sample_rate),
            audio_codec=codec,
            cached=False,
            latency_ms=response.latency_ms,
            request_id=response.request_id,
            fallback_from_provider=fallback_source[0],
            fallback_from_voice_id=fallback_source[1],
        )

        if self.cache and not metadata.cached:
            await self.cache.set(
                cache_key,
                CachedAudio(
                    audio_b64=response.audio_b64,
                    codec=metadata.audio_codec,
                    sample_rate_hz=metadata.sample_rate_hz,
                ),
                ttl=self._ttl_for_level(request.optimization_level),
            )

        # Track cost if tracker is configured (only for non-cached responses)
        if self.cost_tracker and not metadata.cached:
            await self.cost_tracker.track_tts(
                provider=provider,
                characters=len(request.text),
                voice_id=voice_entry.voice_id,
                session_id=session_id,
                turn_id=turn_id,
                metadata={
                    "language_code": request.language_code,
                    "optimization_level": request.optimization_level,
                    "latency_ms": response.latency_ms,
                },
            )

        return SynthesizeResponse(
            audio_b64=response.audio_b64,
            mime_type=self._infer_mime_type(metadata.audio_codec),
            metadata=metadata,
        )

    async def _synthesize_sarvam(
        self,
        request: SynthesizeRequest,
        voice_entry: VoiceEntry,
        op: Optional[InterruptibleOperation] = None,
    ) -> Tuple["TTSResponse", Dict[str, Any], str]:
        """Synthesize with Sarvam with optional interrupt checking."""
        # Check for interrupt before API call
        if op:
            op.check_or_raise()

        payload = self._build_sarvam_payload(request, voice_entry.voice_id)
        start = time.perf_counter_ns()
        response = await self.sarvam_client.convert(payload)
        latency_ms = int((time.perf_counter_ns() - start) / 1_000_000)

        # Check for interrupt after API call
        if op:
            op.check_or_raise()

        audio_b64 = self._extract_audio(response)
        return TTSResponse(
            audio_b64=audio_b64,
            request_id=response.get("request_id"),
            latency_ms=latency_ms,
            sample_rate_hz=payload.get("speech_sample_rate"),
        ), payload, payload.get("output_audio_codec", settings.default_audio_codec)

    async def _synthesize_elevenlabs(
        self,
        request: SynthesizeRequest,
        voice_entry: VoiceEntry,
        op: Optional[InterruptibleOperation] = None,
    ) -> Tuple["TTSResponse", Dict[str, Any], str]:
        """Synthesize with ElevenLabs with optional interrupt checking."""
        # Check for interrupt before API call
        if op:
            op.check_or_raise()

        if not self.elevenlabs_client:
            self.elevenlabs_client = ElevenLabsTTSClient()

        payload = self._build_elevenlabs_payload(request, voice_entry.voice_id)
        start = time.perf_counter_ns()
        response = await self.elevenlabs_client.convert(payload)
        latency_ms = int((time.perf_counter_ns() - start) / 1_000_000)

        # Check for interrupt after API call
        if op:
            op.check_or_raise()

        # ElevenLabs returns base64 audio under the key "audio" in streaming responses,
        # but for synchronous generation we expect "audio" field in the response.
        audio_b64 = response.get("audio")
        if not audio_b64:
            raise ValueError("ElevenLabs response missing 'audio' field.")

        return TTSResponse(
            audio_b64=audio_b64,
            request_id=response.get("request_id"),
            latency_ms=latency_ms,
            sample_rate_hz=payload.get("sample_rate_hz"),
        ), payload, payload.get("output_format", settings.default_audio_codec)

    @staticmethod
    def _build_sarvam_payload(
        request: SynthesizeRequest, resolved_voice_id: str
    ) -> Dict[str, Any]:
        return {
            "text": request.text,
            "target_language_code": request.language_code,
            "speaker": resolved_voice_id,
            "pitch": request.pitch,
            "pace": request.pace,
            "loudness": request.loudness,
            "speech_sample_rate": request.sample_rate_hz
            or settings.default_sample_rate,
            "enable_preprocessing": request.enable_preprocessing,
            "model": "bulbul:v2",
            "output_audio_codec": request.audio_codec or settings.default_audio_codec,
        }

    @staticmethod
    def _build_elevenlabs_payload(
        request: SynthesizeRequest, resolved_voice_id: str
    ) -> Dict[str, Any]:
        return {
            "voice_id": resolved_voice_id,
            "text": request.text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.0,
                "use_speaker_boost": True,
            },
            "output_format": (
                request.audio_codec or settings.default_audio_codec
            ),
        }

    def _resolve_voice(
        self, request: SynthesizeRequest
    ) -> Tuple[VoiceEntry, str, Tuple[Optional[str], Optional[str]]]:
        entry = self.voice_registry.get(request.voice.provider, request.voice.voice_id)
        if entry and request.language_code in entry.languages:
            return entry, entry.provider, (None, None)

        fallback_entry = self._find_fallback_voice(request.language_code)
        if fallback_entry:
            return fallback_entry, fallback_entry.provider, (
                request.voice.provider,
                request.voice.voice_id,
            )

        raise ValueError(
            f"No available TTS voice for language {request.language_code}."
        )

    def _find_fallback_voice(self, language_code: str) -> Optional[VoiceEntry]:
        candidates = self.voice_registry.voices_for_language("sarvam", language_code)
        if candidates:
            return candidates[0]

        default_candidates = self.voice_registry.voices_for_language("sarvam", "en-IN")
        if default_candidates:
            return default_candidates[0]

        return None

    @staticmethod
    def _cache_key(request: SynthesizeRequest, resolved_voice_id: str) -> str:
        parts = [
            request.text,
            request.language_code,
            resolved_voice_id,
            request.audio_codec or settings.default_audio_codec,
            str(request.sample_rate_hz or settings.default_sample_rate),
        ]
        return "|".join(parts)

    @staticmethod
    def _ttl_for_level(level: str) -> int:
        mapping = {
            "quality": settings.cache_ttl_quality,
            "balanced_quality": settings.cache_ttl_quality,
            "balanced": settings.cache_ttl_balanced,
            "balanced_speed": settings.cache_ttl_speed,
            "speed": settings.cache_ttl_speed,
        }
        return mapping.get(level, settings.cache_ttl_balanced)

    @staticmethod
    def _extract_audio(response: Dict[str, Any]) -> str:
        audios = response.get("audios")
        if not audios:
            raise ValueError("Sarvam TTS response did not include audio data.")

        audio_data = audios[0]
        if not isinstance(audio_data, str):
            raise ValueError("Audio data must be a base64 encoded string.")

        # Validate base64 encoding
        try:
            base64.b64decode(audio_data, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid base64 audio data received.") from exc

        return audio_data

    @staticmethod
    def _infer_mime_type(codec: str) -> str:
        return {
            "mp3": "audio/mpeg",
            "linear16": "audio/L16",
            "mulaw": "audio/basic",
            "alaw": "audio/basic",
            "opus": "audio/opus",
            "flac": "audio/flac",
            "aac": "audio/aac",
            "wav": "audio/wav",
        }.get(codec, "audio/wav")


__all__ = ["TTSOrchestrator"]

