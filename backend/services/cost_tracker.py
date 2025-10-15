"""Cost tracking service for monitoring API usage and expenses."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

try:
    import aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None

from backend.utils.logging import get_logger


@dataclass
class CostEntry:
    """Individual cost entry for a service call."""

    service: str  # asr, llm, translation, tts
    provider: str  # sarvam, elevenlabs, openai, etc.
    operation: str  # transcribe, generate, translate, synthesize
    units: int  # tokens, characters, seconds, etc.
    unit_type: str  # tokens, chars, audio_seconds
    cost_usd: Decimal  # Cost in USD
    timestamp: datetime
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "service": self.service,
            "provider": self.provider,
            "operation": self.operation,
            "units": self.units,
            "unit_type": self.unit_type,
            "cost_usd": str(self.cost_usd),
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "CostEntry":
        """Create from dictionary."""
        return CostEntry(
            service=data["service"],
            provider=data["provider"],
            operation=data["operation"],
            units=data["units"],
            unit_type=data["unit_type"],
            cost_usd=Decimal(data["cost_usd"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data.get("session_id"),
            turn_id=data.get("turn_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CostSummary:
    """Summary of costs for a session or time period."""

    total_cost_usd: Decimal
    total_units: int
    entries_count: int
    breakdown_by_service: Dict[str, Decimal]
    breakdown_by_provider: Dict[str, Decimal]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CostTracker:
    """
    Track API usage costs across services with per-session attribution.

    Features:
    - Per-service cost tracking (ASR, LLM, Translation, TTS)
    - Per-session and per-turn attribution
    - Redis-backed persistent storage
    - Real-time cost summaries
    - Configurable pricing models

    Pricing Models:
    - ASR: Per audio second
    - LLM: Per token (input + output)
    - Translation: Per character
    - TTS: Per character

    Usage:
        tracker = CostTracker()

        # Track ASR cost
        await tracker.track_asr(
            provider="sarvam",
            audio_seconds=15.5,
            session_id="session_123",
            turn_id="turn_456"
        )

        # Track LLM cost
        await tracker.track_llm(
            provider="sarvam",
            input_tokens=100,
            output_tokens=50,
            session_id="session_123"
        )

        # Get session summary
        summary = await tracker.get_session_summary("session_123")
        print(f"Total cost: ${summary.total_cost_usd}")
    """

    # Default pricing in USD (can be overridden)
    DEFAULT_PRICING = {
        "asr": {
            "sarvam": Decimal("0.0001"),  # $0.0001 per second
        },
        "llm": {
            "sarvam": {
                "input": Decimal("0.000001"),  # $0.000001 per token
                "output": Decimal("0.000002"),  # $0.000002 per token
            },
            "openai": {
                "input": Decimal("0.00001"),
                "output": Decimal("0.00003"),
            },
        },
        "translation": {
            "sarvam": Decimal("0.000001"),  # $0.000001 per character
        },
        "tts": {
            "sarvam": Decimal("0.000015"),  # $0.000015 per character
            "elevenlabs": Decimal("0.00003"),  # $0.00003 per character
        },
    }

    def __init__(
        self,
        redis_url: Optional[str] = None,
        pricing: Optional[Dict] = None,
        enable_persistence: bool = True,
    ) -> None:
        """
        Initialize cost tracker.

        Args:
            redis_url: Redis URL for persistent storage
            pricing: Custom pricing model (overrides defaults)
            enable_persistence: Whether to persist to Redis
        """
        self.redis_url = redis_url
        self.pricing = pricing or self.DEFAULT_PRICING
        self.enable_persistence = enable_persistence and redis_url is not None
        self._redis = None
        self.logger = get_logger(__name__)

        # In-memory cache for recent entries
        self._local_entries: List[CostEntry] = []
        self._local_lock = asyncio.Lock()

    async def _redis_client(self):
        """Get Redis client."""
        if not self.redis_url:
            return None
        if not aioredis:
            self.logger.warning("aioredis not installed, persistence disabled")
            return None
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url)  # type: ignore
        return self._redis

    async def track_asr(
        self,
        provider: str,
        audio_seconds: float,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """
        Track ASR service cost.

        Args:
            provider: ASR provider name (sarvam, whisper, etc.)
            audio_seconds: Duration of audio in seconds
            session_id: Optional session identifier
            turn_id: Optional turn identifier
            metadata: Additional metadata

        Returns:
            CostEntry for this operation
        """
        units = int(audio_seconds * 1000)  # Store as milliseconds
        unit_price = self.pricing["asr"].get(provider, Decimal("0"))
        cost = Decimal(audio_seconds) * unit_price

        entry = CostEntry(
            service="asr",
            provider=provider,
            operation="transcribe",
            units=units,
            unit_type="audio_ms",
            cost_usd=cost,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            turn_id=turn_id,
            metadata=metadata or {},
        )

        await self._record_entry(entry)
        return entry

    async def track_llm(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """
        Track LLM service cost.

        Args:
            provider: LLM provider name (sarvam, openai, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (for pricing differentiation)
            session_id: Optional session identifier
            turn_id: Optional turn identifier
            metadata: Additional metadata

        Returns:
            CostEntry for this operation
        """
        pricing = self.pricing["llm"].get(provider, {"input": Decimal("0"), "output": Decimal("0")})
        input_cost = Decimal(input_tokens) * pricing["input"]
        output_cost = Decimal(output_tokens) * pricing["output"]
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        entry_metadata = metadata or {}
        entry_metadata.update({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
        })

        entry = CostEntry(
            service="llm",
            provider=provider,
            operation="generate",
            units=total_tokens,
            unit_type="tokens",
            cost_usd=total_cost,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            turn_id=turn_id,
            metadata=entry_metadata,
        )

        await self._record_entry(entry)
        return entry

    async def track_translation(
        self,
        provider: str,
        characters: int,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """
        Track translation service cost.

        Args:
            provider: Translation provider name (sarvam, google, etc.)
            characters: Number of characters translated
            source_lang: Source language code
            target_lang: Target language code
            session_id: Optional session identifier
            turn_id: Optional turn identifier
            metadata: Additional metadata

        Returns:
            CostEntry for this operation
        """
        unit_price = self.pricing["translation"].get(provider, Decimal("0"))
        cost = Decimal(characters) * unit_price

        entry_metadata = metadata or {}
        entry_metadata.update({
            "source_lang": source_lang,
            "target_lang": target_lang,
        })

        entry = CostEntry(
            service="translation",
            provider=provider,
            operation="translate",
            units=characters,
            unit_type="characters",
            cost_usd=cost,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            turn_id=turn_id,
            metadata=entry_metadata,
        )

        await self._record_entry(entry)
        return entry

    async def track_tts(
        self,
        provider: str,
        characters: int,
        voice_id: Optional[str] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """
        Track TTS service cost.

        Args:
            provider: TTS provider name (sarvam, elevenlabs, etc.)
            characters: Number of characters synthesized
            voice_id: Voice identifier
            session_id: Optional session identifier
            turn_id: Optional turn identifier
            metadata: Additional metadata

        Returns:
            CostEntry for this operation
        """
        unit_price = self.pricing["tts"].get(provider, Decimal("0"))
        cost = Decimal(characters) * unit_price

        entry_metadata = metadata or {}
        entry_metadata.update({"voice_id": voice_id})

        entry = CostEntry(
            service="tts",
            provider=provider,
            operation="synthesize",
            units=characters,
            unit_type="characters",
            cost_usd=cost,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            turn_id=turn_id,
            metadata=entry_metadata,
        )

        await self._record_entry(entry)
        return entry

    async def _record_entry(self, entry: CostEntry) -> None:
        """Record cost entry to storage."""
        async with self._local_lock:
            # Add to in-memory cache
            self._local_entries.append(entry)

            # Keep only last 1000 entries in memory
            if len(self._local_entries) > 1000:
                self._local_entries = self._local_entries[-1000:]

        # Persist to Redis if enabled
        if self.enable_persistence:
            await self._persist_entry(entry)

        self.logger.debug(
            f"Tracked {entry.service} cost",
            extra={
                "provider": entry.provider,
                "cost_usd": str(entry.cost_usd),
                "session_id": entry.session_id,
            },
        )

    async def _persist_entry(self, entry: CostEntry) -> None:
        """Persist entry to Redis."""
        client = await self._redis_client()
        if not client:
            return

        # Store entry in multiple indexes for efficient querying
        entry_key = f"cost:entry:{entry.session_id}:{entry.turn_id}:{entry.timestamp.timestamp()}"
        await client.hset(entry_key, mapping=entry.to_dict())

        # Add to session index
        if entry.session_id:
            session_key = f"cost:session:{entry.session_id}"
            await client.zadd(
                session_key,
                {entry_key: entry.timestamp.timestamp()}
            )

        # Add to global index
        global_key = "cost:global"
        await client.zadd(
            global_key,
            {entry_key: entry.timestamp.timestamp()}
        )

    async def get_session_summary(self, session_id: str) -> CostSummary:
        """
        Get cost summary for a session.

        Args:
            session_id: Session identifier

        Returns:
            CostSummary with aggregated costs
        """
        entries = await self._get_session_entries(session_id)

        if not entries:
            return CostSummary(
                total_cost_usd=Decimal("0"),
                total_units=0,
                entries_count=0,
                breakdown_by_service={},
                breakdown_by_provider={},
            )

        total_cost = sum(e.cost_usd for e in entries)
        total_units = sum(e.units for e in entries)

        # Breakdown by service
        by_service: Dict[str, Decimal] = {}
        for entry in entries:
            by_service[entry.service] = by_service.get(entry.service, Decimal("0")) + entry.cost_usd

        # Breakdown by provider
        by_provider: Dict[str, Decimal] = {}
        for entry in entries:
            by_provider[entry.provider] = by_provider.get(entry.provider, Decimal("0")) + entry.cost_usd

        start_time = min(e.timestamp for e in entries) if entries else None
        end_time = max(e.timestamp for e in entries) if entries else None

        return CostSummary(
            total_cost_usd=total_cost,
            total_units=total_units,
            entries_count=len(entries),
            breakdown_by_service=by_service,
            breakdown_by_provider=by_provider,
            start_time=start_time,
            end_time=end_time,
        )

    async def _get_session_entries(self, session_id: str) -> List[CostEntry]:
        """Get all entries for a session."""
        # Try Redis first
        if self.enable_persistence:
            client = await self._redis_client()
            if client:
                session_key = f"cost:session:{session_id}"
                entry_keys = await client.zrange(session_key, 0, -1)

                entries = []
                for key in entry_keys:
                    data = await client.hgetall(key)
                    if data:
                        # Convert bytes to strings
                        data = {k.decode(): v.decode() for k, v in data.items()}
                        entries.append(CostEntry.from_dict(data))
                return entries

        # Fallback to in-memory cache
        async with self._local_lock:
            return [e for e in self._local_entries if e.session_id == session_id]

    async def get_turn_cost(self, session_id: str, turn_id: str) -> Decimal:
        """Get total cost for a specific turn."""
        entries = await self._get_session_entries(session_id)
        turn_entries = [e for e in entries if e.turn_id == turn_id]
        return sum(e.cost_usd for e in turn_entries)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


__all__ = ["CostTracker", "CostEntry", "CostSummary"]
