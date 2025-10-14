"""Unit tests for the voice registry."""

from backend.schemas import VoiceCapability
from backend.utils.voice_registry import VoiceRegistry


def test_register_and_lookup_voice() -> None:
    registry = VoiceRegistry()
    capability = VoiceCapability(
        provider="sarvam",
        voice_id="anushka",
        display_name="Anushka",
        gender="female",
        languages=["en-IN"],
    )

    registry.register(capability)

    entry = registry.get("sarvam", "anushka")
    assert entry is not None
    assert entry.voice_id == "anushka"
    assert "en-IN" in entry.languages


def test_unregister_voice() -> None:
    registry = VoiceRegistry()
    capability = VoiceCapability(
        provider="sarvam",
        voice_id="anushka",
        display_name="Anushka",
        gender="female",
        languages=["en-IN"],
    )

    registry.register(capability)
    registry.unregister("sarvam", "anushka")

    assert registry.get("sarvam", "anushka") is None

