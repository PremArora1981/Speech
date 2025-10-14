"""Conversation pipeline orchestrating ASR → LLM → Translation → TTS."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from backend.schemas import SynthesizeResponse
from backend.services.asr_service import ASRService, TranscriptResult
from backend.services.llm_service import LLMService
from backend.services.translation_service import TranslationService, TranslationConfig
from backend.services.tts_service import TTSOrchestrator
from backend.database.repositories import SessionRepository
from backend.services.rag_service import RAGService
from backend.utils.logging import get_logger, log_with_context


@dataclass
class ConversationTurn:
    transcript: TranscriptResult
    llm_response: str
    translated_text: str
    audio_response: SynthesizeResponse


class ConversationPipeline:
    def __init__(
        self,
        asr_service: Optional[ASRService] = None,
        llm_service: Optional[LLMService] = None,
        translation_service: Optional[TranslationService] = None,
        tts_orchestrator: Optional[TTSOrchestrator] = None,
        session_repository: Optional[SessionRepository] = None,
        rag_service: Optional[RAGService] = None,
    ) -> None:
        self.asr_service = asr_service or ASRService()
        self.llm_service = llm_service or LLMService()
        self.translation_service = translation_service or TranslationService()
        self.tts_orchestrator = tts_orchestrator or TTSOrchestrator()
        self.session_repository = session_repository
        self.rag_service = rag_service
        self.logger = get_logger(__name__)

    async def start_session(self, session_id: str | None, optimization_level: str | None) -> None:
        self.logger.info("Voice session started", extra={"session_id": session_id, "optimization_level": optimization_level})

    async def process_audio_chunk(
        self,
        audio_base64: str | None,
        session_id: str | None,
        timestamp: float | None,
        optimization_level: str | None,
    ) -> ConversationTurn | None:
        if not audio_base64:
            return None
        # TODO: decode audio, stream through ASR/LLM/Translation/TTS respecting optimization level
        self.logger.debug(
            "Received audio chunk",
            extra={"session_id": session_id, "optimization_level": optimization_level, "timestamp": timestamp},
        )
        return None

    async def finish_session(self, session_id: str | None, optimization_level: str | None) -> None:
        self.logger.info("Voice session finished", extra={"session_id": session_id, "optimization_level": optimization_level})

    async def process_audio(
        self,
        audio_url: str,
        target_language: str,
        translation_config: Optional[TranslationConfig] = None,
        session_id: Optional[str] = None,
    ) -> ConversationTurn:
        transcript = await self.asr_service.transcribe(audio_url)
        request_id = session_id or "anonymous"
        log_with_context(self.logger, request_id, logging.INFO, "ASR complete", text=transcript.text)
        rag_context = None
        if self.rag_service:
            rag_context = self.rag_service.retrieve(transcript.text)
            if rag_context:
                rag_context = "\n".join(rag_context)

        llm = await self.llm_service.generate(transcript.text, rag_context=rag_context)
        translated = await self.translation_service.translate(
            llm.text,
            source_language="en-IN",
            target_language=target_language,
            config=translation_config,
        )
        tts_response = await self.tts_orchestrator.synthesize(
            request=self._build_tts_request(translated, target_language)
        )
        if self.session_repository and session_id:
            self.session_repository.add_message(
                session_id,
                "user",
                transcript.text,
                translated_text=translated,
                details={"confidence": transcript.confidence},
            )
        return ConversationTurn(
            transcript=transcript,
            llm_response=llm.text,
            translated_text=translated,
            audio_response=tts_response,
        )

    def _build_tts_request(self, text: str, language: str):
        from backend.schemas import SynthesizeRequest, VoiceSelection

        return SynthesizeRequest(
            text=text,
            language_code=language,
            voice=VoiceSelection(provider="sarvam", voice_id="anushka"),
        )

