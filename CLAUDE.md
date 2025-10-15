# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Speech AI Voice Chat is a full-stack conversational voice assistant with real-time audio processing. The backend orchestrates a multi-stage pipeline: **ASR → LLM → Translation → TTS**, with optional RAG context augmentation. The frontend provides a React-based voice chat interface with telephony integration.

## Architecture

### Backend (FastAPI + Python)

The backend is organized into modular services that can be composed:

- **Conversation Pipeline** (`backend/services/conversation_pipeline.py`): Main orchestrator that chains ASR → LLM → Translation → TTS. Entry point for voice session handling.
- **TTS Orchestrator** (`backend/services/tts_service.py`): Provider-agnostic TTS with fallback logic (Sarvam ↔ ElevenLabs), Redis caching, and Prometheus metrics.
- **Voice Registry** (`backend/utils/voice_registry.py`): Centralized voice catalog mapping language codes to provider-specific voices.
- **ASR Service** (`backend/services/asr_service.py`): Sarvam speech-to-text with batch and streaming transcription.
- **Translation Service** (`backend/services/translation_service.py`): Language translation layer.
- **LLM Service** (`backend/services/llm_service.py`): LLM-based conversational response generation, optionally augmented with RAG context.
- **RAG Service** (`backend/services/rag_service.py`): Weaviate vector store + OpenAI embeddings for document retrieval. Includes URL ingestion.
- **Telephony Service** (`backend/services/telephony_service.py`): LiveKit SIP adapter for outbound/inbound telephony trunks and call initiation.

#### Key Backend Patterns

- **Settings**: All configuration lives in `backend/config/settings.py` (Pydantic BaseSettings). Load from `.env`.
- **Dependency Injection**: Services accept optional client instances in `__init__` for testability.
- **API Authentication**: All `/api/v1/*` routes require `X-API-Key` header (see `backend/api/dependencies.py:8`).
- **Database**: SQLite by default (`backend/database/models.py`). Repositories pattern for data access (`backend/database/repositories.py`).
- **Secrets**: Encrypted storage for telephony credentials using `backend/utils/secrets.py` and `ENCRYPTION_KEY` env var.

### Frontend (React + TypeScript + Vite)

- **VoiceChat Component** (`frontend/src/modules/chat/VoiceChat.tsx`): WebSocket-based real-time audio streaming to backend `/api/v1/voice-session`.
- **TelephonyDashboard** (`frontend/src/modules/admin/TelephonyDashboard.tsx`): Admin UI for SIP trunk management and outbound calls.
- **Optimization Levels**: User-adjustable quality/latency slider (`quality`, `balanced_quality`, `balanced`, `balanced_speed`, `speed`) affects caching TTL and processing modes.

## Development Commands

### Backend

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend server (default port 8000)
uvicorn backend.main:app --reload

# Run all tests
pytest backend/tests

# Run specific test file
pytest backend/tests/test_tts_service.py

# Run tests with verbose output
pytest backend/tests -v

# Set PYTHONPATH before running tests locally (if needed)
set PYTHONPATH=%CD%
pytest backend/tests
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (default port 5173)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm run test
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Required
- `SARVAM_API_KEY`: Sarvam API subscription key (used for both TTS and ASR)
- `ENCRYPTION_KEY`: Base64-encoded 32-byte key for encrypting telephony secrets

### Optional (TTS)
- `ELEVENLABS_API_KEY`: ElevenLabs API key (only needed if using ElevenLabs provider)
- `DEFAULT_TTS_PROVIDER`: `sarvam` (default) or `elevenlabs`
- `DEFAULT_TTS_AUDIO_CODEC`: `wav` (default), `mp3`, `opus`, etc.
- `DEFAULT_TTS_SAMPLE_RATE`: `22050` (default)
- `DEFAULT_OPTIMIZATION_LEVEL`: `quality`, `balanced_quality`, `balanced`, `balanced_speed`, `speed`

### Optional (Caching)
- `REDIS_URL`: Redis connection string for TTS caching (e.g., `redis://localhost:6379/0`)
- `TTS_CACHE_TTL_QUALITY`: TTL in seconds for quality tier (default: 1800)
- `TTS_CACHE_TTL_BALANCED`: TTL in seconds for balanced tier (default: 900)
- `TTS_CACHE_TTL_SPEED`: TTL in seconds for speed tier (default: 300)

### Optional (RAG)
- `WEAVIATE_URL`: Weaviate instance URL (default: `http://localhost:8080`)
- `WEAVIATE_API_KEY`: Weaviate authentication key
- `OPENAI_API_KEY`: OpenAI API key for embeddings
- `OPENAI_EMBEDDING_MODEL`: Embedding model name (default: `text-embedding-3-small`)

### Optional (Telephony)
- `LIVEKIT_PROJECT_URL`: LiveKit Cloud project URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret

### Optional (Database)
- `DATABASE_URL`: SQLAlchemy connection string (default: `sqlite:///./speech.db`)

## Testing Strategy

- **Unit Tests**: Mock external API clients in service tests (e.g., `test_tts_service.py` mocks `SarvamTTSClient`).
- **Integration Tests**: `test_integration_pipeline.py` and `test_conversation_pipeline.py` test cross-service workflows.
- **Load Tests**: `test_load_pipeline.py` for performance validation.
- **Frontend Tests**: Vitest + React Testing Library for component tests.

## Key Implementation Notes

### TTS Provider Fallback Logic

When a TTS request fails or the requested voice/language is unavailable:
1. Check if requested provider supports the language (`backend/services/tts_service.py:215`)
2. Fall back to Sarvam with language-specific voice (`backend/services/tts_service.py:233`)
3. If no language match, fall back to `en-IN` default voice
4. Fallback events emit Prometheus metrics (`tts_fallback_total`)

### Voice Session WebSocket Protocol

Messages to `/api/v1/voice-session` must include:
- `type`: `"start"`, `"audio"`, or `"stop"`
- `sessionId`: Unique session identifier
- `optimizationLevel`: Performance tier (affects caching and streaming)
- `audio` (for `type: "audio"`): Base64-encoded audio chunk
- `timestamp` (optional): Client timestamp for latency tracking

### Telephony Flow

1. Register SIP trunk via `POST /api/v1/telephony/trunks` (stores in database + encrypts credentials)
2. List trunks via `GET /api/v1/telephony/trunks` (syncs LiveKit state to local DB)
3. Initiate call via `POST /api/v1/telephony/calls` (creates LiveKit SIP participant in room)

