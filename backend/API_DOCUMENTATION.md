# Analytics & Monitoring API Documentation

This document describes the analytics and monitoring endpoints for the Speech AI platform.

## Authentication

All API endpoints require an API key to be passed in the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

## Base URL

```
http://localhost:8000/api/v1
```

---

## Session Cost Analytics

### Get Session Costs

Retrieve cost summary for a specific session, including service and provider breakdowns.

**Endpoint:** `GET /sessions/{session_id}/costs`

**Parameters:**
- `session_id` (path, required): Unique identifier for the session

**Response:** `200 OK`

```json
{
  "total_cost_usd": 0.0456,
  "breakdown_by_service": {
    "asr": 0.0023,
    "llm": 0.0245,
    "translation": 0.0012,
    "tts": 0.0176
  },
  "breakdown_by_provider": {
    "sarvam": 0.0456
  },
  "total_entries": 12,
  "cache_savings_usd": 0.0123,
  "optimization_level": "balanced"
}
```

**Response Fields:**
- `total_cost_usd` (float): Total cost in USD for the session
- `breakdown_by_service` (object): Cost breakdown by service type (ASR, LLM, Translation, TTS)
- `breakdown_by_provider` (object): Cost breakdown by provider (Sarvam, OpenAI, ElevenLabs, etc.)
- `total_entries` (integer): Number of cost entries recorded
- `cache_savings_usd` (float): Estimated savings from cache hits (50% of cached operation cost)
- `optimization_level` (string): Current optimization level for the session

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/sessions/session-123/costs" \
  -H "X-API-Key: your-api-key-here"
```

**Use Cases:**
- Display real-time cost tracking in frontend
- Monitor per-session expenses
- Identify cost optimization opportunities
- Track cache effectiveness

---

## Session Metrics

### Get Session Metrics

Retrieve comprehensive performance metrics for a session, including latencies, cache stats, and turn counts.

**Endpoint:** `GET /sessions/{session_id}/metrics`

**Parameters:**
- `session_id` (path, required): Unique identifier for the session

**Response:** `200 OK`

```json
{
  "total_turns": 15,
  "successful_turns": 13,
  "failed_turns": 1,
  "interrupted_turns": 1,
  "avg_asr_latency_ms": 523.4,
  "avg_llm_latency_ms": 1245.7,
  "avg_translation_latency_ms": 312.5,
  "avg_tts_latency_ms": 856.2,
  "avg_total_latency_ms": 2937.8,
  "cache_hit_rate": 0.42,
  "llm_cache_hits": 5,
  "llm_cache_misses": 8,
  "tts_cache_hits": 3,
  "tts_cache_misses": 10,
  "guardrail_violations": 2,
  "guardrail_blocks": 1,
  "total_cost_usd": 0.0456,
  "optimization_level": "balanced",
  "language_code": "hi-IN"
}
```

**Response Fields:**

**Turn Statistics:**
- `total_turns` (integer): Total number of conversation turns
- `successful_turns` (integer): Number of successfully completed turns
- `failed_turns` (integer): Number of turns that encountered errors
- `interrupted_turns` (integer): Number of turns interrupted by user barge-in

**Latency Metrics (in milliseconds):**
- `avg_asr_latency_ms` (float): Average ASR (speech-to-text) latency
- `avg_llm_latency_ms` (float): Average LLM (language model) latency
- `avg_translation_latency_ms` (float): Average translation latency
- `avg_tts_latency_ms` (float): Average TTS (text-to-speech) latency
- `avg_total_latency_ms` (float): Average end-to-end pipeline latency

**Cache Performance:**
- `cache_hit_rate` (float): Overall cache hit rate (0.0 to 1.0)
- `llm_cache_hits` (integer): Number of LLM cache hits
- `llm_cache_misses` (integer): Number of LLM cache misses
- `tts_cache_hits` (integer): Number of TTS cache hits
- `tts_cache_misses` (integer): Number of TTS cache misses

**Guardrails:**
- `guardrail_violations` (integer): Number of guardrail violations detected
- `guardrail_blocks` (integer): Number of requests blocked by guardrails

**Session Context:**
- `total_cost_usd` (float): Total cost for the session
- `optimization_level` (string): Current optimization level (quality/balanced/speed)
- `language_code` (string): Language code being used

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/sessions/session-123/metrics" \
  -H "X-API-Key: your-api-key-here"
```

