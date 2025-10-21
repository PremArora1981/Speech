"""SQLAlchemy models for backend persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Numeric, Index
from sqlalchemy.types import JSON
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    language_code = Column(String(10), nullable=False, default="en-IN")
    optimization_level = Column(String(32), nullable=False, default="balanced")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    transcript = Column(Text)
    translated_text = Column(Text)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")


class CostTracking(Base):
    __tablename__ = "cost_tracking"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(DateTime, default=datetime.utcnow)
    service = Column(String(50), nullable=False)
    cost_usd = Column(Float, nullable=False, default=0.0)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_url = Column(String, nullable=False, unique=True)
    checksum = Column(String, nullable=False)
    title = Column(String, nullable=True)
    last_ingested_at = Column(DateTime, default=datetime.utcnow)


class TelephonyTrunk(Base):
    __tablename__ = "telephony_trunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)
    trunk_id = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # inbound | outbound
    sip_uri = Column(String, nullable=False)
    transport = Column(String, nullable=True)
    meta_data = Column(JSON, default=dict)
    credential_ref = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ref = Column(String, nullable=False, unique=True)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GuardrailViolation(Base):
    """Track guardrail violations for monitoring and compliance."""
    __tablename__ = "guardrail_violations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True)
    turn_id = Column(String, nullable=True)
    violation_type = Column(String(50), nullable=False)  # input, output, content, pii
    layer = Column(Integer, nullable=False)  # 1=pre-llm, 2=prompt, 3=post-llm
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    violated_rule = Column(String(100), nullable=False)  # e.g., "medical_advice", "pii_credit_card"
    input_text = Column(Text, nullable=True)  # Sanitized input that triggered violation
    output_text = Column(Text, nullable=True)  # Sanitized output that triggered violation
    safe_response = Column(Text, nullable=True)  # Safe fallback response provided
    meta_data = Column(JSON, default=dict)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_guardrail_session_created', 'session_id', 'created_at'),
        Index('ix_guardrail_type_created', 'violation_type', 'created_at'),
        Index('ix_guardrail_severity_created', 'severity', 'created_at'),
    )


class CostEntry(Base):
    """Enhanced cost tracking with per-service attribution."""
    __tablename__ = "cost_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True)
    turn_id = Column(String, nullable=True)
    service = Column(String(50), nullable=False)  # asr, llm, translation, tts
    provider = Column(String(50), nullable=False)  # sarvam, elevenlabs, openai
    operation = Column(String(50), nullable=False)  # transcribe, generate, translate, synthesize
    units = Column(Integer, nullable=False)  # tokens, characters, audio_ms
    unit_type = Column(String(20), nullable=False)  # tokens, chars, audio_ms
    cost_usd = Column(Numeric(10, 6), nullable=False)  # Precise decimal cost
    optimization_level = Column(String(32), nullable=True)
    cached = Column(Boolean, default=False)  # Was this a cache hit?
    meta_data = Column(JSON, default=dict)  # Additional metadata (model, latency, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_cost_session_created', 'session_id', 'created_at'),
        Index('ix_cost_service_created', 'service', 'created_at'),
        Index('ix_cost_provider_created', 'provider', 'created_at'),
    )


class SessionMetrics(Base):
    """Aggregated metrics per session for analytics."""
    __tablename__ = "session_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, unique=True)

    # Turn counts
    total_turns = Column(Integer, default=0)
    successful_turns = Column(Integer, default=0)
    failed_turns = Column(Integer, default=0)
    interrupted_turns = Column(Integer, default=0)

    # Latency metrics (milliseconds)
    avg_asr_latency_ms = Column(Float, nullable=True)
    avg_llm_latency_ms = Column(Float, nullable=True)
    avg_translation_latency_ms = Column(Float, nullable=True)
    avg_tts_latency_ms = Column(Float, nullable=True)
    avg_total_latency_ms = Column(Float, nullable=True)

    # Cache metrics
    cache_hit_rate = Column(Float, nullable=True)  # 0.0 - 1.0
    llm_cache_hits = Column(Integer, default=0)
    llm_cache_misses = Column(Integer, default=0)
    tts_cache_hits = Column(Integer, default=0)
    tts_cache_misses = Column(Integer, default=0)

    # Guardrail metrics
    guardrail_violations = Column(Integer, default=0)
    guardrail_blocks = Column(Integer, default=0)

    # Cost metrics
    total_cost_usd = Column(Numeric(10, 6), default=0.0)
    asr_cost_usd = Column(Numeric(10, 6), default=0.0)
    llm_cost_usd = Column(Numeric(10, 6), default=0.0)
    translation_cost_usd = Column(Numeric(10, 6), default=0.0)
    tts_cost_usd = Column(Numeric(10, 6), default=0.0)

    # Quality metrics
    avg_asr_confidence = Column(Float, nullable=True)
    avg_user_satisfaction = Column(Float, nullable=True)  # From feedback ratings

    # Session info
    optimization_level = Column(String(32), nullable=True)
    language_code = Column(String(10), nullable=True)
    session_duration_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_metrics_created', 'created_at'),
        Index('ix_metrics_optimization', 'optimization_level', 'created_at'),
    )


class UserFeedback(Base):
    """User feedback on responses for quality monitoring."""
    __tablename__ = "user_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    turn_id = Column(String, nullable=True)
    message_id = Column(String, ForeignKey("messages.id"), nullable=True)

    # Rating
    rating = Column(Integer, nullable=False)  # 1-5 stars, or -1/1 for thumbs down/up
    rating_type = Column(String(20), nullable=False, default="thumbs")  # thumbs, stars

    # Feedback details
    feedback_text = Column(Text, nullable=True)
    feedback_category = Column(String(50), nullable=True)  # accuracy, speed, relevance, etc.

    # Issue flags
    incorrect_response = Column(Boolean, default=False)
    too_slow = Column(Boolean, default=False)
    unhelpful = Column(Boolean, default=False)
    offensive = Column(Boolean, default=False)

    # Context
    user_input = Column(Text, nullable=True)
    assistant_response = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_feedback_session_created', 'session_id', 'created_at'),
        Index('ix_feedback_rating_created', 'rating', 'created_at'),
    )


class TurnEvent(Base):
    """Detailed event log for each conversation turn."""
    __tablename__ = "turn_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    turn_id = Column(String, nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)  # asr_start, asr_complete, llm_start, etc.
    event_status = Column(String(20), nullable=False)  # started, completed, failed, interrupted
    stage = Column(String(20), nullable=False)  # asr, llm, translation, tts

    # Timing
    latency_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Result data
    result_data = Column(JSON, default=dict)  # Service-specific results
    error_message = Column(Text, nullable=True)

    # Performance
    tokens_used = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_turn_session_turn', 'session_id', 'turn_id', 'timestamp'),
        Index('ix_turn_event_type', 'event_type', 'created_at'),
    )


class SystemPrompt(Base):
    """System prompts for LLM conversations."""
    __tablename__ = "system_prompts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    prompt_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # customer_support, sales, technical, etc.
    is_default = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)  # Built-in templates vs user-created
    variables = Column(JSON, default=list)  # List of variable names used in prompt
    meta_data = Column(JSON, default=dict)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_prompt_category', 'category'),
        Index('ix_prompt_is_default', 'is_default'),
    )


class SessionConfiguration(Base):
    """Session-specific configuration for voice chat."""
    __tablename__ = "session_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)  # Optional user association
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # LLM configuration
    llm_provider = Column(String(50), nullable=False, default="sarvam")
    llm_model = Column(String(100), nullable=False, default="sarvam-1")

    # TTS configuration
    tts_provider = Column(String(50), nullable=False, default="sarvam")
    tts_voice_id = Column(String(100), nullable=False, default="anushka")
    voice_tuning = Column(JSON, default=dict)  # {pitch: float, pace: float, loudness: float}

    # System prompt
    system_prompt_id = Column(String, ForeignKey("system_prompts.id"), nullable=True)

    # Other settings
    optimization_level = Column(String(32), nullable=False, default="balanced")
    target_language = Column(String(10), nullable=False, default="en-IN")
    enable_rag = Column(Boolean, default=False)

    # Metadata
    is_default = Column(Boolean, default=False)
    meta_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_config_user', 'user_id'),
        Index('ix_config_is_default', 'is_default'),
    )
