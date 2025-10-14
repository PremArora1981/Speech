"""Tests for repository layer."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base
from backend.database.repositories import SessionRepository, CostRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_session_and_message(db_session):
    repo = SessionRepository(db_session)
    session = repo.create_session("en-IN", "balanced")
    message = repo.add_message(session.id, "user", "Hello")

    assert message.session_id == session.id
    assert message.transcript == "Hello"


def test_log_cost(db_session):
    repo = CostRepository(db_session)
    record = repo.log_cost("tts", 0.01)
    assert record.cost_usd == 0.01

