"""Pydantic models for Text-to-Speech operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator


class VoiceCapability(BaseModel):
    provider: Literal["sarvam", "elevenlabs"]
    voice_id: str
    display_name: str
    gender: Optional[Literal["male", "female", "neutral"]] = None
    languages: list[str]
    characteristics: Optional[list[str]] = None


class VoiceSelection(BaseModel):
    provider: Literal["sarvam", "elevenlabs"]
    voice_id: str


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language_code: str = Field(..., pattern=r"^[a-z]{2}-[A-Z]{2}$")
    optimization_level: Literal[
        "quality",
        "balanced_quality",
        "balanced",
        "balanced_speed",
        "speed",
    ] = "balanced"
    voice: VoiceSelection
    enable_preprocessing: bool = True
    pitch: Optional[float] = Field(None, ge=-1.0, le=1.0)
    pace: Optional[float] = Field(None, ge=0.3, le=3.0)
    loudness: Optional[float] = Field(None, ge=0.0, le=3.0)
    sample_rate_hz: Optional[int] = Field(None, ge=8000, le=48000)
    audio_codec: Optional[Literal[
        "mp3",
        "linear16",
        "mulaw",
        "alaw",
        "opus",
        "flac",
        "aac",
        "wav",
    ]] = None

    @field_validator("pace")
    @classmethod
    def normalize_pace(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        return round(value, 2)

    @field_validator("pitch", "loudness")
    @classmethod
    def normalize_audio_dimension(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is None:
            return value
        return round(value, 2)


class TTSMetadata(BaseModel):
    provider: Literal["sarvam", "elevenlabs"]
    voice_id: str
    language_code: str
    optimization_level: str
    sample_rate_hz: int
    audio_codec: str
    cached: bool = False
    latency_ms: Optional[int] = None
    request_id: Optional[str] = None
    fallback_from_provider: Optional[str] = None
    fallback_from_voice_id: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SynthesizeResponse(BaseModel):
    audio_b64: str
    mime_type: str
    metadata: TTSMetadata


