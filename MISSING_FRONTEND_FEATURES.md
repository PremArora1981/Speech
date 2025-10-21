# Missing Frontend Features

This document lists ALL missing frontend UI controls, with detailed specifications for implementation.

## Table of Contents

1. [Critical Fix: Text Chat](#critical-fix-text-chat)
2. [LLM Provider & Model Selection](#llm-provider--model-selection)
3. [TTS Provider Selection](#tts-provider-selection)
4. [Voice Selection](#voice-selection)
5. [Enhanced Language Selection](#enhanced-language-selection)
6. [Advanced Audio Settings](#advanced-audio-settings)
7. [Barge-In Controls](#barge-in-controls)
8. [Guardrail Management](#guardrail-management)
9. [RAG Configuration](#rag-configuration)
10. [Cost Budget Controls](#cost-budget-controls)

---

## Critical Fix: Text Chat

**Priority:** CRITICAL 🔴

**Current State:** Text chat calls TTS on user's text instead of getting AI response

**Required Fix:**

### Option 1: Extend WebSocket Protocol (Recommended)

**Backend Change:** Add text message support to WebSocket handler

`backend/api/routes.py:44-108` - Update `voice_session` handler:

```python
@router.websocket("/voice-session")
async def voice_session(websocket: WebSocket, ...):
    # ... existing code ...

    while True:
        raw_message = await websocket.receive_text()
        payload = json.loads(raw_message)
        message_type = payload.get("type")

        # ... existing start/audio/stop handlers ...

        # NEW: Handle text input
        if message_type == "text":
            text = payload.get("text")
            target_language = payload.get("targetLanguage", "hi-IN")
            optimization_level = payload.get("optimizationLevel", "balanced")
            session_id = payload.get("sessionId")

            # Process through LLM → Translation → TTS pipeline
            # (skip ASR since we already have text)
            result = await pipeline.process_text(
                text=text,
                target_language=target_language,
                optimization_level=optimization_level,
                session_id=session_id,
            )

            await websocket.send_json({
                "type": "response",
                "text": result.llm_response,
                "translated_text": result.translated_text,
                "audio": result.audio_response.audio_base64,
            })
```

**Frontend Change:** Update `sendTextMessage` function

`frontend/src/modules/chat/VoiceChat.tsx:311-365`:

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

  // ✅ FIX: Send through WebSocket, not REST API
  const ok = sendWsMessage({
    type: 'text',
    sessionId: stableSessionId,
    text: userMessage.text,
    targetLanguage: targetLanguage,
    optimizationLevel: optimizationLevel,
  });

  if (!ok) {
    setError('Failed to send message. WebSocket not connected.');
  }

  // Response will come through handleSocketMessage
  // which already handles the response correctly
}, [input, stableSessionId, targetLanguage, optimizationLevel, sendWsMessage]);
```

### Option 2: Create New REST Endpoint

**Backend:** Add `/api/v1/chat` endpoint

**Frontend:** Replace TTS call with chat endpoint call

---

## LLM Provider & Model Selection

**Priority:** HIGH 🟠

**Current State:** Hardcoded to Sarvam "sarvam-m" model only

**Backend Support:** Only Sarvam is integrated (no OpenAI/Anthropic)

### UI Component Specification: `LLMSettings`

**Location:** `frontend/src/components/settings/LLMSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  LLM Configuration                             │
├────────────────────────────────────────────────┤
│                                                │
│  Provider                                      │
│  ┌──────────────────────────────────────────┐ │
│  │ Sarvam ▼                                 │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Model                                         │
│  ┌──────────────────────────────────────────┐ │
│  │ sarvam-m (Default)                       │ │
│  │ sarvam-l (More capable)                  │ │
│  │ sarvam-xl (Most capable)                 │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ℹ️ Model capabilities:                        │
│  • sarvam-m: Fast, good for most tasks        │
│  • sarvam-l: Better accuracy, slower          │
│  • sarvam-xl: Best quality, highest cost      │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface LLMSettingsProps {
  provider: 'sarvam' | 'openai' | 'anthropic';
  model: string;
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
}
```

**State Management:**

```typescript
// In App.tsx or settings store
const [llmProvider, setLlmProvider] = useState<'sarvam' | 'openai' | 'anthropic'>('sarvam');
const [llmModel, setLlmModel] = useState<string>('sarvam-m');
```

**Model Options by Provider:**

```typescript
const modelsByProvider = {
  sarvam: [
    { id: 'sarvam-m', name: 'Sarvam M', description: 'Fast, good for most tasks' },
    { id: 'sarvam-l', name: 'Sarvam L', description: 'Better accuracy, slower' },
    { id: 'sarvam-xl', name: 'Sarvam XL', description: 'Best quality, highest cost' },
  ],
  openai: [
    { id: 'gpt-4', name: 'GPT-4', description: 'Most capable' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and affordable' },
  ],
  anthropic: [
    { id: 'claude-3-opus', name: 'Claude 3 Opus', description: 'Most intelligent' },
    { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', description: 'Balanced' },
  ],
};
```

**Backend Integration:**

Update `backend/services/conversation_pipeline.py` to accept provider and model:

```python
def _build_llm_request(self, text: str, provider: str, model: str, optimization_level: str):
    # Currently hardcoded at llm_service.py:205
    payload = {
        "model": model,  # ← Use from UI
        "messages": [...],
        "temperature": config.llm_temperature,
        "max_tokens": max_tokens,
    }
```

**Required Backend Work:**

1. Add OpenAI integration to `backend/services/llm_service.py`
2. Add Anthropic integration
3. Create provider abstraction layer
4. Update WebSocket protocol to accept `llmProvider` and `llmModel` parameters

---

## TTS Provider Selection

**Priority:** HIGH 🟠

**Current State:** Hardcoded to Sarvam only

**Backend Support:** Both Sarvam and ElevenLabs are integrated (`backend/services/tts_service.py`)

### UI Component Specification: `TTSProviderSelector`

**Location:** `frontend/src/components/settings/TTSProviderSelector.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Text-to-Speech Provider                       │
├────────────────────────────────────────────────┤
│                                                │
│  ○ Sarvam AI                                   │
│    22 Indian language voices                   │
│    Lower cost, optimized for Indian languages  │
│                                                │
│  ○ ElevenLabs                                  │
│    10 high-quality voices                      │
│    Higher quality, higher cost                 │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface TTSProviderSelectorProps {
  provider: 'sarvam' | 'elevenlabs';
  onChange: (provider: 'sarvam' | 'elevenlabs') => void;
}
```

**State Management:**

```typescript
// In App.tsx or settings store
const [ttsProvider, setTtsProvider] = useState<'sarvam' | 'elevenlabs'>('sarvam');
```

**Provider Details:**

```typescript
const ttsProviders = [
  {
    id: 'sarvam',
    name: 'Sarvam AI',
    description: '22 Indian language voices',
    details: 'Lower cost, optimized for Indian languages',
    voiceCount: 22,
    languages: ['hi-IN', 'ta-IN', 'te-IN', 'kn-IN', 'ml-IN', 'mr-IN', 'gu-IN', 'bn-IN', 'pa-IN', 'or-IN'],
  },
  {
    id: 'elevenlabs',
    name: 'ElevenLabs',
    description: '10 high-quality voices',
    details: 'Higher quality, higher cost',
    voiceCount: 10,
    languages: ['en-IN', 'en-US', 'en-GB'],
  },
];
```

**Backend Integration:**

Update `backend/services/conversation_pipeline.py:449`:

```python
def _build_tts_request(
    self,
    text: str,
    language: str,
    provider: str,  # ← NEW: From UI
    voice_id: str,  # ← NEW: From UI
    optimization_level: Optional[str] = None
):
    return SynthesizeRequest(
        text=text,
        language_code=language,
        voice=VoiceSelection(
            provider=provider,  # ← Use from UI instead of hardcoded "sarvam"
            voice_id=voice_id   # ← Use from UI instead of hardcoded "anushka"
        ),
        optimization_level=optimization_level or "balanced",
    )
```

**Required Backend Work:**

1. Update WebSocket protocol to accept `ttsProvider` parameter
2. Pass provider to `_build_tts_request`

---

## Voice Selection

**Priority:** HIGH 🟠

**Current State:** Hardcoded to "anushka" voice only

**Backend Support:** 22+ voices available in `backend/utils/voice_registry.py`

### UI Component Specification: `VoiceSelector`

**Location:** `frontend/src/components/settings/VoiceSelector.tsx`

**Layout (Grid View):**

```
┌────────────────────────────────────────────────────────────────┐
│  Voice Selection                                               │
│  Provider: Sarvam ▼                        Search: [____]      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Anushka     │  │  Maitreyi    │  │  Swati       │        │
│  │  Hindi       │  │  Hindi       │  │  Tamil       │        │
│  │  Female      │  │  Female      │  │  Female      │        │
│  │  [▶ Preview] │  │  [▶ Preview] │  │  [▶ Preview] │        │
│  │  [✓ Select]  │  │  [ Select ]  │  │  [ Select ]  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Aarav       │  │  Priya       │  │  Ravi        │        │
│  │  Hindi       │  │  Tamil       │  │  Telugu      │        │
│  │  Male        │  │  Female      │  │  Male        │        │
│  │  [▶ Preview] │  │  [▶ Preview] │  │  [▶ Preview] │        │
│  │  [ Select ]  │  │  [ Select ]  │  │  [ Select ]  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                │
│  ... (22 voices total)                                        │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Custom Preview                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │ Enter text to preview in selected voice...        │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │  [▶ Preview Custom Text]                                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface VoiceSelectorProps {
  provider: 'sarvam' | 'elevenlabs';
  selectedVoiceId: string;
  language: string;  // Filter by language
  onVoiceChange: (voiceId: string) => void;
}
```

**Voice Data Structure:**

```typescript
interface Voice {
  id: string;
  name: string;
  provider: 'sarvam' | 'elevenlabs';
  language: string;  // e.g., 'hi-IN'
  gender: 'male' | 'female' | 'neutral';
  description?: string;
  previewText: string;  // Default preview text in that language
}
```

**Voice List (from `backend/utils/voice_registry.py`):**

**Sarvam Voices:**

```typescript
const sarvamVoices: Voice[] = [
  {
    id: 'anushka',
    name: 'Anushka',
    provider: 'sarvam',
    language: 'hi-IN',
    gender: 'female',
    previewText: 'नमस्ते, मैं अनुष्का हूं।',
  },
  {
    id: 'maitreyi',
    name: 'Maitreyi',
    provider: 'sarvam',
    language: 'hi-IN',
    gender: 'female',
    previewText: 'नमस्ते, मैं मैत्रेयी हूं।',
  },
  {
    id: 'swati',
    name: 'Swati',
    provider: 'sarvam',
    language: 'ta-IN',
    gender: 'female',
    previewText: 'வணக்கம், நான் ஸ்வாதி.',
  },
  // ... 19+ more voices
];
```

**ElevenLabs Voices:**

```typescript
const elevenlabsVoices: Voice[] = [
  {
    id: '21m00Tcm4TlvDq8ikWAM',
    name: 'Rachel',
    provider: 'elevenlabs',
    language: 'en-US',
    gender: 'female',
    description: 'Calm, clear voice',
    previewText: 'Hello, I am Rachel.',
  },
  {
    id: 'AZnzlk1XvdvUeBnXmlld',
    name: 'Domi',
    provider: 'elevenlabs',
    language: 'en-US',
    gender: 'female',
    description: 'Energetic, friendly voice',
    previewText: 'Hi there! I am Domi.',
  },
  // ... 8+ more voices
];
```

**Features:**

1. **Filter by Language:** Only show voices for selected target language
2. **Search:** Filter by voice name
3. **Preview (Standard):** Click "Preview" to hear default sample text
4. **Preview (Custom):** Enter custom text to preview
5. **Select:** Click "Select" to use that voice

**Preview API Endpoint:**

```
POST /api/v1/tts/preview
{
  "voice_id": "anushka",
  "provider": "sarvam",
  "text": "नमस्ते, मैं अनुष्का हूं।",
  "language_code": "hi-IN"
}

Response:
{
  "audio_b64": "...",
  "mime_type": "audio/wav"
}
```

**Backend Work Required:**

1. Create `/api/v1/tts/preview` endpoint
2. Update WebSocket protocol to accept `voiceId` parameter

---

## Enhanced Language Selection

**Priority:** MEDIUM 🟡

**Current State:** User manually selects from 22 languages

**Missing Feature:** Multilingual mode (auto-detect language from speech)

### UI Component Specification: `LanguageSettings`

**Location:** `frontend/src/components/settings/LanguageSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Language Settings                             │
├────────────────────────────────────────────────┤
│                                                │
│  Mode                                          │
│  ○ Single Language                             │
│    Select one target language                  │
│                                                │
│  ● Multilingual (Auto-detect)                  │
│    Automatically detect and respond in the     │
│    same language the user speaks               │
│                                                │
│  ┌────────────────────────────────────────────┤
│  │ Single Language Mode                       │
│  │                                            │
│  │ Target Language                            │
│  │ ┌────────────────────────────────────────┐│
│  │ │ Hindi (हिंदी) ▼                        ││
│  │ └────────────────────────────────────────┘│
│  │                                            │
│  │ Options: Hindi, Tamil, Telugu, Kannada,   │
│  │ Malayalam, Marathi, Gujarati, Bengali,    │
│  │ Punjabi, Odia, Assamese, English, etc.    │
│  └────────────────────────────────────────────┘
│                                                │
│  ┌────────────────────────────────────────────┤
│  │ Multilingual Mode                         │
│  │                                            │
│  │ ✅ Auto-detect language from speech        │
│  │                                            │
│  │ Allowed Languages (Select multiple)       │
│  │ ☑ Hindi       ☑ Tamil       ☑ Telugu      │
│  │ ☑ Kannada     ☑ Malayalam   ☑ Marathi     │
│  │ ☑ Gujarati    ☑ Bengali     ☑ Punjabi     │
│  │ ☑ English     ☐ Odia        ☐ Assamese    │
│  │                                            │
│  │ ℹ️ AI will detect which language you're    │
│  │   speaking and respond in the same         │
│  │   language.                                │
│  └────────────────────────────────────────────┘
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface LanguageSettingsProps {
  mode: 'single' | 'multilingual';
  singleLanguage: LanguageCode;
  allowedLanguages: LanguageCode[];
  onModeChange: (mode: 'single' | 'multilingual') => void;
  onSingleLanguageChange: (lang: LanguageCode) => void;
  onAllowedLanguagesChange: (langs: LanguageCode[]) => void;
}
```

**State Management:**

```typescript
// In App.tsx or settings store
const [languageMode, setLanguageMode] = useState<'single' | 'multilingual'>('single');
const [singleLanguage, setSingleLanguage] = useState<LanguageCode>('hi-IN');
const [allowedLanguages, setAllowedLanguages] = useState<LanguageCode[]>([
  'hi-IN',
  'ta-IN',
  'te-IN',
  'en-IN',
]);
```

**Backend Integration:**

**Option 1: ASR Language Detection**

Sarvam ASR can detect language automatically. Update `backend/services/asr_service.py`:

```python
async def transcribe(
    self,
    audio_url: str,
    language_code: Optional[str] = None,  # ← Make optional
    enable_auto_detect: bool = False,     # ← NEW parameter
    allowed_languages: Optional[list[str]] = None,  # ← NEW parameter
):
    if enable_auto_detect:
        # Use Sarvam's language detection
        # Response will include detected language
        payload = {
            "audio_url": audio_url,
            "language_codes": allowed_languages or ["hi-IN", "en-IN", "ta-IN"],
            "auto_detect": True,
        }
    else:
        payload = {
            "audio_url": audio_url,
            "language_code": language_code,
        }

    # ... make API call ...

    return TranscriptResult(
        text=data["transcript"],
        confidence=data.get("confidence"),
        detected_language=data.get("detected_language"),  # ← NEW field
    )
```

**Option 2: LLM Language Detection**

If ASR doesn't support auto-detect, use LLM to detect language:

```python
# In conversation_pipeline.py, after ASR:
if language_mode == "multilingual":
    # Ask LLM to detect language
    detected_lang = await self.llm_service.detect_language(
        transcript.text,
        allowed_languages=allowed_languages,
    )
    target_language = detected_lang
else:
    target_language = single_language  # From UI
```

**Frontend Display:**

Show detected language in UI:

```typescript
// In message bubble
<div className="message-meta">
  Detected: Hindi (हिंदी)
  <span className="badge">auto-detected</span>
</div>
```

**Backend Work Required:**

1. Add language detection support to ASR service
2. Update WebSocket protocol to accept `languageMode`, `singleLanguage`, `allowedLanguages`
3. Update conversation pipeline to handle multilingual mode

---

## Advanced Audio Settings

**Priority:** MEDIUM 🟡

**Current State:** No audio processing controls in UI

**Backend Support:** Noise suppression, echo cancellation available in AudioRecorder

### UI Component Specification: `AudioSettings`

**Location:** `frontend/src/components/settings/AudioSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Audio Processing                              │
├────────────────────────────────────────────────┤
│                                                │
│  Presets                                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Quiet  │ │Moderate│ │ Noisy  │ │ Custom │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ │
│                                                │
│  Noise Suppression                             │
│  ☑ Enabled                                     │
│  Level: ○ Low  ● Medium  ○ High  ○ Very High  │
│                                                │
│  Echo Cancellation                             │
│  ☑ Enabled                                     │
│                                                │
│  Auto Gain Control                             │
│  ☑ Enabled                                     │
│                                                │
│  Sarvam AI Preprocessing (Premium)             │
│  ☐ Enable AI noise reduction                   │
│  ℹ️ Advanced noise removal using Sarvam AI     │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface AudioSettingsProps {
  preset: 'quiet' | 'moderate' | 'noisy' | 'custom';
  noiseSuppression: boolean;
  noiseSuppressionLevel: 'low' | 'medium' | 'high' | 'very_high';
  echoCancellation: boolean;
  autoGainControl: boolean;
  sarvamPreprocessing: boolean;
  onPresetChange: (preset: string) => void;
  onSettingsChange: (settings: AudioProcessingSettings) => void;
}
```

**Preset Configurations:**

```typescript
const audioPresets = {
  quiet: {
    noiseSuppression: true,
    noiseSuppressionLevel: 'low',
    echoCancellation: false,
    autoGainControl: true,
    sarvamPreprocessing: false,
  },
  moderate: {
    noiseSuppression: true,
    noiseSuppressionLevel: 'medium',
    echoCancellation: true,
    autoGainControl: true,
    sarvamPreprocessing: false,
  },
  noisy: {
    noiseSuppression: true,
    noiseSuppressionLevel: 'very_high',
    echoCancellation: true,
    autoGainControl: true,
    sarvamPreprocessing: true,
  },
  custom: {
    // User-defined
  },
};
```

**Frontend Integration:**

Update `AudioRecorder` to use these settings:

```typescript
// In AudioRecorder.ts
const constraints: MediaStreamConstraints = {
  audio: {
    echoCancellation: settings.echoCancellation,
    noiseSuppression: settings.noiseSuppression,
    autoGainControl: settings.autoGainControl,
  },
};
```

---

## Barge-In Controls

**Priority:** MEDIUM 🟡

**Current State:** Interrupt manager exists in backend, no UI controls

**Backend Support:** Full interrupt support in `backend/services/interrupt_manager.py`

### UI Component Specification: `BargeInSettings`

**Location:** `frontend/src/components/settings/BargeInSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Barge-In (Interrupt) Settings                 │
├────────────────────────────────────────────────┤
│                                                │
│  Enable Barge-In                               │
│  ☑ Allow interrupting AI while speaking        │
│                                                │
│  Voice Activity Detection (VAD)                │
│  Sensitivity: [────●──────] 70%                │
│  Less ←                        → More          │
│                                                │
│  Minimum Speech Duration: 300 ms               │
│  ┌────────────────────────────────────────┐   │
│  │ [slider: 100-1000ms]                   │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  Interruption Delay: 0 ms                      │
│  ┌────────────────────────────────────────┐   │
│  │ [slider: 0-500ms]                      │   │
│  └────────────────────────────────────────┘   │
│  ℹ️ Delay before canceling AI response         │
│                                                │
│  Resume After False Trigger                    │
│  ☑ Resume playback if user stops talking       │
│                                                │
│  [Test Barge-In] button                        │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface BargeInSettingsProps {
  enabled: boolean;
  vadSensitivity: number;  // 0-1
  minSpeechDuration: number;  // ms
  interruptionDelay: number;  // ms
  resumeAfterFalse: boolean;
  onSettingsChange: (settings: BargeInSettings) => void;
}
```

**Frontend Integration:**

Update `AudioRecorder` to detect voice activity:

```typescript
// In AudioRecorder.ts
class AudioRecorder {
  private vad: VoiceActivityDetector;

  constructor(settings: BargeInSettings) {
    this.vad = new VoiceActivityDetector({
      sensitivity: settings.vadSensitivity,
      minDuration: settings.minSpeechDuration,
    });
  }

  async start(onChunk: (chunk: AudioChunk) => void) {
    // ... existing code ...

    this.vad.on('speech-start', () => {
      // User started speaking
      if (this.settings.enabled) {
        // Notify backend to interrupt current operation
        this.onBargeIn?.();
      }
    });
  }
}
```

**Backend Integration:**

Send interrupt signal via WebSocket:

```typescript
// In VoiceChat.tsx
const handleBargeIn = useCallback(() => {
  sendWsMessage({
    type: 'interrupt',
    sessionId: stableSessionId,
    turnId: currentTurnId,
    reason: 'user_barge_in',
  });
}, [stableSessionId, currentTurnId, sendWsMessage]);
```

**Backend Handler:**

```python
# In routes.py WebSocket handler
if message_type == "interrupt":
    turn_id = payload.get("turnId")
    await pipeline.interrupt_turn(
        session_id=session_id,
        turn_id=turn_id,
        reason=InterruptReason.USER_BARGE_IN,
    )
```

---

## Guardrail Management

**Priority:** LOW 🟢

**Current State:** Guardrails work in backend, no admin UI

**Backend Support:** Full guardrail system in `backend/services/guardrail_service.py`

### UI Component Specification: `GuardrailSettings` (Admin)

**Location:** `frontend/src/components/admin/GuardrailSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  Guardrail Configuration                                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Active Rules                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Rule Name          │ Type      │ Status  │ Actions       │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │ Profanity Filter   │ Keyword   │ ✅ On   │ [Edit][Del]  │ │
│  │ PII Detection      │ Pattern   │ ✅ On   │ [Edit][Del]  │ │
│  │ Prompt Injection   │ AI-based  │ ✅ On   │ [Edit][Del]  │ │
│  │ Custom Rule 1      │ Keyword   │ ⭕ Off  │ [Edit][Del]  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  [+ Add New Rule]                                             │
│                                                                │
│  Blocked Keywords                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ [offensive_word_1] [x]  [offensive_word_2] [x]           │ │
│  │ [banned_term] [x]       [another_term] [x]               │ │
│  │                                                          │ │
│  │ [+ Add Keyword] [Bulk Import]                            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Violation Statistics                                          │
│  ┌────────────────┬────────────────┬────────────────────────┐ │
│  │ Total: 42      │ Last 24h: 3    │ Last 7d: 12           │ │
│  └────────────────┴────────────────┴────────────────────────┘ │
│                                                                │
│  Recent Violations                                             │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Time       │ Rule          │ Layer     │ Input          │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │ 2 min ago  │ Profanity     │ Pre-LLM   │ [text...]      │ │
│  │ 1 hour ago │ PII           │ Post-LLM  │ [text...]      │ │
│  │ 3 hours    │ Prompt Inject │ Pre-LLM   │ [text...]      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface GuardrailSettingsProps {
  rules: GuardrailRule[];
  blockedKeywords: string[];
  violations: GuardrailViolation[];
  onRuleToggle: (ruleId: string, enabled: boolean) => void;
  onRuleEdit: (rule: GuardrailRule) => void;
  onRuleDelete: (ruleId: string) => void;
  onKeywordAdd: (keyword: string) => void;
  onKeywordRemove: (keyword: string) => void;
}
```

**Backend API Endpoints:**

```
GET /api/v1/admin/guardrails/rules
GET /api/v1/admin/guardrails/violations?limit=100
POST /api/v1/admin/guardrails/rules
PUT /api/v1/admin/guardrails/rules/{id}
DELETE /api/v1/admin/guardrails/rules/{id}
```

---

## RAG Configuration

**Priority:** LOW 🟢

**Current State:** RAG works in backend, no UI controls for configuration

**Backend Support:** RAG service in `backend/services/rag_service.py`

### UI Component Specification: `RAGSettings` (Admin)

**Location:** `frontend/src/components/admin/RAGSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  RAG (Retrieval Augmented Generation)         │
├────────────────────────────────────────────────┤
│                                                │
│  Enable RAG                                    │
│  ☑ Use knowledge base for responses            │
│                                                │
│  Retrieval Settings                            │
│  Max Chunks: [slider: 1-10] 5                  │
│  ℹ️ Number of context chunks to retrieve       │
│                                                │
│  Similarity Threshold: [slider: 0.5-1.0] 0.7   │
│  ℹ️ Minimum similarity score for relevance     │
│                                                │
│  Optimization-Level Behavior                   │
│  ┌────────────────────────────────────────┐   │
│  │ Quality:         10 chunks, deep search│   │
│  │ Balanced Quality: 5 chunks             │   │
│  │ Balanced:         3 chunks             │   │
│  │ Balanced Speed:   2 chunks             │   │
│  │ Speed:            0 chunks (RAG off)   │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  Knowledge Base                                │
│  Documents: 42                                 │
│  Chunks: 1,284                                 │
│  Last Updated: 2 hours ago                     │
│                                                │
│  [Manage Documents] button                     │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface RAGSettingsProps {
  enabled: boolean;
  maxChunks: number;
  similarityThreshold: number;
  documentCount: number;
  chunkCount: number;
  lastUpdated: Date;
  onSettingsChange: (settings: RAGSettings) => void;
}
```

---

## Cost Budget Controls

**Priority:** MEDIUM 🟡

**Current State:** Cost tracking exists, no budget limits in UI

**Backend Support:** Cost tracker in `backend/services/cost_tracker.py`

### UI Component Specification: `BudgetSettings`

**Location:** `frontend/src/components/settings/BudgetSettings.tsx`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Monthly Budget                                │
├────────────────────────────────────────────────┤
│                                                │
│  Budget Limit: $50.00 / month                  │
│  ┌────────────────────────────────────────┐   │
│  │ [slider: $0-$500]                      │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  Current Usage                                 │
│  $12.35 / $50.00 (24.7%)                       │
│  ┌────────────────────────────────────────┐   │
│  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  Alert Thresholds                              │
│  ☑ 50% ($25.00)  - Email notification          │
│  ☑ 75% ($37.50)  - Email + Dashboard warning   │
│  ☑ 90% ($45.00)  - Email + Reduce quality      │
│  ☑ 100% ($50.00) - Stop API calls              │
│                                                │
│  Projected End-of-Month: $49.40                │
│  ℹ️ Based on current usage trends              │
│                                                │
│  [View Detailed Breakdown]                     │
│                                                │
└────────────────────────────────────────────────┘
```

**Component Props:**

```typescript
interface BudgetSettingsProps {
  monthlyLimit: number;
  currentSpending: number;
  projectedSpending: number;
  alerts: BudgetAlert[];
  onLimitChange: (limit: number) => void;
  onAlertsChange: (alerts: BudgetAlert[]) => void;
}
```

**Backend API:**

```
GET /api/v1/budget/current
PUT /api/v1/budget/limit
GET /api/v1/budget/projected
```

---

## Summary of Missing Features

### Critical (Must Fix Immediately) 🔴

1. **Text Chat Bug** - Currently broken, needs immediate fix

### High Priority (Before Production) 🟠

2. **LLM Provider & Model Selection** - Hardcoded to Sarvam only
3. **TTS Provider Selection** - Hardcoded to Sarvam only
4. **Voice Selection** - Hardcoded to "anushka" only

### Medium Priority (Nice to Have) 🟡

5. **Enhanced Language Selection** - Add multilingual auto-detect mode
6. **Advanced Audio Settings** - Noise suppression, echo cancellation controls
7. **Barge-In Controls** - UI for interrupt settings
8. **Cost Budget Controls** - Monthly budget limits and alerts

### Low Priority (Future Enhancement) 🟢

9. **Guardrail Management** - Admin UI for rule management
10. **RAG Configuration** - Admin UI for knowledge base settings

---

## Implementation Order Recommendation

1. **Week 1:** Fix text chat bug (Critical)
2. **Week 2:** Add TTS provider + voice selection
3. **Week 3:** Add LLM provider + model selection
4. **Week 4:** Add multilingual mode
5. **Week 5:** Add audio settings + barge-in controls
6. **Week 6:** Add budget controls
7. **Week 7:** Add admin features (guardrails, RAG)

---

## Next Steps

1. Review this document with stakeholders
2. Prioritize which features to implement first
3. Create detailed implementation tasks for each feature
4. Assign to development sprints
