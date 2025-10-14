# Speech Backend Overview

## Text-to-Speech Service

The backend provides a modular TTS service orchestrating Sarvam AI and ElevenLabs providers with translation-aware voice selection, caching, and telemetry.

### Features

- **Providers**: Sarvam (default) and ElevenLabs with automatic fallback to Sarvam for unsupported languages or failures.
- **Voice Registry**: Pre-configured voices across providers with language alignment, accessible via `VoiceRegistry`.
- **Caching**: Optional Redis-backed TTS caching keyed on text, language, voice, codec, and sample rate with optimization-level TTLs.
- **Metrics**: Prometheus counters and histograms for request volume, latency, cache hits, failures, and fallback transitions.
- **Schemas**: Pydantic v2 models validating requests (`SynthesizeRequest`) and responses (`SynthesizeResponse`).
- **Testing**: Async unit tests covering provider orchestration, caching behaviour, and fallback safety.

### Configuration

Environment variables (see `backend/config/settings.py` for full list):

| Variable | Description |
|----------|-------------|
| `SARVAM_API_KEY` | Required Sarvam API subscription key |
| `ELEVENLABS_API_KEY` | Optional key when ElevenLabs provider is enabled |
| `REDIS_URL` | Redis connection string for caching (optional) |
| `DEFAULT_TTS_PROVIDER` | `sarvam` (default) or `elevenlabs` |
| `DEFAULT_TTS_AUDIO_CODEC` | Desired codec (`wav`, `mp3`, etc.) |
| `TTS_CACHE_TTL_QUALITY` | TTL (seconds) for quality optimization tier |
| `TTS_CACHE_TTL_BALANCED` | TTL (seconds) for balanced tier |
| `TTS_CACHE_TTL_SPEED` | TTL (seconds) for speed tiers |

Set `PYTHONPATH` to project root when running tests locally.

Example `.env` stub:

```env
ENVIRONMENT=development
DEBUG=false

SARVAM_API_KEY=changeme
ELEVENLABS_API_KEY=

DEFAULT_TTS_PROVIDER=sarvam
DEFAULT_TTS_AUDIO_CODEC=wav
DEFAULT_TTS_SAMPLE_RATE=22050
DEFAULT_OPTIMIZATION_LEVEL=balanced

REDIS_URL=redis://localhost:6379/0
TTS_CACHE_TTL_QUALITY=1800
TTS_CACHE_TTL_BALANCED=900
TTS_CACHE_TTL_SPEED=300
```

### Metrics

Prometheus metrics exposed in `backend/utils/metrics.py`:

- `tts_requests_total{provider,cache}`
- `tts_latency_seconds{provider}`
- `tts_cache_hits_total{provider}`
- `tts_failures_total{provider,reason}`
- `tts_fallback_total{from_provider,to_provider}`

### Running Tests

```
pytest backend/tests/test_tts_service.py backend/tests/test_voice_registry.py
```

Ensure virtualenv is activated and dependencies installed (see requirements in code comments).


