# Backend Architecture Overview

## High-Level Flow

```
Audio Input → ASR Service → LLM Orchestrator → Translation Service → TTS Orchestrator → Audio Output
                        ↘ Guardrails & RAG ↗
```

1. **Ingress**
   - REST `/api/v1/tts` (existing) and forthcoming WebSocket `/api/v1/voice-session` handle session lifecycle.
   - Auth via API key header; rate limiting middleware planned in `api/middleware.py`.

2. **ASR Service (`backend/services/asr_service.py`)**
   - Wraps Sarvam ASR API for streaming and batch transcription.
   - Emits structured transcript payload `{text_en, language_code, confidence}`.
   - optional VAD hooks for barge-in.

3. **LLM Service (`backend/services/llm_service.py`)**
   - Single-call orchestration enforcing guardrails.
   - Integrates RAG context provider (`backend/services/rag_service.py`).
   - Produces response text + safety metadata.

4. **Translation Service (`backend/services/translation_service.py`)**
   - Applies colloquial/code-mixing configuration per session.
   - Uses Sarvam translation API with caching.

5. **TTS Service (`backend/services/tts_service.py`)**
   - Already implemented with Sarvam/ElevenLabs + caching & metrics.

6. **Persistence (`backend/repository/`)**
   - PostgreSQL for sessions, messages, cost tracking.
   - Redis for short-lived cache (ASR segments, translation, TTS).

7. **Observability**
   - Prometheus metrics via `/metrics`.
   - Structured logging with correlation IDs (planned `backend/utils/logging.py`).

## External Dependencies

| Service | Provider | Status | File |
|---------|----------|--------|------|
| ASR | Sarvam SaaS | TODO | `services/asr_service.py` |
| LLM | Sarvam (`sarvam-m`) + optional OpenAI | TODO | `services/llm_service.py` |
| Translation | Sarvam | TODO | `services/translation_service.py` |
| TTS | Sarvam, ElevenLabs | DONE | `services/tts_service.py` |
| RAG Vector DB | Pinecone or Weaviate | TODO | `services/rag_service.py` |
| Caching | Redis | PARTIAL | `utils/cache.py` |
| Persistence | PostgreSQL | TODO | `repository/session_repository.py` |

## Module Responsibilities

- `backend/api/`: FastAPI routers, dependencies, middleware.
- `backend/services/`: stateless service classes orchestrating providers.
- `backend/repository/`: database repositories and migrations.
- `backend/utils/`: shared helpers (cache, metrics, logging, voice registry).
- `backend/schemas/`: Pydantic models for transport and validation.

## Data Contracts

### Transcript Payload
```json
{
  "text": "Customer request in English",
  "language_code": "hi-IN",
  "confidence": 0.92,
  "raw_segments": [ ... ]
}
```

### LLM Response Payload
```json
{
  "response_text": "Localized response",
  "guardrail_flags": {"safe": true},
  "metadata": {"tokens": 345}
}
```

## TODO Summary

- [ ] Implement ASR wrapper and tests.
- [ ] Implement LLM orchestration with guardrails.
- [ ] Implement translation service and caching.
- [ ] Build RAG connector.
- [ ] Define repositories and migrations.
- [ ] Add middleware for auth/rate limiting.
- [ ] Wire WebSocket voice-session endpoint.


