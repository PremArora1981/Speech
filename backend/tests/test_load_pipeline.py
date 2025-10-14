"""Performance smoke test for pipeline."""

import time

import pytest

from backend.services.conversation_pipeline import ConversationPipeline


@pytest.mark.performance
def test_pipeline_latency_smoke(monkeypatch):
    class MockASR:
        async def transcribe(self, audio_url):
            return type("Result", (), {"text": "hi", "language_code": "en-IN", "confidence": 0.9})

    class MockLLM:
        async def generate(self, transcript, rag_context=None):
            return type("Result", (), {"text": "hello"})

    class MockTranslation:
        async def translate(self, text, source_language, target_language, config=None):
            return "hola"

    class MockTTS:
        async def synthesize(self, request):
            return type("Response", (), {"audio_b64": "SGVsbG8=", "mime_type": "audio/wav", "metadata": None})

    pipeline = ConversationPipeline(MockASR(), MockLLM(), MockTranslation(), MockTTS())

    import asyncio

    start = time.time()
    asyncio.run(pipeline.process_audio("http://example.com/audio.wav", "es-ES"))
    latency = (time.time() - start) * 1000
    assert latency < 500

