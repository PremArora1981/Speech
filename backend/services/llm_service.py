"""LLM orchestration with guardrails and optional RAG context."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

import httpx

from backend.config.settings import settings, get_optimization_config
from backend.services.guardrail_service import GuardrailService
from backend.services.interrupt_manager import InterruptManager, InterruptibleOperation
from backend.services.cost_tracker import CostTracker
from backend.utils.cache import LLMCache, CachedLLMResponse


DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class GuardrailViolation(Exception):
    """Raised when a guardrail blocks the request."""


@dataclass
class GuardrailFlags:
    safe: bool = True
    reason: Optional[str] = None
    post_checked: bool = False


@dataclass
class LLMResponse:
    text: str
    guardrail_flags: GuardrailFlags
    tokens: dict[str, int]


class LLMService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        rag_provider: Optional[Callable[[str], Awaitable[str]]] = None,
        guardrail_service: Optional[GuardrailService] = None,
        llm_cache: Optional[LLMCache] = None,
        interrupt_manager: Optional[InterruptManager] = None,
        cost_tracker: Optional[CostTracker] = None,
        max_output_tokens: int = 600,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.rag_provider = rag_provider
        self.guardrail_service = guardrail_service or GuardrailService(enabled=True)
        self.llm_cache = llm_cache or (
            LLMCache(settings.redis_url) if settings.redis_url else None
        )
        self.interrupt_manager = interrupt_manager
        self.cost_tracker = cost_tracker
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries
        # Keep for backwards compatibility
        self.blocked_keywords = []

    async def generate(
        self,
        transcript: str,
        rag_context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        optimization_level: Optional[str] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate LLM response with guardrails and optimization-level-aware settings.

        Args:
            transcript: User input transcript
            rag_context: Optional RAG context
            system_prompt: Optional system prompt override
            optimization_level: Optimization level (affects temperature, max_tokens)
            session_id: Optional session ID for interrupt tracking
            turn_id: Optional turn ID for interrupt tracking

        Returns:
            LLMResponse with text and guardrail flags

        Raises:
            InterruptedError: If operation is interrupted
        """
        opt_level = optimization_level or "balanced"

        # Use interruptible operation if manager and IDs provided
        if self.interrupt_manager and session_id and turn_id:
            async with InterruptibleOperation(
                self.interrupt_manager, session_id, turn_id, "llm"
            ) as op:
                return await self._generate_internal(
                    transcript,
                    rag_context,
                    system_prompt,
                    opt_level,
                    session_id,
                    turn_id,
                    op,
                )
        else:
            return await self._generate_internal(
                transcript, rag_context, system_prompt, opt_level
            )

    async def _generate_internal(
        self,
        transcript: str,
        rag_context: Optional[str],
        system_prompt: Optional[str],
        opt_level: str,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        op: Optional[InterruptibleOperation] = None,
    ) -> LLMResponse:
        """Internal generation logic with optional interrupt checking."""
        # Check for interrupt at the start
        if op:
            op.check_or_raise()

        # Layer 0: Cache Check (before guardrails for performance)
        if self.llm_cache:
            # Try exact match first
            cached = await self.llm_cache.get_exact(transcript, opt_level)
            if cached:
                return LLMResponse(
                    text=cached.response_text,
                    guardrail_flags=GuardrailFlags(
                        safe=cached.guardrail_safe, post_checked=True
                    ),
                    tokens={"total_tokens": cached.token_count},
                )

            # Try semantic match for quality levels
            cached = await self.llm_cache.get_semantic(
                transcript, opt_level, similarity_threshold=0.7
            )
            if cached:
                return LLMResponse(
                    text=cached.response_text,
                    guardrail_flags=GuardrailFlags(
                        safe=cached.guardrail_safe, post_checked=True
                    ),
                    tokens={"total_tokens": cached.token_count},
                )

        # Check for interrupt after cache check
        if op:
            op.check_or_raise()

        # Layer 1: Pre-LLM guardrail check
        input_check = self.guardrail_service.check_input(transcript)
        if not input_check.passed:
            # Input blocked by guardrails
            return LLMResponse(
                text=input_check.safe_response or "I cannot process this request.",
                guardrail_flags=GuardrailFlags(
                    safe=False,
                    reason=input_check.violations[0].message if input_check.violations else "Blocked",
                    post_checked=False,
                ),
                tokens={},
            )

        # Get optimization config
        config = get_optimization_config(opt_level or "balanced")

        if not rag_context and self.rag_provider:
            rag_context = await self.rag_provider(transcript)

        # Layer 2: Build system prompt with guardrails
        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant for customer support."

        # Add guardrail instructions to system prompt
        guardrail_instructions = self.guardrail_service.get_system_prompt_guardrails()
        full_prompt = system_prompt + guardrail_instructions

        if rag_context:
            full_prompt += f"\n\nKNOWLEDGE BASE:\n{rag_context}"

        # Apply optimization-level settings
        max_tokens = config.response_max_tokens if config.response_max_tokens else self.max_output_tokens

        payload = {
            "model": "sarvam-m",
            "messages": [
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": transcript},
            ],
            "temperature": config.llm_temperature,
            "max_tokens": max_tokens,
        }

        # Check for interrupt before making API call
        if op:
            op.check_or_raise()

        data = await self._request_with_retry(payload, session_id, turn_id)
        choice = data["choices"][0]
        text = choice["message"]["content"]

        # Check for interrupt after API call
        if op:
            op.check_or_raise()

        # Layer 3: Post-LLM guardrail check
        output_check = self.guardrail_service.check_output(text)
        if not output_check.passed:
            # Response blocked by guardrails
            return LLMResponse(
                text=output_check.safe_response or "I cannot provide that information.",
                guardrail_flags=GuardrailFlags(
                    safe=False,
                    reason=output_check.violations[0].message if output_check.violations else "Blocked",
                    post_checked=True,
                ),
                tokens=data.get("usage") or {},
            )

        # Layer 4: Cache successful response
        if self.llm_cache:
            cached_response = CachedLLMResponse(
                response_text=text,
                query_hash=self.llm_cache._hash_query(transcript, opt_level),
                guardrail_safe=True,
                token_count=data.get("usage", {}).get("total_tokens", 0),
                optimization_level=opt_level,
            )
            # Use optimization-level-aware TTL
            ttl = self._get_cache_ttl(opt_level)
            await self.llm_cache.set(transcript, cached_response, ttl=ttl)

        # Track cost if tracker is configured
        if self.cost_tracker:
            usage = data.get("usage", {})
            await self.cost_tracker.track_llm(
                provider="sarvam",
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model="sarvam-m",
                session_id=session_id,
                turn_id=turn_id,
                metadata={
                    "optimization_level": opt_level,
                    "temperature": config.llm_temperature,
                    "cached": False,
                },
            )

        return LLMResponse(
            text=text,
            guardrail_flags=GuardrailFlags(safe=True, post_checked=True),
            tokens=data.get("usage") or {},
        )

    def _get_cache_ttl(self, optimization_level: str) -> int:
        """
        Get cache TTL based on optimization level.

        Quality levels get longer TTL (more expensive to recompute).
        Speed levels get shorter TTL (cheaper to regenerate).
        """
        ttl_map = {
            "quality": 3600,  # 1 hour (expensive, cache longer)
            "balanced_quality": 2400,  # 40 minutes
            "balanced": 1800,  # 30 minutes (default)
            "balanced_speed": 1200,  # 20 minutes
            "speed": 600,  # 10 minutes (cheap, cache shorter)
        }
        return ttl_map.get(optimization_level, 1800)

    def _pre_guardrail_check(self, transcript: str) -> None:
        """Deprecated: Use guardrail_service.check_input() instead."""
        lowered = transcript.lower()
        for keyword in self.blocked_keywords:
            if keyword.lower() in lowered:
                raise GuardrailViolation(f"Blocked keyword detected: {keyword}")

    def _post_guardrail_check(self, text: str) -> GuardrailFlags:
        """Deprecated: Use guardrail_service.check_output() instead."""
        max_words = 150
        words = text.split()
        if len(words) > max_words:
            return GuardrailFlags(safe=False, reason="Response too long", post_checked=True)
        return GuardrailFlags(safe=True, post_checked=True)

    async def _request_with_retry(
        self,
        payload: dict,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> dict:
        """Make HTTP request with retry logic and interrupt support."""
        headers = {
            "api-subscription-key": self.api_key,
        }
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            # Check for interrupt before each attempt
            if self.interrupt_manager and session_id and turn_id:
                if self.interrupt_manager.is_interrupted(session_id, turn_id):
                    raise InterruptedError("LLM request interrupted")

            try:
                response = await self.client.post(
                    "/v1/chat/completions",
                    json=payload,
                    headers=headers,
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
        raise RuntimeError("LLM request failed after retries")

    async def close(self) -> None:
        await self.client.aclose()


