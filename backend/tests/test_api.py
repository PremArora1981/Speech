"""API-level tests for TTS endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import app


def test_tts_endpoint_success(monkeypatch):
    from backend.services.tts_service import TTSOrchestrator
    from backend.schemas import SynthesizeResponse, TTSMetadata

    async def mock_synthesize(self, request):
        return SynthesizeResponse(
            audio_b64="SGVsbG8=",
            mime_type="audio/wav",
            metadata=TTSMetadata(
                provider="sarvam",
                voice_id="anushka",
                language_code="en-IN",
                optimization_level="balanced",
                sample_rate_hz=22050,
                audio_codec="wav",
            ),
        )

    monkeypatch.setattr(TTSOrchestrator, "synthesize", mock_synthesize)

    client = TestClient(app)
    response = client.post(
        "/api/v1/tts",
        json={
            "text": "Hello",
            "language_code": "en-IN",
            "optimization_level": "balanced",
            "voice": {"provider": "sarvam", "voice_id": "anushka"},
            "enable_preprocessing": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["provider"] == "sarvam"
    assert data["audio_b64"] == "SGVsbG8="

