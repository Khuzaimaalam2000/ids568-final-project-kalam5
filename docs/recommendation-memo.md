# A/B Test Recommendation Memo
**TO:** Engineering Lead, MLOps Team  
**FROM:** Khuzaima Alam (kalam5)  
**DATE:** April 2026  
**RE:** EXP-001 — Ship Decision: Baseline (A) vs Optimized Server (B)

---

## Recommendation: SHIP VARIANT B

Based on the results of EXP-001, I recommend **shipping Variant B**
(optimized LLM inference server with dynamic batching and caching)
to 100% of production traffic.

---

## Key Results

| Metric | Variant A | Variant B | Change | Significant |
|---|---|---|---|---|
| Avg Latency | 420ms | 148ms | -65% | ✓ (p<0.0001) |
| P95 Latency | 560ms | 480ms | -14% | — |
| Throughput | 2.1 rps | 9.8 rps | +367% | ✓ (p<0.0001) |
| Error Rate | 2.0% | 1.2% | -40% | ✓ (p=0.021) |
| Cache Hit Rate | 0% | 65% | +65pp | — |

All three primary metrics achieved statistical significance well
below the Bonferroni-adjusted threshold of α=0.017. The 95%
bootstrap confidence interval for latency reduction is
[250ms, 290ms], confirming the improvement is both statistically
significant and practically meaningful.

---

## Why Ship B

**1. Latency improvement is large and robust.**
The 65% average latency reduction (420ms → 148ms) is driven
primarily by cache hits (65% of requests served in <8ms) combined
with batching efficiency for cache misses. The bootstrap CI confirms
this improvement is not a statistical artifact.

**2. Throughput increase enables cost reduction.**
The 367% throughput improvement means the same workload can be
served with approximately one-quarter the number of server instances,
directly reducing infrastructure cost.

**3. No guardrail metrics were breached.**
Error rate decreased rather than increased. P99 latency improved.
Server availability remained at 100% throughout the simulation.

**4. Effect size is practically significant.**
Cohen's d = 6.2 for latency, indicating an extremely large practical
effect — not just a statistically detectable noise difference.

---

## Risks and Mitigations

**Risk:** Cache introduces stale responses after model updates.  
**Mitigation:** Flush cache on every model version deployment.
Cache keys include model name, making stale entries unreachable
after version change.

**Risk:** Cache hit rate may degrade for highly diverse workloads.  
**Mitigation:** Monitor cache hit rate in production. If sustained
below 30%, consider increasing TTL or implementing semantic caching.

**Risk:** Batching adds latency for low-traffic periods.  
**Mitigation:** 50ms batch timeout ensures maximum 50ms added
latency even at zero load — acceptable for all current use cases.

---

## Recommended Rollout Plan

1. Deploy Variant B to 10% of traffic for 24 hours (canary)
2. Verify production metrics match simulation results
3. Ramp to 50% for 48 hours, monitor error rate and P99
4. Full 100% rollout if no regressions observed
5. Decommission Variant A infrastructure after 7-day soak period

---

## Next Steps

- Update model card (C3) to reflect new serving configuration
- Add cache hit rate to production monitoring dashboard (C1)
- Schedule drift detection review (C4) for 30 days post-launch
- Document configuration change in audit trail (C3)