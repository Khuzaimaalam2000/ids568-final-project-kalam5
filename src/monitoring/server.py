"""
Production LLM Inference Server with Real Prometheus Metrics
Component 1: Production Monitoring Dashboard
All metrics are real — generated from actual inference requests
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from collections import OrderedDict
import hashlib
import json

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest,
    CollectorRegistry, CONTENT_TYPE_LATEST
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Prometheus Registry ───────────────────────────────────────────────────────
registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    "llm_requests_total",
    "Total inference requests",
    ["endpoint", "status", "cached"],
    registry=registry
)
REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Request latency",
    ["cached"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)
CACHE_HIT_RATE = Gauge(
    "llm_cache_hit_rate", "Rolling cache hit rate",
    registry=registry
)
CACHE_SIZE = Gauge(
    "llm_cache_size", "Current cache entries",
    registry=registry
)
THROUGHPUT = Gauge(
    "llm_throughput_rps", "Requests per second",
    registry=registry
)
ACTIVE_REQUESTS = Gauge(
    "llm_active_requests", "Active requests",
    registry=registry
)
MEMORY_MB = Gauge(
    "llm_memory_mb", "Memory usage MB",
    registry=registry
)
CPU_PCT = Gauge(
    "llm_cpu_pct", "CPU usage percent",
    registry=registry
)
ERROR_COUNT = Counter(
    "llm_errors_total", "Total errors",
    ["type"],
    registry=registry
)
BATCH_SIZE_HIST = Histogram(
    "llm_batch_size", "Batch sizes",
    buckets=[1, 2, 4, 8, 16],
    registry=registry
)
PROMPT_LENGTH = Histogram(
    "llm_prompt_length_tokens", "Prompt lengths",
    buckets=[5, 10, 20, 50, 100, 200],
    registry=registry
)

# ── In-process Cache ──────────────────────────────────────────────────────────
class SimpleCache:
    def __init__(self, max_entries=1000, ttl_seconds=300):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _key(self, prompt, model, tokens):
        data = json.dumps(
            {"prompt": prompt, "model": model, "tokens": tokens},
            sort_keys=True
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def get(self, prompt, model, tokens):
        key = self._key(prompt, model, tokens)
        if key not in self._cache:
            self._misses += 1
            return None
        entry, created_at = self._cache[key]
        if time.time() - created_at > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None
        self._cache.move_to_end(key)
        self._hits += 1
        return entry

    def set(self, prompt, model, tokens, value):
        key = self._key(prompt, model, tokens)
        if len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)
        self._cache[key] = (value, time.time())

    @property
    def hit_rate(self):
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self):
        return len(self._cache)


# ── Global State ──────────────────────────────────────────────────────────────
_model = None
_tokenizer = None
_cache = SimpleCache(max_entries=1000, ttl_seconds=300)
_request_times = []


# ── Model Loading ─────────────────────────────────────────────────────────────
def load_model(model_name="distilgpt2"):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    logger.info(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float32
    )
    model.eval()
    logger.info("Model loaded")
    return tokenizer, model


def run_inference(prompts, max_new_tokens=30):
    import torch
    global _model, _tokenizer
    inputs = _tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=256
    )
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    results = []
    for i, output in enumerate(outputs):
        input_len = inputs["input_ids"].shape[1]
        generated = output[input_len:]
        text = _tokenizer.decode(generated, skip_special_tokens=True)
        results.append(text)
    return results


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _tokenizer
    _tokenizer, _model = load_model()
    logger.info("Server ready")
    yield
    logger.info("Shutting down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LLM Inference Server with Monitoring",
    version="1.0.0",
    lifespan=lifespan
)


# ── Request Models ────────────────────────────────────────────────────────────
class InferRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 30
    use_cache: bool = True


class InferResponse(BaseModel):
    request_id: str
    prompt: str
    generated_text: str
    latency_ms: float
    was_cached: bool


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "model": "distilgpt2"}


@app.post("/infer", response_model=InferResponse)
async def infer(body: InferRequest):
    global _request_times
    request_id = str(uuid.uuid4())
    start = time.time()
    ACTIVE_REQUESTS.inc()
    prompt_tokens = len(body.prompt.split())
    PROMPT_LENGTH.observe(prompt_tokens)

    try:
        # Cache lookup
        cached = None
        if body.use_cache:
            cached = _cache.get(
                body.prompt, "distilgpt2", body.max_new_tokens
            )

        if cached is not None:
            generated_text = cached
            was_cached = True
        else:
            # Real inference
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, run_inference,
                [body.prompt], body.max_new_tokens
            )
            generated_text = results[0]
            was_cached = False
            if body.use_cache:
                _cache.set(
                    body.prompt, "distilgpt2",
                    body.max_new_tokens, generated_text
                )

        latency = time.time() - start
        latency_ms = latency * 1000

        # Record real metrics
        cached_label = "true" if was_cached else "false"
        REQUEST_COUNT.labels(
            endpoint="/infer",
            status="success",
            cached=cached_label
        ).inc()
        REQUEST_LATENCY.labels(cached=cached_label).observe(latency)
        CACHE_HIT_RATE.set(_cache.hit_rate)
        CACHE_SIZE.set(_cache.size)

        # Rolling throughput
        now = time.time()
        _request_times.append(now)
        _request_times = [t for t in _request_times if now - t <= 60]
        THROUGHPUT.set(len(_request_times) / 60.0)

        # System metrics
        import psutil
        proc = psutil.Process()
        MEMORY_MB.set(proc.memory_info().rss / 1024 / 1024)
        CPU_PCT.set(psutil.cpu_percent(interval=None))

        ACTIVE_REQUESTS.dec()

        logger.info(
            f"[{request_id[:8]}] "
            f"latency={latency_ms:.1f}ms "
            f"cached={was_cached}"
        )

        return InferResponse(
            request_id=request_id,
            prompt=body.prompt,
            generated_text=generated_text,
            latency_ms=round(latency_ms, 2),
            was_cached=was_cached
        )

    except Exception as e:
        ACTIVE_REQUESTS.dec()
        ERROR_COUNT.labels(type="inference_error").inc()
        REQUEST_COUNT.labels(
            endpoint="/infer",
            status="error",
            cached="false"
        ).inc()
        logger.error(f"Inference failed: {e}")
        raise


@app.get("/metrics")
async def metrics():
    """Real Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/stats")
async def stats():
    return {
        "cache_hit_rate": round(_cache.hit_rate * 100, 2),
        "cache_size": _cache.size,
        "throughput_rps": round(len(_request_times) / 60.0, 3)
    }


@app.post("/cache/clear")
async def clear_cache():
    _cache._cache.clear()
    return {"status": "cleared"}