### RAG Document Ingestion

Use `RAGService.ingest_url(url)` to:
1. Fetch and parse URL content via `URLIngestor` (`backend/ingestion/url_ingestor.py`)
2. Chunk text and generate OpenAI embeddings
3. Store in Weaviate `DocumentChunk` class with metadata (source URL, checksum, chunk index)
4. Track ingested documents in SQLite via `DocumentRepository`

## API Endpoints

- `POST /api/v1/tts`: Synthesize speech (request body: `SynthesizeRequest`)
- `GET /metrics`: Prometheus metrics endpoint
- `WS /api/v1/voice-session`: Real-time voice conversation WebSocket
- `POST /api/v1/telephony/calls`: Initiate outbound SIP call
- `GET /api/v1/telephony/trunks`: List registered SIP trunks
- `POST /api/v1/telephony/trunks`: Register new SIP trunk
- `GET /api/v1/health`: Health check

All `/api/v1/*` routes require `X-API-Key` header matching `SARVAM_API_KEY`.

## Metrics

Prometheus metrics are exposed at `/metrics`:
- `tts_requests_total{provider, cache}`: Total TTS requests
- `tts_latency_seconds{provider}`: TTS request latency histogram
- `tts_cache_hits_total{provider}`: Cache hit counter
- `tts_failures_total{provider, reason}`: TTS failure counter
- `tts_fallback_total{from_provider, to_provider}`: Provider fallback counter

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push/PR:
- Python 3.12
- Installs dependencies from `requirements.txt`
- Runs `pytest backend/tests`

---

# IMPLEMENTATION ROADMAP

Based on Requirements_v2.txt, here is the comprehensive to-do list for implementing all required features.

## Current Status Assessment

### ✅ Already Implemented (MVP Foundation)
- [x] Basic FastAPI backend with WebSocket support
- [x] Sarvam ASR integration (speech-to-text)
- [x] LLM service with Sarvam integration
- [x] Translation service
- [x] TTS orchestrator with dual provider support (Sarvam/ElevenLabs)
- [x] Voice registry with language mapping
- [x] Redis caching for TTS
- [x] Prometheus metrics
- [x] RAG service with Weaviate + OpenAI embeddings
- [x] Basic telephony integration via LiveKit
- [x] Secret encryption for telephony credentials
- [x] React frontend with TypeScript
- [x] Basic voice chat UI with optimization level slider
- [x] Telephony dashboard
- [x] Database models and repositories
- [x] API authentication with X-API-Key header

## Phase 1: Quality-Latency Optimization System (High Priority)

### Backend: Optimization Level Implementation
- [ ] **Enhance ConversationPipeline with optimization-aware processing** (`backend/services/conversation_pipeline.py`)
  - [ ] Implement streaming vs. batch processing based on level
  - [ ] Add speculation thresholds (conservative/moderate/aggressive)
  - [ ] Implement parallel vs. sequential execution modes
  - [ ] Add shortcut paths for speed levels
  - [ ] Implement response truncation for max speed level

- [ ] **Extend caching strategies beyond TTS** (`backend/utils/cache.py`)
  - [ ] Add semantic similarity caching for "balanced quality" level
  - [ ] Implement aggressive caching for "balanced speed" level
  - [ ] Add cache warming/prefetching for "speed" level
  - [ ] Cache LLM responses by query similarity

- [ ] **Implement RAG depth controls** (`backend/services/rag_service.py`)
  - [ ] Quality level: Retrieve 10 chunks with deep search
  - [ ] Balanced Quality: Retrieve 5 chunks
  - [ ] Balanced: Retrieve 3 chunks
  - [ ] Balanced Speed: Retrieve 1-2 chunks
  - [ ] Speed: Skip RAG entirely

- [ ] **Add optimization configuration to settings** (`backend/config/settings.py`)
  - [ ] Add configuration mapping for each of 5 optimization levels
  - [ ] Add streaming thresholds and confidence levels
  - [ ] Add LLM temperature settings per level

### Frontend: Enhanced Optimization Controls
- [ ] **Improve PerformanceSettings component** (`frontend/src/App.tsx`)
  - [ ] Add real-time accuracy/speed gauges
  - [ ] Display warnings for extreme levels (max speed)
  - [ ] Show expected latency ranges for each level
  - [ ] Add visual feedback for current optimization impact

- [ ] **Add latency monitoring dashboard**
  - [ ] Create real-time latency breakdown chart
  - [ ] Display ASR, LLM, Translation, TTS latencies separately
  - [ ] Show P50, P95, P99 latency metrics
  - [ ] Add historical latency trends

## Phase 2: Advanced Audio Features (High Priority)

### Barge-In System
- [ ] **Implement Voice Activity Detection (VAD)**
  - [ ] Add WebRTC VAD in frontend audio processor (`frontend/src/services/audio/AudioRecorder.ts`)
  - [ ] Implement configurable sensitivity (0-1 scale)
  - [ ] Add minimum speech duration threshold (300ms)
  - [ ] Add sustained duration check (500ms)

- [ ] **Backend barge-in handling** (`backend/services/conversation_pipeline.py`)
  - [ ] Add interrupt signal handling in WebSocket
  - [ ] Implement TTS cancellation on interrupt
  - [ ] Preserve conversation context on barge-in
  - [ ] Add option to resume playback after false positive

- [ ] **Frontend barge-in UI**
  - [ ] Create BargeInSettings component
  - [ ] Add enable/disable toggle
  - [ ] Add VAD sensitivity slider
  - [ ] Add interruption delay control (0-500ms)
  - [ ] Add "resume after false trigger" option

### Noise Handling (Multi-Layer)
- [ ] **Frontend WebRTC noise suppression** (`frontend/src/services/audio/AudioRecorder.ts`)
  - [ ] Implement WebRTC noise suppression controls
  - [ ] Add echo cancellation
  - [ ] Add auto-gain control
  - [ ] Create quick presets (quiet/moderate/noisy)

- [ ] **Backend audio preprocessing**
  - [ ] Add high-pass filter for noise reduction
  - [ ] Implement Sarvam preprocessing option
  - [ ] Add audio quality validation (SNR, clipping detection)

