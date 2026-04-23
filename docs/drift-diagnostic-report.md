# Drift Diagnostic Report
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Date:** April 2026  
**Reference Period:** March 2026 (1,000 samples)  
**Production Period:** April–May 2026 (8 windows × 200 samples)

---

## 1. Executive Summary

Drift analysis across 8 production windows reveals **progressive and
statistically significant drift** in all four monitored features:
prompt_length, latency_ms, transaction_amount, and response_length.
The drift begins as a WARNING at Window 2 and escalates to CRITICAL
at Window 5 for all features. Immediate retraining and workload
investigation are recommended.

---

## 2. Features Analyzed

| Feature | Reference Mean | Production Mean (W7) | PSI (W7) | Severity |
|---|---|---|---|---|
| prompt_length | 12.5 tokens | 30.5 tokens | >0.20 | CRITICAL |
| latency_ms | 420ms | 700ms | >0.20 | CRITICAL |
| transaction_amount | $250 | $400 | >0.20 | CRITICAL |
| response_length | 28.4 tokens | 48.4 tokens | >0.20 | CRITICAL |

---

## 3. Which Features Drifted Most

### 3.1 prompt_length — Most Drifted Feature

Prompt length shows the earliest and most severe drift of all
monitored features. The reference distribution is centered at
12.5 tokens (std=3.2). By Window 7 the production distribution
has shifted to approximately 30.5 tokens (std=8.2) — a 144%
increase in mean prompt length.

**PSI progression:**
- Windows 0-1: PSI < 0.1 (STABLE)
- Windows 2-3: PSI 0.1-0.2 (WARNING)
- Windows 4-7: PSI > 0.2 (CRITICAL)

**KS test results:** KS statistic exceeds 0.20 from Window 4
onward with p-values < 0.001, confirming the drift is highly
statistically significant and not attributable to random sampling
variation.

**Root cause hypothesis:** Users are submitting increasingly
complex and detailed queries over time, shifting from short
factual questions to longer multi-part prompts. This may reflect
growing user sophistication or a change in the user population
accessing the API.

### 3.2 latency_ms — Second Most Drifted

Inference latency drifts from a reference mean of 420ms to
approximately 700ms by Window 7 — a 67% increase. This drift
is directly caused by the prompt_length drift: longer prompts
require more tokens to process, increasing both tokenization
time and autoregressive generation steps.

**Impact:** P95 latency crosses the 500ms SLA threshold at
Window 5, representing a production SLA breach if not addressed.

### 3.3 transaction_amount — Third Most Drifted

Transaction amount distribution shifts from mean $250 to $400,
indicating a change in the underlying business data distribution.
This could reflect seasonal effects, a change in customer segment,
or upstream data pipeline changes.

### 3.4 response_length — Correlated with prompt_length

Response length increases proportionally with prompt length,
as expected — longer prompts generate longer responses. This
is a derived drift rather than an independent signal.

---

## 4. Impact on Model Performance

### 4.1 Direct Performance Impact

| Impact Area | Window 0 | Window 7 | Change |
|---|---|---|---|
| Avg Latency | 420ms | 700ms | +67% |
| Error Rate | 2% | 14% | +600% |
| Cache Hit Rate | 65% | 20% | -69% |
| SLA Compliance (P95<500ms) | ✓ | ✗ | Breached |

### 4.2 Cache Effectiveness Degradation

The cache hit rate drops from 65% to 20% as prompt diversity
increases with longer, more unique prompts. This compounds the
latency impact: not only are prompts slower to process, but
fewer responses are served from cache, eliminating the primary
latency optimization.

### 4.3 Error Rate Escalation

The error rate climbs from 2% (reference) to 14% by Window 7.
This is attributable to:
1. Longer prompts exceeding context window limits (1,024 tokens)
2. Increased inference time causing timeout events
3. Memory pressure from larger batch tensors

### 4.4 Model Output Quality Degradation (Projected)

While direct output quality metrics are not captured in this
simulation, the literature indicates that distribution shift
of this magnitude (PSI > 0.2, KS > 0.3) typically correlates
with 5-15% degradation in task-specific accuracy metrics for
generative models. A human evaluation study is recommended to
quantify actual output quality change.

---

## 5. Anomaly Detection Results

Z-score based anomaly detection (threshold: 3σ) identified
anomalous requests across all features:

| Feature | Anomaly Rate (W0) | Anomaly Rate (W7) | Change |
|---|---|---|---|
| prompt_length | 0.3% | 4.2% | +1300% |
| latency_ms | 0.5% | 6.8% | +1260% |
| transaction_amount | 0.4% | 5.1% | +1175% |
| response_length | 0.3% | 3.9% | +1200% |

The increasing anomaly rate indicates that the production
distribution is developing a heavy right tail — a small but
growing proportion of requests are extreme outliers that
disproportionately impact system performance.

---

## 6. Retraining and Intervention Recommendations

### Immediate Actions (Window 5-6, now)

1. **Alert engineering team** — drift score has crossed CRITICAL
   threshold for all features. SLA breach is occurring.

2. **Implement prompt length guardrail** — reject or truncate
   prompts exceeding 50 tokens at the API gateway level until
   retraining is complete. This immediately reduces latency
   and error rate.

3. **Increase cache TTL** — extend from 300s to 900s to improve
   hit rate for the new longer prompt distribution.

4. **Scale horizontally** — add 2 additional server instances
   to absorb increased per-request compute load.

### Short-term Actions (1-2 weeks)

5. **Collect labeled evaluation data** — sample 200 requests
   from the drifted distribution and evaluate model output
   quality manually to quantify accuracy degradation.

6. **Fine-tune on drifted distribution** — if quality degradation
   is confirmed, fine-tune DistilGPT-2 on a curated sample of
   the new longer-prompt distribution.

7. **Update reference distribution** — after retraining, reset
   the drift monitoring reference to the new baseline.

### Long-term Actions (1 month)

8. **Implement continuous drift monitoring** — automate weekly
   drift reports with threshold-triggered alerts connected to
   the CI/CD pipeline.

9. **Add semantic caching** — use embedding similarity matching
   to improve cache hit rates for semantically similar but
   lexically different prompts.

10. **Establish retraining cadence** — schedule quarterly
    retraining evaluations regardless of drift alert status.

---

## 7. Connection to Monitoring Dashboard

The drift scores reported here correspond directly to the
**Drift Score Panel** in the Grafana monitoring dashboard
(Component 1). The dashboard's KS statistic threshold of 0.10
(WARNING) and 0.20 (CRITICAL) align with the PSI thresholds
used in this report. When the dashboard drift alert fires,
this diagnostic report provides the detailed feature-level
analysis needed to identify root cause and select appropriate
intervention.

See `visualizations/drift_analysis.png` and
`visualizations/anomaly_detection.png` for full visualizations.