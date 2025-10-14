"""Unit tests for TTSOrchestrator."""

import asyncio
from typing import Any, Dict, Optional

import pytest

from backend.schemas import SynthesizeRequest, VoiceSelection
from backend.services import TTSOrchestrator
from backend.utils.cache import CachedAudio
from backend.utils.voice_registry import VoiceRegistry, VoiceCapability


class MockSarvamClient:
    async def convert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert payload["text"] == "Hello"
        assert payload["speaker"] == "anushka"
        return {
            "request_id": "mock-123",
            "audios": ["SGVsbG8="]
        }


class MockElevenLabsClient:
    async def convert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert payload["voice_id"] == "rachel"
        return {
            "request_id": "mock-elevenlabs",
            "audio": "RWxldmVuTGFiUw==",
        }


class FailingElevenLabsClient(MockElevenLabsClient):
    async def convert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("test failure")


@pytest.fixture
def stub_voice_registry() -> VoiceRegistry:
    registry = VoiceRegistry()
    registry.register(
        VoiceCapability(
            provider="sarvam",
            voice_id="anushka",
            display_name="Anushka",
            gender="female",
            languages=["en-IN"],
        )
    )
    registry.register(
        VoiceCapability(
            provider="elevenlabs",
            voice_id="rachel",
            display_name="Rachel",
            gender="female",
            languages=["en-IN"],
        )
    )
    return registry


class MockCache:
    def __init__(self) -> None:
        self.storage: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str):
        data = self.storage.get(key)
        if not data:
            return None
        return CachedAudio(
            audio_b64=data["audio"],
            codec=data["codec"],
            sample_rate_hz=data["sample_rate_hz"],
        )

    async def set(self, key: str, value, ttl: Optional[int] = None):
        self.storage[key] = {
            "audio": value.audio_b64,
            "codec": value.codec,
            "sample_rate_hz": value.sample_rate_hz,
        }


@pytest.mark.asyncio
async def test_synthesize_returns_audio_response(
    stub_voice_registry: VoiceRegistry,
) -> None:
    orchestrator = TTSOrchestrator(
        sarvam_client=MockSarvamClient(),
        voice_registry=stub_voice_registry,
    )
    req = SynthesizeRequest(
        text="Hello",
        language_code="en-IN",
        optimization_level="balanced",
        voice=VoiceSelection(provider="sarvam", voice_id="anushka"),
        enable_preprocessing=True,
    )

    response = await orchestrator.synthesize(req)

    assert response.audio_b64 == "SGVsbG8="
    assert response.metadata.provider == "sarvam"
    assert response.metadata.voice_id == "anushka"
    assert response.metadata.fallback_from_provider is None
    assert response.metadata.fallback_from_voice_id is None
    assert response.metadata.language_code == "en-IN"
    assert response.metadata.request_id == "mock-123"


@pytest.mark.asyncio
async def test_synthesize_falls_back_when_voice_missing(
    stub_voice_registry: VoiceRegistry,
) -> None:
    orchestrator = TTSOrchestrator(
        sarvam_client=MockSarvamClient(),
        voice_registry=stub_voice_registry,
    )

    req = SynthesizeRequest(
        text="Hello",
        language_code="hi-IN",
        optimization_level="balanced",
        voice=VoiceSelection(provider="sarvam", voice_id="unknown"),
        enable_preprocessing=True,
    )

    response = await orchestrator.synthesize(req)

    assert response.metadata.voice_id == "anushka"
    assert response.metadata.fallback_from_provider == "sarvam"
    assert response.metadata.fallback_from_voice_id == "unknown"


@pytest.mark.asyncio
async def test_synthesize_uses_elevenlabs_provider(
    stub_voice_registry: VoiceRegistry,
) -> None:
    orchestrator = TTSOrchestrator(
        sarvam_client=MockSarvamClient(),
        elevenlabs_client=MockElevenLabsClient(),
        voice_registry=stub_voice_registry,
    )

    req = SynthesizeRequest(
        text="Hello",
        language_code="en-IN",
        optimization_level="balanced",
        voice=VoiceSelection(provider="elevenlabs", voice_id="rachel"),
        enable_preprocessing=True,
        audio_codec="mp3",
    )

    response = await orchestrator.synthesize(req)

    assert response.metadata.provider == "elevenlabs"
    assert response.metadata.voice_id == "rachel"
    assert response.metadata.fallback_from_provider is None
    assert response.metadata.fallback_from_voice_id is None
    assert response.audio_b64 == "RWxldmVuTGFiUw=="


@pytest.mark.asyncio
async def test_synthesize_returns_cached_value(stub_voice_registry: VoiceRegistry) -> None:
    cache = MockCache()
    orchestrator = TTSOrchestrator(
        sarvam_client=MockSarvamClient(),
        voice_registry=stub_voice_registry,
        cache=cache,
    )

    req = SynthesizeRequest(
        text="Hello",
        language_code="en-IN",
        optimization_level="balanced",
        voice=VoiceSelection(provider="sarvam", voice_id="anushka"),
        enable_preprocessing=True,
    )

    # First call populates cache
    response = await orchestrator.synthesize(req)
    assert not response.metadata.cached

    # Manually populate cache with different audio to verify retrieval
    key = orchestrator._cache_key(req, "anushka")  # type: ignore[attr-defined]
    cache.storage[key] = {
        "audio": "Q0FDSERBVEE=",
        "codec": "wav",
        "sample_rate_hz": 22050,
    }

    response_cached = await orchestrator.synthesize(req)
    assert response_cached.metadata.cached
    assert response_cached.audio_b64 == "Q0FDSERBVEE="


@pytest.mark.asyncio
async def test_elevenlabs_failure_falls_back_to_sarvam(
    stub_voice_registry: VoiceRegistry,
) -> None:
    orchestrator = TTSOrchestrator(
        sarvam_client=MockSarvamClient(),
        elevenlabs_client=FailingElevenLabsClient(),
        voice_registry=stub_voice_registry,
    )

    req = SynthesizeRequest(
        text="Hello",
        language_code="en-IN",
        optimization_level="balanced",
        voice=VoiceSelection(provider="elevenlabs", voice_id="rachel"),
        enable_preprocessing=True,
    )

    response = await orchestrator.synthesize(req)

    assert response.metadata.provider == "sarvam"
    assert response.metadata.voice_id == "anushka"