- [ ] **Real-time quality monitoring**
  - [ ] Create AudioQualityMonitor component
  - [ ] Display real-time audio quality score
  - [ ] Show quality warnings and suggestions
  - [ ] Track and display signal-to-noise ratio

### Background Noise Injection (Testing Only)
- [ ] **Create noise injection service**
  - [ ] Add noise audio file library (call center, cafe, street, office)
  - [ ] Implement audio mixing in frontend
  - [ ] Add configurable noise volume (0-1)
  - [ ] Create noise preview functionality

- [ ] **Frontend noise injection UI**
  - [ ] Create NoiseInjection component
  - [ ] Add noise type selector (grid layout)
  - [ ] Add noise volume slider
  - [ ] Add specific noise options (e.g., call center: chatter, typing, phone rings)
  - [ ] Add preview button

## Phase 3: Language & Voice Features (Medium Priority)

### Colloquial Language & Code-Mixing
- [ ] **Enhance translation service** (`backend/services/translation_service.py`)
  - [ ] Add formality level parameter (0-100 scale)
  - [ ] Implement mode mapping (formal/conversational/informal)
  - [ ] Add code-mixing support with English ratio control
  - [ ] Implement domain-specific term preservation (tech, business)

- [ ] **Frontend language settings UI**
  - [ ] Create LanguageSettings component
  - [ ] Add colloquial language toggle
  - [ ] Add formality level slider (0-100)
  - [ ] Add code-mixing toggle
  - [ ] Add English mix ratio slider
  - [ ] Add domain preservation checkboxes

### Voice Selection & Preview
- [ ] **Expand voice registry** (`backend/utils/voice_registry.py`)
  - [ ] Add voice metadata (gender, characteristics, language support)
  - [ ] Create voice preview endpoint

- [ ] **Create voice preview API endpoint**
  - [ ] Add `POST /api/v1/tts/preview` endpoint
  - [ ] Support both standard and custom text preview
  - [ ] Return audio for immediate playback

- [ ] **Frontend voice selection UI**
  - [ ] Create VoiceSettings component with gallery view
  - [ ] Add provider selector (Sarvam/ElevenLabs)
  - [ ] Display voice cards with metadata
  - [ ] Add standard preview button per voice
  - [ ] Add custom text preview input and playback
  - [ ] Add voice tuning controls (pitch, speed, volume) for Sarvam

## Phase 4: SIP Trunk Integration Enhancement (Medium Priority)

### Multi-Provider SIP Support
- [ ] **Extend telephony adapters** (`backend/services/telephony_service.py`)
  - [ ] Add Twilio adapter class
  - [ ] Add Vonage/Nexmo adapter class
  - [ ] Add Bandwidth adapter class
  - [ ] Create generic custom SIP adapter

- [ ] **Add SIP trunk configuration models**
  - [ ] Add provider-specific credential schemas
  - [ ] Add webhook configuration support
  - [ ] Add IVR configuration models

- [ ] **Create SIP configuration endpoints**
  - [ ] Add provider-specific configuration validation
  - [ ] Add test connection endpoint
  - [ ] Add webhook registration endpoints

### Frontend SIP Configuration UI
- [ ] **Create comprehensive SIPConfiguration component**
  - [ ] Add provider selector dropdown
  - [ ] Add Twilio configuration form
  - [ ] Add Vonage configuration form
  - [ ] Add Bandwidth configuration form
  - [ ] Add custom SIP configuration form
  - [ ] Add connection testing button
  - [ ] Add webhook configuration section
  - [ ] Add IVR settings

## Phase 5: Guardrails & Safety (High Priority)

### Multi-Layer Guardrail System
- [ ] **Create guardrail service** (`backend/services/guardrail_service.py`)
  - [ ] Implement pre-LLM keyword blocking
  - [ ] Add configurable blocked terms list
  - [ ] Create fast pattern matching for common violations

- [ ] **Enhance LLM service with guardrails** (`backend/services/llm_service.py`)
  - [ ] Add guardrail instructions to system prompt
  - [ ] Define strict rules (product-only, no medical/legal advice, no PII)
  - [ ] Implement scope limitation prompts

- [ ] **Implement post-LLM validation**
  - [ ] Add PII detection (credit cards, SSN, etc.)
  - [ ] Add response length validation
  - [ ] Add content safety checks
  - [ ] Create fallback responses for violations

- [ ] **Create guardrail management database tables**
  - [ ] Add guardrail_rules table
  - [ ] Add violation logging
  - [ ] Add rule enable/disable functionality

### Admin Guardrail Management
- [ ] **Create admin guardrail UI**
  - [ ] Add GuardrailSettings component
  - [ ] Display active rules list
  - [ ] Add rule enable/disable toggles
  - [ ] Add blocked keyword management
  - [ ] Display violation statistics

## Phase 6: Test Agent Mode (Medium Priority)

### Real API Testing Infrastructure
- [ ] **Create test scenario system**
  - [ ] Define test scenario JSON schema
  - [ ] Create scenario storage/loading mechanism
  - [ ] Implement automated scenario execution
  - [ ] Add scenario step validation

- [ ] **Create test agent service** (`backend/services/test_agent_service.py`)
  - [ ] Implement real API execution (no mocks)
  - [ ] Add metrics collection per test
  - [ ] Add audio recording for all tests
  - [ ] Implement automated evaluation (ASR accuracy, latency, relevance)

- [ ] **Create scenario library**
  - [ ] Add order status flow scenario
  - [ ] Add product inquiry scenario
  - [ ] Add multilingual scenarios
  - [ ] Add error handling scenarios
  - [ ] Add barge-in test scenarios

### Frontend Test Agent UI
- [ ] **Create TestAgentInterface component**
  - [ ] Implement split layout (agent panel + metrics panel)
  - [ ] Add live conversation display
  - [ ] Add real-time metrics display (ASR, LLM, Total latency)
  - [ ] Add test controls (start/stop)
  - [ ] Add noise injection controls in test mode
  - [ ] Add scenario library browser
  - [ ] Add automated test execution
  - [ ] Add test results dashboard
  - [ ] Add latency breakdown charts
  - [ ] Add pass/fail statistics

## Phase 7: Advanced Pipeline Features (Low Priority)

### Streaming & Speculation
- [ ] **Implement ASR streaming support** (`backend/services/asr_service.py`)
  - [ ] Enhance stream_transcribe for real-time partial results
  - [ ] Add confidence threshold filtering

