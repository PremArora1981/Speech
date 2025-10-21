"""Repository layer for database operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    CostTracking,
    Message,
    Session as SessionModel,
    Document,
    TelephonyTrunk,
    Secret,
    GuardrailViolation,
    CostEntry,
    SessionMetrics,
    UserFeedback,
    TurnEvent,
    SystemPrompt,
    SessionConfiguration,
)


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, language_code: str, optimization_level: str) -> SessionModel:
        session = SessionModel(language_code=language_code, optimization_level=optimization_level)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        return self.db.query(SessionModel).filter(SessionModel.id == session_id).first()

    def add_message(
        self,
        session_id: str,
        role: str,
        transcript: str,
        translated_text: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            transcript=transcript,
            translated_text=translated_text,
            details=details or {},
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message


class CostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log_cost(self, service: str, cost_usd: float) -> CostTracking:
        record = CostTracking(service=service, cost_usd=cost_usd)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_document(self, source_url: str, checksum: str, title: str | None = None) -> Document:
        doc = self.db.query(Document).filter(Document.source_url == source_url).first()
        if doc:
            doc.checksum = checksum
            doc.title = title
        else:
            doc = Document(source_url=source_url, checksum=checksum, title=title)
            self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc


class SecretRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def store_or_update(self, ref: str, encrypted_value: str) -> Secret:
        secret = self.db.query(Secret).filter(Secret.ref == ref).first()
        if secret:
            secret.encrypted_value = encrypted_value
        else:
            secret = Secret(ref=ref, encrypted_value=encrypted_value)
            self.db.add(secret)
        self.db.commit()
        self.db.refresh(secret)
        return secret

    def get_secret(self, ref: str) -> Secret | None:
        return self.db.query(Secret).filter(Secret.ref == ref).first()

    def delete_secret(self, ref: str) -> None:
        secret = self.get_secret(ref)
        if secret:
            self.db.delete(secret)
            self.db.commit()


class TelephonyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_trunk(
        self,
        provider: str,
        trunk_id: str,
        direction: str,
        sip_uri: str,
        transport: str | None,
        meta_data: dict | None,
        credential_ref: str | None,
    ) -> TelephonyTrunk:
        trunk = self.db.query(TelephonyTrunk).filter(TelephonyTrunk.trunk_id == trunk_id).first()
        if trunk:
            trunk.provider = provider
            trunk.direction = direction
            trunk.sip_uri = sip_uri
            trunk.transport = transport
            trunk.meta_data = meta_data or {}
            trunk.credential_ref = credential_ref
        else:
            trunk = TelephonyTrunk(
                provider=provider,
                trunk_id=trunk_id,
                direction=direction,
                sip_uri=sip_uri,
                transport=transport,
                meta_data=meta_data or {},
                credential_ref=credential_ref,
            )
            self.db.add(trunk)
        self.db.commit()
        self.db.refresh(trunk)
        return trunk

    def list_trunks(self) -> list[TelephonyTrunk]:
        return self.db.query(TelephonyTrunk).all()

    def get_trunk(self, trunk_id: str) -> TelephonyTrunk | None:
        return self.db.query(TelephonyTrunk).filter(TelephonyTrunk.trunk_id == trunk_id).first()


class GuardrailRepository:
    """Repository for guardrail violation tracking."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def log_violation(
        self,
        violation_type: str,
        layer: int,
        violated_rule: str,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        severity: str = "medium",
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        safe_response: Optional[str] = None,
        meta_data: Optional[dict] = None,
    ) -> GuardrailViolation:
        """Log a guardrail violation."""
        violation = GuardrailViolation(
            session_id=session_id,
            turn_id=turn_id,
            violation_type=violation_type,
            layer=layer,
            severity=severity,
            violated_rule=violated_rule,
            input_text=input_text,
            output_text=output_text,
            safe_response=safe_response,
            meta_data=meta_data or {},
        )
        self.db.add(violation)
        self.db.commit()
        self.db.refresh(violation)
        return violation

    def get_session_violations(self, session_id: str) -> list[GuardrailViolation]:
        """Get all violations for a session."""
        return (
            self.db.query(GuardrailViolation)
            .filter(GuardrailViolation.session_id == session_id)
            .order_by(GuardrailViolation.created_at.desc())
            .all()
        )

    def get_violations_by_severity(
        self, severity: str, limit: int = 100
    ) -> list[GuardrailViolation]:
        """Get recent violations by severity."""
        return (
            self.db.query(GuardrailViolation)
            .filter(GuardrailViolation.severity == severity)
            .order_by(GuardrailViolation.created_at.desc())
            .limit(limit)
            .all()
        )


