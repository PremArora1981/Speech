"""Integration test for conversation pipeline with mocks."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


class MockPipeline:
    async def process_audio(self, audio_url, target_language, translation_config=None, session_id=None):
        class Response:
            llm_response = "Hello"
            translated_text = "Hola"

        return Response()


@pytest.fixture
def client(monkeypatch):
    from backend.config.settings import settings
    from backend.api.routes import get_pipeline

    def override_pipeline():
        return MockPipeline()

    app.dependency_overrides[get_pipeline] = override_pipeline
    original_key = settings.sarvam_api_key
    settings.sarvam_api_key = "secret"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    settings.sarvam_api_key = original_key


def test_voice_session_flow(client):
    with client.websocket_connect("/api/v1/voice-session", headers={"X-API-Key": "secret"}) as ws:
        ws.send_text("http://example.com/audio.wav")
        data = ws.receive_json()
        assert data["text"] == "Hello"