- [ ] **Add speculative execution to pipeline** (`backend/services/conversation_pipeline.py`)
  - [ ] Implement early LLM triggering based on partial transcript
  - [ ] Add confidence-based speculation thresholds
  - [ ] Implement cancellation of speculative calls

- [ ] **Add parallel processing for independent operations**
  - [ ] Parallelize translation and TTS preparation where safe
  - [ ] Add parallel RAG retrieval
  - [ ] Implement proper error handling for parallel operations

## Phase 8: Monitoring & Analytics Enhancements (Low Priority)

### Extended Metrics
- [ ] **Add comprehensive metrics** (`backend/utils/metrics.py`)
  - [ ] Add ASR accuracy tracking
  - [ ] Add LLM response quality metrics
  - [ ] Add user satisfaction metrics
  - [ ] Add language distribution metrics
  - [ ] Add cost tracking per conversation

- [ ] **Create analytics database tables**
  - [ ] Add cost_tracking table with service breakdown
  - [ ] Add user feedback collection
  - [ ] Add conversation quality ratings

### Admin Analytics Dashboard
- [ ] **Create comprehensive analytics UI**
  - [ ] Add real-time performance dashboard
  - [ ] Add quality trends over time charts
  - [ ] Add cost tracking visualizations
  - [ ] Add language distribution charts
  - [ ] Add user satisfaction trends

## Phase 9: Security & Compliance (High Priority)

### Enhanced Security
- [ ] **Implement data encryption**
  - [ ] Add AES-256-GCM encryption for data at rest
  - [ ] Ensure TLS 1.3 for all external connections
  - [ ] Implement API key rotation mechanism
  - [ ] Add rate limiting to prevent abuse

- [ ] **Add security audit logging**
  - [ ] Log all authentication attempts
  - [ ] Log all API key usage
  - [ ] Log all data access
  - [ ] Add alerting for suspicious activity

### GDPR Compliance
- [ ] **Create GDPR service** (`backend/services/gdpr_service.py`)
  - [ ] Implement user data export (right to access)
  - [ ] Implement user data deletion (right to erasure)
  - [ ] Add data retention policies
  - [ ] Create consent management

- [ ] **Add GDPR endpoints**
  - [ ] Add `GET /api/v1/user/{id}/data` for data export
  - [ ] Add `DELETE /api/v1/user/{id}` for data deletion
  - [ ] Add consent tracking endpoints

## Phase 10: Production Readiness (High Priority)

### Infrastructure & Deployment
- [ ] **Create Docker configuration**
  - [ ] Add optimized Dockerfile
  - [ ] Create docker-compose.yml for local development
  - [ ] Add separate configs for frontend/backend

- [ ] **Create Kubernetes manifests**
  - [ ] Add Deployment configuration
  - [ ] Add Service configuration
  - [ ] Add HorizontalPodAutoscaler
  - [ ] Add ConfigMap and Secret management
  - [ ] Add Ingress configuration

- [ ] **Setup monitoring infrastructure**
  - [ ] Deploy Prometheus
  - [ ] Create Grafana dashboards
  - [ ] Add Sentry for error tracking
  - [ ] Configure alerting rules

### Cost Management
- [ ] **Implement budget controls** (`backend/services/cost_service.py`)
  - [ ] Add monthly budget limits
  - [ ] Implement alert thresholds (50%, 75%, 90%, 100%)
  - [ ] Add automatic rate limiting at 100% budget
  - [ ] Create cost attribution by user/session

- [ ] **Add cost dashboard**
  - [ ] Display current month spending
  - [ ] Show service breakdown (ASR, LLM, TTS, Translation)
  - [ ] Add budget alerts configuration
  - [ ] Show cost per conversation trends

### Documentation
- [ ] **Create comprehensive API documentation**
  - [ ] Add OpenAPI/Swagger specification
  - [ ] Document all endpoints with examples
  - [ ] Add authentication guide
  - [ ] Create error code reference

- [ ] **Create user documentation**
  - [ ] Write user guide for voice chat interface
  - [ ] Document all settings and controls
  - [ ] Create troubleshooting guide
  - [ ] Add FAQ section

- [ ] **Create admin documentation**
  - [ ] Write admin guide for telephony setup
  - [ ] Document SIP trunk configuration for each provider
  - [ ] Create guardrail management guide
  - [ ] Add monitoring and alerting guide

### Load Testing
- [ ] **Create load testing suite**
  - [ ] Add locust configuration for load tests
  - [ ] Test 100+ concurrent users
  - [ ] Test various optimization levels under load
  - [ ] Identify bottlenecks and optimize

## Phase 11: Nice-to-Have Features (Low Priority)

### Conversation Management
- [ ] **Add conversation history UI**
  - [ ] Display past conversations
  - [ ] Add search and filtering
  - [ ] Allow conversation replay
  - [ ] Add export functionality

### Advanced Admin Features
- [ ] **Create user management UI**
  - [ ] Add user listing and search
  - [ ] Display user statistics
  - [ ] Add user blocking/suspension
  - [ ] Create user audit logs

### Enhanced RAG Features
- [ ] **Add document management UI**
  - [ ] List ingested documents
  - [ ] Add document upload interface
  - [ ] Display document statistics
  - [ ] Add document versioning
  - [ ] Implement document deletion

---

# PRIORITY MATRIX

## Critical Path (Weeks 1-8)
1. **Quality-Latency Optimization System** - Core differentiator
2. **Guardrails & Safety** - Security requirement
3. **Production Readiness** - Deployment infrastructure
4. **Enhanced Caching** - Performance requirement

## High Value (Weeks 9-12)
5. **Barge-In System** - User experience enhancement
6. **Noise Handling** - Quality improvement
7. **Test Agent Mode** - Quality assurance
8. **Cost Management** - Operational requirement

## Medium Value (Weeks 13-16)
9. **Colloquial Language** - Feature enhancement
10. **Voice Selection UI** - User experience
11. **SIP Multi-Provider** - Enterprise requirement
12. **Analytics Dashboard** - Business intelligence

## Low Priority (Weeks 17-20)
13. **Streaming/Speculation** - Performance optimization
14. **Conversation History** - Nice-to-have
15. **Document Management UI** - Administrative convenience

---

# NEXT IMMEDIATE STEPS

1. **Start with Quality-Latency Optimization** (`backend/services/conversation_pipeline.py`)
   - Implement optimization-level-aware processing
   - Add streaming support based on confidence thresholds
   - Implement parallel execution for higher speed levels

