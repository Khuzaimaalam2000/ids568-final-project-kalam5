# Dashboard Interpretation: LLM Inference Server
**Author:** Khuzaima Alam | **NetID:** kalam5  
**System:** DistilGPT-2 Inference API with Dynamic Batching and Caching  
**Dashboard:** Prometheus/Grafana — LLM Inference Server Production Dashboard

---

## 1. What the Dashboard Reveals About System Health

The production monitoring dashboard tracks six primary signal categories
across five simulated traffic phases: Normal Traffic, Cache Warming, Load
Spike, Error Injection, and Drift Simulation. Together these panels provide
a complete picture of system health at any point in time.

### 1.1 Latency Panels (P50 / P95 / P99)

The latency time series is the most critical health indicator. Under normal
traffic the P50 latency sits at approximately 380ms — this reflects the
cold-inference cost of running DistilGPT-2 on CPU without a cache hit.
During cache warming the P50 drops sharply to under 8ms, confirming that
the LRU cache is functioning correctly and serving repeated prompts from
memory rather than re-invoking the model.

During the load spike phase P95 latency rises to approximately 560ms. This
is still within the 500ms SLA threshold marked on the dashboard but leaves
minimal headroom. The P99 line crossing 700ms during this phase is the
clearest signal that the system is approaching saturation and would require
horizontal scaling or batch timeout tuning to maintain SLA compliance under
sustained high load.

**Key reading:** When P95 > 500ms for more than 2 consecutive minutes,
the system is approaching its single-node capacity limit.

### 1.2 Throughput Panel

The throughput gauge peaks at approximately 18.5 req/s during the cache
warming phase when virtually all requests are cache hits. Under normal
cold-inference traffic the throughput drops to 2-3 req/s, reflecting the
CPU-bound nature of on-device LLM inference.

This 9x throughput differential between cached and uncached operation is
the most actionable finding from the dashboard: cache hit rate is the
single biggest lever for throughput improvement, far more impactful than
tuning batch size or timeout parameters on CPU hardware.

### 1.3 Cache Hit Rate Panel

The cache hit rate starts at 0% during initial cold traffic, rises to 35%
as repeated prompts accumulate, and reaches 95% during the cache warming
phase. It stabilizes at 72-88% during subsequent phases as the workload
mix shifts.

A sustained hit rate below 30% indicates a workload dominated by unique
prompts where caching provides limited benefit. In this scenario the
recommended action is to increase batch size and batch timeout to maximize
GPU/CPU utilization per batch rather than relying on cache savings.

### 1.4 Error Rate Panel

The error rate remains below 2% during normal and cache-warmed operation.
A sharp spike to 28% is visible during the error injection phase at
approximately the 80-minute mark. This spike is clearly visible against
the 5% alert threshold line marked on the panel.

The spike is short-lived (approximately 15 minutes) and self-resolving in
the simulation, representing a transient model inference failure. In
production a spike of this magnitude would trigger an immediate PagerDuty
alert and warrant investigation of the model serving process, GPU memory
state, and upstream request queue depth.

### 1.5 Drift Score Panel (KS Statistic)

The drift score panel tracks the Kolmogorov-Smirnov statistic comparing
the current prompt length distribution against the reference distribution
established during the first 50 requests of normal traffic.

The score remains below 0.05 during normal and cache phases, rises
gradually during the load spike as shorter prompts dominate, and crosses
the 0.10 warning threshold at approximately the 100-minute mark during the
drift simulation phase when the workload shifts toward progressively longer
prompts.

A KS statistic above 0.20 (the red alert line) indicates that the input
distribution has shifted significantly enough to warrant investigation of
whether model performance has degraded. At this level a retraining
evaluation should be triggered.

### 1.6 Memory Panel

Memory usage remains stable at 30-32MB throughout the simulation. The
gradual upward drift of approximately 0.01MB per minute is attributable to
cache entry accumulation. At this rate the cache would consume an
additional ~14MB over 24 hours of operation — well within acceptable
limits for the 1,000-entry max_entries configuration.

---

## 2. Identified Bottlenecks and Risks

### Bottleneck 1: CPU-Bound Inference Latency
The most significant bottleneck is cold-inference latency on CPU hardware.
At 380-480ms per request for a 82M-parameter model (DistilGPT-2), the
system would require GPU acceleration to serve latency-sensitive
applications. On GPU hardware the same model would achieve 10-50ms
inference latency, enabling throughput of 50-200 req/s without caching.

