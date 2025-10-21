# Enhanced UX Implementation Plan
## Option 3: Full Feature Enhancement (3-4 Weeks)

**Document Version:** 1.0
**Date:** 2025-10-15
**Total Tasks:** 44
**Estimated Duration:** 3-4 weeks
**Target:** 100% Requirements Coverage for User-Facing Features

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Production Hardening](#phase-1-production-hardening) (Week 1)
3. [Phase 2: Quality-Latency UI](#phase-2-quality-latency-ui) (Week 1-2)
4. [Phase 3: Barge-In UI](#phase-3-barge-in-ui) (Week 2)
5. [Phase 4: Voice Selection UI](#phase-4-voice-selection-ui) (Week 2-3)
6. [Phase 5: Language Settings UI](#phase-5-language-settings-ui) (Week 3)
7. [Phase 6: Noise Handling UI](#phase-6-noise-handling-ui) (Week 3-4)
8. [Phase 7: Testing & Documentation](#phase-7-testing--documentation) (Week 4)
9. [Implementation Order](#implementation-order)
10. [Success Criteria](#success-criteria)

---

## Overview

### Current Status
- ✅ **Backend:** 95% complete (production-ready)
- ⚠️ **Frontend:** 60% complete (basic features only)
- ⚠️ **Infrastructure:** 40% complete (missing deployment configs)
- ⚠️ **Security:** 60% complete (missing rate limiting, TLS enforcement)

### Target Status
- ✅ **Backend:** 100% complete
- ✅ **Frontend:** 100% complete (all UI components)
- ✅ **Infrastructure:** 100% complete (Docker, K8s ready)
- ✅ **Security:** 95% complete (production-hardened)

### What Will Be Built

**Phase 1 (5 tasks):** Production hardening
- Rate limiting middleware
- TLS/HTTPS enforcement
- Docker configuration
- Prometheus metrics

**Phase 2 (5 tasks):** Quality-Latency controls
- Interactive slider with 5 levels
- Real-time gauges
- Warning system

**Phase 3 (6 tasks):** Barge-In controls
- VAD sensitivity control
- Interruption settings
- False positive handling

**Phase 4 (7 tasks):** Voice selection system
- Voice gallery with previews
- Custom text testing
- Voice tuning controls

**Phase 5 (6 tasks):** Language customization
- Formality controls
- Code-mixing settings
- Domain preservation

**Phase 6 (7 tasks):** Audio quality controls
- Noise handling presets
- Real-time monitoring
- Quality warnings

**Phase 7 (8 tasks):** Polish and launch
- Documentation
- Testing
- Deployment guides

---

## Phase 1: Production Hardening
**Duration:** 2-3 days
**Priority:** 🔴 HIGH
**Dependencies:** None

### Task 1.1: Rate Limiting Middleware
**File:** `backend/api/middleware.py` (NEW)
**Effort:** 3 hours

**Implementation:**
```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    """Rate limiting middleware using token bucket algorithm."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.buckets: Dict[str, dict] = defaultdict(lambda: {
            "minute": {"count": 0, "reset_at": time.time() + 60},
            "hour": {"count": 0, "reset_at": time.time() + 3600}
        })

    async def __call__(self, request: Request, call_next):
        # Get client identifier (API key or IP)
        client_id = request.headers.get("X-API-Key", request.client.host)

        # Check rate limits
        current_time = time.time()
        bucket = self.buckets[client_id]

        # Check minute limit
        if current_time > bucket["minute"]["reset_at"]:
            bucket["minute"] = {"count": 0, "reset_at": current_time + 60}

        if bucket["minute"]["count"] >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(int(bucket["minute"]["reset_at"] - current_time))}
            )

        # Check hour limit
        if current_time > bucket["hour"]["reset_at"]:
            bucket["hour"] = {"count": 0, "reset_at": current_time + 3600}

        if bucket["hour"]["count"] >= self.rph:
            return JSONResponse(
                status_code=429,
                content={"error": "Hourly rate limit exceeded."},
                headers={"Retry-After": str(int(bucket["hour"]["reset_at"] - current_time))}
            )

        # Increment counters
        bucket["minute"]["count"] += 1
        bucket["hour"]["count"] += 1

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining-Minute"] = str(self.rpm - bucket["minute"]["count"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(self.rph - bucket["hour"]["count"])

        return response
```

**Integration in `backend/main.py`:**
```python
from backend.api.middleware import RateLimiter

app = FastAPI()
app.middleware("http")(RateLimiter(requests_per_minute=60, requests_per_hour=1000))
```

---

### Task 1.2: TLS/HTTPS Enforcement
**File:** `backend/api/middleware.py` (UPDATE)
**Effort:** 1 hour

**Implementation:**
```python
from fastapi import Request
from fastapi.responses import RedirectResponse

async def https_redirect_middleware(request: Request, call_next):
    """Redirect HTTP to HTTPS in production."""
    if settings.environment == "production":
        if request.url.scheme != "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)

    response = await call_next(request)

    # Add security headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response

# Add to main.py
app.middleware("http")(https_redirect_middleware)
```

---

### Task 1.3: Create Dockerfile
**File:** `Dockerfile` (NEW)
**Effort:** 2 hours

**Implementation:**
```dockerfile
# Multi-stage build for Python backend
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY backend ./backend
COPY alembic.ini .
COPY .env.example .env

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && \
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

### Task 1.4: Create docker-compose.yml
**File:** `docker-compose.yml` (NEW)
**Effort:** 2 hours

**Implementation:**
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: speech-ai-db
    environment:
      POSTGRES_DB: speech_ai
      POSTGRES_USER: speech_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U speech_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: speech-ai-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Backend API
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: speech-ai-backend
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://speech_user:${DB_PASSWORD:-changeme}@postgres:5432/speech_ai
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./backend:/app/backend
      - ./logs:/app/logs

  # Frontend (Optional - for development)
  frontend:
    image: node:18-alpine
    container_name: speech-ai-frontend
    working_dir: /app
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: sh -c "npm install && npm run dev"
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
      VITE_VOICE_WS_URL: ws://localhost:8000/api/v1/voice-session
    depends_on:
      - backend

  # Prometheus (Monitoring)
  prometheus:
    image: prom/prometheus:latest
    container_name: speech-ai-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    restart: unless-stopped

  # Grafana (Visualization)
  grafana:
    image: grafana/grafana:latest
    container_name: speech-ai-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    name: speech-ai-network
```

---

### Task 1.5: Add Prometheus Metrics Endpoint
**File:** `backend/utils/metrics.py` (NEW)
**Effort:** 3 hours

**Implementation:**
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics definitions
request_count = Counter(
    'speech_ai_requests_total',
    'Total request count',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'speech_ai_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

pipeline_latency = Histogram(
    'speech_ai_pipeline_latency_ms',
    'Pipeline latency in milliseconds',
    ['stage']  # asr, llm, translation, tts
)

active_sessions = Gauge(
    'speech_ai_active_sessions',
    'Number of active voice sessions'
)

cost_total = Counter(
    'speech_ai_cost_usd_total',
    'Total cost in USD',
    ['service', 'provider']
)

cache_hits = Counter(
    'speech_ai_cache_hits_total',
    'Total cache hits',
    ['cache_type']  # llm, tts
)

cache_misses = Counter(
    'speech_ai_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

guardrail_violations = Counter(
    'speech_ai_guardrail_violations_total',
    'Total guardrail violations',
    ['layer', 'severity']
)

class MetricsMiddleware:
    """Middleware to track request metrics."""

    async def __call__(self, request: Request, call_next):
        start_time = time.time()

        # Track active sessions
        if request.url.path == "/api/v1/voice-session":
            active_sessions.inc()

        try:
            response = await call_next(request)

            # Track request count
            request_count.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()

            # Track request duration
            duration = time.time() - start_time
            request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)

            return response

        finally:
            if request.url.path == "/api/v1/voice-session":
                active_sessions.dec()

# Metrics endpoint
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Add to `backend/api/routes.py`:**
```python
from backend.utils.metrics import metrics_endpoint

@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()
```

**Create `prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'speech-ai-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/api/v1/metrics'
```

---

## Phase 2: Quality-Latency UI
**Duration:** 3-4 days
**Priority:** 🔴 HIGH
**Dependencies:** Phase 1

### Task 2.1: Create PerformanceSettings Component
**File:** `frontend/src/components/PerformanceSettings.tsx` (NEW)
**Effort:** 4 hours

**Implementation:**
```typescript
import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';

interface OptimizationConfig {
  level: string;
  value: number;
  label: string;
  latency: string;
  accuracy: number;
  description: string;
  warnings?: string[];
}

const OPTIMIZATION_LEVELS: OptimizationConfig[] = [
  {
    level: 'quality',
    value: 0,
    label: 'Quality',
    latency: '3-4s',
    accuracy: 98,
    description: 'Maximum accuracy for critical operations',
    warnings: []
  },
  {
    level: 'balanced_quality',
    value: 25,
    label: 'Balanced Quality',
    latency: '2-3s',
    accuracy: 95,
    description: 'High accuracy for customer support',
    warnings: []
  },
  {
    level: 'balanced',
    value: 50,
    label: 'Balanced',
    latency: '1.5-2s',
    accuracy: 90,
    description: 'Optimal balance for most applications',
    warnings: []
  },
  {
    level: 'balanced_speed',
    value: 75,
    label: 'Balanced Speed',
    latency: '1-1.5s',
    accuracy: 85,
    description: 'Faster responses with good accuracy',
    warnings: ['Slightly reduced accuracy']
  },
  {
    level: 'speed',
    value: 100,
    label: 'Max Speed',
    latency: '0.7-1s',
    accuracy: 75,
    description: 'Maximum speed for real-time interactions',
    warnings: ['May sacrifice accuracy', 'Not for critical use']
  }
];

interface PerformanceSettingsProps {
  value: string;
  onChange: (level: string) => void;
  className?: string;
}

export function PerformanceSettings({
  value,
  onChange,
  className = ''
}: PerformanceSettingsProps) {
  const currentConfig = OPTIMIZATION_LEVELS.find(c => c.level === value) || OPTIMIZATION_LEVELS[2];
  const [sliderValue, setSliderValue] = useState(currentConfig.value);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value);
    setSliderValue(newValue);

    // Find closest optimization level
    const closest = OPTIMIZATION_LEVELS.reduce((prev, curr) => {
      return Math.abs(curr.value - newValue) < Math.abs(prev.value - newValue) ? curr : prev;
    });

    onChange(closest.level);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-100">
          Performance Optimization
        </h3>
        <p className="text-sm text-neutral-400 mt-1">
          Control the balance between response speed and accuracy
        </p>
      </div>

      {/* Slider */}
      <div className="space-y-4">
        <input
          type="range"
          min="0"
          max="100"
          step="25"
          value={sliderValue}
          onChange={handleSliderChange}
          className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider"
        />

        {/* Marks */}
        <div className="flex justify-between text-xs">
          {OPTIMIZATION_LEVELS.map((config) => (
            <div
              key={config.level}
              className="flex flex-col items-center"
              style={{ width: '20%' }}
            >
              <div className={`w-2 h-2 rounded-full mb-1 ${
                config.value === currentConfig.value
                  ? 'bg-blue-500'
                  : 'bg-neutral-600'
              }`} />
              <span className={`text-center ${
                config.value === currentConfig.value
                  ? 'text-blue-400 font-medium'
                  : 'text-neutral-500'
              }`}>
                {config.label}
              </span>
              <span className="text-neutral-600 mt-0.5">
                {config.latency}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Current Selection Info */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h4 className="font-medium text-neutral-100">
              {currentConfig.label}
            </h4>
            <p className="text-sm text-neutral-400 mt-1">
              {currentConfig.description}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-400">
              {currentConfig.latency}
            </div>
            <div className="text-xs text-neutral-500">
              Target Latency
            </div>
          </div>
        </div>

        {/* Gauges */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Gauge
            label="Accuracy"
            value={currentConfig.accuracy}
            max={100}
            color="emerald"
          />
          <Gauge
            label="Speed"
            value={100 - currentConfig.accuracy}
            max={100}
            color="blue"
          />
        </div>

        {/* Warnings */}
        {currentConfig.warnings && currentConfig.warnings.length > 0 && (
          <div className="mt-4 rounded-md bg-amber-500/10 border border-amber-500/20 p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                {currentConfig.warnings.map((warning, idx) => (
                  <p key={idx} className="text-sm text-amber-400">
                    {warning}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
        }

        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}

// Gauge component
interface GaugeProps {
  label: string;
  value: number;
  max: number;
  color: 'emerald' | 'blue' | 'amber';
}

function Gauge({ label, value, max, color }: GaugeProps) {
  const percentage = (value / max) * 100;

  const colorClasses = {
    emerald: 'bg-emerald-500',
    blue: 'bg-blue-500',
    amber: 'bg-amber-500'
  };

  const textColorClasses = {
    emerald: 'text-emerald-400',
    blue: 'text-blue-400',
    amber: 'text-amber-400'
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-neutral-400">{label}</span>
        <span className={`text-sm font-medium ${textColorClasses[color]}`}>
          {value}%
        </span>
      </div>
      <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

---

### Tasks 2.2-2.5: (Covered in 2.1)
The implementation above covers:
- ✅ Slider with marks (Task 2.2)
- ✅ Accuracy and speed gauges (Task 2.3)
- ✅ Warning messages (Task 2.4)
- ✅ Ready for integration (Task 2.5)

---

## Phase 3: Barge-In UI
**Duration:** 2-3 days
**Priority:** 🟡 MEDIUM
**Dependencies:** Phase 2

### Task 3.1: Create BargeInSettings Component
**File:** `frontend/src/components/BargeInSettings.tsx` (NEW)
**Effort:** 3 hours

**Implementation:**
```typescript
import React from 'react';
import { Mic, AlertCircle } from 'lucide-react';

interface BargeInConfig {
  enabled: boolean;
  vadSensitivity: number;
  interruptionDelay: number;
  resumeAfterFalse: boolean;
}

interface BargeInSettingsProps {
  config: BargeInConfig;
  onChange: (config: BargeInConfig) => void;
  className?: string;
}

export function BargeInSettings({
  config,
  onChange,
  className = ''
}: BargeInSettingsProps) {
  const updateConfig = (updates: Partial<BargeInConfig>) => {
    onChange({ ...config, ...updates });
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-neutral-100 flex items-center gap-2">
          <Mic className="w-5 h-5" />
          Barge-In Settings
        </h3>
        <p className="text-sm text-neutral-400 mt-1">
          Configure how users can interrupt the bot while it's speaking
        </p>
      </div>

      {/* Enable Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-neutral-100">
            Enable Barge-In
          </label>
          <p className="text-xs text-neutral-500 mt-1">
            Allow users to interrupt bot responses
          </p>
        </div>
        <Toggle
          checked={config.enabled}
          onChange={(enabled) => updateConfig({ enabled })}
        />
      </div>

      {/* Settings (only show when enabled) */}
      {config.enabled && (
        <div className="space-y-6 pl-4 border-l-2 border-neutral-800">
          {/* VAD Sensitivity */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-neutral-100">
                Voice Detection Sensitivity
              </label>
              <span className="text-sm text-blue-400 font-mono">
                {config.vadSensitivity.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={config.vadSensitivity}
              onChange={(e) => updateConfig({ vadSensitivity: parseFloat(e.target.value) })}
              className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-neutral-500">
              <span>Less Sensitive</span>
              <span>More Sensitive</span>
            </div>
            <div className="rounded-md bg-neutral-900/50 p-3 text-xs text-neutral-400">
              {config.vadSensitivity < 0.5 && (
                <>
                  <AlertCircle className="w-3 h-3 inline mr-1" />
                  May miss quiet interruptions
                </>
              )}
              {config.vadSensitivity >= 0.5 && config.vadSensitivity < 0.8 && (
                <>Balanced - Recommended for most use cases</>
              )}
              {config.vadSensitivity >= 0.8 && (
                <>
                  <AlertCircle className="w-3 h-3 inline mr-1" />
                  May trigger false positives from background noise
                </>
              )}
            </div>
          </div>

          {/* Interruption Delay */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-neutral-100">
                Interruption Delay
              </label>
              <span className="text-sm text-blue-400 font-mono">
                {config.interruptionDelay}ms
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="500"
              step="50"
              value={config.interruptionDelay}
              onChange={(e) => updateConfig({ interruptionDelay: parseInt(e.target.value) })}
              className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-neutral-500">
              <span>Instant</span>
              <span>500ms</span>
            </div>
            <p className="text-xs text-neutral-400">
              Small delay to prevent accidental interruptions
            </p>
          </div>

          {/* Resume After False Positive */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-neutral-100">
                Resume After False Trigger
              </label>
              <p className="text-xs text-neutral-500 mt-1">
                Continue bot response if interruption was accidental
              </p>
            </div>
            <Toggle
              checked={config.resumeAfterFalse}
              onChange={(resumeAfterFalse) => updateConfig({ resumeAfterFalse })}
            />
          </div>
        </div>
      )}

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
        }

        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
}

// Toggle component
interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function Toggle({ checked, onChange }: ToggleProps) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-blue-600' : 'bg-neutral-700'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}
```

---

### Tasks 3.2-3.6: (Covered in 3.1)
The implementation above covers all barge-in UI tasks.

---

## Phase 4-7: (Continued in next section)

Due to length, I'll create the remaining phases in the next message. The pattern is established - each component follows similar structure with:
- TypeScript interfaces
- Props and state management
- Tailwind styling
- Accessibility features
- Integration hooks

---

## Implementation Order (Priority Sequence)

### Week 1 (Days 1-5)
1. **Day 1:** Rate limiting + TLS enforcement
2. **Day 2:** Docker + docker-compose
3. **Day 3:** Prometheus metrics
4. **Day 4-5:** PerformanceSettings component

### Week 2 (Days 6-10)
5. **Day 6-7:** BargeInSettings component
6. **Day 8-10:** VoiceSettings component (gallery + preview)

### Week 3 (Days 11-15)
7. **Day 11-12:** LanguageSettings component
8. **Day 13-15:** AudioProcessing component

### Week 4 (Days 16-20)
9. **Day 16-18:** Testing all components
10. **Day 19-20:** Documentation + deployment guide

---

## Success Criteria

### Phase 1: Production Hardening
- ✅ Rate limiting prevents abuse (test with 100 req/min)
- ✅ HTTPS redirect works in production
- ✅ Docker build succeeds
- ✅ docker-compose up runs all services
- ✅ Prometheus metrics accessible at `/metrics`

### Phase 2: Quality-Latency UI
- ✅ Slider changes optimization level
- ✅ Gauges update in real-time
- ✅ Warnings show for extreme settings
- ✅ Selection persists across page reload

### Phases 3-6: Feature UIs
- ✅ All settings save to backend
- ✅ Real-time updates work
- ✅ Mobile responsive
- ✅ Accessible (keyboard navigation)

### Phase 7: Launch Ready
- ✅ All components documented
- ✅ Example code provided
- ✅ Deployment guide tested
- ✅ No console errors

---

**Total: 44 tasks across 7 phases, 3-4 weeks implementation time**

Ready to proceed? Let me know which phase you'd like to start with!
