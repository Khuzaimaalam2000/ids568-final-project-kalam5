# Dashboard Interpretation: LLM Inference Server
**Author:** Khuzaima Alam | **NetID:** kalam5  
**System:** DistilGPT-2 Inference API with Dynamic Batching and Caching  
**Dashboard:** Prometheus metrics via /metrics endpoint  
**Real Traffic:** 45 requests | Captured: April 2026

---

## Real Metrics Summary

| Metric | Value | Source |
|---|---|---|
| Total Requests | 45 | llm_requests_total |
| Cold Requests (inference) | 13 | cached="false" counter |
| Warm Requests (cache hits) | 32 | cached="true" counter |
| Cold Avg Latency | 849.4ms | llm_request_latency_seconds_sum/count |
| Warm Avg Latency | 0.058ms | llm_request_latency_seconds_sum/count |
| Cache Speedup | 14,645x | cold/warm ratio |
| Cache Hit Rate | 71.1% | llm_cache_hit_rate gauge |
| Cache Entries | 13 | llm_cache_size gauge |
| Memory Usage | 482.9MB | llm_memory_mb gauge |
| CPU Usage | 55.8% | llm_cpu_pct gauge |
| Throughput | 0.75 rps | llm_throughput_rps gauge |
| Avg Prompt Length | 4.2 tokens | llm_prompt_length_tokens |

---

## 1. What the Dashboard Reveals About System Health

The production monitoring dashboard tracks six primary signal
categories across three real traffic phases: Cold Cache (requests
1-10), Warm Cache (requests 11-30), and Mixed Traffic
(requests 31-45). All metrics are sourced from the live
Prometheus /metrics endpoint — no simulated data.

The most important interpretation is that the service is healthy
for repeated short-prompt workloads, but not uniformly fast under
all traffic conditions. The dashboard shows a system whose user
experience depends heavily on cache reuse and warm process state.
That distinction matters because a blended average could make the
system look healthier than the uncached path really is.

### 1.1 Latency Panels

The latency comparison is the most critical health indicator.
Under cold cache conditions the average latency is 849.4ms —
this reflects the real cost of running DistilGPT-2 inference
on CPU without a cache hit. The first request took 4,293ms
due to model warm-up overhead (JIT compilation, memory
allocation), after which inference stabilized at 387-448ms
for subsequent cold requests.

During warm cache operation the average latency drops to
0.058ms — a 14,645x reduction. This confirms the LRU cache
is functioning correctly, serving repeated prompts from
in-process memory with sub-millisecond response times.

The real latency histogram from Prometheus shows:
- 9 of 13 cold requests completed under 500ms
- 2 completed between 500ms-1s
- 1 completed between 1s-2s
- 1 completed between 2s-5s (the initial warm-up request)

**Key reading:** When cold latency exceeds 1,000ms consistently,
model warm-up is incomplete or the system is under memory
pressure. The 849ms average is acceptable for CPU inference
but would require GPU acceleration for latency-sensitive SLAs.

That means the correct diagnosis is not simply "latency is under a
second." It is "the cold path is barely acceptable for internal or
offline use, but misses the margin needed for an interactive SLA."
If the cache hit rate falls or the service restarts, users quickly
move from sub-millisecond responses to near-second responses.

A useful counterfactual makes this clearer. If every request looked
like the 32 cache hits, the system would appear massively
overprovisioned. If every request looked like the 13 cache misses,
the same system would look borderline for user-facing traffic. The
dashboard therefore shows a bimodal service, not a consistently
fast one, and operational planning has to be based on the slower
mode because that is what users see whenever reuse disappears.

### 1.2 Throughput Panel

The throughput gauge shows 0.75 rps at time of measurement.
This reflects post-traffic measurement — during active traffic
generation the effective throughput was higher. The low RPS
is expected for CPU-bound LLM inference without caching.

During warm cache phases the effective throughput for cached
requests exceeded 100 rps (sub-millisecond responses). The
combined throughput is dominated by cold inference time when
cache miss rate is high.

Throughput therefore should be read as a workload-dependent metric,
not a fixed property of the architecture. If prompt diversity
increases, the effective throughput will collapse toward the
CPU-bound cold path. In production, a throughput drop would most
likely be explained by lower cache reuse or longer prompts, not by
an isolated serving bug.

