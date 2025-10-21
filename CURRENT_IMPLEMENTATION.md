# Current Implementation Analysis

This document describes what is **ACTUALLY** happening in the codebase right now, with code references and data flow diagrams.

## Table of Contents

1. [User Interaction Flows](#user-interaction-flows)
2. [Backend Pipeline Architecture](#backend-pipeline-architecture)
3. [WebSocket Protocol](#websocket-protocol)
4. [Hardcoded Configuration Points](#hardcoded-configuration-points)
5. [Service Integration Details](#service-integration-details)
6. [Optimization Levels](#optimization-levels)
7. [Critical Bug: Text Chat](#critical-bug-text-chat)

---

## User Interaction Flows

### Flow 1: Voice Input (WORKING CORRECTLY ✅)

```
User clicks Mic button
    ↓
AudioRecorder starts capturing microphone
    ↓
Audio chunks encoded to base64
    ↓
WebSocket sends: { type: "audio", sessionId, audio: base64, timestamp, optimizationLevel }
    ↓
Backend receives in routes.py:44-108 (voice_session WebSocket handler)
    ↓
Calls pipeline.process_audio_chunk() (conversation_pipeline.py:70-160)
    ↓
FULL PIPELINE EXECUTES:
    1. ASR (Sarvam speech-to-text)
    2. RAG (optional context retrieval)
    3. LLM (Sarvam with guardrails)
    4. Translation (to target language)
    5. TTS (Sarvam synthesize)
    ↓
WebSocket sends back: { type: "response", text, translated_text, audio: base64 }
    ↓
Frontend receives in VoiceChat.tsx:212-254 (handleSocketMessage)
    ↓
AudioPlayer plays the TTS audio
    ↓
User hears AI speaking
```

**Code References:**
- Frontend: `frontend/src/modules/chat/VoiceChat.tsx:367-417` (`startRecording`, `stopRecording`)
- Backend WebSocket: `backend/api/routes.py:44-108` (`voice_session`)
- Pipeline: `backend/services/conversation_pipeline.py:70-160` (`process_audio_chunk`)
- Full Pipeline: `backend/services/conversation_pipeline.py:196-451` (`process_audio`)

---

### Flow 2: Text Input (BROKEN - CRITICAL BUG ❌)

```
User types text and clicks Send
    ↓
sendTextMessage() called (VoiceChat.tsx:311-365)
    ↓
❌ BUG: Calls POST /api/v1/tts DIRECTLY with user's text
    ↓
TTS converts USER'S TEXT to speech (not AI response!)
    ↓
User hears their own text spoken back
    ↓
NO LLM PROCESSING, NO CONVERSATION
```

**What it SHOULD do:**
```
User types text
    ↓
Send to WebSocket OR LLM endpoint
    ↓
LLM generates AI response
    ↓
TTS converts AI RESPONSE to speech
    ↓
User hears AI speaking
```

**Bug Location:** `frontend/src/modules/chat/VoiceChat.tsx:311-365`

**Problem Code:**
```typescript
const sendTextMessage = useCallback(async () => {
  // ... add user message to UI ...

  // ❌ BUG: Calls TTS on user's own text instead of getting AI response
  const response = await axios.post(
    REST_TTS_URL,
    {
      text: userMessage.text,  // ← USER'S TEXT, not AI response!
      language_code: 'en-IN',
      voice: { provider: 'sarvam', voice_id: 'anushka' },
    },
    // ...
  );
  // ... plays audio of user's own text ...
}, []);
```

---

## Backend Pipeline Architecture

### The Full Pipeline: ASR → RAG → LLM → Translation → TTS

**Entry Point:** `backend/services/conversation_pipeline.py:196-451` (`process_audio` method)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ConversationPipeline                        │
│                                                                 │
│  process_audio(audio_url, target_language, optimization_level) │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │  1. ASR Service (Sarvam)              │
        │     - Transcribe audio to text        │
        │     - Track latency                   │
        │     - Cost tracking                   │
        │  Code: asr_service.py                 │
        └───────────────────────────────────────┘
                            ↓
                      transcript.text
                            ↓
        ┌───────────────────────────────────────┐
        │  2. RAG Service (Optional)            │
        │     - Retrieve context from Weaviate  │
        │     - Optimization-level aware        │
        │     - Skip if optimization = "speed"  │
        │  Code: rag_service.py                 │
        └───────────────────────────────────────┘
                            ↓
                    rag_context (optional)
                            ↓
        ┌───────────────────────────────────────┐
        │  3. LLM Service (Sarvam)              │
        │     - 3-layer guardrails:             │
        │       • Pre-LLM (input check)         │
        │       • In-prompt (system instructions)│
        │       • Post-LLM (output check)       │
        │     - LLM caching (exact + semantic)  │
        │     - Interrupt support               │
        │     - Cost tracking                   │
        │  Code: llm_service.py:66-287          │
        └───────────────────────────────────────┘
                            ↓
                      llm_response.text
                            ↓
        ┌───────────────────────────────────────┐
        │  4. Translation Service               │
        │     - Translate to target language    │
        │     - Cost tracking                   │
        │  Code: translation_service.py         │
        └───────────────────────────────────────┘
                            ↓
                      translated_text
                            ↓
        ┌───────────────────────────────────────┐
        │  5. TTS Orchestrator (Sarvam)         │
        │     - Synthesize speech               │
        │     - Redis caching                   │
        │     - Interrupt support               │
        │     - Cost tracking                   │
        │  Code: tts_service.py                 │
        └───────────────────────────────────────┘
                            ↓
                audio_response (base64 audio)
                            ↓
        ┌───────────────────────────────────────┐
        │  Return ConversationTurn              │
        │     - transcript                      │
        │     - llm_response                    │
        │     - translated_text                 │
        │     - audio_response                  │
        └───────────────────────────────────────┘
```

### Metrics Tracking

All latencies are tracked and stored in database:

```python
# conversation_pipeline.py:324-368
with SessionLocal() as db:
    metrics_repo = SessionMetricsRepository(db)
    metrics = metrics_repo.get_or_create(session_id)

    # Update turn counts
    metrics.total_turns += 1
    metrics.successful_turns += 1

    # Update latency averages
    metrics.avg_asr_latency_ms = update_running_avg(...)
    metrics.avg_llm_latency_ms = update_running_avg(...)
    metrics.avg_translation_latency_ms = update_running_avg(...)
    metrics.avg_tts_latency_ms = update_running_avg(...)
    metrics.avg_total_latency_ms = update_running_avg(...)

    # Track guardrail violations
    if not llm.guardrail_flags.safe:
        metrics.guardrail_violations += 1
```

---

## WebSocket Protocol

### Connection

**URL:** `ws://localhost:8000/api/v1/voice-session?api_key=YOUR_API_KEY`

**Frontend Code:** `frontend/src/modules/chat/VoiceChat.tsx:256-301`

```typescript
const wsUrl = `${WEB_SOCKET_URL}?api_key=${encodeURIComponent(API_KEY)}`;
const socket = new WebSocket(wsUrl);

socket.addEventListener('open', () => {
  setConnectionStatus('connected');
  socket.send(JSON.stringify({
    type: 'auth',
    apiKey: API_KEY,
    sessionId: stableSessionId
  }));
});
```

### Message Types

#### Outgoing (Frontend → Backend)

**1. Start Session**
```json
{
  "type": "start",
  "sessionId": "uuid",
  "optimizationLevel": "balanced"
}
```

**2. Audio Chunk**
```json
{
  "type": "audio",
  "sessionId": "uuid",
  "audio": "base64_encoded_audio",
  "timestamp": 1234567890,
  "optimizationLevel": "balanced"
}
```

**3. Stop Session**
```json
{
  "type": "stop",
  "sessionId": "uuid",
  "optimizationLevel": "balanced"
}
```

#### Incoming (Backend → Frontend)

**1. Session Started**
```json
{
  "type": "session_started",
  "sessionId": "uuid"
}
```

**2. Response (Full Pipeline Result)**
```json
{
  "type": "response",
  "text": "AI response text",
  "translated_text": "Translated text",
  "audio": "base64_encoded_audio",
  "transcript": "User's transcribed speech"
}
```

**3. Session Stopped**
```json
{
  "type": "session_stopped",
  "sessionId": "uuid"
}
```

### Backend Handler

**Code:** `backend/api/routes.py:44-108`

```python
@router.websocket("/voice-session")
async def voice_session(
    websocket: WebSocket,
    pipeline: ConversationPipeline = Depends(get_pipeline),
    api_key: str = None
):
    # API key validation
    if api_key != settings.api_key:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    while True:
        raw_message = await websocket.receive_text()
        payload = json.loads(raw_message)
        message_type = payload.get("type")

        if message_type == "start":
            await pipeline.start_session(session_id, optimization_level)

        elif message_type == "audio":
            result = await pipeline.process_audio_chunk(
                audio_base64=payload.get("audio"),
                session_id=session_id,
                timestamp=payload.get("timestamp"),
                optimization_level=optimization_level,
                target_language=target_language,
            )
            if result:
                await websocket.send_json({
                    "type": "response",
                    "text": result.llm_response,
                    "translated_text": result.translated_text,
                    "audio": result.audio_response.audio_base64,
                    "transcript": result.transcript.text,
                })

        elif message_type == "stop":
            await pipeline.finish_session(session_id, optimization_level)
```

---

## Hardcoded Configuration Points

### 1. LLM Provider (HARDCODED ❌)

**Location:** `backend/services/llm_service.py:205`

```python
payload = {
    "model": "sarvam-m",  # ← HARDCODED: Only Sarvam, no other providers
    "messages": [...],
    "temperature": config.llm_temperature,
    "max_tokens": max_tokens,
}
```

**No UI Control:** Users cannot select LLM provider or model.

**What Exists in Backend:**
- Only Sarvam LLM integration
- No OpenAI integration
- No Anthropic integration
- No provider abstraction layer

---

### 2. TTS Provider (HARDCODED ❌)

**Location:** `backend/services/conversation_pipeline.py:449`

```python
def _build_tts_request(self, text: str, language: str, optimization_level: Optional[str] = None):
    return SynthesizeRequest(
        text=text,
        language_code=language,
        voice=VoiceSelection(
            provider="sarvam",  # ← HARDCODED: Always Sarvam
            voice_id="anushka"  # ← HARDCODED: Always this voice
        ),
        optimization_level=optimization_level or "balanced",
    )
```

**No UI Control:** Users cannot select TTS provider.

**What Exists in Backend:**
- Sarvam TTS
- ElevenLabs TTS (available but not selectable in UI)
- Provider fallback logic exists (`backend/services/tts_service.py`)
- Voice registry with 22+ voices (`backend/utils/voice_registry.py`)

---

### 3. Voice Selection (HARDCODED ❌)

**Location:** Same as above (`conversation_pipeline.py:449`)

```python
voice=VoiceSelection(
    provider="sarvam",
    voice_id="anushka"  # ← HARDCODED: Only one voice
)
```

**No UI Control:** Users cannot select different voices.

**What Exists in Backend:**

From `backend/utils/voice_registry.py`, these voices are available but not selectable:

**Sarvam Voices:**
- `anushka` (Hindi, female)
- `maitreyi` (Hindi, female)
- `swati` (Tamil, female)
- And 19+ more for various Indian languages

**ElevenLabs Voices:**
- `21m00Tcm4TlvDq8ikWAM` (Rachel, English)
- `AZnzlk1XvdvUeBnXmlld` (Domi, English)
- And 8+ more

---

### 4. Language Selection (PARTIALLY WORKING ⚠️)

**Frontend:** `frontend/src/App.tsx:5,68-70`

```typescript
import { LanguageSelector, type LanguageCode } from './components/LanguageSelector';

// In render:
<div className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
  <LanguageSelector value={targetLanguage} onChange={setTargetLanguage} />
</div>
```

**What Works:**
- User can select from 22 Indian languages
- Selection is passed to backend via WebSocket

**What's Missing:**
- No "multilingual mode" (auto-detect language)
- Target language is selected manually, not detected from user's speech
- No UI to show detected source language

---

## Service Integration Details

### LLM Service with Guardrails

**Code:** `backend/services/llm_service.py:66-287`

**3-Layer Guardrail System:**

```python
async def generate(self, transcript: str, ...) -> LLMResponse:
    # Layer 0: Cache Check (before guardrails for performance)
    if self.llm_cache:
        cached = await self.llm_cache.get_exact(transcript, opt_level)
        if cached:
            return LLMResponse(text=cached.response_text, ...)

    # Layer 1: Pre-LLM guardrail check (input validation)
    input_check = self.guardrail_service.check_input(transcript)
    if not input_check.passed:
        # Log violations to database
        self.guardrail_service.log_violation(...)
        return LLMResponse(
            text=input_check.safe_response or "I cannot process this request.",
            guardrail_flags=GuardrailFlags(safe=False, reason=...),
        )

    # Layer 2: Add guardrail instructions to system prompt
    guardrail_instructions = self.guardrail_service.get_system_prompt_guardrails()
    full_prompt = system_prompt + guardrail_instructions

    # Make LLM API call
    data = await self._request_with_retry(payload, session_id, turn_id)
    text = data["choices"][0]["message"]["content"]

    # Layer 3: Post-LLM guardrail check (output validation)
    output_check = self.guardrail_service.check_output(text)
    if not output_check.passed:
        # Log violations to database
        self.guardrail_service.log_violation(...)
        return LLMResponse(
            text=output_check.safe_response or "I cannot provide that information.",
            guardrail_flags=GuardrailFlags(safe=False, reason=...),
        )

    # Layer 4: Cache successful response
    await self.llm_cache.set(transcript, cached_response, ttl=ttl)

    return LLMResponse(text=text, guardrail_flags=GuardrailFlags(safe=True))
```

**Guardrail Checks Include:**
- Profanity detection
- PII detection (emails, phone numbers, credit cards, SSN)
- Prompt injection detection
- Blocked keywords
- Response length limits

**Database Logging:**
All violations are logged to `guardrail_violations` table with:
- `session_id` and `turn_id` attribution
- Layer (1=pre_llm, 2=llm_prompt, 3=post_llm)
- Violation details (input, output, safe response)

---

### LLM Caching

**Code:** `backend/utils/cache.py` (LLMCache class)

**Two-Level Cache:**

1. **Exact Match:** Hash of query + optimization level
2. **Semantic Match:** Cosine similarity of query embeddings (threshold: 0.7)

```python
# Try exact match first
cached = await self.llm_cache.get_exact(transcript, opt_level)
if cached:
    return cached

# Try semantic match for quality levels
cached = await self.llm_cache.get_semantic(
    transcript, opt_level, similarity_threshold=0.7
)
```

**TTL by Optimization Level:**

```python
def _get_cache_ttl(self, optimization_level: str) -> int:
    ttl_map = {
        "quality": 3600,           # 1 hour (expensive, cache longer)
        "balanced_quality": 2400,  # 40 minutes
        "balanced": 1800,          # 30 minutes (default)
        "balanced_speed": 1200,    # 20 minutes
        "speed": 600,              # 10 minutes (cheap, cache shorter)
    }
    return ttl_map.get(optimization_level, 1800)
```

---

### Interrupt Manager

**Code:** `backend/services/interrupt_manager.py`

**Purpose:** Cancel in-flight operations when user interrupts (barge-in).

**Usage Example:**

```python
# Start turn tracking
turn_id = self.interrupt_manager.start_turn(session_id, turn_id)

# Use interruptible operation
async with InterruptibleOperation(
    self.interrupt_manager, session_id, turn_id, "llm"
) as op:
    # Check for interrupt periodically
    op.check_or_raise()  # Raises InterruptedError if interrupted

    # Make API call
    data = await self._request_with_retry(payload)

    # Check again after API call
    op.check_or_raise()

# Finish turn tracking
self.interrupt_manager.finish_turn(session_id, turn_id)
```

**Services with Interrupt Support:**
- LLM Service (`llm_service.py`)
- TTS Orchestrator (`tts_service.py`)
- ASR Service (`asr_service.py`)

---

### Cost Tracker

**Code:** `backend/services/cost_tracker.py`

**Dual Storage:**
1. **Redis:** Real-time cost tracking (fast)
2. **Database:** Persistent storage (audit trail)

**Usage Example:**

```python
await self.cost_tracker.track_llm(
    provider="sarvam",
    input_tokens=usage.get("prompt_tokens", 0),
    output_tokens=usage.get("completion_tokens", 0),
    model="sarvam-m",
    session_id=session_id,
    turn_id=turn_id,
    metadata={
        "optimization_level": opt_level,
        "temperature": 0.7,
        "cached": False,
    },
)
```

**Cost Summary API:**

```
GET /api/v1/sessions/{session_id}/costs
```

Returns:
```json
{
  "total_cost_usd": 0.025,
  "breakdown_by_service": {
    "asr": 0.005,
    "llm": 0.012,
    "translation": 0.003,
    "tts": 0.005
  },
  "breakdown_by_provider": {
    "sarvam": 0.025
  },
  "cache_savings_usd": 0.008
}
```

---

## Optimization Levels

**Defined In:** `backend/config/settings.py`

### 5 Optimization Levels

| Level            | LLM Temperature | Response Max Tokens | Cache TTL | RAG Depth | Use Case           |
|------------------|-----------------|---------------------|-----------|-----------|-------------------|
| `quality`        | 0.3             | 600                 | 3600s     | 10 chunks | Max accuracy      |
| `balanced_quality` | 0.5           | 500                 | 2400s     | 5 chunks  | Good accuracy     |
| `balanced`       | 0.7             | 400                 | 1800s     | 3 chunks  | Default           |
| `balanced_speed` | 0.8             | 300                 | 1200s     | 2 chunks  | Fast with quality |
| `speed`          | 0.9             | 200                 | 600s      | 0 chunks  | Max speed         |

**How It Works:**

```python
# Get config for current optimization level
config = get_optimization_config(optimization_level)

# Apply to LLM
payload = {
    "model": "sarvam-m",
    "temperature": config.llm_temperature,  # 0.3 to 0.9
    "max_tokens": config.response_max_tokens,  # 200 to 600
}

# Apply to RAG
if optimization_level == "speed":
    # Skip RAG entirely for max speed
    rag_chunks = []
else:
    # Retrieve chunks based on level
    rag_chunks = retrieve_chunks(depth=config.rag_depth)
```

**Frontend Control:** `frontend/src/App.tsx:38-66`

```typescript
<input
  type='range'
  min={0}
  max={100}
  step={25}
  value={currentSliderValue}
  onChange={event => {
    const numericValue = Number(event.currentTarget.value);
    const match = sliderMarks.find(mark => mark.value === numericValue);
    if (match) setOptimizationLevel(match.level);
  }}
/>
```

---

## Critical Bug: Text Chat

### The Problem

**Code:** `frontend/src/modules/chat/VoiceChat.tsx:311-365`

```typescript
const sendTextMessage = useCallback(async () => {
  if (!input.trim()) return;

  // Add user message to UI
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    text: input,
    timestamp: new Date().toISOString(),
    status: 'final',
  };
  setMessages(prev => [...prev, userMessage]);
  setInput('');

  try {
    // ❌ BUG: Calls TTS endpoint directly with user's text
    const response = await axios.post(
      REST_TTS_URL,  // http://localhost:8000/api/v1/tts
      {
        text: userMessage.text,  // USER'S TEXT (not AI response!)
        language_code: 'en-IN',
        voice: { provider: 'sarvam', voice_id: 'anushka' },
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
      },
    );

    // Gets back audio of USER'S TEXT spoken
    const { audio_b64: audioBase64, mime_type: mimeType, metadata } = response.data ?? {};

    if (audioBase64) {
      const player = ensureAudioPlayer();
      player.enqueue(audioBase64, mimeType ?? metadata?.mime_type);
      // Plays USER'S TEXT as speech
    }

    // Adds a fake "assistant" message that's just the user's text
    setMessages(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: metadata?.text ?? metadata?.prompt ?? '[Audio response ready]',
        timestamp: new Date().toISOString(),
        status: 'final',
      },
    ]);
  } catch (err) {
    console.error(err);
    setError('Failed to send message.');
  }
}, [ensureAudioPlayer, input, updateAudioStatusMessage]);
```

### Why This is Wrong

1. **No LLM Processing:** User's text never goes through the LLM to generate a response
2. **No Conversation:** It's just text-to-speech of the user's own words
3. **Bypasses Pipeline:** Skips ASR, LLM, Translation, and guardrails
4. **Misleading UI:** Shows user's text as "assistant" message

### What It Should Do

**Option 1: Send via WebSocket (Recommended)**

```typescript
const sendTextMessage = useCallback(async () => {
  if (!input.trim()) return;

  // Add user message to UI
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    text: input,
    timestamp: new Date().toISOString(),
    status: 'final',
  };
  setMessages(prev => [...prev, userMessage]);
  setInput('');

  // ✅ FIX: Send text through WebSocket
  // Backend will need to handle text input (not just audio)
  sendWsMessage({
    type: 'text',
    sessionId: stableSessionId,
    text: input,
    optimizationLevel,
  });

  // Backend processes through full pipeline:
  // LLM → Translation → TTS
  // Response comes back via WebSocket message handler
}, [input, stableSessionId, optimizationLevel, sendWsMessage]);
```

**Option 2: Create New LLM Endpoint**

```typescript
const sendTextMessage = useCallback(async () => {
  // ... add user message to UI ...

  // ✅ FIX: Call LLM endpoint (not TTS endpoint)
  const response = await axios.post(
    'http://localhost:8000/api/v1/chat',  // New endpoint
    {
      text: userMessage.text,
      target_language: targetLanguage,
      optimization_level: optimizationLevel,
      session_id: sessionId,
    },
    {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
    },
  );

  // Response includes AI's response text + audio
  const { response_text, translated_text, audio_b64 } = response.data;

  // Add AI's response to UI
  setMessages(prev => [
    ...prev,
    {
      id: crypto.randomUUID(),
      role: 'assistant',
      text: response_text,  // ✅ AI's actual response
      timestamp: new Date().toISOString(),
      status: 'final',
    },
  ]);

  // Play AI's response audio
  if (audio_b64) {
    const player = ensureAudioPlayer();
    player.enqueue(audio_b64);
  }
}, [input, targetLanguage, optimizationLevel, sessionId]);
```

---

## Summary

### What Works ✅

1. **Voice Input:** Microphone → WebSocket → Full Pipeline → Audio Playback
2. **Backend Pipeline:** ASR → RAG → LLM → Translation → TTS (fully functional)
3. **Guardrails:** 3-layer protection with database logging
4. **Cost Tracking:** Dual storage (Redis + Database)
5. **Metrics:** Session metrics with latency tracking
6. **Optimization Levels:** 5 levels with different quality/speed tradeoffs
7. **Language Selection:** 22 Indian languages selectable
8. **Interrupts:** Barge-in support for canceling operations

### What's Broken ❌

1. **Text Chat:** Bypasses LLM, just echoes user's text as speech

### What's Missing (No UI) ⚠️

1. **LLM Provider Selection:** Hardcoded to Sarvam only
2. **LLM Model Selection:** Hardcoded to "sarvam-m"
3. **TTS Provider Selection:** Hardcoded to Sarvam (ElevenLabs available but not selectable)
4. **Voice Selection:** Hardcoded to "anushka" (22+ voices available but not selectable)
5. **Multilingual Mode:** No auto-detect language feature
6. **Advanced Settings:** Many backend features have no frontend controls

---

## Next Steps

See `MISSING_FRONTEND_FEATURES.md` for a comprehensive list of all missing UI controls and their specifications.
