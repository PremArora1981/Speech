"""Tests for API authentication middleware."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config.settings import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_health_requires_api_key(client, monkeypatch):
    original = settings.sarvam_api_key
    settings.sarvam_api_key = "secret"

    response = client.get("/api/v1/health")
    assert response.status_code == 401

    response_ok = client.get("/api/v1/health", headers={"X-API-Key": "secret"})
    assert response_ok.status_code == 200

    settings.sarvam_api_key = original

