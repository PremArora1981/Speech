"""Conversation pipeline orchestrating ASR → LLM → Translation → TTS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from backend.schemas import SynthesizeResponse
from backend.services.asr_service import ASRService, TranscriptResult
from backend.services.llm_service import LLMService
from backend.services.translation_service import TranslationService, TranslationConfig
from backend.services.tts_service import TTSOrchestrator
from backend.services.interrupt_manager import InterruptManager, InterruptReason
from backend.services.cost_tracker import CostTracker
from backend.database.repositories import SessionRepository, SessionMetricsRepository, GuardrailRepository
from backend.database import SessionLocal
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
        target_language: str = "hi-IN",
        translation_config: Optional[TranslationConfig] = None,
    ) -> ConversationTurn | None:
        """
        Process a base64-encoded audio chunk through the full pipeline.

        Args:
            audio_base64: Base64-encoded audio data
            session_id: Session identifier
            timestamp: Timestamp of audio chunk
            optimization_level: Optimization level (quality/balanced/speed)
            target_language: Target language for translation
            translation_config: Optional translation configuration

        Returns:
            ConversationTurn with complete response, or None if no audio provided

        Raises:
            InterruptedError: If turn is interrupted during processing
        """
        if not audio_base64:
            return None

        self.logger.debug(
            "Received audio chunk",
            extra={"session_id": session_id, "optimization_level": optimization_level, "timestamp": timestamp},
        )

        # Decode base64 audio and save to temporary file
        import base64
        import tempfile
        import os

        temp_file_path = None
        try:
            # Remove data URL prefix if present (e.g., "data:audio/wav;base64,")
            if "," in audio_base64:
                audio_base64 = audio_base64.split(",", 1)[1]

            # Decode base64 to bytes
            audio_bytes = base64.b64decode(audio_base64)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            self.logger.debug(
                "Audio chunk decoded and saved",
                extra={"session_id": session_id, "file_size": len(audio_bytes), "temp_path": temp_file_path},
            )

            # Process through full pipeline using existing process_audio method
            result = await self.process_audio(
                audio_url=temp_file_path,
                target_language=target_language,
                translation_config=translation_config,
                session_id=session_id,
                optimization_level=optimization_level,
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to process audio chunk",
                extra={"session_id": session_id, "error": str(e)},
            )
            raise

        finally:
            # Clean up temporary file
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    self.logger.debug(
                        "Temporary audio file cleaned up",
                        extra={"session_id": session_id, "temp_path": temp_file_path},
                    )
            except Exception as cleanup_error:
                self.logger.warning(
                    "Failed to clean up temporary file",
                    extra={"session_id": session_id, "error": str(cleanup_error)},
                )

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

        # Track latencies
        start_time = time.time()
        asr_latency = llm_latency = translation_latency = tts_latency = None

        try:
            # Step 1: ASR - Transcribe audio
            asr_start = time.time()
            transcript = await self.asr_service.transcribe(
                audio_url, session_id=session_id, turn_id=turn_id
            )
            asr_latency = (time.time() - asr_start) * 1000  # Convert to ms
            request_id = session_id or "anonymous"
            log_with_context(
                self.logger, request_id, logging.INFO, "ASR complete",
                text=transcript.text, latency_ms=asr_latency
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
            llm_start = time.time()
            llm = await self.llm_service.generate(
                transcript.text,
                rag_context=rag_context,
                optimization_level=optimization_level,
                session_id=session_id,
                turn_id=turn_id,
            )
            llm_latency = (time.time() - llm_start) * 1000  # Convert to ms
            log_with_context(
                self.logger,
                request_id,
                logging.INFO,
                "LLM complete",
                safe=llm.guardrail_flags.safe,
                latency_ms=llm_latency
            )

            # Step 4: Translation - Translate to target language
            translation_start = time.time()
            translated = await self.translation_service.translate(
                llm.text,
                source_language="en-IN",
                target_language=target_language,
                config=translation_config,
                session_id=session_id,
                turn_id=turn_id,
            )
            translation_latency = (time.time() - translation_start) * 1000  # Convert to ms
            log_with_context(
                self.logger, request_id, logging.INFO, "Translation complete",
                latency_ms=translation_latency
            )

            # Step 5: TTS - Synthesize speech (with interrupts)
            tts_start = time.time()
            tts_response = await self.tts_orchestrator.synthesize(
                request=self._build_tts_request(
                    translated, target_language, optimization_level
                ),
                session_id=session_id,
                turn_id=turn_id,
            )
            tts_latency = (time.time() - tts_start) * 1000  # Convert to ms
            log_with_context(self.logger, request_id, logging.INFO, "TTS complete",
                latency_ms=tts_latency)

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

            # Update session metrics in database
            if session_id:
                try:
                    with SessionLocal() as db:
                        metrics_repo = SessionMetricsRepository(db)

                        # Update turn count - successful
                        metrics = metrics_repo.get_or_create(session_id)
                        metrics.total_turns += 1
                        metrics.successful_turns += 1

                        # Update latencies (running averages)
                        if asr_latency:
                            metrics.avg_asr_latency_ms = self._update_avg(
                                metrics.avg_asr_latency_ms, asr_latency, metrics.successful_turns
                            )
                        if llm_latency:
                            metrics.avg_llm_latency_ms = self._update_avg(
                                metrics.avg_llm_latency_ms, llm_latency, metrics.successful_turns
                            )
                        if translation_latency:
                            metrics.avg_translation_latency_ms = self._update_avg(
                                metrics.avg_translation_latency_ms, translation_latency, metrics.successful_turns
                            )
                        if tts_latency:
                            metrics.avg_tts_latency_ms = self._update_avg(
                                metrics.avg_tts_latency_ms, tts_latency, metrics.successful_turns
                            )

                        # Update total latency
                        total_latency = (asr_latency or 0) + (llm_latency or 0) + (translation_latency or 0) + (tts_latency or 0)
                        metrics.avg_total_latency_ms = self._update_avg(
                            metrics.avg_total_latency_ms, total_latency, metrics.successful_turns
                        )

                        # Track guardrail violations if any
                        if not llm.guardrail_flags.safe:
                            metrics.guardrail_violations += 1
                            if llm.guardrail_flags.reason:
                                metrics.guardrail_blocks += 1

                        # Update optimization level
                        if optimization_level:
                            metrics.optimization_level = optimization_level

                        db.commit()
                except Exception as e:
                    self.logger.error(f"Failed to update session metrics: {e}")

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

            # Update metrics for interrupted turn
            if session_id:
                try:
                    with SessionLocal() as db:
                        metrics_repo = SessionMetricsRepository(db)
                        metrics = metrics_repo.get_or_create(session_id)
                        metrics.total_turns += 1
                        metrics.interrupted_turns += 1
                        db.commit()
                except Exception as metrics_error:
                    self.logger.error(f"Failed to update interrupted turn metrics: {metrics_error}")

            raise

        except Exception as e:
            # Turn failed, log and update metrics
            self.logger.error(
                "Turn processing failed",
                extra={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "error": str(e),
                },
            )

            # Update metrics for failed turn
            if session_id:
                try:
                    with SessionLocal() as db:
                        metrics_repo = SessionMetricsRepository(db)
                        metrics = metrics_repo.get_or_create(session_id)
                        metrics.total_turns += 1
                        metrics.failed_turns += 1
                        db.commit()
                except Exception as metrics_error:
                    self.logger.error(f"Failed to update failed turn metrics: {metrics_error}")

            raise

        finally:
            # Clean up turn tracking
            if session_id and turn_id:
                self.interrupt_manager.finish_turn(session_id, turn_id)

    def _update_avg(self, current_avg: Optional[float], new_value: float, count: int) -> float:
        """Update running average with new value."""
        if current_avg is None or count == 1:
            return new_value
        # Running average formula: new_avg = ((old_avg * (n-1)) + new_value) / n
        return ((current_avg * (count - 1)) + new_value) / count

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

