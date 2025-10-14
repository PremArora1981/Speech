"""Simple caching utilities for TTS responses."""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Optional

try:
    import aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None


class CacheNotConfiguredError(RuntimeError):
    """Raised when cache operations are attempted without configuration."""


@dataclass(frozen=True)
class CachedAudio:
    audio_b64: str
    codec: str
    sample_rate_hz: int

    def encode(self) -> str:
        return json.dumps(
            {
                "audio": self.audio_b64,
                "codec": self.codec,
                "sample_rate_hz": self.sample_rate_hz,
            }
        )

    @staticmethod
    def decode(value: str) -> "CachedAudio":
        payload = json.loads(value)
        return CachedAudio(
            audio_b64=payload["audio"],
            codec=payload["codec"],
            sample_rate_hz=payload["sample_rate_hz"],
        )


class TTSCache:
    def __init__(self, redis_url: Optional[str] = None, default_ttl_seconds: int = 600) -> None:
        if redis_url and not aioredis:
            raise RuntimeError("aioredis must be installed for Redis caching support.")
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self._redis = None

    async def _redis_client(self):
        if not self.redis_url:
            raise CacheNotConfiguredError("Redis URL not configured.")
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url)  # type: ignore
        return self._redis

    async def get(self, key: str) -> Optional[CachedAudio]:
        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return None

        value = await client.get(key)
        if value is None:
            return None

        return CachedAudio.decode(value.decode("utf-8"))

    async def set(self, key: str, value: CachedAudio, ttl: Optional[int] = None) -> None:
        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return

        await client.set(key, value.encode(), ex=ttl or self.default_ttl_seconds)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