This is why throughput by itself is a weak management metric here.
Throughput is the output of several upstream conditions: prompt
complexity, cache reuse, and cold-path latency. Treating a lower
throughput number as the problem would be analytically backward.
The real problem would be whichever upstream driver caused the
throughput number to fall.

### 1.3 Cache Hit Rate Panel

The cache hit rate reached 71.1% across all 45 requests.
Starting at 0% during the cold phase, it rose progressively
as repeated prompts accumulated in the cache, stabilizing
at 71.1% once the 13 unique prompts were cached.

The real traffic breakdown confirms:
- 13 unique prompts → 13 cold inferences (cache misses)
- 32 repeated prompts → 32 cache hits (0.058ms each)

A sustained hit rate above 60% indicates the workload has
sufficient prompt repetition for caching to provide
meaningful latency benefits. Our 71.1% rate exceeds this
threshold.

This is the strongest positive signal on the dashboard, but it is
also the most fragile one. A 71.1% hit rate says the current
traffic mix is favorable, not that the system is inherently cheap
or fast. If this metric drops below 40% for a sustained interval,
the expected consequence is not just a lower optimization score; it
is materially worse end-user latency and lower throughput.

More importantly, cache hit rate is a leverage metric. A 31-point
drop from 71% to 40% would likely matter more operationally than a
similar-sized change in memory usage because it changes how often
the service is forced onto the expensive cold path. That makes it a
better early-warning indicator than several traditional
infrastructure metrics.

### 1.4 Memory Panel

Process memory consumption is 482.9MB — significantly higher
than baseline because the DistilGPT-2 model weights (82M
parameters, ~330MB in float32) are loaded into RAM. This is
the dominant memory consumer. The cache itself contributes
negligibly (13 entries × average response size ≈ <1MB).

CPU usage at 55.8% reflects post-inference measurement. During
active cold inference CPU spikes to 90-100% as the model
performs autoregressive token generation.

The deeper reading is that memory is stable but CPU is the true
saturation point. The model comfortably fits in RAM for a single
instance, so the first production failure mode is CPU contention
during cache misses, which then appears downstream as latency
increase, timeouts, and lower request throughput.

### 1.5 Prompt Length Distribution

The real prompt length histogram shows 41 of 45 prompts
contain 5 or fewer tokens (short factual questions like
"What is machine learning"). This short-prompt workload
explains the relatively fast cold inference times of
387-448ms — longer prompts would take proportionally more
time to process.

This panel is diagnostically important because it explains why the
current results look good. The workload is dominated by short
questions. If prompt length shifts upward, the dashboard should be
expected to show worsening latency, lower cache effectiveness, and
more outlier requests. Prompt length is therefore a leading signal,
not just descriptive context.

In practice, this means the prompt-length panel should be treated as
an explanatory variable for the rest of the dashboard. If prompt
length stays flat while latency rises, the likely cause is
infrastructure saturation. If prompt length rises first and latency
follows, the likely cause is workload shift. That distinction helps
separate platform issues from product-usage change.

---

## 2. Identified Bottlenecks and Risks

### Bottleneck 1: CPU Cold Inference Latency (849ms avg)
The dominant bottleneck is cold-inference latency on CPU.
At 849ms average (with 4,293ms warm-up spike), the system
cannot serve latency-sensitive applications without caching.

**Real evidence:** 1 of 13 cold requests took 4,293ms
(initial JIT warm-up). Subsequent requests stabilized at
387-448ms. This warm-up overhead must be accounted for in
production deployment — the first request after server
restart will always be significantly slower.

**Mitigation:** Pre-warm the model on startup with a dummy
inference request. Deploy on GPU hardware for 10-50x
latency reduction. Use quantized model (INT8) for 3-5x
CPU improvement.

This bottleneck matters because it defines whether the system can
meet any interactive SLA once the cache fast path is unavailable.
If cold latency stays above 1,500ms for multiple intervals, the
correct response is architectural intervention or capacity change,
not simply acknowledging an alert.

The analytical point is that the cache does not eliminate the need
for a viable base serving path; it only masks that need when prompt
reuse is high. A mature production review would therefore grade the
system on the cold path first and treat cache wins as upside rather
than as the sole justification for readiness.

### Bottleneck 2: Memory Pressure at 482.9MB
At 482.9MB the process is consuming significant RAM for
a single-model deployment. Horizontal scaling to 4
instances would require ~2GB RAM minimum.

**Mitigation:** Use quantized model weights (INT8 reduces
to ~83MB). Implement model sharing across worker processes.