**Use Cases:**
- Monitor session performance in real-time
- Identify latency bottlenecks in the pipeline
- Track cache effectiveness
- Monitor guardrail activity
- Calculate success rates

---

## User Feedback

### Submit Feedback

Submit user feedback for a conversation turn or message.

**Endpoint:** `POST /feedback`

**Request Body:**

```json
{
  "session_id": "session-123",
  "turn_id": "turn-456",
  "message_id": "msg-789",
  "rating": 1,
  "rating_type": "thumbs",
  "feedback_text": "Great response, very helpful!",
  "feedback_category": "quality",
  "incorrect_response": false,
  "too_slow": false,
  "unhelpful": false,
  "offensive": false,
  "user_input": "What is my order status?",
  "assistant_response": "Your order is being processed and will ship tomorrow.",
  "metadata": {
    "optimization_level": "balanced",
    "language": "hi-IN"
  }
}
```

**Request Fields:**

**Required:**
- `session_id` (string): Session identifier
- `rating` (integer): Rating value
  - For `thumbs` type: `-1` (thumbs down) or `1` (thumbs up)
  - For `stars` type: `1` to `5`
- `rating_type` (string): Either `"thumbs"` or `"stars"`

**Optional:**
- `turn_id` (string): Turn identifier
- `message_id` (string): Message identifier
- `feedback_text` (string): Free-form feedback text
- `feedback_category` (string): Category of feedback (e.g., "quality", "accuracy", "speed")
- `incorrect_response` (boolean): Flag if response was incorrect
- `too_slow` (boolean): Flag if response was too slow
- `unhelpful` (boolean): Flag if response was unhelpful
- `offensive` (boolean): Flag if response was offensive
- `user_input` (string): User's input text (for context)
- `assistant_response` (string): Assistant's response text (for context)
- `metadata` (object): Additional metadata

**Response:** `201 Created`

```json
{
  "id": 42,
  "session_id": "session-123",
  "rating": 1,
  "rating_type": "thumbs",
  "created_at": "2025-10-15T14:32:10.123456"
}
```

**Response Fields:**
- `id` (integer): Unique feedback entry ID
- `session_id` (string): Session identifier
- `rating` (integer): Rating value submitted
- `rating_type` (string): Rating type used
- `created_at` (string): ISO 8601 timestamp of feedback submission

**Error Responses:**

`400 Bad Request` - Invalid rating for rating type:

```json
{
  "detail": "Rating must be -1 (thumbs down) or 1 (thumbs up) for thumbs type"
}
```

```json
{
  "detail": "Rating must be between 1 and 5 for stars type"
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-123",
    "turn_id": "turn-456",
    "rating": 1,
    "rating_type": "thumbs",
    "feedback_text": "Excellent response!",
    "user_input": "What is my order status?",
    "assistant_response": "Your order is being processed."
  }'
```

**Use Cases:**
- Collect user satisfaction ratings
- Identify problematic responses
- Track quality over time
- Improve model performance based on feedback
- Flag responses for review

---

## Data Models

### CostEntry

Individual cost entry for a service call.

```python
{
  "service": "llm",           # asr, llm, translation, tts
  "provider": "sarvam",       # sarvam, elevenlabs, openai, etc.
  "operation": "generate",    # transcribe, generate, translate, synthesize
  "units": 1500,              # tokens, characters, seconds
  "unit_type": "tokens",      # tokens, chars, audio_seconds
  "cost_usd": 0.0030,         # Cost in USD
  "session_id": "session-123",
  "turn_id": "turn-456",
  "cached": false,
  "optimization_level": "balanced",
  "timestamp": "2025-10-15T14:32:10.123456"
}
```

### SessionMetrics

Aggregated metrics for a session.