2. **Enhance Caching Strategy** (`backend/utils/cache.py`)
   - Add semantic similarity caching for LLM responses
   - Implement cache warming for common queries

3. **Implement Barge-In System**
   - Add VAD to frontend audio processor
   - Handle interrupt signals in WebSocket
   - Add barge-in settings UI

4. **Add Guardrails Service** (`backend/services/guardrail_service.py`)
   - Implement 3-layer guardrail system
   - Add pre-LLM, in-prompt, and post-LLM checks

5. **Create Test Agent Mode**
   - Build scenario execution framework
   - Add real-time metrics collection
   - Create test UI with split layout

---

# FRONTEND-SPECIFIC IMPLEMENTATION ROADMAP

## Current Frontend Status

### ✅ Already Implemented
- [x] React 18 + TypeScript + Vite setup
- [x] Tailwind CSS styling
- [x] Basic App.tsx with optimization slider
- [x] VoiceChat component with WebSocket
- [x] TelephonyDashboard component
- [x] AudioRecorder service
- [x] AudioPlayer service
- [x] Basic API client (`frontend/src/lib/api.ts`)
- [x] Config management (`frontend/src/lib/config.ts`)

### 📦 Required Dependencies to Add
```bash
# State Management
npm install @tanstack/react-query zustand

# UI Components
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-slider
npm install @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-tooltip

# Audio Processing
npm install @sentry/browser lamejs recorder-js

# WebSocket
npm install socket.io-client

# Charts & Visualization
npm install recharts d3

# Forms & Validation
npm install react-hook-form zod @hookform/resolvers

# Testing
npm install -D @testing-library/jest-dom @testing-library/user-event vitest jsdom
```

---

## Frontend Phase 1: Core UI Components & State Management

### Component Architecture Setup
- [ ] **Create component library structure**
  ```
  frontend/src/
  ├── components/
  │   ├── ui/                    # Reusable UI primitives
  │   │   ├── Button.tsx
  │   │   ├── Slider.tsx
  │   │   ├── Toggle.tsx
  │   │   ├── Input.tsx
  │   │   ├── Select.tsx
  │   │   ├── Card.tsx
  │   │   ├── Badge.tsx
  │   │   ├── Tooltip.tsx
  │   │   └── Dialog.tsx
  │   ├── chat/                  # Chat-related components
  │   │   ├── ChatInterface.tsx
  │   │   ├── MessageList.tsx
  │   │   ├── MessageBubble.tsx
  │   │   └── MicButton.tsx
  │   ├── settings/              # Settings panels
  │   │   ├── PerformanceSettings.tsx
  │   │   ├── LanguageSettings.tsx
  │   │   ├── VoiceSettings.tsx
  │   │   ├── AudioSettings.tsx
  │   │   ├── BargeInSettings.tsx
  │   │   └── NoiseSettings.tsx
  │   ├── admin/                 # Admin components
  │   │   ├── Dashboard.tsx
  │   │   ├── SIPConfiguration.tsx
  │   │   ├── GuardrailSettings.tsx
  │   │   ├── AnalyticsDashboard.tsx
  │   │   └── TestAgentInterface.tsx
  │   └── monitoring/            # Monitoring components
  │       ├── LatencyMonitor.tsx
  │       ├── QualityMonitor.tsx
  │       ├── MetricsChart.tsx
  │       └── CostDashboard.tsx
  ```

### State Management
- [ ] **Setup Zustand stores**
  - [ ] Create `stores/conversationStore.ts` (messages, session state)
  - [ ] Create `stores/settingsStore.ts` (all user settings)
  - [ ] Create `stores/audioStore.ts` (audio state, recording status)
  - [ ] Create `stores/metricsStore.ts` (latency, quality metrics)
  - [ ] Create `stores/adminStore.ts` (admin configurations)

- [ ] **Setup React Query**
  - [ ] Configure QueryClient in `main.tsx`
  - [ ] Create query hooks in `hooks/queries/`
  - [ ] Add mutation hooks for API calls
  - [ ] Setup cache invalidation strategies

### Core UI Primitives
- [ ] **Build reusable UI components** (`components/ui/`)
  - [ ] Button component with variants (primary, secondary, ghost)
  - [ ] Slider component with marks and labels
  - [ ] Toggle/Switch component
  - [ ] Input component with validation
  - [ ] Select/Dropdown component
  - [ ] Card component with header/footer
  - [ ] Badge component for status indicators
  - [ ] Tooltip component
  - [ ] Dialog/Modal component

---

## Frontend Phase 2: Enhanced Chat Interface

### Chat Components
- [ ] **Enhance VoiceChat component** (`modules/chat/VoiceChat.tsx`)
  - [ ] Add message history display
  - [ ] Add typing indicators
  - [ ] Add message status (sending, sent, error)
  - [ ] Add avatar support
  - [ ] Add timestamp display
  - [ ] Add scroll to bottom on new messages
  - [ ] Add "scroll to bottom" button when not at bottom

- [ ] **Create MessageList component**
  - [ ] Virtualized scrolling for performance
  - [ ] Auto-scroll behavior
  - [ ] Message grouping by time
  - [ ] Load more messages on scroll up

- [ ] **Create MessageBubble component**
  - [ ] User vs bot message styling
  - [ ] Support for audio playback in messages
  - [ ] Show transcription and translation
  - [ ] Display latency metadata
  - [ ] Add copy message button
  - [ ] Add regenerate button for bot messages

- [ ] **Enhance MicButton component**
  - [ ] Add recording animation
  - [ ] Show recording duration
  - [ ] Add push-to-talk mode
  - [ ] Add continuous recording mode
  - [ ] Display audio level visualization
  - [ ] Add keyboard shortcuts (space bar)

### Audio Visualization
- [ ] **Create AudioVisualizer component**
  - [ ] Real-time waveform display
  - [ ] Audio level meter
  - [ ] Recording indicator animation
  - [ ] Speaking detection visual feedback

---

## Frontend Phase 3: Performance Settings UI

### Performance Dashboard
- [ ] **Enhance PerformanceSettings component**
  - [ ] Add detailed optimization level descriptions
  - [ ] Create accuracy gauge (circular progress)
  - [ ] Create speed gauge (circular progress)
  - [ ] Add expected latency display per level
  - [ ] Show warnings for extreme levels
  - [ ] Add "Reset to Default" button
  - [ ] Add preset buttons (Quality/Balanced/Speed)

