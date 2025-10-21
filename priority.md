# Implementation Priorities

**Project:** Speech AI Voice Chat
**Last Updated:** 2025-10-21
**Current Sprint:** Week 5-6 (Production Hardening + Enhanced UX)

---

## Current Status: ~85% Complete

### ✅ Completed Features (Weeks 1-4)

**Backend Services (90% Complete)**
- [x] Multi-stage pipeline: ASR → LLM → Translation → TTS
- [x] TTS orchestrator with dual provider support (Sarvam/ElevenLabs)
- [x] RAG service with Weaviate + OpenAI embeddings
- [x] LiveKit telephony integration
- [x] 3-layer guardrail system with database logging
- [x] Cost tracking service (Redis + database)
- [x] 5-level optimization system (quality → speed)
- [x] WebSocket audio streaming with base64 decoding
- [x] LLM response caching (exact + semantic)
- [x] Prometheus metrics integration

**Frontend Components (70% Complete)**
- [x] React 19 + TypeScript + Vite setup
- [x] VoiceChat component with WebSocket
- [x] LanguageSelector (22 Indian languages)
- [x] CostTracker component
- [x] SessionMetrics component
- [x] LatencyIndicator component
- [x] FeedbackRating component
- [x] AnalyticsDashboard component
- [x] TelephonyDashboard component

**API Endpoints**
- [x] `WS /api/v1/voice-session` - Real-time voice conversation
- [x] `POST /api/v1/tts` - Text-to-speech synthesis
- [x] `GET /api/v1/sessions/{id}/costs` - Cost summary
- [x] `GET /api/v1/sessions/{id}/metrics` - Session metrics
- [x] `POST /api/v1/feedback` - User feedback
- [x] Telephony endpoints (calls, trunks)

---

## Critical Path: Weeks 5-8

### 🎯 Week 5-6: Production Hardening (HIGH PRIORITY)

**Goal:** Make the application production-ready and secure

#### 1. Rate Limiting & Security
**Priority:** CRITICAL
**Estimated Time:** 2-3 days
**Files:**
- Create `backend/api/middleware.py`
- Update `backend/main.py`

**Tasks:**
- [ ] Implement rate limiting middleware
  - [ ] Per-IP rate limiting (100 req/min)
  - [ ] Per-API-key rate limiting (1000 req/min)
  - [ ] WebSocket connection limits (10 concurrent per IP)
  - [ ] Add Redis backend for distributed rate limiting
- [ ] Add request validation middleware
- [ ] Add CORS configuration
- [ ] Add request ID tracking
- [ ] Add request logging

**Acceptance Criteria:**
- Rate limits enforced on all `/api/v1/*` endpoints
- Clear error messages when limits exceeded (429 status)
- Admin endpoints have stricter limits

---

#### 2. Docker Configuration
**Priority:** CRITICAL
**Estimated Time:** 2-3 days
**Files:**
- Create `Dockerfile.backend`
- Create `Dockerfile.frontend`
- Create `docker-compose.yml`
- Create `docker-compose.prod.yml`
- Create `.dockerignore`

**Tasks:**
- [ ] Create optimized backend Dockerfile
  - [ ] Multi-stage build
  - [ ] Python 3.12 slim base image
  - [ ] Install dependencies in separate layer
  - [ ] Non-root user
  - [ ] Health check
- [ ] Create optimized frontend Dockerfile
  - [ ] Node 20 alpine base image
  - [ ] Multi-stage build (build + nginx)
  - [ ] Serve static files with nginx
- [ ] Create docker-compose.yml for local development
  - [ ] Backend service
  - [ ] Frontend service
  - [ ] Redis service
  - [ ] Weaviate service
  - [ ] Prometheus service
  - [ ] Volume mounts for development
- [ ] Create docker-compose.prod.yml for production
  - [ ] Environment variable configuration
  - [ ] Resource limits
  - [ ] Restart policies
  - [ ] Network configuration
- [ ] Add build and deployment scripts
  - [ ] `scripts/build.sh`
  - [ ] `scripts/deploy.sh`
  - [ ] `scripts/start-dev.sh`

