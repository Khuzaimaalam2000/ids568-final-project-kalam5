# A/B Experiment Specification
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Experiment ID:** EXP-001  
**Date:** April 2026  
**System:** LLM Inference Server (DistilGPT-2)

---

## 1. Hypothesis

**Null Hypothesis (H₀):** Enabling dynamic request batching and
intelligent caching in the LLM inference server produces no statistically
significant difference in request latency, throughput, or error rate
compared to the baseline server configuration.

**Alternative Hypothesis (H₁):** The optimized server (Variant B) with
dynamic batching (batch_size=8, timeout=50ms) and LRU caching
(TTL=300s, max_entries=1000) produces a statistically significant
reduction in median request latency and increase in throughput compared
to the baseline server (Variant A) with no batching or caching.

**Expected Direction:** Variant B will reduce average latency by at least
30ms (7% relative improvement) and increase throughput by at least
2 req/s (95% relative improvement) compared to Variant A.

---

## 2. Success Metrics

### Primary Metrics (must achieve statistical significance)

| Metric | Baseline (A) | Target (B) | MDE | Test |
|---|---|---|---|---|
| Avg Request Latency | ~420ms | ≤390ms | -30ms | Welch t-test |
| Throughput (rps) | ~2.1 rps | ≥4.0 rps | +2.0 rps | Welch t-test |

### Secondary Metrics (directional, no significance required)

| Metric | Baseline (A) | Target (B) | Direction |
|---|---|---|---|
| P95 Latency | ~560ms | ≤520ms | Decrease |
| P99 Latency | ~720ms | ≤650ms | Decrease |
| Error Rate | ~2.0% | ≤1.5% | Decrease |
| Cache Hit Rate | 0% | ≥60% | Increase |

### Guardrail Metrics (must not degrade)

| Metric | Threshold | Action if breached |
|---|---|---|
| Error Rate | Must not exceed 5% | Stop experiment |
| P99 Latency | Must not exceed 2000ms | Stop experiment |
| Server Availability | Must remain ≥99% | Stop experiment |

---

## 3. Randomization Method

Requests are assigned to variants using **hash-based deterministic
routing** on a per-request basis:

```python
import hashlib

def assign_variant(request_id: str) -> str:
    hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
    return "A" if hash_val % 2 == 0 else "B"
```

This approach ensures:
- **Determinism:** The same request_id always maps to the same variant
- **Independence:** Assignment is independent of request content or timing
- **Even split:** Approximately 50/50 traffic split across variants
- **No leakage:** Users in variant A cannot receive variant B responses

**Traffic Split:** 50% Variant A / 50% Variant B

---

## 4. Required Sample Size and Duration

### Power Analysis

Using a two-sample Welch t-test with the following parameters:

| Parameter | Value | Justification |
|---|---|---|
| Significance level (α) | 0.05 | Industry standard for A/B tests |
| Statistical power (1-β) | 0.80 | 80% chance of detecting true effect |
| Baseline mean latency | 420ms | Measured from Milestone 5 benchmarks |
| Baseline std deviation | 45ms | Measured from Milestone 5 benchmarks |
| Minimum Detectable Effect | 30ms | 7% relative improvement threshold |

**Computed required sample size: 36 requests per variant**

The power analysis confirms that 36 samples per group are sufficient
to detect a 30ms latency reduction with 80% power at α=0.05. We use
500 samples per variant in the simulation to achieve higher precision
and more reliable confidence intervals.

### Experiment Duration

At a baseline traffic rate of 2.1 req/s with 50% allocation to each
variant:
Requests per variant per hour = 2.1 × 0.5 × 3600 = 3,780
Required duration = 36 / 3,780 = 0.01 hours ≈ 1 minute minimum
Recommended duration = 7 days (for day-of-week effects)

**Recommended experiment duration: 7 days**

A 7-day window captures weekly traffic patterns (weekday vs weekend
usage differences) and provides >260,000 samples per variant — far
exceeding the minimum required — for highly precise estimates.

---

## 5. Experiment Design Details

### Variant Configurations

**Variant A — Baseline:**
- Batching: disabled (batch_size=1)
- Caching: disabled
- Model: DistilGPT-2
- max_new_tokens: 50

**Variant B — Optimized:**
- Batching: enabled (max_batch_size=8, timeout_ms=50)
- Caching: enabled (TTL=300s, max_entries=1000)
- Model: DistilGPT-2 (same model)
- max_new_tokens: 50

### What is Held Constant
- Model architecture and weights
- Hardware configuration
- Request prompts and workload distribution
- max_new_tokens setting
- Server host and infrastructure

### Potential Confounders
- **Time of day:** Controlled by running both variants simultaneously
- **Prompt complexity:** Controlled by identical workload distributions
- **Cache cold start:** Handled by warm-up period before measurement
- **Network latency:** Controlled by same-host deployment

---

## 6. Statistical Analysis Plan

1. Collect latency, throughput, and error samples for both variants
2. Test normality using Shapiro-Wilk test
3. Apply Welch t-test (unequal variance) for latency and throughput
4. Apply chi-square test for error rate proportions
5. Compute 95% bootstrap confidence intervals for all primary metrics
6. Compute Cohen's d effect size for practical significance assessment
7. Apply Bonferroni correction for multiple comparisons (3 primary metrics):
   adjusted α = 0.05 / 3 = 0.017

### Decision Rules
- **Ship B:** All primary metrics show p < 0.017 with improvement in
  expected direction AND no guardrail metrics breached
- **Ship A (keep baseline):** Any primary metric shows regression
  (B worse than A) with p < 0.05
- **Collect more data:** Primary metrics show improvement but
  p > 0.017, OR guardrail metrics approach thresholds