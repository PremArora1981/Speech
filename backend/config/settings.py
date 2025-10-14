"""Application settings and configuration management."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import AnyHttpUrl, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

__all__ = ["Settings", "settings", "get_settings"]

