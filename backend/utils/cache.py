"""Advanced caching utilities for TTS and LLM responses with semantic similarity."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from redis import asyncio as aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None


class CacheNotConfiguredError(RuntimeError):
    """Raised when cache operations are attempted without configuration."""


@dataclass(frozen=True)
class CachedAudio:
    """Cached TTS audio response."""

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


@dataclass(frozen=True)
class CachedLLMResponse:
    """Cached LLM response with metadata."""

    response_text: str
    query_hash: str
    guardrail_safe: bool
    token_count: int
    optimization_level: str

    def encode(self) -> str:
        return json.dumps(
            {
                "response_text": self.response_text,
                "query_hash": self.query_hash,
                "guardrail_safe": self.guardrail_safe,
                "token_count": self.token_count,
                "optimization_level": self.optimization_level,
            }
        )

    @staticmethod
    def decode(value: str) -> "CachedLLMResponse":
        payload = json.loads(value)
        return CachedLLMResponse(
            response_text=payload["response_text"],
            query_hash=payload["query_hash"],
            guardrail_safe=payload["guardrail_safe"],
            token_count=payload["token_count"],
            optimization_level=payload["optimization_level"],
        )


class TTSCache:
    def __init__(self, redis_url: Optional[str] = None, default_ttl_seconds: int = 600) -> None:
        if redis_url and not aioredis:
            raise RuntimeError("redis package must be installed for Redis caching support.")
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


class LLMCache:
    """
    Advanced LLM response caching with exact and semantic similarity matching.

    Caching Strategies:
    1. Exact Match: Hash-based lookup for identical queries
    2. Semantic Similarity: Fuzzy matching for similar queries (balanced_quality+)
    3. Aggressive Caching: Broader matching for speed levels

    Cache Keys:
    - exact:{hash}: Exact query match
    - semantic:{normalized_query}: Semantic similarity match
    - query_index: Sorted set of all cached queries for similarity search
    """

    def __init__(
        self, redis_url: Optional[str] = None, default_ttl_seconds: int = 1800
    ) -> None:
        if redis_url and not aioredis:
            raise RuntimeError(
                "redis package must be installed for Redis caching support."
            )
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self._redis = None

    async def _redis_client(self):
        if not self.redis_url:
            raise CacheNotConfiguredError("Redis URL not configured.")
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url)  # type: ignore
        return self._redis

    def _hash_query(self, query: str, optimization_level: str = "balanced") -> str:
        """Generate hash for exact cache key."""
        content = f"{query.lower().strip()}:{optimization_level}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _normalize_query(self, query: str) -> str:
        """Normalize query for semantic matching."""
        # Remove punctuation, extra spaces, lowercase
        normalized = query.lower().strip()
        normalized = " ".join(normalized.split())  # Remove extra spaces
        return normalized

    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate simple word-overlap similarity between queries.

        Returns: Similarity score 0.0-1.0
        """
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    async def get_exact(
        self, query: str, optimization_level: str = "balanced"
    ) -> Optional[CachedLLMResponse]:
        """Get cached response by exact query match."""
        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return None

        query_hash = self._hash_query(query, optimization_level)
        cache_key = f"llm:exact:{query_hash}"

        value = await client.get(cache_key)
        if value is None:
            return None

        return CachedLLMResponse.decode(value.decode("utf-8"))

    async def get_semantic(
        self,
        query: str,
        optimization_level: str = "balanced",
        similarity_threshold: float = 0.7,
    ) -> Optional[CachedLLMResponse]:
        """
        Get cached response by semantic similarity match.

        Only enabled for balanced_quality and quality levels.
        Uses simple word-overlap similarity for performance.
        """
        # Semantic matching only for quality/balanced_quality
        if optimization_level not in ["quality", "balanced_quality"]:
            return None

        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return None

        normalized_query = self._normalize_query(query)

        # Get recent queries from index (last 100)
        recent_queries = await client.zrevrange("llm:query_index", 0, 99)

        best_match = None
        best_similarity = 0.0

        for cached_query_key in recent_queries:
            cached_query = cached_query_key.decode("utf-8")
            similarity = self._calculate_similarity(normalized_query, cached_query)

            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = cached_query

        if best_match:
            # Get cached response for best matching query
            cache_key = f"llm:semantic:{best_match}"
            value = await client.get(cache_key)
            if value:
                return CachedLLMResponse.decode(value.decode("utf-8"))

        return None

    async def set(
        self,
        query: str,
        response: CachedLLMResponse,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache LLM response with both exact and semantic keys.
        """
        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return

        ttl_seconds = ttl or self.default_ttl_seconds
        encoded_response = response.encode()

        # 1. Store exact match
        query_hash = self._hash_query(query, response.optimization_level)
        exact_key = f"llm:exact:{query_hash}"
        await client.set(exact_key, encoded_response, ex=ttl_seconds)

        # 2. Store semantic match (for quality/balanced_quality)
        if response.optimization_level in ["quality", "balanced_quality"]:
            normalized_query = self._normalize_query(query)
            semantic_key = f"llm:semantic:{normalized_query}"
            await client.set(semantic_key, encoded_response, ex=ttl_seconds)

            # 3. Add to query index with timestamp score
            import time

            await client.zadd(
                "llm:query_index", {normalized_query: time.time()}
            )

            # 4. Trim index to last 1000 queries
            await client.zremrangebyrank("llm:query_index", 0, -1001)

    async def invalidate(self, query: str, optimization_level: str = "balanced") -> None:
        """Invalidate cached response for a query."""
        try:
            client = await self._redis_client()
        except CacheNotConfiguredError:
            return

        # Invalidate exact match
        query_hash = self._hash_query(query, optimization_level)
        exact_key = f"llm:exact:{query_hash}"
        await client.delete(exact_key)

        # Invalidate semantic match
        normalized_query = self._normalize_query(query)
        semantic_key = f"llm:semantic:{normalized_query}"
        await client.delete(semantic_key)

        # Remove from index
        await client.zrem("llm:query_index", normalized_query)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()


__all__ = [
    "CacheNotConfiguredError",
    "CachedAudio",
    "CachedLLMResponse",
    "TTSCache",
    "LLMCache",
]

