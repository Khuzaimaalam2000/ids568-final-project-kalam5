# Risk Matrix: LLM Inference System
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Date:** April 2026

---

## Risk Matrix (Likelihood × Severity)

| Risk ID | Risk Description | Likelihood | Severity | Score | Priority | Mitigation |
|---|---|---|---|---|---|---|
| RM-01 | Hallucination produces dangerous medical/legal advice | Medium | Critical | 8 | P1 | Disable for high-stakes domains; add disclaimers |
| RM-02 | Prompt injection bypasses safety measures | Medium | High | 6 | P1 | Input sanitization; output moderation |
| RM-03 | Temporal drift causes SLA breach (P95 > 500ms) | High | High | 9 | P1 | Automated drift alerts; horizontal scaling |
| RM-04 | GDPR erasure request cannot be fulfilled | Medium | High | 6 | P1 | User-to-key registry; cache invalidation API |
| RM-05 | Training data PII leakage via memorization | Low | High | 4 | P2 | PII detection filter on outputs |
| RM-06 | Cache poisoning serves harmful content to users | Low | High | 4 | P2 | Output validation before caching |
| RM-07 | API abuse for spam/phishing content generation | Medium | High | 6 | P1 | Rate limiting; API key auth |
| RM-08 | Model knowledge cutoff causes factual errors | High | Medium | 6 | P2 | Cutoff disclaimer; RAG integration |
| RM-09 | Cache staleness after model update | Medium | Medium | 4 | P3 | Model version in cache key |
| RM-10 | Gender/cultural bias in generated outputs | High | Medium | 6 | P2 | Bias detection; output filtering |
| RM-11 | No authentication allows unauthorized access | High | High | 9 | P1 | API key auth before production |
| RM-12 | Single point of failure — no redundancy | Medium | High | 6 | P2 | Load balancer; multiple instances |
| RM-13 | Memory exhaustion from cache growth | Low | Medium | 2 | P4 | max_entries cap; TTL enforcement |
| RM-14 | EU AI Act compliance gap | Low | Medium | 2 | P4 | Transparency disclosure; audit trail |
| RM-15 | Cold start latency spikes on server restart | Medium | Low | 2 | P4 | Cache warming on startup |

---

## Risk Heatmap

Severity →    Low      Medium    High     Critical
Likelihood ↓
High          RM-15    RM-08     RM-03    —
RM-10         RM-11
Low           RM-13    RM-05     RM-06    —
RM-14
Medium        —        RM-09     RM-01    RM-01
RM-02
RM-04
RM-07
RM-12

---

## Priority 1 Risks — Immediate Action Required

### RM-01: Hallucination Risk
**Current state:** No hallucination detection implemented  
**Target state:** Output confidence scoring + domain restriction  
**Timeline:** Before any production deployment  
**Owner:** kalam5  

### RM-03: Input Drift → SLA Breach
**Current state:** Drift monitoring implemented; alert at KS > 0.10  
**Target state:** Automated retraining trigger at KS > 0.20  
**Timeline:** 2 weeks  
**Owner:** kalam5  

### RM-04: GDPR Erasure Gap
**Current state:** No user-to-key registry  
**Target state:** Registry implemented with /cache/invalidate endpoint  
**Timeline:** 4 weeks  
**Owner:** kalam5  

### RM-07: API Abuse
**Current state:** No rate limiting or authentication  
**Target state:** 100 req/min rate limit; API key required  
**Timeline:** Before any public exposure  
**Owner:** kalam5  

### RM-11: No Authentication
**Current state:** All endpoints publicly accessible  
**Target state:** OAuth 2.0 or API key authentication  
**Timeline:** Before production deployment  
**Owner:** kalam5  

---

## Residual Risk Assessment

After implementing all Priority 1 mitigations the overall
system risk profile reduces from **HIGH** to **MEDIUM-LOW**,
acceptable for internal research and development use.
Production deployment with external users requires additional
Priority 2 mitigations to achieve **LOW** residual risk.