### Bottleneck 3: Single-Node Throughput Ceiling
Peak measured throughput of 0.75 rps (post-traffic) with
no horizontal scaling. Under sustained unique-prompt load
the system cannot exceed ~2 rps on CPU hardware.

**Mitigation:** Load balancer + multiple instances for
horizontal scaling. Shared Redis cache to preserve hit
rates across instances.

This is also a business risk. A single-node ceiling that looks
acceptable in a demo environment leaves very little headroom for
traffic growth, incident recovery, or a shift toward more diverse
prompts. The dashboard shows a system optimized for efficiency
under repetition, not yet resilience under expansion.

Said differently, the current architecture is elastic with respect
to repeated prompts but not elastic with respect to demand shape.
That is a subtler but more important limitation than simply saying
"throughput is low on one node."

### Risk 1: Warm-up Latency Spike on Restart
The first cold inference takes 4,293ms — 5x slower than
subsequent requests. This creates a visible latency spike
after any server restart or deployment.

**Mitigation:** Implement startup inference warm-up:
send 1-2 dummy requests during lifespan startup before
marking server as ready.

### Risk 2: Cache Effectiveness Degrades with Unique Prompts
With 13 unique prompts out of 45 total requests, the
hit rate stabilized at 71.1%. For workloads with higher
prompt diversity the hit rate will be lower and latency
will approach cold inference times.

**Mitigation:** Monitor cache hit rate in production.
If sustained below 30% consider semantic caching using
embedding similarity to match similar prompts.

### Risk 3: No Authentication on /metrics Endpoint
The Prometheus /metrics endpoint exposes system resource
usage (memory, CPU) without authentication. This could
leak operational intelligence to unauthorized parties.

**Mitigation:** Restrict /metrics to internal network
only via firewall rules or API gateway configuration.

---

## 3. Alert Trigger Conditions for Production

| Alert | Metric | Condition | Severity | Action |
|---|---|---|---|---|
| Warm-up Spike | Cold latency | > 3,000ms on first request | Warning | Expected — log only |
| High Cold Latency | Cold avg latency | > 1,500ms sustained | Warning | Check CPU/memory |
| Critical Latency | P99 latency | > 5,000ms | Critical | Page on-call |
| Low Cache Hit Rate | Hit rate | < 20% for 5min | Info | Review workload |
| Memory Pressure | Memory | > 1,500MB | Warning | Restart or scale |
| High CPU | CPU | > 90% for 2min | Warning | Scale out |
| Error Rate | Error rate | > 5% | Critical | Investigate logs |
| Throughput Drop | RPS | < 0.1 for 2min | Warning | Health check |

These alert thresholds are most useful when read together. For
example, low cache hit rate plus rising latency suggests workload
change, while high CPU plus rising error rate suggests active user
impact from saturation. The dashboard is strongest as a diagnostic
surface when it is used to connect signals rather than react to one
number at a time.

That multi-signal reading is the main analytical value of the
dashboard. A single metric can indicate that something changed; a
combination of metrics can indicate why it changed and whether the
right response is scaling, retraining, cache redesign, or simple
observation.

---

## 4. Dashboard Design Justification

### Why Prometheus + python prometheus_client
Prometheus was selected because it is the industry-standard
open-source metrics backend with native Python client support.
The prometheus_client library adds zero-overhead instrumentation
via Counter, Histogram, and Gauge primitives that integrate
directly into the FastAPI server without modifying inference
logic.

The /metrics endpoint follows the OpenMetrics standard,
making the instrumentation compatible with any Prometheus-
compatible visualization tool (Grafana, Datadog, New Relic)
without code changes.

### Why These Specific Metrics
The metrics were selected to cover the four Google SRE
golden signals: latency (REQUEST_LATENCY histogram),
traffic (REQUEST_COUNT, THROUGHPUT), errors (ERROR_COUNT),
and saturation (MEMORY_MB, CPU_PCT, ACTIVE_REQUESTS).

The cache-specific metrics (CACHE_HIT_RATE, CACHE_SIZE)
are LLM-specific additions that go beyond standard service
monitoring to address the caching optimization that is the
primary performance lever for this system.

### Real vs Simulated Data
All metrics in this dashboard are sourced from real inference
requests against the live DistilGPT-2 model. The raw
Prometheus output is saved in
`logs/real_prometheus_metrics.txt` for full reproducibility.
No simulated or estimated values are used in the metrics
panels.