class CostEntryRepository:
    """Repository for enhanced cost tracking."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def log_cost(
        self,
        service: str,
        provider: str,
        operation: str,
        units: int,
        unit_type: str,
        cost_usd: float,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        optimization_level: Optional[str] = None,
        cached: bool = False,
        meta_data: Optional[dict] = None,
    ) -> CostEntry:
        """Log a cost entry."""
        entry = CostEntry(
            session_id=session_id,
            turn_id=turn_id,
            service=service,
            provider=provider,
            operation=operation,
            units=units,
            unit_type=unit_type,
            cost_usd=cost_usd,
            optimization_level=optimization_level,
            cached=cached,
            meta_data=meta_data or {},
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_session_costs(self, session_id: str) -> list[CostEntry]:
        """Get all cost entries for a session."""
        return (
            self.db.query(CostEntry)
            .filter(CostEntry.session_id == session_id)
            .order_by(CostEntry.created_at)
            .all()
        )

    def get_session_total_cost(self, session_id: str) -> float:
        """Get total cost for a session."""
        from sqlalchemy import func

        result = self.db.query(func.sum(CostEntry.cost_usd)).filter(
            CostEntry.session_id == session_id
        ).scalar()
        return float(result or 0.0)


class SessionMetricsRepository:
    """Repository for session metrics tracking."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, session_id: str) -> SessionMetrics:
        """Get existing metrics or create new one."""
        metrics = (
            self.db.query(SessionMetrics)
            .filter(SessionMetrics.session_id == session_id)
            .first()
        )
        if not metrics:
            metrics = SessionMetrics(session_id=session_id)
            self.db.add(metrics)
            self.db.commit()
            self.db.refresh(metrics)
        return metrics

    def update_turn_count(
        self, session_id: str, status: str = "successful"
    ) -> SessionMetrics:
        """Update turn count metrics."""
        metrics = self.get_or_create(session_id)
        metrics.total_turns += 1

        if status == "successful":
            metrics.successful_turns += 1
        elif status == "failed":
            metrics.failed_turns += 1
        elif status == "interrupted":
            metrics.interrupted_turns += 1

        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    def update_latency(
        self,
        session_id: str,
        asr_ms: Optional[float] = None,
        llm_ms: Optional[float] = None,
        translation_ms: Optional[float] = None,
        tts_ms: Optional[float] = None,
    ) -> SessionMetrics:
        """Update average latency metrics."""
        metrics = self.get_or_create(session_id)

        # Calculate running averages
        if asr_ms is not None:
            metrics.avg_asr_latency_ms = self._update_avg(
                metrics.avg_asr_latency_ms, asr_ms, metrics.total_turns
            )
        if llm_ms is not None:
            metrics.avg_llm_latency_ms = self._update_avg(
                metrics.avg_llm_latency_ms, llm_ms, metrics.total_turns
            )
        if translation_ms is not None:
            metrics.avg_translation_latency_ms = self._update_avg(
                metrics.avg_translation_latency_ms, translation_ms, metrics.total_turns
            )
        if tts_ms is not None:
            metrics.avg_tts_latency_ms = self._update_avg(
                metrics.avg_tts_latency_ms, tts_ms, metrics.total_turns
            )

        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    def update_cache_stats(
        self,
        session_id: str,
        llm_hit: bool = False,
        tts_hit: bool = False,
    ) -> SessionMetrics:
        """Update cache hit/miss statistics."""
        metrics = self.get_or_create(session_id)

        if llm_hit:
            metrics.llm_cache_hits += 1
        else:
            metrics.llm_cache_misses += 1

        if tts_hit:
            metrics.tts_cache_hits += 1
        else:
            metrics.tts_cache_misses += 1

        # Recalculate hit rate
        total_cache_requests = (
            metrics.llm_cache_hits
            + metrics.llm_cache_misses
            + metrics.tts_cache_hits
            + metrics.tts_cache_misses
        )
        if total_cache_requests > 0:
            metrics.cache_hit_rate = (
                metrics.llm_cache_hits + metrics.tts_cache_hits
            ) / total_cache_requests

        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    def increment_guardrail_violation(self, session_id: str) -> SessionMetrics:
        """Increment guardrail violation count."""
        metrics = self.get_or_create(session_id)
        metrics.guardrail_violations += 1
        metrics.guardrail_blocks += 1
        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    @staticmethod
    def _update_avg(
        current_avg: Optional[float], new_value: float, count: int
    ) -> float:
        """Calculate new running average."""
        if current_avg is None:
            return new_value
        return ((current_avg * (count - 1)) + new_value) / count


