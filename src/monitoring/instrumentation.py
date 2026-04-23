"""
Production Monitoring Instrumentation
Tracks latency, throughput, error rate, cache performance,
drift signals, and input integrity for the LLM inference server.
Built on prometheus_client for metrics emission.
"""

import time
import hashlib
import logging
import statistics
from typing import Optional, List, Dict
from collections import deque
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)

# ── Registry ──────────────────────────────────────────────────────────────────
registry = CollectorRegistry()

# ── Counters ──────────────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "llm_requests_total",
    "Total number of inference requests",
    ["endpoint", "status"],
    registry=registry
)

CACHE_HITS = Counter(
    "llm_cache_hits_total",
    "Total cache hits",
    registry=registry
)

CACHE_MISSES = Counter(
    "llm_cache_misses_total",
    "Total cache misses",
    registry=registry
)

BATCH_COUNT = Counter(
    "llm_batches_total",
    "Total number of batches processed",
    registry=registry
)

ERROR_COUNT = Counter(
    "llm_errors_total",
    "Total errors by type",
    ["error_type"],
    registry=registry
)

DRIFT_ALERTS = Counter(
    "llm_drift_alerts_total",
    "Total drift alerts triggered",
    ["feature"],
    registry=registry
)

# ── Histograms ────────────────────────────────────────────────────────────────
REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "cached"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

BATCH_SIZE = Histogram(
    "llm_batch_size",
    "Distribution of batch sizes",
    buckets=[1, 2, 4, 8, 16, 32],
    registry=registry
)

PROMPT_LENGTH = Histogram(
    "llm_prompt_length_tokens",
    "Distribution of prompt lengths in tokens",
    buckets=[10, 25, 50, 100, 200, 500, 1000],
    registry=registry
)

RESPONSE_LENGTH = Histogram(
    "llm_response_length_tokens",
    "Distribution of response lengths in tokens",
    buckets=[5, 10, 20, 50, 100, 200],
    registry=registry
)

# ── Gauges ────────────────────────────────────────────────────────────────────
ACTIVE_REQUESTS = Gauge(
    "llm_active_requests",
    "Currently active requests",
    registry=registry
)

QUEUE_SIZE = Gauge(
    "llm_queue_size",
    "Current batch queue size",
    registry=registry
)

CACHE_SIZE = Gauge(
    "llm_cache_size",
    "Current number of cache entries",
    registry=registry
)

CACHE_HIT_RATE = Gauge(
    "llm_cache_hit_rate",
    "Rolling cache hit rate (last 100 requests)",
    registry=registry
)

MEMORY_USAGE_MB = Gauge(
    "llm_memory_usage_mb",
    "Process memory usage in MB",
    registry=registry
)

CPU_USAGE_PCT = Gauge(
    "llm_cpu_usage_pct",
    "Process CPU usage percentage",
    registry=registry
)

THROUGHPUT_RPS = Gauge(
    "llm_throughput_rps",
    "Rolling requests per second (last 60s window)",
    registry=registry
)

DRIFT_SCORE = Gauge(
    "llm_drift_score",
    "Current drift score for input distribution",
    ["feature"],
    registry=registry
)

MODEL_VERSION = Gauge(
    "llm_model_version_info",
    "Model version information",
    ["model_name", "version"],
    registry=registry
)

# ── Summaries ─────────────────────────────────────────────────────────────────
INFERENCE_TIME = Summary(
    "llm_inference_duration_seconds",
    "Time spent on model inference only",
    registry=registry
)


# ── Metrics Collector ─────────────────────────────────────────────────────────