```python
{
  "session_id": "session-123",
  "total_turns": 15,
  "successful_turns": 13,
  "failed_turns": 1,
  "interrupted_turns": 1,
  "avg_asr_latency_ms": 523.4,
  "avg_llm_latency_ms": 1245.7,
  "avg_translation_latency_ms": 312.5,
  "avg_tts_latency_ms": 856.2,
  "avg_total_latency_ms": 2937.8,
  "cache_hit_rate": 0.42,
  "llm_cache_hits": 5,
  "llm_cache_misses": 8,
  "tts_cache_hits": 3,
  "tts_cache_misses": 10,
  "guardrail_violations": 2,
  "guardrail_blocks": 1,
  "total_cost_usd": 0.0456,
  "optimization_level": "balanced",
  "language_code": "hi-IN"
}
```

### UserFeedback

User feedback entry.

```python
{
  "id": 42,
  "session_id": "session-123",
  "turn_id": "turn-456",
  "message_id": "msg-789",
  "rating": 1,
  "rating_type": "thumbs",
  "feedback_text": "Great response!",
  "feedback_category": "quality",
  "incorrect_response": false,
  "too_slow": false,
  "unhelpful": false,
  "offensive": false,
  "user_input": "What is my order status?",
  "assistant_response": "Your order is being processed.",
  "metadata": {},
  "created_at": "2025-10-15T14:32:10.123456"
}
```

---

## Rate Limiting

Currently, there are no rate limits on these endpoints. However, it's recommended to:
- Poll cost/metrics endpoints at intervals of 3-5 seconds
- Avoid excessive polling that could impact backend performance
- Implement exponential backoff on errors

## Error Handling

All endpoints may return the following error responses:

**401 Unauthorized** - Missing or invalid API key:
```json
{
  "detail": "Invalid API key"
}
```

**404 Not Found** - Session not found:
```json
{
  "detail": "Session not found"
}
```

**500 Internal Server Error** - Server error:
```json
{
  "detail": "Internal server error"
}
```

## Frontend Integration Examples

### React/TypeScript Example

```typescript
// Fetch session costs
const fetchCosts = async (sessionId: string) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/sessions/${sessionId}/costs`,
    {
      headers: {
        'X-API-Key': process.env.VITE_API_KEY || '',
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch costs');
  }

  return await response.json();
};

// Fetch session metrics
const fetchMetrics = async (sessionId: string) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/sessions/${sessionId}/metrics`,
    {
      headers: {
        'X-API-Key': process.env.VITE_API_KEY || '',
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch metrics');
  }

  return await response.json();
};

// Submit feedback
const submitFeedback = async (feedback: FeedbackRequest) => {
  const response = await fetch(
    'http://localhost:8000/api/v1/feedback',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.VITE_API_KEY || '',
      },
      body: JSON.stringify(feedback),
    }
  );

  if (!response.ok) {
    throw new Error('Failed to submit feedback');
  }

  return await response.json();
};

// Auto-refresh with polling
useEffect(() => {
  const interval = setInterval(() => {
    void fetchCosts(sessionId);
    void fetchMetrics(sessionId);
  }, 5000); // Poll every 5 seconds

  return () => clearInterval(interval);
}, [sessionId]);
```

### Python Example

```python
import requests

API_KEY = "your-api-key-here"
BASE_URL = "http://localhost:8000/api/v1"

# Fetch session costs
response = requests.get(
    f"{BASE_URL}/sessions/session-123/costs",
    headers={"X-API-Key": API_KEY}
)
costs = response.json()
print(f"Total cost: ${costs['total_cost_usd']:.4f}")

# Fetch session metrics
response = requests.get(
    f"{BASE_URL}/sessions/session-123/metrics",
    headers={"X-API-Key": API_KEY}
)
metrics = response.json()
print(f"Success rate: {metrics['successful_turns'] / metrics['total_turns'] * 100:.1f}%")

# Submit feedback
feedback = {
    "session_id": "session-123",
    "turn_id": "turn-456",
    "rating": 1,
    "rating_type": "thumbs",
    "feedback_text": "Great response!"
}
response = requests.post(
    f"{BASE_URL}/feedback",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json=feedback
)
print(f"Feedback ID: {response.json()['id']}")
```

---

## Changelog

### Version 1.0.0 (2025-10-15)
- Initial release
- Added `/sessions/{session_id}/costs` endpoint
- Added `/sessions/{session_id}/metrics` endpoint
- Added `/feedback` endpoint
- Integrated cost tracking with database persistence
- Added metrics tracking to conversation pipeline
