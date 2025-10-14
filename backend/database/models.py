"""SQLAlchemy models for backend persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
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
    metadata = Column(JSON, default=dict)
    credential_ref = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ref = Column(String, nullable=False, unique=True)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