class MetricsCollector:
    """
    Central metrics collector.
    Tracks rolling windows for hit rate, throughput, and drift signals.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._request_times: deque = deque(maxlen=window_size)
        self._cache_results: deque = deque(maxlen=window_size)
        self._latencies: deque = deque(maxlen=window_size)
        self._prompt_lengths: deque = deque(maxlen=window_size)
        self._response_lengths: deque = deque(maxlen=window_size)

        # Reference distribution for drift detection
        self._reference_prompt_lengths: List[float] = []
        self._drift_scores: Dict[str, float] = {}

        # Set model version
        MODEL_VERSION.labels(
            model_name="distilgpt2",
            version="1.0.0"
        ).set(1)

        logger.info("MetricsCollector initialized")

    def record_request_start(self) -> float:
        """Record request start, return start timestamp"""
        ACTIVE_REQUESTS.inc()
        return time.time()

    def record_request_end(
        self,
        start_time: float,
        endpoint: str,
        status: str,
        was_cached: bool,
        prompt_length: int = 0,
        response_length: int = 0
    ) -> None:
        """Record completed request metrics"""
        latency = time.time() - start_time
        cached_label = "true" if was_cached else "false"

        # Counters
        REQUEST_COUNT.labels(endpoint=endpoint, status=status).inc()
        if was_cached:
            CACHE_HITS.inc()
        else:
            CACHE_MISSES.inc()

        # Histograms
        REQUEST_LATENCY.labels(
            endpoint=endpoint,
            cached=cached_label
        ).observe(latency)

        if prompt_length > 0:
            PROMPT_LENGTH.observe(prompt_length)
        if response_length > 0:
            RESPONSE_LENGTH.observe(response_length)

        # Rolling windows
        self._request_times.append(time.time())
        self._cache_results.append(1 if was_cached else 0)
        self._latencies.append(latency * 1000)
        if prompt_length > 0:
            self._prompt_lengths.append(prompt_length)
        if response_length > 0:
            self._response_lengths.append(response_length)

        # Update rolling metrics
        self._update_rolling_metrics()

        ACTIVE_REQUESTS.dec()

    def record_error(self, error_type: str) -> None:
        """Record an error event"""
        ERROR_COUNT.labels(error_type=error_type).inc()
        ACTIVE_REQUESTS.dec()

    def record_batch(self, batch_size: int) -> None:
        """Record batch processing event"""
        BATCH_COUNT.inc()
        BATCH_SIZE.observe(batch_size)

    def record_inference_time(self, duration_s: float) -> None:
        """Record raw model inference time"""
        INFERENCE_TIME.observe(duration_s)

    def update_cache_stats(self, cache_size: int) -> None:
        """Update cache size gauge"""
        CACHE_SIZE.set(cache_size)

    def update_queue_size(self, size: int) -> None:
        """Update batch queue size gauge"""
        QUEUE_SIZE.set(size)

    def update_system_metrics(self) -> None:
        """Update CPU and memory gauges"""
        import psutil
        process = psutil.Process()
        MEMORY_USAGE_MB.set(process.memory_info().rss / 1024 / 1024)
        CPU_USAGE_PCT.set(process.cpu_percent(interval=None))

    def set_reference_distribution(self, prompt_lengths: List[float]) -> None:
        """Set reference prompt length distribution for drift detection"""
        self._reference_prompt_lengths = prompt_lengths
        logger.info(
            f"Reference distribution set: "
            f"n={len(prompt_lengths)}, "
            f"mean={statistics.mean(prompt_lengths):.1f}"
        )

    def check_drift(self) -> Dict[str, float]:
        """
        Check for input distribution drift using PSI
        (Population Stability Index).
        PSI > 0.2 indicates significant drift.
        """
        if (len(self._prompt_lengths) < 10 or
                len(self._reference_prompt_lengths) < 10):
            return {}

        from scipy.stats import ks_2samp
        stat, pvalue = ks_2samp(
            self._reference_prompt_lengths,
            list(self._prompt_lengths)
        )

        drift_score = stat
        self._drift_scores["prompt_length"] = drift_score
        DRIFT_SCORE.labels(feature="prompt_length").set(drift_score)

        if drift_score > 0.3:
            DRIFT_ALERTS.labels(feature="prompt_length").inc()
            logger.warning(
                f"Drift alert: prompt_length drift={drift_score:.3f}"
            )

        return {"prompt_length": drift_score, "p_value": pvalue}

    def get_summary(self) -> dict:
        """Return current metrics summary"""
        latencies = list(self._latencies)
        sorted_l = sorted(latencies) if latencies else []

        return {
            "total_requests": sum(
                REQUEST_COUNT.labels(
                    endpoint=e, status=s
                )._value.get()
                for e in ["/infer", "/health"]
                for s in ["success", "error"]
            ),
            "cache_hit_rate_pct": round(
                sum(self._cache_results) /
                len(self._cache_results) * 100
                if self._cache_results else 0, 2
            ),
            "avg_latency_ms": round(
                statistics.mean(latencies) if latencies else 0, 2
            ),
            "p95_latency_ms": round(
                sorted_l[int(len(sorted_l) * 0.95)]
                if sorted_l else 0, 2
            ),
            "p99_latency_ms": round(
                sorted_l[int(len(sorted_l) * 0.99)]
                if sorted_l else 0, 2
            ),
            "drift_scores": self._drift_scores
        }

    def _update_rolling_metrics(self) -> None:
        """Update rolling gauges"""
        # Cache hit rate
        if self._cache_results:
            hit_rate = sum(self._cache_results) / len(self._cache_results)
            CACHE_HIT_RATE.set(hit_rate)

        # Throughput — requests in last 60 seconds
        now = time.time()
        recent = [t for t in self._request_times if now - t <= 60]
        THROUGHPUT_RPS.set(len(recent) / 60.0)

    def get_prometheus_metrics(self) -> bytes:
        """Return Prometheus-formatted metrics"""
        return generate_latest(registry)


# Global collector instance
collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return collector