"""Tests for TranslationService."""

import pytest

from backend.services.translation_service import TranslationService, TranslationConfig


class MockTranslationClient:
    def __init__(self):
        self.requests = []

    async def post(self, path, json=None, headers=None, timeout=None):
        self.requests.append(json)

        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"translated_text": "Hola"}

        return MockResponse()

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_translate_sends_config():
    client = MockTranslationClient()
    service = TranslationService(client=client)
    config = TranslationConfig(colloquial=True, formality_level=20, code_mixing_enabled=True, english_ratio=60)
    text = await service.translate("Hello", "en-IN", "es-ES", config=config)

    payload = client.requests[-1]
    assert payload["colloquial"] is True
    assert payload["english_ratio"] == 60
    assert text == "Hola"