class UserFeedbackRepository:
    """Repository for user feedback tracking."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_feedback(
        self,
        session_id: str,
        rating: int,
        rating_type: str = "thumbs",
        turn_id: Optional[str] = None,
        message_id: Optional[str] = None,
        feedback_text: Optional[str] = None,
        feedback_category: Optional[str] = None,
        incorrect_response: bool = False,
        too_slow: bool = False,
        unhelpful: bool = False,
        offensive: bool = False,
        user_input: Optional[str] = None,
        assistant_response: Optional[str] = None,
        meta_data: Optional[dict] = None,
    ) -> UserFeedback:
        """Add user feedback."""
        feedback = UserFeedback(
            session_id=session_id,
            turn_id=turn_id,
            message_id=message_id,
            rating=rating,
            rating_type=rating_type,
            feedback_text=feedback_text,
            feedback_category=feedback_category,
            incorrect_response=incorrect_response,
            too_slow=too_slow,
            unhelpful=unhelpful,
            offensive=offensive,
            user_input=user_input,
            assistant_response=assistant_response,
            meta_data=meta_data or {},
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_session_feedback(self, session_id: str) -> list[UserFeedback]:
        """Get all feedback for a session."""
        return (
            self.db.query(UserFeedback)
            .filter(UserFeedback.session_id == session_id)
            .order_by(UserFeedback.created_at)
            .all()
        )

    def get_average_rating(self, session_id: str) -> Optional[float]:
        """Get average rating for a session."""
        from sqlalchemy import func

        result = self.db.query(func.avg(UserFeedback.rating)).filter(
            UserFeedback.session_id == session_id
        ).scalar()
        return float(result) if result else None


class TurnEventRepository:
    """Repository for turn event logging."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def log_event(
        self,
        session_id: str,
        turn_id: str,
        event_type: str,
        event_status: str,
        stage: str,
        latency_ms: Optional[int] = None,
        result_data: Optional[dict] = None,
        error_message: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cache_hit: bool = False,
    ) -> TurnEvent:
        """Log a turn event."""
        event = TurnEvent(
            session_id=session_id,
            turn_id=turn_id,
            event_type=event_type,
            event_status=event_status,
            stage=stage,
            latency_ms=latency_ms,
            result_data=result_data or {},
            error_message=error_message,
            tokens_used=tokens_used,
            cache_hit=cache_hit,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_turn_events(self, session_id: str, turn_id: str) -> list[TurnEvent]:
        """Get all events for a turn."""
        return (
            self.db.query(TurnEvent)
            .filter(
                TurnEvent.session_id == session_id, TurnEvent.turn_id == turn_id
            )
            .order_by(TurnEvent.timestamp)
            .all()
        )

    def get_session_events(self, session_id: str) -> list[TurnEvent]:
        """Get all events for a session."""
        return (
            self.db.query(TurnEvent)
            .filter(TurnEvent.session_id == session_id)
            .order_by(TurnEvent.timestamp)
            .all()
        )


class SessionConfigRepository:
    """Repository for session configuration management."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        name: str,
        llm_provider: str,
        llm_model: str,
        tts_provider: str,
        tts_voice_id: str,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        voice_tuning: Optional[dict] = None,
        system_prompt_id: Optional[str] = None,
        optimization_level: str = "balanced",
        target_language: str = "en-IN",
        enable_rag: bool = False,
        is_default: bool = False,
        meta_data: Optional[dict] = None,
    ) -> SessionConfiguration:
        """Create a new session configuration."""
        config = SessionConfiguration(
            user_id=user_id,
            name=name,
            description=description,
            llm_provider=llm_provider,
            llm_model=llm_model,
            tts_provider=tts_provider,
            tts_voice_id=tts_voice_id,
            voice_tuning=voice_tuning or {},
            system_prompt_id=system_prompt_id,
            optimization_level=optimization_level,
            target_language=target_language,
            enable_rag=enable_rag,
            is_default=is_default,
            meta_data=meta_data or {},
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get(self, config_id: str) -> Optional[SessionConfiguration]:
        """Get a configuration by ID."""
        return (
            self.db.query(SessionConfiguration)
            .filter(SessionConfiguration.id == config_id)
            .first()
        )

    def list(self, user_id: Optional[str] = None) -> list[SessionConfiguration]:
        """List configurations, optionally filtered by user."""
        query = self.db.query(SessionConfiguration)
        if user_id:
            query = query.filter(SessionConfiguration.user_id == user_id)
        return query.order_by(SessionConfiguration.created_at.desc()).all()

    def get_default(self, user_id: Optional[str] = None) -> Optional[SessionConfiguration]:
        """Get the default configuration for a user."""
        query = self.db.query(SessionConfiguration).filter(
            SessionConfiguration.is_default == True
        )
        if user_id:
            query = query.filter(SessionConfiguration.user_id == user_id)
        return query.first()

    def update(
        self,
        config_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        tts_provider: Optional[str] = None,
        tts_voice_id: Optional[str] = None,
        voice_tuning: Optional[dict] = None,
        system_prompt_id: Optional[str] = None,
        optimization_level: Optional[str] = None,
        target_language: Optional[str] = None,
        enable_rag: Optional[bool] = None,
        is_default: Optional[bool] = None,
        meta_data: Optional[dict] = None,
    ) -> Optional[SessionConfiguration]:
        """Update a configuration."""
        config = self.get(config_id)
        if not config:
            return None

        if name is not None:
            config.name = name
        if description is not None:
            config.description = description
        if llm_provider is not None:
            config.llm_provider = llm_provider
        if llm_model is not None:
            config.llm_model = llm_model
        if tts_provider is not None:
            config.tts_provider = tts_provider
        if tts_voice_id is not None:
            config.tts_voice_id = tts_voice_id
        if voice_tuning is not None:
            config.voice_tuning = voice_tuning
        if system_prompt_id is not None:
            config.system_prompt_id = system_prompt_id
        if optimization_level is not None:
            config.optimization_level = optimization_level
        if target_language is not None:
            config.target_language = target_language
        if enable_rag is not None:
            config.enable_rag = enable_rag
        if is_default is not None:
            if is_default:
                # Unset other defaults
                self._unset_defaults(config.user_id)
            config.is_default = is_default
        if meta_data is not None:
            config.meta_data = meta_data

        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config_id: str) -> bool:
        """Delete a configuration."""
        config = self.get(config_id)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()
        return True

    def _unset_defaults(self, user_id: Optional[str] = None) -> None:
        """Unset all existing default configurations for a user."""
        query = self.db.query(SessionConfiguration).filter(
            SessionConfiguration.is_default == True
        )
        if user_id:
            query = query.filter(SessionConfiguration.user_id == user_id)
        query.update({"is_default": False})
        self.db.commit()