- [ ] **Create LatencyMonitor component**
  - [ ] Real-time latency display
  - [ ] Breakdown chart (ASR, LLM, Translation, TTS)
  - [ ] Show P50, P95, P99 metrics
  - [ ] Historical trend line chart (last 10 interactions)
  - [ ] Color-coded status (green/yellow/red)
  - [ ] Export metrics button

- [ ] **Create QualityMonitor component**
  - [ ] Audio quality score (0-100)
  - [ ] SNR (Signal-to-Noise Ratio) display
  - [ ] Clipping detection indicator
  - [ ] Quality suggestions popup
  - [ ] Connection quality indicator

---

## Frontend Phase 4: Language & Voice Settings

### Language Settings
- [ ] **Create LanguageSettings component** (`components/settings/LanguageSettings.tsx`)
  - [ ] Language selector dropdown (23 Indian languages)
  - [ ] Colloquial language toggle
  - [ ] Formality level slider (0-100)
    - [ ] Add marks at 0 (Formal), 50 (Conversational), 100 (Informal)
    - [ ] Show real-time example translations
  - [ ] Code-mixing toggle
  - [ ] English mix ratio slider
  - [ ] Domain preservation checkboxes (Tech, Business, Medical)
  - [ ] Preview translation button

### Voice Settings
- [ ] **Create VoiceSettings component** (`components/settings/VoiceSettings.tsx`)
  - [ ] Provider selector (Sarvam/ElevenLabs)
  - [ ] Voice gallery grid layout
  - [ ] Voice filter (gender, language, characteristics)
  - [ ] Sort options (name, popularity, newest)

- [ ] **Create VoiceCard component**
  - [ ] Voice name and description
  - [ ] Gender and characteristics badges
  - [ ] Supported languages list
  - [ ] Standard preview button with sample text
  - [ ] Custom preview section
    - [ ] Text input for custom preview
    - [ ] Play button for custom text
    - [ ] Loading state during synthesis
  - [ ] Select/Selected state
  - [ ] Favorite/bookmark functionality

- [ ] **Create VoiceTuning component** (Sarvam-specific)
  - [ ] Pitch slider (-0.75 to 0.75)
  - [ ] Speed slider (0.3 to 3.0)
  - [ ] Volume slider (0 to 3.0)
  - [ ] Real-time preview with adjustments
  - [ ] Reset to defaults button

---

## Frontend Phase 5: Audio Processing UI

### Audio Settings
- [ ] **Create AudioSettings component** (`components/settings/AudioSettings.tsx`)
  - [ ] Create preset buttons section
    - [ ] Quiet preset
    - [ ] Moderate preset
    - [ ] Noisy preset
    - [ ] Custom preset
  - [ ] Noise suppression toggle
  - [ ] Noise suppression level select (low/medium/high/very_high)
  - [ ] Echo cancellation toggle
  - [ ] Auto gain control toggle
  - [ ] Sarvam AI preprocessing toggle (with "Premium" badge)

- [ ] **Enhance AudioQualityMonitor component**
  - [ ] Real-time quality bar (0-100)
  - [ ] Quality label (Excellent/Good/Fair/Poor)
  - [ ] Warning messages when quality < 50
  - [ ] Suggestions list (quieter location, closer to mic, etc.)
  - [ ] Technical details collapse section (SNR, frequency response)

### Barge-In Settings
- [ ] **Create BargeInSettings component** (`components/settings/BargeInSettings.tsx`)
  - [ ] Enable barge-in toggle
  - [ ] VAD sensitivity slider (0-1)
    - [ ] Left label: "Less Sensitive"
    - [ ] Right label: "More Sensitive"
  - [ ] Minimum speech duration input (ms)
  - [ ] Interruption delay slider (0-500ms)
  - [ ] Resume after false trigger toggle
  - [ ] Test barge-in button with live feedback

### Noise Injection (Testing)
- [ ] **Create NoiseInjection component** (`components/settings/NoiseSettings.tsx`)
  - [ ] Info banner explaining testing purpose
  - [ ] Noise type grid selector
    - [ ] None card (default)
    - [ ] Call Center card
    - [ ] Café card
    - [ ] Street card
    - [ ] Office card
    - [ ] Custom upload card
  - [ ] Noise volume slider (0-1)
  - [ ] Noise-specific options
    - [ ] Call Center: chatter/typing/phone rings toggles
    - [ ] Café: music/chatter/machine toggles
    - [ ] Street: traffic/horns/footsteps toggles
  - [ ] Preview noise button
  - [ ] Apply noise in real-time toggle

---

## Frontend Phase 6: Admin & Telephony UI

### SIP Configuration
- [ ] **Create SIPConfiguration component** (`components/admin/SIPConfiguration.tsx`)
  - [ ] Provider selector (Twilio/Vonage/Bandwidth/Custom)
  - [ ] Dynamic form based on provider
  - [ ] Test connection button with loading state
  - [ ] Connection status indicator
  - [ ] Save configuration button
  - [ ] Configuration list/history

- [ ] **Create TwilioConfig component**
  - [ ] Account SID input
  - [ ] Auth Token password input
  - [ ] Phone Number input with validation
  - [ ] Test connection button
  - [ ] Status indicator

- [ ] **Create VonageConfig component**
  - [ ] API Key input
  - [ ] API Secret password input
  - [ ] Application ID input
  - [ ] Private key upload
  - [ ] Test connection button

- [ ] **Create CustomSIPConfig component**
  - [ ] SIP Domain input
  - [ ] Username input
  - [ ] Password input
  - [ ] Transport select (UDP/TCP/TLS)
  - [ ] Port input
  - [ ] Advanced settings collapse

- [ ] **Enhance TelephonyDashboard component**
  - [ ] Active calls list
  - [ ] Call history table
  - [ ] Trunk status indicators
  - [ ] Quick dial section
  - [ ] Call analytics charts

### Guardrails Management
- [ ] **Create GuardrailSettings component** (`components/admin/GuardrailSettings.tsx`)
  - [ ] Active rules list/table
  - [ ] Rule enable/disable toggles
  - [ ] Add new rule button
  - [ ] Edit rule dialog
  - [ ] Delete rule confirmation
  - [ ] Blocked keywords management
    - [ ] Keyword list with tags
    - [ ] Add keyword input
    - [ ] Bulk import keywords
  - [ ] Violation statistics
    - [ ] Total violations chart
    - [ ] Violations by rule type
    - [ ] Recent violations table

