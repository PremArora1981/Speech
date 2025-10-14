"""Tests for ConversationPipeline."""

import pytest

from backend.services.conversation_pipeline import ConversationPipeline
from backend.services.asr_service import TranscriptResult, TranscriptSegment


class MockASR:
    async def transcribe(self, audio_url: str):
        return TranscriptResult(
            text="hello",
            language_code="en-IN",
            confidence=0.9,
            segments=[TranscriptSegment("hello", 0, 1000, 0.9)],
        )


class MockLLM:
    async def generate(self, transcript: str, rag_context=None):
        class Result:
            text = "hola"

        return Result()


class MockTranslation:
    async def translate(self, text, source_language, target_language, config=None):
        return "hola"


class MockTTS:
    async def synthesize(self, request):
        class Response:
            audio_b64 = "SGVsbG8="
            mime_type = "audio/wav"
            metadata = None

        return Response()


@pytest.mark.asyncio
async def test_pipeline_process_audio():
    pipeline = ConversationPipeline(
        asr_service=MockASR(),
        llm_service=MockLLM(),
        translation_service=MockTranslation(),
        tts_orchestrator=MockTTS(),
    )

    turn = await pipeline.process_audio("http://example.com/audio.wav", "es-ES", session_id="123")

    assert turn.llm_response == "hola"
    assert turn.translated_text == "hola"