**Acceptance Criteria:**
- `docker-compose up` starts full development environment
- Hot reload works for both frontend and backend
- Production build creates optimized images < 500MB
- All services can communicate via Docker network

---

#### 3. Enhanced Prometheus Metrics
**Priority:** HIGH
**Estimated Time:** 1-2 days
**Files:**
- Update `backend/main.py`
- Create `backend/monitoring/metrics.py`
- Create `prometheus.yml`

**Tasks:**
- [ ] Expand existing `/metrics` endpoint
- [ ] Add business KPI metrics
  - [ ] Active users gauge
  - [ ] Conversations per hour counter
  - [ ] Average conversation duration histogram
  - [ ] User satisfaction score gauge
- [ ] Add system metrics
  - [ ] Memory usage
  - [ ] CPU usage
  - [ ] Disk usage
  - [ ] Database connection pool
- [ ] Add custom metrics
  - [ ] Guardrail violations by type
  - [ ] Cache efficiency metrics
  - [ ] Provider availability
- [ ] Create Prometheus configuration
- [ ] Create Grafana dashboards (JSON)
  - [ ] System health dashboard
  - [ ] Application metrics dashboard
  - [ ] Cost tracking dashboard

**Acceptance Criteria:**
- Prometheus scrapes `/metrics` successfully
- All new metrics appear in Prometheus
- Grafana dashboards load and display data
- Alerts configured for critical metrics

---

### 🎯 Week 7-8: Enhanced UX Components (HIGH PRIORITY)

**Goal:** Improve user experience with advanced settings and controls

#### 4. PerformanceSettings Component
**Priority:** HIGH
**Estimated Time:** 2-3 days
**Files:**
- Create `frontend/src/components/settings/PerformanceSettings.tsx`
- Create `frontend/src/components/ui/Gauge.tsx`
- Update `frontend/src/App.tsx`

**Tasks:**
- [ ] Create reusable Gauge component
  - [ ] Circular progress indicator
  - [ ] Configurable colors
  - [ ] Animated transitions
  - [ ] Label and value display
- [ ] Build PerformanceSettings component
  - [ ] Optimization level slider (1-5)
  - [ ] Accuracy gauge (0-100)
  - [ ] Speed gauge (0-100)
  - [ ] Expected latency display per level
  - [ ] Warning banner for extreme levels
  - [ ] Detailed descriptions per level
  - [ ] Reset to default button
  - [ ] Quick preset buttons (Quality/Balanced/Speed)
- [ ] Add real-time feedback
  - [ ] Update gauges as slider moves
  - [ ] Show impact description
  - [ ] Highlight trade-offs
- [ ] Integrate with conversation pipeline
  - [ ] Pass optimization level via WebSocket
  - [ ] Track performance changes

**Acceptance Criteria:**
- Slider changes update gauges smoothly
- Clear warnings appear for max speed (level 5)
- Expected latency ranges accurate
- Settings persist across sessions

---

#### 5. BargeInSettings Component
**Priority:** HIGH
**Estimated Time:** 3-4 days
**Files:**
- Create `frontend/src/components/settings/BargeInSettings.tsx`
- Update `frontend/src/services/audio/AudioRecorder.ts`
- Update `backend/services/conversation_pipeline.py`

**Tasks:**
- [ ] Implement WebRTC VAD in frontend
  - [ ] Add VAD configuration to AudioRecorder
  - [ ] Detect voice activity in real-time
  - [ ] Emit barge-in events
  - [ ] Add configurable sensitivity
  - [ ] Add minimum speech duration threshold
  - [ ] Add sustained duration check
- [ ] Create BargeInSettings component
  - [ ] Enable/disable toggle
  - [ ] VAD sensitivity slider (0-1)
    - [ ] Labels: "Less Sensitive" / "More Sensitive"
    - [ ] Show current value
  - [ ] Minimum speech duration input (100-1000ms)
  - [ ] Interruption delay slider (0-500ms)
  - [ ] Resume after false trigger toggle
  - [ ] Test mode with live visualization
  - [ ] Real-time voice activity indicator
