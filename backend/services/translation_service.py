"""Translation service with colloquial and code-mixing support."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

import httpx

from backend.config.settings import settings
from backend.services.cost_tracker import CostTracker

DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


@dataclass
class TranslationConfig:
    """
    Configuration for translation behavior.

    Attributes:
        colloquial: Enable colloquial/informal language
        formality_level: 0-100 scale (0=very formal, 50=conversational, 100=very informal)
        code_mixing_enabled: Mix English words with target language
        english_ratio: Percentage of English in code-mixing (0-100)
        preserve_domains: List of domain terms to keep in English
        mode: Translation mode override (formal/conversational/informal)
    """

    colloquial: bool = False
    formality_level: int = 50  # 0-100 scale
    code_mixing_enabled: bool = False
    english_ratio: int = 30  # 0-100 percentage
    preserve_domains: List[str] = field(default_factory=list)  # e.g., ["tech", "business"]
    mode: Optional[Literal["formal", "conversational", "informal"]] = None


class TranslationService:
    """
    Translation service with advanced colloquial and code-mixing features.

    Supports:
    - Formality level control (0-100 scale)
    - Code-mixing with configurable English ratio
    - Domain-specific term preservation (tech, business, medical)
    """

    # Domain-specific terms to preserve in English
    DOMAIN_TERMS = {
        "tech": [
            "API",
            "database",
            "server",
            "cloud",
            "app",
            "software",
            "hardware",
            "website",
            "email",
            "internet",
            "laptop",
            "smartphone",
            "password",
            "login",
            "download",
            "upload",
            "wifi",
            "bluetooth",
        ],
        "business": [
            "meeting",
            "deadline",
            "client",
            "revenue",
            "profit",
            "budget",
            "invoice",
            "contract",
            "portfolio",
            "stakeholder",
            "ROI",
            "KPI",
            "target",
            "strategy",
        ],
        "medical": [
            "doctor",
            "hospital",
            "medicine",
            "prescription",
            "diagnosis",
            "symptoms",
            "treatment",
            "surgery",
            "emergency",
        ],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 3,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        self.api_key = api_key or settings.sarvam_api_key
        self.client = client or httpx.AsyncClient(base_url=str(settings.sarvam_api_base))
        self.max_retries = max_retries
        self.cost_tracker = cost_tracker

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        config: Optional[TranslationConfig] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> str:
        """
        Translate text with colloquial and code-mixing support.

        Args:
            text: Text to translate
            source_language: Source language code (e.g., "en-IN")
            target_language: Target language code (e.g., "hi-IN")
            config: Translation configuration
            session_id: Optional session ID for cost tracking
            turn_id: Optional turn ID for cost tracking

        Returns:
            Translated text with applied formality and code-mixing settings
        """
        # Skip translation if source and target are the same
        if source_language == target_language:
            return text

        cfg = config or TranslationConfig()

        # Step 1: Preserve domain-specific terms if requested
        preserved_terms = self._extract_preserve_terms(text, cfg.preserve_domains)
        text_with_placeholders = self._replace_with_placeholders(text, preserved_terms)

        # Step 2: Determine translation mode based on formality level
        mode = cfg.mode or self._get_mode_from_formality(cfg.formality_level)

        # Step 3: Build translation payload
        payload = {
            "text": text_with_placeholders,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "mode": mode,  # formal, conversational, informal
        }

        # Add code-mixing parameters if enabled
        if cfg.code_mixing_enabled:
            payload["enable_code_mixing"] = True
            payload["english_ratio"] = cfg.english_ratio / 100.0  # Convert to 0-1 scale

        # Step 4: Call translation API
        data = await self._request_with_retry(payload)
        translated = data.get("translated_text", text)

        # Step 5: Restore preserved terms
        translated = self._restore_preserved_terms(translated, preserved_terms)

        # Track cost if tracker is configured
        if self.cost_tracker:
            await self.cost_tracker.track_translation(
                provider="sarvam",
                characters=len(text),
                source_lang=source_language,
                target_lang=target_language,
                session_id=session_id,
                turn_id=turn_id,
                metadata={
                    "mode": mode,
                    "formality_level": cfg.formality_level,
                    "code_mixing": cfg.code_mixing_enabled,
                },
            )

        return translated

    def _get_mode_from_formality(self, formality_level: int) -> str:
        """
        Map formality level (0-100) to translation mode.

        0-33: formal (very formal language)
        34-66: conversational (natural, everyday language)
        67-100: informal (casual, colloquial language)
        """
        if formality_level <= 33:
            return "formal"
        elif formality_level <= 66:
            return "conversational"
        else:
            return "informal"

    def _extract_preserve_terms(self, text: str, domains: List[str]) -> List[tuple[str, str]]:
        """
        Extract domain-specific terms to preserve in English.

        Returns:
            List of (term, placeholder) tuples
        """
        if not domains:
            return []

        preserved = []
        terms_to_preserve = set()

        # Collect terms from requested domains
        for domain in domains:
            if domain in self.DOMAIN_TERMS:
                terms_to_preserve.update(self.DOMAIN_TERMS[domain])

        # Find terms in text (case-insensitive)
        for i, term in enumerate(terms_to_preserve):
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            if pattern.search(text):
                placeholder = f"__PRESERVE_{i}__"
                preserved.append((term, placeholder))

        return preserved

    def _replace_with_placeholders(self, text: str, preserved_terms: List[tuple[str, str]]) -> str:
        """Replace preserved terms with placeholders."""
        for term, placeholder in preserved_terms:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            text = pattern.sub(placeholder, text)
        return text

    def _restore_preserved_terms(self, text: str, preserved_terms: List[tuple[str, str]]) -> str:
        """Restore preserved terms from placeholders."""
        for term, placeholder in preserved_terms:
            text = text.replace(placeholder, term)
        return text

    async def _request_with_retry(self, payload: dict) -> dict:
        headers = {"api-subscription-key": self.api_key}
        delay = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(
                    "/text/translate",
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
        raise RuntimeError("Translation request failed after retries")

    async def close(self) -> None:
        await self.client.aclose()


