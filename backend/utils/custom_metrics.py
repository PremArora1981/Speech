"""Custom Prometheus metrics for business KPIs."""

from prometheus_client import Counter, Histogram, Gauge, Summary, REGISTRY

# Prevent duplicate registration during development with --reload
_metrics_registered = False

def _get_or_create_metric(metric_class, name, description, labelnames=None, **kwargs):
    """Get existing metric or create new one."""
    labelnames = labelnames or []
    # Try to find existing metric
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    # Create new metric
    return metric_class(name, description, labelnames, **kwargs)

# Conversation Metrics
conversation_starts_total = _get_or_create_metric(
    Counter,
    'conversation_starts_total',
    'Total number of conversation sessions started',
    ['optimization_level', 'target_language']
)

conversation_turns_total = _get_or_create_metric(
    Counter,
    'conversation_turns_total',
    'Total number of conversation turns',
    ['status', 'optimization_level']  # status: success/failed/interrupted
)

conversation_duration_seconds = _get_or_create_metric(
    Histogram,
    'conversation_duration_seconds',
    'Duration of conversation sessions',
    ['optimization_level'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

# Pipeline Stage Latencies
asr_latency_seconds = _get_or_create_metric(
    Histogram,
    'asr_latency_seconds',
    'ASR transcription latency',
    ['provider', 'optimization_level'],
    buckets=(.1, .25, .5, 1.0, 2.0, 5.0, 10.0)
)

llm_latency_seconds = _get_or_create_metric(
    Histogram,
    'llm_latency_seconds',
    'LLM generation latency',
    ['provider', 'optimization_level', 'cached'],
    buckets=(.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)
)

translation_latency_seconds = _get_or_create_metric(
    Histogram,
    'translation_latency_seconds',
    'Translation latency',
    ['source_language', 'target_language', 'optimization_level'],
    buckets=(.1, .25, .5, 1.0, 2.0, 5.0)
)

tts_latency_seconds = _get_or_create_metric(
    Histogram,
    'tts_latency_seconds',
    'TTS synthesis latency',
    ['provider', 'language', 'optimization_level', 'cached'],
    buckets=(.25, .5, 1.0, 2.0, 5.0, 10.0)
)

total_pipeline_latency_seconds = _get_or_create_metric(
    Histogram,
    'total_pipeline_latency_seconds',
    'End-to-end pipeline latency',
    ['optimization_level'],
    buckets=(1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

# Cache Metrics
cache_hits_total = _get_or_create_metric(
    Counter,
    'cache_hits_total',
    'Total cache hits',
    ['cache_type', 'optimization_level']  # cache_type: llm/tts
)

cache_misses_total = _get_or_create_metric(
    Counter,
    'cache_misses_total',
    'Total cache misses',
    ['cache_type', 'optimization_level']
)

cache_size_bytes = _get_or_create_metric(
    Gauge,
    'cache_size_bytes',
    'Current cache size in bytes',
    ['cache_type']
)

# Cost Metrics
api_cost_usd = _get_or_create_metric(
    Counter,
    'api_cost_usd',
    'Total API costs in USD',
    ['service', 'provider']  # service: asr/llm/translation/tts
)

api_requests_total = _get_or_create_metric(
    Counter,
    'api_requests_total',
    'Total API requests',
    ['service', 'provider', 'status']  # status: success/failure
)

# Guardrail Metrics
guardrail_violations_total = _get_or_create_metric(
    Counter,
    'guardrail_violations_total',
    'Total guardrail violations',
    ['layer', 'violation_type', 'severity']  # layer: pre_llm/llm_prompt/post_llm
)

guardrail_blocks_total = _get_or_create_metric(
    Counter,
    'guardrail_blocks_total',
    'Total requests blocked by guardrails',
    ['layer', 'reason']
)

# Interrupt/Barge-in Metrics
interrupts_total = _get_or_create_metric(
    Counter,
    'interrupts_total',
    'Total barge-in interrupts',
    ['stage']  # stage: asr/llm/translation/tts
)

# User Feedback Metrics
user_feedback_total = _get_or_create_metric(
    Counter,
    'user_feedback_total',
    'Total user feedback submissions',
    ['rating', 'turn_status']  # rating: positive/negative, turn_status: success/failed
)

# RAG Metrics
rag_retrievals_total = _get_or_create_metric(
    Counter,
    'rag_retrievals_total',
    'Total RAG document retrievals',
    ['optimization_level']
)

rag_documents_total = _get_or_create_metric(
    Gauge,
    'rag_documents_total',
    'Total documents in RAG index'
)

rag_retrieval_latency_seconds = _get_or_create_metric(
    Histogram,
    'rag_retrieval_latency_seconds',
    'RAG retrieval latency',
    ['optimization_level'],
    buckets=(.05, .1, .25, .5, 1.0, 2.0)
)

# Telephony Metrics
telephony_calls_total = _get_or_create_metric(
    Counter,
    'telephony_calls_total',
    'Total telephony calls',
    ['direction', 'status']  # direction: inbound/outbound, status: success/failed/ongoing
)

telephony_call_duration_seconds = _get_or_create_metric(
    Histogram,
    'telephony_call_duration_seconds',
    'Telephony call duration',
    ['direction'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

# System Health Metrics
active_websocket_connections = _get_or_create_metric(
    Gauge,
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

database_connections = _get_or_create_metric(
    Gauge,
    'database_connections',
    'Number of active database connections'
)

redis_memory_bytes = _get_or_create_metric(
    Gauge,
    'redis_memory_bytes',
    'Redis memory usage in bytes'
)

# Error Metrics
errors_total = _get_or_create_metric(
    Counter,
    'errors_total',
    'Total errors by type',
    ['error_type', 'component']  # component: asr/llm/translation/tts/rag/telephony
)

# Optimization Level Distribution
optimization_level_usage = _get_or_create_metric(
    Counter,
    'optimization_level_usage',
    'Usage count by optimization level',
    ['level']  # quality/balanced_quality/balanced/balanced_speed/speed
)

# Language Distribution
language_usage = _get_or_create_metric(
    Counter,
    'language_usage',
    'Usage count by language',
    ['language_code']
)
