"""Tests for ASRService."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.services.asr_service import ASRService, TranscriptSegment


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")


class MockClient:
    def __init__(self):
        self.requests = []

    async def post(self, path, json=None, headers=None, timeout=None):
        self.requests.append((path, json, headers))
        data = {
            "text": "hello",
            "language_code": "en-IN",
            "confidence": 0.9,
            "segments": [
                {"text": "he", "start_ms": 0, "end_ms": 500, "confidence": 0.8},
                {"text": "llo", "start_ms": 500, "end_ms": 1000, "confidence": 0.9},
            ],
        }
        return MockResponse(data)

    def stream(self, method, path, headers=None, timeout=None, data=None):
        assert method == "POST"
        assert path == "/speech-to-text/stream"

        class StreamContext:
            async def __aenter__(self_inner):
                async def aiter_lines():
                    yield json.dumps({"text": "hello", "start_ms": 0, "end_ms": 500, "confidence": 0.8})

                response = SimpleNamespace()
                response.aiter_lines = aiter_lines
                response.raise_for_status = lambda: None
                return response

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return StreamContext()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_transcribe_returns_segments():
    client = MockClient()
    service = ASRService(api_key="test", client=client)
    result = await service.transcribe("http://example.com/audio.wav")

    assert result.text == "hello"
    assert len(result.segments) == 2
    assert isinstance(result.segments[0], TranscriptSegment)


@pytest.mark.asyncio
async def test_stream_transcribe_yields_segments():
    async def audio_stream():
        yield b"chunk1"
        yield b"chunk2"

    client = MockClient()
    service = ASRService(api_key="test", client=client)

    segments = []
    async for seg in service.stream_transcribe(audio_stream()):
        segments.append(seg)

    assert len(segments) == 1
    assert segments[0].text == "hello"

