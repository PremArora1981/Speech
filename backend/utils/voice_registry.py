"""Voice capability registry and helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from backend.schemas import VoiceCapability


@dataclass(frozen=True)
class VoiceEntry:
    capability: VoiceCapability

    @property
    def provider(self) -> str:
        return self.capability.provider

    @property
    def voice_id(self) -> str:
        return self.capability.voice_id

    @property
    def languages(self) -> Iterable[str]:
        return self.capability.languages


class VoiceRegistry:
    """Basic registry for supported TTS voices across providers."""

    def __init__(self) -> None:
        self._voices: Dict[str, VoiceEntry] = {}

    def register(self, capability: VoiceCapability) -> None:
        key = self._voice_key(capability.provider, capability.voice_id)
        self._voices[key] = VoiceEntry(capability)

    def unregister(self, provider: str, voice_id: str) -> None:
        key = self._voice_key(provider, voice_id)
        self._voices.pop(key, None)

    def get(self, provider: str, voice_id: str) -> Optional[VoiceEntry]:
        key = self._voice_key(provider, voice_id)
        return self._voices.get(key)

    def voices_for_language(self, provider: str, language_code: str) -> list[VoiceEntry]:
        return [
            entry
            for entry in self._voices.values()
            if entry.provider == provider and language_code in entry.languages
        ]

    @staticmethod
    def _voice_key(provider: str, voice_id: str) -> str:
        return f"{provider}:{voice_id}"


VOICE_REGISTRY = VoiceRegistry()

_SARVAM_VOICES = (
    VoiceCapability(
        provider="sarvam",
        voice_id="anushka",
        display_name="Anushka",
        gender="female",
        languages=[
            "hi-IN",
            "en-IN",
            "bn-IN",
            "gu-IN",
            "ta-IN",
            "te-IN",
            "ml-IN",
            "kn-IN",
            "mr-IN",
            "pa-IN",
        ],
        characteristics=["warm", "natural"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="abhilash",
        display_name="Abhilash",
        gender="male",
        languages=[
            "hi-IN",
            "en-IN",
            "bn-IN",
            "gu-IN",
            "ta-IN",
            "te-IN",
            "ml-IN",
            "kn-IN",
            "mr-IN",
            "pa-IN",
        ],
        characteristics=["confident"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="manisha",
        display_name="Manisha",
        gender="female",
        languages=["hi-IN", "en-IN"],
        characteristics=["clear"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="vidya",
        display_name="Vidya",
        gender="female",
        languages=["ta-IN", "en-IN"],
        characteristics=["professional"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="arya",
        display_name="Arya",
        gender="female",
        languages=["bn-IN", "en-IN"],
        characteristics=["friendly"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="karun",
        display_name="Karun",
        gender="male",
        languages=["ta-IN", "en-IN"],
        characteristics=["calm"],
    ),
    VoiceCapability(
        provider="sarvam",
        voice_id="hitesh",
        display_name="Hitesh",
        gender="male",
        languages=["gu-IN", "en-IN"],
        characteristics=["energetic"],
    ),
)

for voice in _SARVAM_VOICES:
    VOICE_REGISTRY.register(voice)

_ELEVENLABS_VOICES = (
    VoiceCapability(
        provider="elevenlabs",
        voice_id="rachel",
        display_name="Rachel",
        gender="female",
        languages=["en-IN", "en-US"],
        characteristics=["premium", "natural"],
    ),
    VoiceCapability(
        provider="elevenlabs",
        voice_id="bella",
        display_name="Bella",
        gender="female",
        languages=["en-IN", "en-US"],
        characteristics=["expressive"],
    ),
    VoiceCapability(
        provider="elevenlabs",
        voice_id="adam",
        display_name="Adam",
        gender="male",
        languages=["en-IN", "en-US"],
        characteristics=["premium"],
    ),
)

for voice in _ELEVENLABS_VOICES:
    VOICE_REGISTRY.register(voice)