- [ ] **Create GuardrailRuleDialog component**
  - [ ] Rule name input
  - [ ] Rule type select (keyword/pattern/AI)
  - [ ] Keywords/patterns input
  - [ ] Response template textarea
  - [ ] Severity select (low/medium/high)
  - [ ] Save/Cancel buttons

---

## Frontend Phase 7: Test Agent Mode

### Test Agent Interface
- [ ] **Create TestAgentInterface component** (`components/admin/TestAgentInterface.tsx`)
  - [ ] Implement split layout
    - [ ] Left panel: Live agent + controls (60%)
    - [ ] Right panel: Metrics + results (40%)
  - [ ] Resizable panels
  - [ ] Full-screen mode toggle

- [ ] **Create AgentPanel component**
  - [ ] Live conversation display
  - [ ] Message list with timestamps
  - [ ] Audio playback for each message
  - [ ] Real-time status indicator
  - [ ] Current scenario display

- [ ] **Create TestControls component**
  - [ ] Start test button
  - [ ] Stop test button
  - [ ] Pause/Resume test button
  - [ ] Speed control (1x/2x/5x/10x)
  - [ ] Scenario selector dropdown
  - [ ] Noise type selector
  - [ ] Noise volume slider
  - [ ] Optimization level quick selector

- [ ] **Create MetricsPanel component**
  - [ ] Real-time metrics cards
    - [ ] ASR latency gauge with target line
    - [ ] LLM latency gauge with target line
    - [ ] Translation latency gauge
    - [ ] TTS latency gauge
    - [ ] Total latency gauge
    - [ ] Accuracy percentage
  - [ ] Latency breakdown chart (stacked bar)
  - [ ] Historical trend line chart
  - [ ] Test results summary
    - [ ] Total tests counter
    - [ ] Passed counter (green)
    - [ ] Failed counter (red)
    - [ ] Success rate percentage

- [ ] **Create ScenarioPanel component**
  - [ ] Scenario library grid
  - [ ] Scenario filter (language, type, status)
  - [ ] Scenario search
  - [ ] Create new scenario button
  - [ ] Import scenarios button
  - [ ] Export scenarios button

- [ ] **Create ScenarioCard component**
  - [ ] Scenario name and description
  - [ ] Language badge
  - [ ] Step count display
  - [ ] Last run status
  - [ ] Last run time
  - [ ] Run button
  - [ ] Edit button
  - [ ] Delete button
  - [ ] View results button

- [ ] **Create ScenarioEditor component**
  - [ ] Scenario name input
  - [ ] Description textarea
  - [ ] Language selector
  - [ ] Settings section (optimization, noise)
  - [ ] Steps list builder
    - [ ] Add step button
    - [ ] Reorder steps (drag & drop)
    - [ ] Edit step inline
    - [ ] Delete step button
  - [ ] Expected results section
  - [ ] Save scenario button

- [ ] **Create TestResultsDialog component**
  - [ ] Test summary section
  - [ ] Step-by-step results
  - [ ] Actual vs expected comparison
  - [ ] Latency breakdown per step
  - [ ] Audio playback for each step
  - [ ] Export results button
  - [ ] Rerun test button

---

## Frontend Phase 8: Analytics & Monitoring

### Analytics Dashboard
- [ ] **Create AnalyticsDashboard component** (`components/admin/AnalyticsDashboard.tsx`)
  - [ ] Date range selector
  - [ ] Time granularity selector (hour/day/week/month)
  - [ ] Refresh button with auto-refresh toggle
  - [ ] Export data button

- [ ] **Create PerformanceMetrics section**
  - [ ] Average latency trend chart
  - [ ] P95 latency trend chart
  - [ ] Error rate chart
  - [ ] Request volume chart
  - [ ] Cache hit rate chart

- [ ] **Create QualityMetrics section**
  - [ ] ASR accuracy trend
  - [ ] User satisfaction score
  - [ ] Conversation completion rate
  - [ ] Barge-in frequency

- [ ] **Create LanguageDistribution component**
  - [ ] Pie chart of languages used
  - [ ] Bar chart of requests per language
  - [ ] Language trend over time

- [ ] **Create CostDashboard component**
  - [ ] Current month spending display
  - [ ] Budget progress bar
  - [ ] Cost breakdown by service (pie chart)
  - [ ] Cost trend line chart
  - [ ] Cost per conversation metric
  - [ ] Projected end-of-month cost
  - [ ] Budget alerts section
  - [ ] Alert threshold configuration

- [ ] **Create UserMetrics section**
  - [ ] Active users chart
  - [ ] New users chart
  - [ ] Session duration distribution
  - [ ] Returning users chart

---

## Frontend Phase 9: Advanced Features

### Conversation History
- [ ] **Create ConversationHistory component**
  - [ ] Conversation list with search
  - [ ] Date range filter
  - [ ] Language filter
  - [ ] Status filter (completed/abandoned)
  - [ ] Sort options (newest/oldest/duration)
  - [ ] Pagination or infinite scroll

- [ ] **Create ConversationDetail component**
  - [ ] Full conversation transcript
  - [ ] Audio playback for each turn
  - [ ] Metadata display (duration, language, latency)
  - [ ] User feedback display
  - [ ] Export conversation button
  - [ ] Delete conversation button

### User Management
- [ ] **Create UserManagement component**
  - [ ] User list table
  - [ ] Search users
  - [ ] Filter by status (active/blocked)
  - [ ] Sort options
  - [ ] Bulk actions (block/unblock/delete)

- [ ] **Create UserDetail component**
  - [ ] User info display
  - [ ] Conversation count
  - [ ] Total time spent
  - [ ] Preferred language
  - [ ] Recent activity
  - [ ] Block/Unblock user button
  - [ ] Delete user button with confirmation
  - [ ] Export user data button (GDPR)

### Document Management (RAG)
- [ ] **Create DocumentManagement component**
  - [ ] Document list table
  - [ ] Upload document button
  - [ ] Bulk upload
  - [ ] Document search
  - [ ] Filter by status (processing/ready/error)
  - [ ] Sort options

