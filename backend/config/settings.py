"""Application settings and configuration management."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Optional

from pydantic import AnyHttpUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class OptimizationConfig:
    """Configuration for a specific optimization level."""

    level: str
    target_latency_ms: tuple[int, int]  # (min, max)
    expected_accuracy: float
    streaming_enabled: bool
    streaming_confidence_threshold: float
    speculation_enabled: bool
    speculation_word_threshold: int
    parallel_execution: bool
    rag_top_k: int
    llm_temperature: float
    response_max_tokens: Optional[int]
    enable_shortcuts: bool


# Optimization level configurations based on Requirements_v2.txt
OPTIMIZATION_CONFIGS = {
    "quality": OptimizationConfig(
        level="quality",
        target_latency_ms=(3000, 4000),
        expected_accuracy=0.98,
        streaming_enabled=False,
        streaming_confidence_threshold=1.0,
        speculation_enabled=False,
        speculation_word_threshold=999,
        parallel_execution=False,
        rag_top_k=10,
        llm_temperature=0.3,
        response_max_tokens=None,
        enable_shortcuts=False,
    ),
    "balanced_quality": OptimizationConfig(
        level="balanced_quality",
        target_latency_ms=(2000, 3000),
        expected_accuracy=0.95,
        streaming_enabled=False,
        streaming_confidence_threshold=1.0,
        speculation_enabled=False,
        speculation_word_threshold=999,
        parallel_execution=True,
        rag_top_k=5,
        llm_temperature=0.5,
        response_max_tokens=None,
        enable_shortcuts=False,
    ),
    "balanced": OptimizationConfig(
        level="balanced",
        target_latency_ms=(1500, 2000),
        expected_accuracy=0.90,
        streaming_enabled=True,
        streaming_confidence_threshold=0.80,
        speculation_enabled=True,
        speculation_word_threshold=5,
        parallel_execution=True,
        rag_top_k=3,
        llm_temperature=0.7,
        response_max_tokens=None,
        enable_shortcuts=False,
    ),
    "balanced_speed": OptimizationConfig(
        level="balanced_speed",
        target_latency_ms=(1000, 1500),
        expected_accuracy=0.85,
        streaming_enabled=True,
        streaming_confidence_threshold=0.60,
        speculation_enabled=True,
        speculation_word_threshold=3,
        parallel_execution=True,
        rag_top_k=2,
        llm_temperature=0.8,
        response_max_tokens=None,
        enable_shortcuts=True,
    ),
    "speed": OptimizationConfig(
        level="speed",
        target_latency_ms=(700, 1000),
        expected_accuracy=0.75,
        streaming_enabled=True,
        streaming_confidence_threshold=0.40,
        speculation_enabled=True,
        speculation_word_threshold=2,
        parallel_execution=True,
        rag_top_k=0,  # Skip RAG
        llm_temperature=0.9,
        response_max_tokens=50,  # Truncate for speed
        enable_shortcuts=True,
    ),
}


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development", validation_alias="ENVIRONMENT"
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")

    sarvam_api_base: AnyHttpUrl = Field(
        default="https://api.sarvam.ai", validation_alias="SARVAM_API_BASE"
    )
    sarvam_api_key: str = Field(validation_alias="SARVAM_API_KEY")

    elevenlabs_api_base: Optional[AnyHttpUrl] = Field(
        default="https://api.elevenlabs.io",
        validation_alias="ELEVENLABS_API_BASE",
    )
    elevenlabs_api_key: Optional[str] = Field(
        default=None, validation_alias="ELEVENLABS_API_KEY"
    )

    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")
    cache_ttl_quality: int = Field(default=1800, validation_alias="TTS_CACHE_TTL_QUALITY")
    cache_ttl_balanced: int = Field(default=900, validation_alias="TTS_CACHE_TTL_BALANCED")
    cache_ttl_speed: int = Field(default=300, validation_alias="TTS_CACHE_TTL_SPEED")

    database_url: str = Field(
        default="sqlite:///./speech.db",
        validation_alias="DATABASE_URL",
    )
    weaviate_url: str = Field(
        default="http://localhost:8080",
        validation_alias="WEAVIATE_URL",
    )
    weaviate_api_key: Optional[str] = Field(default=None, validation_alias="WEAVIATE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
    )

    default_tts_provider: Literal["sarvam", "elevenlabs"] = Field(
        default="sarvam", validation_alias="DEFAULT_TTS_PROVIDER"
    )
    default_sample_rate: int = Field(
        default=22050, validation_alias="DEFAULT_TTS_SAMPLE_RATE"
    )
    default_audio_codec: Literal[
        "mp3",
        "linear16",
        "mulaw",
        "alaw",
        "opus",
        "flac",
        "aac",
        "wav",
    ] = Field(default="wav", validation_alias="DEFAULT_TTS_AUDIO_CODEC")

    quality_latency_level: Literal[
        "quality",
        "balanced_quality",
        "balanced",
        "balanced_speed",
        "speed",
    ] = Field(default="balanced", validation_alias="DEFAULT_OPTIMIZATION_LEVEL")

    livekit_project_url: Optional[AnyHttpUrl] = Field(
        default=None, validation_alias="LIVEKIT_PROJECT_URL"
    )
    livekit_api_key: Optional[str] = Field(
        default=None, validation_alias="LIVEKIT_API_KEY"
    )
    livekit_api_secret: Optional[str] = Field(
        default=None, validation_alias="LIVEKIT_API_SECRET"
    )

    encryption_key: Optional[str] = Field(
        default=None, validation_alias="ENCRYPTION_KEY",
        description="Base64 encoded 32-byte key for encrypting telephony secrets",
    )

    @field_validator("elevenlabs_api_key")
    @classmethod
    def validate_elevenlabs_credentials(
        cls, value: Optional[str], values: dict[str, object]
    ) -> Optional[str]:
        default_provider = values.data.get("default_tts_provider")
        if not value and default_provider == "elevenlabs":
            raise ValueError("ELEVENLABS_API_KEY must be set when using ElevenLabs.")
        return value


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()


def get_optimization_config(level: str) -> OptimizationConfig:
    """Get optimization configuration for a given level."""
    return OPTIMIZATION_CONFIGS.get(level, OPTIMIZATION_CONFIGS["balanced"])


__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "OptimizationConfig",
    "OPTIMIZATION_CONFIGS",
    "get_optimization_config",
]

