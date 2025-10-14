"""Prometheus metrics for backend services."""

from prometheus_client import Counter, Histogram


metrics = {
    "tts_requests_total": Counter(
        "tts_requests_total",
        "Total TTS synthesis requests",
        labelnames=("provider", "cache"),
    ),
    "tts_latency_seconds": Histogram(
        "tts_latency_seconds",
        "Latency of TTS synthesis",
        labelnames=("provider",),
        buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10),
    ),
    "tts_cache_hits_total": Counter(
        "tts_cache_hits_total",
        "Number of cache hits for TTS",
        labelnames=("provider",),
    ),
    "tts_failures_total": Counter(
        "tts_failures_total",
        "Number of synthesis failures",
        labelnames=("provider", "reason"),
    ),
    "tts_fallback_total": Counter(
        "tts_fallback_total",
        "Fallbacks triggered during synthesis",
        labelnames=("from_provider", "to_provider"),
    ),
}


