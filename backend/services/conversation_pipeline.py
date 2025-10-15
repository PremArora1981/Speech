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
from backend.services.interrupt_manager import InterruptManager, InterruptReason
from backend.services.cost_tracker import CostTracker
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
        interrupt_manager: Optional[InterruptManager] = None,
        cost_tracker: Optional[CostTracker] = None,
    ) -> None:
        # Create shared managers if not provided
        self.interrupt_manager = interrupt_manager or InterruptManager()
        self.cost_tracker = cost_tracker or CostTracker()

        # Initialize services with shared managers
        self.asr_service = asr_service or ASRService(
            interrupt_manager=self.interrupt_manager,
            cost_tracker=self.cost_tracker
        )
        self.llm_service = llm_service or LLMService(
            interrupt_manager=self.interrupt_manager,
            cost_tracker=self.cost_tracker
        )
        self.translation_service = translation_service or TranslationService(
            cost_tracker=self.cost_tracker
        )
        self.tts_orchestrator = tts_orchestrator or TTSOrchestrator(
            interrupt_manager=self.interrupt_manager,
            cost_tracker=self.cost_tracker
        )
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

    async def interrupt_turn(
        self,
        session_id: str,
        turn_id: str,
        reason: InterruptReason = InterruptReason.USER_BARGE_IN,
    ) -> None:
        """
        Interrupt an active conversation turn.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier to interrupt
            reason: Reason for interruption
        """
        await self.interrupt_manager.interrupt(session_id, turn_id, reason)
        self.logger.info(
            "Turn interrupted",
            extra={"session_id": session_id, "turn_id": turn_id, "reason": reason.value},
        )

    async def get_session_cost_summary(self, session_id: str):
        """
        Get cost summary for a session.

        Args:
            session_id: Session identifier

        Returns:
            CostSummary with total costs and breakdowns
        """
        return await self.cost_tracker.get_session_summary(session_id)

    async def process_audio(
        self,
        audio_url: str,
        target_language: str,
        translation_config: Optional[TranslationConfig] = None,
        session_id: Optional[str] = None,
        optimization_level: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> ConversationTurn:
        """
        Process audio through ASR → RAG → LLM → Translation → TTS pipeline.

        Args:
            audio_url: URL or path to audio file
            target_language: Target language for translation
            translation_config: Optional translation configuration
            session_id: Optional session identifier
            optimization_level: Optimization level (quality/balanced/speed)
            turn_id: Optional turn identifier (auto-generated if not provided)

        Returns:
            ConversationTurn with complete response

        Raises:
            InterruptedError: If turn is interrupted during processing
        """
        # Start turn tracking for interrupt support
        if session_id:
            turn_id = self.interrupt_manager.start_turn(session_id, turn_id)

        try:
            # Step 1: ASR - Transcribe audio
            transcript = await self.asr_service.transcribe(
                audio_url, session_id=session_id, turn_id=turn_id
            )
            request_id = session_id or "anonymous"
            log_with_context(
                self.logger, request_id, logging.INFO, "ASR complete", text=transcript.text
            )

            # Step 2: RAG - Retrieve context (optimization-level aware)
            rag_context = None
            if self.rag_service:
                rag_chunks = self.rag_service.retrieve(
                    transcript.text, optimization_level=optimization_level
                )
                if rag_chunks:
                    rag_context = "\n\n".join(rag_chunks)
                    log_with_context(
                        self.logger,
                        request_id,
                        logging.INFO,
                        "RAG retrieved",
                        chunks=len(rag_chunks),
                    )

            # Step 3: LLM - Generate response (with guardrails and optimization + interrupts)
            llm = await self.llm_service.generate(
                transcript.text,
                rag_context=rag_context,
                optimization_level=optimization_level,
                session_id=session_id,
                turn_id=turn_id,
            )
            log_with_context(
                self.logger,
                request_id,
                logging.INFO,
                "LLM complete",
                safe=llm.guardrail_flags.safe,
            )

            # Step 4: Translation - Translate to target language
            translated = await self.translation_service.translate(
                llm.text,
                source_language="en-IN",
                target_language=target_language,
                config=translation_config,
                session_id=session_id,
                turn_id=turn_id,
            )
            log_with_context(
                self.logger, request_id, logging.INFO, "Translation complete"
            )

            # Step 5: TTS - Synthesize speech (with interrupts)
            tts_response = await self.tts_orchestrator.synthesize(
                request=self._build_tts_request(
                    translated, target_language, optimization_level
                ),
                session_id=session_id,
                turn_id=turn_id,
            )
            log_with_context(self.logger, request_id, logging.INFO, "TTS complete")

            # Store in session repository if available
            if self.session_repository and session_id:
                self.session_repository.add_message(
                    session_id,
                    "user",
                    transcript.text,
                    translated_text=translated,
                    details={
                        "confidence": transcript.confidence,
                        "optimization_level": optimization_level,
                        "guardrail_safe": llm.guardrail_flags.safe,
                        "turn_id": turn_id,
                    },
                )

            return ConversationTurn(
                transcript=transcript,
                llm_response=llm.text,
                translated_text=translated,
                audio_response=tts_response,
            )

        except InterruptedError as e:
            # Turn was interrupted, log and re-raise
            self.logger.info(
                "Turn processing interrupted",
                extra={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "error": str(e),
                },
            )
            raise

        finally:
            # Clean up turn tracking
            if session_id and turn_id:
                self.interrupt_manager.finish_turn(session_id, turn_id)

    def _build_tts_request(
        self, text: str, language: str, optimization_level: Optional[str] = None
    ):
        """Build TTS request with optimization level."""
        from backend.schemas import SynthesizeRequest, VoiceSelection

        return SynthesizeRequest(
            text=text,
            language_code=language,
            voice=VoiceSelection(provider="sarvam", voice_id="anushka"),
            optimization_level=optimization_level or "balanced",
        )