**Mitigation:** Deploy on GPU instance (e.g., AWS g4dn.xlarge) or use
a quantized model variant (INT8/INT4) to reduce CPU inference time by
3-5x.

### Bottleneck 2: Single-Node Throughput Ceiling
The peak observed throughput of 18.5 req/s (cached) represents the
practical ceiling for a single-process Python server. Under uncached
load the ceiling drops to 2-3 req/s. There is no horizontal scaling
in the current deployment.

**Mitigation:** Add a load balancer (nginx or AWS ALB) in front of
multiple server instances. Each instance maintains its own in-process
cache; a shared Redis cache would be required to preserve hit rates
across instances.

### Bottleneck 3: In-Process Cache Not Shared Across Instances
The current LRU cache lives in process memory. Any horizontal scaling
would start each new instance with a cold cache, temporarily
eliminating the caching benefit.

**Mitigation:** Migrate to Redis with a consistent hashing strategy
so all instances share a single cache namespace.

### Risk 1: P99 Latency SLA Breach Under Sustained Load
P99 latency crosses 700ms during the load spike phase. If sustained
for more than 5 minutes this would breach most enterprise SLA
commitments of 500ms at P95.

### Risk 2: Error Rate Spike During Inference Failure
The 28% error rate during error injection, while simulated, represents
a realistic risk during GPU out-of-memory events or model serving
crashes. Without circuit-breaker logic the server will continue
accepting requests it cannot serve, increasing queue depth and
worsening latency for all users.

**Mitigation:** Implement circuit-breaker pattern: if error rate
exceeds 10% for 60 seconds, return 503 responses immediately rather
than queuing requests.

### Risk 3: Input Drift Leading to Silent Performance Degradation
The drift score crossing 0.10 at the 100-minute mark is a leading
indicator of potential model performance degradation. Unlike latency
or error rate spikes which are immediately visible, drift-induced
accuracy degradation is silent and may not be detected until user
complaints surface.

**Mitigation:** Automated drift monitoring with threshold-triggered
retraining pipeline. Connect drift alerts (C1) to the retraining
audit trail (C3) and the drift diagnostic report (C4).

---

## 3. Alert Trigger Conditions for Production

| Alert | Metric | Condition | Severity | Action |
|---|---|---|---|---|
| High Latency | P95 latency | > 500ms for 2min | Warning | Scale out |
| Critical Latency | P99 latency | > 1000ms for 1min | Critical | Page on-call |
| High Error Rate | Error rate | > 5% for 1min | Warning | Investigate logs |
| Critical Error Rate | Error rate | > 15% for 30s | Critical | Circuit breaker |
| Low Cache Hit Rate | Hit rate | < 20% for 5min | Info | Review workload |
| Memory Pressure | Memory | > 4GB | Warning | Restart server |
| Input Drift Warning | KS statistic | > 0.10 | Warning | Review inputs |
| Input Drift Alert | KS statistic | > 0.20 | Critical | Trigger retraining |
| Queue Saturation | Queue depth | > 80 requests | Warning | Scale out |
| Throughput Drop | RPS | < 0.5 for 2min | Warning | Health check |

---

## 4. Dashboard Design Justification

### Why Prometheus + Grafana
Prometheus was selected as the metrics backend because it is the
industry-standard open-source time-series database for service
monitoring, with native support for the pull-based scrape model
that works well with Python FastAPI services. The prometheus_client
Python library provides zero-overhead histogram and counter
instrumentation with minimal code changes to the existing server.

Grafana provides the visualization layer with support for threshold
coloring, time range selection, and alert rule configuration — all
critical for production monitoring workflows.

### Why These Specific Metrics
The six primary metrics (latency percentiles, throughput, cache hit
rate, error rate, drift score, memory) were selected to cover all
four dimensions of the Google SRE golden signals framework:
latency, traffic, errors, and saturation. The drift score is an
LLM-specific addition that goes beyond traditional service monitoring
to address model-specific reliability concerns.

### Panel Layout Rationale
The top row of stat panels provides an at-a-glance health summary
for on-call engineers. The middle row of time series panels enables
trend analysis and correlation between metrics. The bottom row of
detailed panels (phase breakdown, cumulative cache performance,
summary stats) supports post-incident analysis and capacity planning.