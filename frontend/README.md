# Speech AI Frontend

Modern React-based frontend for the Speech AI voice chat application with real-time analytics and monitoring.

## Features

### Core Voice Interface
- **WebSocket-based real-time voice chat**
- **Audio recording** with MediaRecorder API
- **Audio playback** with Web Audio API
- **Barge-in support** for natural conversation flow
- **Optimization level selector** (Quality → Speed)

### Analytics & Monitoring
- **Real-time cost tracking** with service/provider breakdown
- **Session metrics** including latency, cache performance, and success rates
- **Visual latency indicators** with per-stage breakdown
- **Guardrail activity monitoring**

### Language Support
- **22 Indian languages** including:
  - Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati
  - Kannada, Malayalam, Punjabi, Odia, Urdu, Assamese
  - Kashmiri, Nepali, Sanskrit, Sindhi, Maithili
  - Konkani, Dogri, Manipuri, Santali, English

### User Feedback
- **Thumbs up/down rating system** for responses
- **Feedback collection** with context capture

## Tech Stack

- **React 19** with TypeScript
- **Vite** for build tooling
- **TailwindCSS** for styling
- **Lucide React** for icons
- **Web Audio API** for audio handling
- **WebSocket** for real-time communication

## Getting Started

### Install Dependencies

```bash
npm install
```

### Environment Variables

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_VOICE_WS_URL=ws://localhost:8000/api/v1/voice-session
VITE_TTS_URL=http://localhost:8000/api/v1/tts
VITE_API_KEY=your-api-key-here
```

### Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Run Tests

```bash
npm test
```

### Lint Code

```bash
npm run lint
```

## Component Documentation

### `LanguageSelector`

Language picker with 22 Indian languages.

```tsx
import { LanguageSelector } from './components';

<LanguageSelector
  value={targetLanguage}
  onChange={setTargetLanguage}
/>
```

**Props:**
- `value: LanguageCode` - Currently selected language
- `onChange: (language: LanguageCode) => void` - Change handler
- `className?: string` - Optional CSS classes

### `CostTracker`

Real-time cost tracking dashboard.

```tsx
import { CostTracker } from './components';

<CostTracker
  sessionId="session-123"
  apiUrl="http://localhost:8000/api/v1"
  apiKey="your-api-key"
  refreshInterval={5000}
/>
```

**Props:**
- `sessionId: string` - Session identifier
- `apiUrl?: string` - API base URL (default: `http://localhost:8000/api/v1`)
- `apiKey?: string` - API authentication key
- `refreshInterval?: number` - Refresh interval in ms (default: 5000)

**Features:**
- Total cost display
- Service breakdown (ASR, LLM, Translation, TTS)
- Provider breakdown (Sarvam, OpenAI, ElevenLabs)
- Cache savings with percentage
- Optimization level badge

### `SessionMetrics`

Comprehensive session analytics.

```tsx
import { SessionMetrics } from './components';

<SessionMetrics
  sessionId="session-123"
  apiUrl="http://localhost:8000/api/v1"
  apiKey="your-api-key"
  refreshInterval={3000}
/>
```

**Props:**
- `sessionId: string` - Session identifier
- `apiUrl?: string` - API base URL
- `apiKey?: string` - API authentication key
- `refreshInterval?: number` - Refresh interval in ms (default: 3000)

**Metrics Displayed:**
- Turn statistics (total, successful, failed, interrupted)
- Success rate
- Average latency per stage (ASR, LLM, Translation, TTS)
- Cache hit rate
- Cache hits/misses (LLM, TTS)
- Guardrail violations and blocks

### `LatencyIndicator`

Visual latency breakdown with color-coded thresholds.

```tsx
import { LatencyIndicator, createPipelineStages } from './components';

// With stages
const stages = createPipelineStages(500, 1200, 300, 800);
<LatencyIndicator
  stages={stages}
  optimizationLevel="balanced"
/>

// Or just total
<LatencyIndicator
  totalLatency={2800}
  optimizationLevel="balanced"
/>
```

**Props:**
- `stages?: LatencyStage[]` - Array of pipeline stages
- `totalLatency?: number` - Total latency in milliseconds
- `optimizationLevel?: string` - Optimization level for threshold calculation
- `className?: string` - Optional CSS classes

### `FeedbackRating`

Thumbs up/down feedback component.

```tsx
import { FeedbackRating } from './components';

<FeedbackRating
  messageId="msg-123"
  sessionId="session-123"
  turnId="turn-456"
  userInput="What is my order status?"
  assistantResponse="Your order is being processed."
/>
```

**Props:**
- `messageId: string` - Message identifier
- `sessionId: string` - Session identifier
- `turnId?: string` - Turn identifier
- `userInput?: string` - User's input text
- `assistantResponse?: string` - Assistant's response text

**Rating Values:**
- `1` - Thumbs up (helpful)
- `-1` - Thumbs down (not helpful)

### `AnalyticsDashboard`

Comprehensive analytics dashboard combining all metrics.

```tsx
import { AnalyticsDashboard } from './components';

<AnalyticsDashboard
  sessionId="session-123"
  optimizationLevel="balanced"
/>
```

**Props:**
- `sessionId: string` - Session identifier
- `optimizationLevel?: string` - Current optimization level
- `apiUrl?: string` - API base URL
- `apiKey?: string` - API authentication key
- `className?: string` - Optional CSS classes

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── AnalyticsDashboard.tsx
│   │   ├── CostTracker.tsx
│   │   ├── SessionMetrics.tsx
│   │   ├── LatencyIndicator.tsx
│   │   ├── FeedbackRating.tsx
│   │   ├── LanguageSelector.tsx
│   │   └── index.ts
│   ├── modules/             # Feature modules
│   │   ├── chat/
│   │   │   └── VoiceChat.tsx
│   │   └── admin/
│   │       └── TelephonyDashboard.tsx
│   ├── services/            # Service layer
│   │   └── audio/
│   │       ├── AudioRecorder.ts
│   │       ├── AudioPlayer.ts
│   │       └── __tests__/
│   ├── lib/                 # Utility functions
│   │   ├── config.ts
│   │   └── api.ts
│   ├── App.tsx              # Main app component
│   └── main.tsx             # Entry point
├── public/                  # Static assets
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

## Browser Support

- **Chrome/Edge:** Full support
- **Firefox:** Full support
- **Safari:** Full support (iOS 14.5+)
- **Opera:** Full support

**Required Features:**
- WebSocket API
- Web Audio API
- MediaRecorder API
- ES2020+

## License

Proprietary - Speech AI Platform