- [ ] Add backend barge-in handling
  - [ ] Handle interrupt signal in WebSocket
  - [ ] Cancel ongoing TTS playback
  - [ ] Preserve conversation context
  - [ ] Resume option implementation
- [ ] Add metrics tracking
  - [ ] Barge-in frequency
  - [ ] False positive rate
  - [ ] User satisfaction with barge-in

**Acceptance Criteria:**
- VAD detects speech reliably
- Barge-in interrupts playback immediately
- No conversation context lost on interrupt
- Test mode shows real-time VAD activity
- Settings save and restore correctly

---

#### 6. Frontend VAD Integration
**Priority:** HIGH
**Estimated Time:** 2 days
**Files:**
- Update `frontend/src/services/audio/AudioRecorder.ts`
- Create `frontend/src/hooks/useVAD.ts`

**Tasks:**
- [ ] Add WebRTC VAD support
  - [ ] Configure MediaStreamTrack constraints
  - [ ] Add echoCancellation
  - [ ] Add noiseSuppression
  - [ ] Add autoGainControl
- [ ] Create useVAD hook
  - [ ] Voice activity state
  - [ ] Sensitivity configuration
  - [ ] Speech detection logic
  - [ ] Event callbacks
- [ ] Add audio visualization
  - [ ] Real-time audio level meter
  - [ ] Voice activity indicator
  - [ ] Speaking animation
- [ ] Test with various environments
  - [ ] Quiet room
  - [ ] Moderate noise
  - [ ] High noise

**Acceptance Criteria:**
- VAD detects speech accurately in various noise levels
- No false positives in silence
- No missed speech in normal conversation
- Visual feedback is responsive

---

## High Value: Weeks 9-12

### 7. VoiceSettings Component
**Priority:** MEDIUM
**Estimated Time:** 3-4 days

**Tasks:**
- [ ] Create voice gallery UI
- [ ] Add voice preview API endpoint
- [ ] Implement voice card grid
- [ ] Add standard preview (play button)
- [ ] Add custom text preview
- [ ] Add voice tuning controls (Sarvam)
- [ ] Add voice filtering and search

### 8. LanguageSettings Component
**Priority:** MEDIUM
**Estimated Time:** 2-3 days

**Tasks:**
- [ ] Enhance translation service with formality levels
- [ ] Add code-mixing support
- [ ] Create UI for colloquial language controls
- [ ] Add formality level slider (0-100)
- [ ] Add English mix ratio slider
- [ ] Add domain preservation options
- [ ] Add preview translation feature

### 9. AudioProcessing Component
**Priority:** MEDIUM
**Estimated Time:** 2-3 days

**Tasks:**
- [ ] Create noise handling UI
- [ ] Add quick presets (Quiet/Moderate/Noisy)
- [ ] Add individual control toggles
- [ ] Add noise suppression level selector
- [ ] Create AudioQualityMonitor
- [ ] Add real-time quality display
- [ ] Add suggestions for poor quality

### 10. Test Agent Interface
**Priority:** MEDIUM
**Estimated Time:** 4-5 days

**Tasks:**
- [ ] Create test scenario system
- [ ] Build test agent service
- [ ] Create scenario library
- [ ] Build TestAgentInterface component
- [ ] Add live conversation display
- [ ] Add real-time metrics
- [ ] Add automated test execution
- [ ] Create test results dashboard

---

## Medium Value: Weeks 13-16

### 11. Advanced Caching
**Priority:** MEDIUM
**Estimated Time:** 2-3 days

**Tasks:**
- [ ] Implement cache warming for common queries
- [ ] Add semantic similarity caching for LLM
- [ ] Optimize cache eviction policies
- [ ] Add cache statistics endpoint

### 12. SIP Multi-Provider Support
**Priority:** MEDIUM
**Estimated Time:** 3-4 days

**Tasks:**
- [ ] Add Twilio adapter
- [ ] Add Vonage adapter
- [ ] Add Bandwidth adapter
- [ ] Create provider-specific UIs
- [ ] Add connection testing
- [ ] Add webhook configuration

### 13. Guardrail Admin UI
**Priority:** LOW
**Estimated Time:** 2-3 days

