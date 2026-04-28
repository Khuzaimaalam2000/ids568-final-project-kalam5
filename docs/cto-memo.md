# Memorandum: AI Risk Assessment Findings
**TO:** Chief Technology Officer  
**FROM:** Khuzaima Alam, MLOps Engineer (kalam5)  
**DATE:** April 2026  
**RE:** Production Readiness Assessment — LLM Inference Server  
**CLASSIFICATION:** Internal — Confidential

---

## Summary

This memo summarizes key findings from a comprehensive governance
and risk assessment of the DistilGPT-2 LLM inference server
developed across IDS568 Milestones 5 and Final Project. The
system demonstrates strong operational optimization (228x latency
improvement via caching, 367% throughput improvement via batching)
but has **five critical gaps** that must be addressed before any
external production deployment.

The central judgment is that the architecture is efficient enough
to be useful, but not yet controlled enough to be exposed safely to
untrusted external traffic. The model-serving design is working;
the remaining weaknesses are in safeguards, compliance readiness,
and robustness under drifted workloads.

---

## Key Findings

### Finding 1: System is Operationally Strong ✓
The inference server achieves production-grade performance metrics:
- 228x latency reduction via intelligent caching (454ms → 2ms)
- 734 req/s peak throughput under cached workload
- Stable P95 latency under 18ms for cached traffic
- Comprehensive monitoring with drift detection and alerting

These results, validated by A/B experiment EXP-001 (p<0.0001),
confirm the optimization architecture is sound and ready for
internal use.

### Finding 2: Input Drift is Occurring NOW ⚠
Drift analysis across 8 production windows reveals that prompt
length distribution has shifted 144% from the reference baseline.
PSI scores exceed the CRITICAL threshold (0.20) from Window 5
onward. The error rate has climbed from 2% to 14% and the SLA
P95 latency threshold (500ms) is being breached.

**Immediate action required:** Deploy prompt length guardrail
(reject prompts >50 tokens) and scale to 3 instances within
48 hours. Initiate retraining evaluation within 2 weeks.

This finding matters because it connects model risk to operational
risk. The drift is not only lowering likely output quality; it is
also weakening the cache-driven efficiency that made the current
deployment performant. Delaying action would therefore increase
both user-facing degradation and infrastructure stress.

That makes drift the most strategically important near-term issue
in the memo. Security gaps are serious, but they are latent until
external exposure. Drift is already harming the observed operating
state now. A CTO reading should therefore separate "must fix before
launch" from "must fix immediately because the system is already
degrading."

### Finding 3: Five Critical Security Gaps ✗
The following gaps must be resolved before external deployment:

| Gap | Risk | Fix |
|---|---|---|
| No authentication | Unauthorized access | API key auth |
| No rate limiting | DoS / abuse | 100 req/min limit |
| No output moderation | Harmful content | Content filter |
| No GDPR erasure support | Regulatory violation | Key registry |
| No hallucination detection | User harm | Confidence scoring |

### Finding 4: Governance Artifacts are Complete ✓
The system has comprehensive governance documentation:
- Model card with performance metrics, limitations, and ethical risks
- Risk register with 20 identified risks and mitigations
- Structured audit trail with 8 documented events
- Drift diagnostic report with intervention recommendations
- This governance memo

These artifacts do not by themselves make the system
production-ready, but they materially reduce decision risk. We know
what the system is, where it is weak, and which controls are still
missing. That makes the next launch decision auditable rather than
improvised.

This is an analytical advantage, not just a documentation virtue.
Good governance artifacts shorten incident diagnosis, clarify
ownership, and make mitigation decisions faster because the system
boundaries and risks are already named. That has real operational
value even before any regulator or auditor sees the project.

### Finding 5: Compliance Gaps for External Use ✗
The system is not currently compliant with GDPR, CCPA, or HIPAA
for external user deployments. EU AI Act requirements for limited-
risk GPAI systems are partially met (transparency disclosure and
audit trail are in place; consent mechanism is not).

From a leadership perspective, this means the blocker to launch is
not model capability. The blocker is that the organization has not
yet added the controls required to turn a capable prototype into an
accountable product. If shipped today, the most likely failure mode
would be compliance or abuse exposure, not raw performance.

This distinction matters because it changes investment priority.
Spending the next month on further latency tuning would likely have
lower business value than spending it on authentication, rate
limiting, moderation, and erasure support. The memo therefore
argues for control maturity over incremental speed gains.

---

## Recommended Actions

### Immediate (this week)
1. Deploy prompt length guardrail to stop SLA breach
2. Scale to 3 server instances behind load balancer
3. Implement API key authentication

### Short-term (30 days)
4. Add rate limiting (100 req/min per API key)
5. Implement output content moderation
6. Build GDPR user-to-key registry
7. Add knowledge cutoff disclaimer to all responses

### Long-term (90 days)
8. Integrate retrieval-augmented generation to reduce hallucination
9. Fine-tune model on drifted prompt distribution
10. Complete GDPR compliance review with legal counsel
11. Implement semantic caching for higher hit rates

---

## Risk Summary

| Category | Current Risk | After Mitigations |
|---|---|---|
| Security | HIGH | LOW |
| Privacy/Compliance | HIGH | MEDIUM |
| Reliability/Drift | HIGH | LOW |
| Hallucination | MEDIUM | LOW |
| Overall | HIGH | MEDIUM-LOW |

---

## Conclusion

The LLM inference server is ready for **internal research use**
with the current drift mitigation applied immediately. External
production deployment requires completion of the 30-day action
plan above. I recommend scheduling a follow-up review in 45 days
to assess mitigation progress before any public launch decision.

In short: approve internal use, do not approve public launch yet.
The evidence supports confidence in the optimization strategy, but
not confidence in the external governance posture. The follow-up
review should ask whether the five named control gaps are closed
and whether post-mitigation drift metrics return to an acceptable
range.

That recommendation is deliberately asymmetric. Internal use is
justified because it captures the learning value of the system
while keeping risk exposure bounded. Public launch is not justified
because the unresolved control gaps would transfer too much
avoidable risk to end users and the organization.

I am available to discuss these findings at your convenience.

**Khuzaima Alam**  
MLOps Engineer | NetID: kalam5  
IDS568 Final Project