- [ ] **Create DocumentUpload component**
  - [ ] File upload drag & drop
  - [ ] URL input for web documents
  - [ ] Multiple file selection
  - [ ] Upload progress bars
  - [ ] Metadata input (title, tags)
  - [ ] Chunk size configuration

- [ ] **Create DocumentDetail component**
  - [ ] Document title and metadata
  - [ ] Chunk count display
  - [ ] Upload date
  - [ ] File size
  - [ ] Processing status
  - [ ] View chunks button
  - [ ] Reprocess button
  - [ ] Delete button

---

## Frontend Phase 10: Hooks & Services

### Custom Hooks
- [ ] **Create custom hooks** (`hooks/`)
  - [ ] `useVoiceChat.ts` - WebSocket connection, send/receive messages
  - [ ] `useAudioRecorder.ts` - Recording state, start/stop, audio data
  - [ ] `useAudioPlayer.ts` - Play audio, control playback
  - [ ] `useWebSocket.ts` - Generic WebSocket management
  - [ ] `useLatency.ts` - Track and calculate latencies
  - [ ] `useSettings.ts` - Read/write user settings
  - [ ] `useOptimization.ts` - Optimization level logic
  - [ ] `useVAD.ts` - Voice Activity Detection
  - [ ] `useNoiseInjection.ts` - Noise mixing logic
  - [ ] `useMetrics.ts` - Collect and aggregate metrics

### API Service Layer
- [ ] **Enhance API services** (`services/api/`)
  - [ ] Create `chatbotApi.ts` with all endpoints
  - [ ] Create `ttsApi.ts` for TTS operations
  - [ ] Create `telephonyApi.ts` for SIP operations
  - [ ] Create `adminApi.ts` for admin operations
  - [ ] Create `analyticsApi.ts` for metrics/analytics
  - [ ] Add request/response interceptors
  - [ ] Add error handling
  - [ ] Add retry logic
  - [ ] Add request cancellation

### Audio Services
- [ ] **Enhance audio services** (`services/audio/`)
  - [ ] Enhance `AudioRecorder.ts`
    - [ ] Add WebRTC constraints
    - [ ] Add noise suppression options
    - [ ] Add echo cancellation
    - [ ] Add auto-gain control
    - [ ] Add VAD integration
    - [ ] Add audio quality monitoring
  - [ ] Enhance `AudioPlayer.ts`
    - [ ] Add queue management
    - [ ] Add playback controls (pause/resume)
    - [ ] Add volume control
    - [ ] Add playback events
  - [ ] Create `AudioProcessor.ts`
    - [ ] High-pass filter
    - [ ] Noise injection
    - [ ] Audio level monitoring
    - [ ] Format conversion
  - [ ] Create `NoiseLibrary.ts`
    - [ ] Load noise audio files
    - [ ] Mix audio streams
    - [ ] Volume control

---

## Frontend Phase 11: Testing & Quality

### Component Tests
- [ ] **Write unit tests for components**
  - [ ] Test all UI components with React Testing Library
  - [ ] Test user interactions
  - [ ] Test accessibility
  - [ ] Test responsive behavior
  - [ ] Test error states

### Integration Tests
- [ ] **Write integration tests**
  - [ ] Test VoiceChat end-to-end flow
  - [ ] Test WebSocket connection handling
  - [ ] Test audio recording and playback
  - [ ] Test settings persistence
  - [ ] Test error recovery

### E2E Tests
- [ ] **Setup E2E testing** (Playwright/Cypress)
  - [ ] Test complete conversation flow
  - [ ] Test telephony integration
  - [ ] Test admin operations
  - [ ] Test analytics dashboard

---

## Frontend Phase 12: Performance Optimization

### Code Splitting
- [ ] **Implement lazy loading**
  - [ ] Lazy load admin routes
  - [ ] Lazy load analytics dashboard
  - [ ] Lazy load test agent
  - [ ] Code split by feature

### Performance Optimizations
- [ ] **Optimize rendering**
  - [ ] Add React.memo to expensive components
  - [ ] Use useMemo for expensive calculations
  - [ ] Use useCallback for event handlers
  - [ ] Implement virtual scrolling for long lists
  - [ ] Optimize re-renders with proper state structure

- [ ] **Optimize assets**
  - [ ] Compress images
  - [ ] Use WebP format
  - [ ] Lazy load images
  - [ ] Implement audio streaming

### Bundle Optimization
- [ ] **Reduce bundle size**
  - [ ] Analyze bundle with vite-bundle-visualizer
  - [ ] Tree-shake unused code
  - [ ] Remove duplicate dependencies
  - [ ] Use lighter alternatives where possible

---

## Frontend Phase 13: Accessibility & UX

### Accessibility
- [ ] **Implement WCAG 2.1 AA compliance**
  - [ ] Add ARIA labels to all interactive elements
  - [ ] Ensure keyboard navigation works everywhere
  - [ ] Add focus indicators
  - [ ] Ensure color contrast meets standards
  - [ ] Add screen reader support
  - [ ] Test with screen readers

### Responsive Design
- [ ] **Ensure mobile responsiveness**
  - [ ] Test all components on mobile
  - [ ] Add mobile-specific layouts
  - [ ] Optimize touch interactions
  - [ ] Add swipe gestures where appropriate

### Loading & Error States
- [ ] **Improve UX for all states**
  - [ ] Add skeleton loaders
  - [ ] Add loading spinners
  - [ ] Add empty states
  - [ ] Add error boundaries
  - [ ] Add retry mechanisms
  - [ ] Add offline mode indicators

---

## Frontend Phase 14: Internationalization

### i18n Setup
- [ ] **Add internationalization support**
  - [ ] Install react-i18next
  - [ ] Create translation files for UI
  - [ ] Add language switcher
  - [ ] Support RTL languages
  - [ ] Test all languages

---

## Frontend Priority Summary

### Week 1-2: Foundation
- Core UI components
- State management setup
- Enhanced chat interface

### Week 3-4: Settings
- Performance settings UI
- Language & voice settings
- Audio settings

### Week 5-6: Advanced Features
- Barge-in UI
- Noise handling UI
- Test agent interface basics

### Week 7-8: Admin
- SIP configuration
- Guardrails UI
- Analytics dashboard basics

### Week 9-10: Testing & Polish
- Component tests
- Integration tests
- Performance optimization
- Accessibility improvements

### Week 11-12: Advanced Admin
- Complete test agent
- Complete analytics
- User & document management