**Tasks:**
- [ ] Create GuardrailSettings component
- [ ] Add rule management UI
- [ ] Add blocked keyword management
- [ ] Display violation statistics
- [ ] Add rule enable/disable toggles

---

## Low Priority: Weeks 17-20

### 14. Conversation History
**Tasks:**
- [ ] Create conversation list UI
- [ ] Add search and filtering
- [ ] Add conversation replay
- [ ] Add export functionality

### 15. Document Management UI
**Tasks:**
- [ ] Create document management UI
- [ ] Add document upload
- [ ] Display document statistics
- [ ] Add document search

### 16. User Management
**Tasks:**
- [ ] Create user management UI
- [ ] Add user listing
- [ ] Add user statistics
- [ ] Add GDPR data export

---

## Dependency Tree

```
Week 5-6: Production Hardening
├── Rate Limiting (No dependencies)
├── Docker Configuration (No dependencies)
└── Prometheus Metrics (No dependencies)

Week 7-8: Enhanced UX
├── PerformanceSettings (Depends on: UI components)
├── BargeInSettings (Depends on: VAD implementation)
└── VAD Integration (No dependencies)

Week 9-12: Advanced Features
├── VoiceSettings (Depends on: Voice preview API)
├── LanguageSettings (Depends on: Enhanced translation)
├── AudioProcessing (Depends on: VAD)
└── Test Agent (Depends on: All core features)
```

---

## Success Metrics

### Production Readiness (Week 5-6)
- [ ] Docker builds complete in < 5 minutes
- [ ] All containers start successfully
- [ ] Rate limiting blocks excess requests
- [ ] Prometheus scrapes all metrics
- [ ] Zero critical security vulnerabilities

### Enhanced UX (Week 7-8)
- [ ] Performance settings change latency by 50%+
- [ ] Barge-in works with < 200ms latency
- [ ] VAD false positive rate < 5%
- [ ] User satisfaction score > 4.0/5.0
- [ ] Settings persist across sessions

### Advanced Features (Week 9-12)
- [ ] Voice preview loads in < 1 second
- [ ] Translation quality scores > 0.8
- [ ] Audio quality score > 70/100
- [ ] Test agent runs 100+ scenarios/hour

---

## Risk Assessment

### High Risk Items
1. **VAD Integration** - May require multiple iterations to tune sensitivity
2. **Docker Configuration** - Complex multi-service setup
3. **Rate Limiting** - Must not impact legitimate users

### Mitigation Strategies
1. VAD - Add test mode with visualization for tuning
2. Docker - Start with simple config, iterate incrementally
3. Rate Limiting - Use generous limits initially, monitor and adjust

---

## Resource Requirements

### Development Environment
- Node.js 20+
- Python 3.12+
- Docker Desktop
- Redis
- Weaviate
- Prometheus + Grafana

### External Services
- Sarvam API (ASR, TTS, LLM)
- OpenAI API (embeddings)
- LiveKit Cloud (telephony)
- Optional: ElevenLabs API (TTS)

### Infrastructure (Production)
- 2-4 vCPU backend server
- 2-4 GB RAM
- Redis instance
- Weaviate instance
- Load balancer
- CDN for frontend

---

## Next Actions (Start Immediately)

1. **TODAY:** Create rate limiting middleware
2. **TODAY:** Create Docker configuration files
3. **TOMORROW:** Test Docker setup locally
4. **DAY 3:** Enhance Prometheus metrics
5. **DAY 4:** Create PerformanceSettings component
6. **DAY 5:** Implement WebRTC VAD
7. **WEEK 2:** Create BargeInSettings component
8. **WEEK 2:** Test and iterate on VAD tuning

---

## Questions to Resolve

- [ ] What are acceptable rate limits for production?
- [ ] Which cloud provider for deployment (AWS/GCP/Azure)?
- [ ] Do we need multi-region deployment?
- [ ] What's the budget for external API calls?
- [ ] Are there specific compliance requirements (HIPAA, SOC2)?

---

**Status:** Ready to begin Week 5-6 (Production Hardening)
**Next Review:** End of Week 6
**Owner:** Development Team
