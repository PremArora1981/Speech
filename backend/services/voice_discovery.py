"""Voice Discovery Service for dynamically fetching voices from TTS providers."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from backend.clients.elevenlabs_tts import ElevenLabsTTSClient
from backend.schemas.tts import VoiceCapability
from backend.utils.cache import get_cache
from backend.utils.voice_registry import VOICE_REGISTRY

logger = logging.getLogger(__name__)


class VoiceDiscoveryService:
    """Service for discovering and caching voices from TTS providers."""

    # Cache TTL: 1 hour
    CACHE_TTL_SECONDS = 3600

    def __init__(
        self,
        elevenlabs_client: Optional[ElevenLabsTTSClient] = None,
    ) -> None:
        """Initialize the voice discovery service.

        Args:
            elevenlabs_client: Optional ElevenLabs client for testing
        """
        self._elevenlabs_client = elevenlabs_client
        self._cache = get_cache()

    async def fetch_all_voices(
        self,
        provider: Optional[str] = None,
        language: Optional[str] = None,
        include_custom: bool = True,
    ) -> List[VoiceCapability]:
        """Fetch all available voices, optionally filtered by provider and language.

        Args:
            provider: Filter by provider ("sarvam" or "elevenlabs")
            language: Filter by language code (e.g., "en-IN")
            include_custom: Include custom/cloned voices (ElevenLabs only)

        Returns:
            List of voice capabilities
        """
        voices: List[VoiceCapability] = []

        # Fetch from both providers if no specific provider requested
        if provider is None or provider == "sarvam":
            sarvam_voices = await self.fetch_sarvam_voices()
            voices.extend(sarvam_voices)

        if provider is None or provider == "elevenlabs":
            elevenlabs_voices = await self.fetch_elevenlabs_voices(
                include_custom=include_custom
            )
            voices.extend(elevenlabs_voices)

        # Filter by language if specified
        if language:
            voices = [v for v in voices if language in v.languages]

        return voices

    async def fetch_sarvam_voices(self) -> List[VoiceCapability]:
        """Fetch Sarvam voices.

        Currently returns voices from static registry.
        TODO: Update when Sarvam provides a voice listing API.

        Returns:
            List of Sarvam voice capabilities
        """
        # Check cache first
        cache_key = "voices:sarvam"
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.info("Returning cached Sarvam voices")
            return cached

        # Use static registry (no Sarvam API for voice listing yet)
        voices = []
        for entry in VOICE_REGISTRY._voices.values():
            if entry.provider == "sarvam":
                voices.append(entry.capability)

        # Cache the results
        await self._set_in_cache(cache_key, voices)

        logger.info(f"Fetched {len(voices)} Sarvam voices from registry")
        return voices

    async def fetch_elevenlabs_voices(
        self,
        include_custom: bool = True,
    ) -> List[VoiceCapability]:
        """Fetch ElevenLabs voices from API.

        Args:
            include_custom: Include custom/cloned voices

        Returns:
            List of ElevenLabs voice capabilities
        """
        # Check cache first
        cache_key = f"voices:elevenlabs:custom={include_custom}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.info("Returning cached ElevenLabs voices")
            return cached

        try:
            # Get or create ElevenLabs client
            client = self._elevenlabs_client or ElevenLabsTTSClient()

            # Fetch voices from API
            response = await client.list_voices()

            # Parse response
            voices = self._parse_elevenlabs_response(
                response, include_custom=include_custom
            )

            # Cache the results
            await self._set_in_cache(cache_key, voices)

            logger.info(f"Fetched {len(voices)} ElevenLabs voices from API")
            return voices

        except Exception as e:
            logger.error(f"Failed to fetch ElevenLabs voices: {e}")
            # Fallback to static registry
            logger.info("Falling back to static ElevenLabs voice registry")
            return await self._get_elevenlabs_fallback()

    async def fetch_custom_elevenlabs_voices(
        self,
        api_key: Optional[str] = None,
    ) -> List[VoiceCapability]:
        """Fetch only custom/cloned voices from user's ElevenLabs account.

        Args:
            api_key: User's ElevenLabs API key (if different from default)

        Returns:
            List of custom voice capabilities
        """
        try:
            # Create client with user's API key if provided
            client = (
                ElevenLabsTTSClient(api_key=api_key)
                if api_key
                else self._elevenlabs_client or ElevenLabsTTSClient()
            )

            # Fetch voices from API
            response = await client.list_voices()

            # Filter for custom voices only
            custom_voices = []
            for voice_data in response.get("voices", []):
                # ElevenLabs marks custom voices with category "cloned" or "generated"
                category = voice_data.get("category", "")
                if category in ["cloned", "generated"]:
                    voice = self._parse_elevenlabs_voice(voice_data, is_custom=True)
                    if voice:
                        custom_voices.append(voice)

            logger.info(f"Fetched {len(custom_voices)} custom ElevenLabs voices")
            return custom_voices

        except Exception as e:
            logger.error(f"Failed to fetch custom ElevenLabs voices: {e}")
            return []

    def _parse_elevenlabs_response(
        self,
        response: Dict,
        include_custom: bool = True,
    ) -> List[VoiceCapability]:
        """Parse ElevenLabs API response into VoiceCapability list.

        Args:
            response: Raw API response
            include_custom: Whether to include custom/cloned voices

        Returns:
            List of parsed voice capabilities
        """
        voices = []
        for voice_data in response.get("voices", []):
            # Filter custom voices if needed
            category = voice_data.get("category", "")
            is_custom = category in ["cloned", "generated"]

            if not include_custom and is_custom:
                continue

            voice = self._parse_elevenlabs_voice(voice_data, is_custom=is_custom)
            if voice:
                voices.append(voice)

        return voices

    def _parse_elevenlabs_voice(
        self,
        voice_data: Dict,
        is_custom: bool = False,
    ) -> Optional[VoiceCapability]:
        """Parse a single ElevenLabs voice into VoiceCapability.

        Args:
            voice_data: Raw voice data from API
            is_custom: Whether this is a custom/cloned voice

        Returns:
            Parsed VoiceCapability or None if parsing fails
        """
        try:
            voice_id = voice_data.get("voice_id", "")
            name = voice_data.get("name", "")

            # Get labels for characteristics
            labels = voice_data.get("labels", {})
            characteristics = []

            # Add common characteristics
            if is_custom:
                characteristics.append("custom")
            else:
                characteristics.append("premium")

            # Add descriptive labels
            if "accent" in labels:
                characteristics.append(labels["accent"])
            if "age" in labels:
                characteristics.append(labels["age"])
            if "use case" in labels:
                characteristics.append(labels["use case"])

            # Get gender from labels
            gender = labels.get("gender", "").lower()
            if gender not in ["male", "female", "neutral"]:
                gender = None

            # ElevenLabs voices support multiple languages
            # Default to English for now, can be enhanced later
            languages = ["en-US", "en-IN"]

            return VoiceCapability(
                provider="elevenlabs",
                voice_id=voice_id,
                display_name=name,
                gender=gender,  # type: ignore
                languages=languages,
                characteristics=characteristics,
            )

        except Exception as e:
            logger.warning(f"Failed to parse ElevenLabs voice: {e}")
            return None

    async def _get_elevenlabs_fallback(self) -> List[VoiceCapability]:
        """Get ElevenLabs voices from static registry as fallback."""
        voices = []
        for entry in VOICE_REGISTRY._voices.values():
            if entry.provider == "elevenlabs":
                voices.append(entry.capability)
        return voices

    async def _get_from_cache(self, key: str) -> Optional[List[VoiceCapability]]:
        """Get voices from cache.

        Args:
            key: Cache key

        Returns:
            Cached voices or None
        """
        if not self._cache:
            return None

        try:
            cached_data = await self._cache.get(key)
            if cached_data:
                # Parse cached JSON back to VoiceCapability objects
                return [VoiceCapability(**v) for v in cached_data]
        except Exception as e:
            logger.warning(f"Failed to get from cache: {e}")

        return None

    async def _set_in_cache(
        self,
        key: str,
        voices: List[VoiceCapability],
    ) -> None:
        """Store voices in cache.

        Args:
            key: Cache key
            voices: List of voice capabilities to cache
        """
        if not self._cache:
            return

        try:
            # Convert to dict for JSON serialization
            data = [v.model_dump() for v in voices]
            await self._cache.set(key, data, ttl=self.CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Failed to set in cache: {e}")


__all__ = ["VoiceDiscoveryService"]
