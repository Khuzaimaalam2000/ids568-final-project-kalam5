# Risk Register: LLM Inference Server
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Version:** 1.0.0 | **Date:** April 2026  
**Framework:** NIST AI Risk Management Framework (AI RMF)

---

## Risk Categories

### Category 1: Bias Risks

| ID | Risk | Likelihood | Severity | Risk Score | Mitigation |
|---|---|---|---|---|---|
| B-01 | Gender bias in generated text associates professions with specific genders | High | Medium | 6 | Add output filtering layer; include bias disclaimers in API responses |
| B-02 | Cultural bias produces Western-centric responses to global questions | High | Medium | 6 | Document limitation in model card; restrict use for culturally sensitive applications |
| B-03 | Underrepresentation of minority languages produces poor quality outputs | High | Low | 3 | Reject non-English inputs with clear error message |
| B-04 | Socioeconomic bias reflects Reddit demographics not general population | Medium | Medium | 4 | User education; avoid using for population-representative surveys |
| B-05 | Temporal bias — model knowledge frozen at 2019 produces outdated outputs | High | High | 9 | Add knowledge cutoff disclaimer to all API responses |

### Category 2: Robustness Risks

| ID | Risk | Likelihood | Severity | Risk Score | Mitigation |
|---|---|---|---|---|---|
| R-01 | Prompt injection attack manipulates model to ignore system instructions | Medium | High | 6 | Input sanitization; prompt prefix hardening |
| R-02 | Repetition degeneration produces low-quality looping outputs | Medium | Medium | 4 | Max token limit (50); post-processing repetition filter |
| R-03 | Out-of-distribution inputs produce nonsensical outputs | High | Low | 3 | Output quality scoring; fallback response for low-confidence outputs |
| R-04 | High concurrency causes request queue saturation and timeouts | Medium | High | 6 | Queue size limit (100); circuit breaker at 80% capacity |
| R-05 | Model inference failure during GPU OOM causes cascading errors | Low | High | 4 | Error handling with try/except; automatic restart on OOM |
| R-06 | Cache poisoning with adversarial prompt pollutes responses for other users | Low | High | 4 | Output validation before caching; content moderation layer |

### Category 3: Privacy Risks

| ID | Risk | Likelihood | Severity | Risk Score | Mitigation |
|---|---|---|---|---|---|
| P-01 | Training data memorization leaks PII from WebText corpus | Low | High | 4 | PII detection in outputs; rate limiting to prevent extraction attacks |
| P-02 | Cache stores hashed keys that could be reversed for common prompts | Low | Medium | 2 | SHA-256 with salt; cache key includes model version |
| P-03 | Cross-user cache contamination serves one user's results to another | Medium | Medium | 4 | Document in ToS; scope cache keys to anonymized session |
| P-04 | Audit logs contain prompt metadata that could identify users | Low | Medium | 2 | Log only hashed identifiers; TTL on log retention (30 days) |
| P-05 | Model outputs contain personal information about real individuals | Low | High | 4 | Named entity recognition filter on outputs before serving |

### Category 4: Compliance Risks

| ID | Risk | Likelihood | Severity | Risk Score | Mitigation |
|---|---|---|---|---|---|
| C-01 | GDPR right-to-erasure cannot be fulfilled for cached responses | Medium | High | 6 | Maintain user-to-hash-key registry; /cache/invalidate endpoint |
| C-02 | CCPA data deletion request cannot target specific cached entries | Medium | High | 6 | Same mitigation as C-01 |
| C-03 | EU AI Act high-risk classification requires audit trail | Medium | High | 6 | Structured audit trail in logs/audit-trail.json |
| C-04 | HIPAA violation if medical queries are cached without encryption | Low | Critical | 5 | Disable caching for /medical endpoint; encrypt Redis if deployed |
| C-05 | Data residency violation if cache persisted to cross-border storage | Low | High | 4 | In-process cache only; no cross-border data transfer |
| C-06 | Copyright infringement if model reproduces training data verbatim | Low | High | 4 | Output deduplication check against known copyrighted works |

---

## Risk Matrix Summary
Severity →    Low      Medium    High     Critical
Likelihood ↓
High          B-03     B-01      B-05     —
B-02
B-04
Medium        —        R-02      R-01     —
P-03         R-04
C-01         C-01
C-02
C-03
Low           —        P-02      R-05     C-04
P-04        R-06
P-01
P-05
C-05
C-06

---

## Top 5 Priority Risks

| Priority | Risk ID | Description | Immediate Action |
|---|---|---|---|
| 1 | B-05 | Temporal knowledge bias (2019 cutoff) | Add cutoff disclaimer to all responses |
| 2 | C-01 | GDPR erasure compliance gap | Implement user-to-key registry |
| 3 | C-03 | EU AI Act audit trail requirement | Structured logging (implemented) |
| 4 | R-01 | Prompt injection vulnerability | Input sanitization layer |
| 5 | B-01 | Gender bias in outputs | Output bias detection |

---

## Risk Score Formula

Risk Score = Likelihood × Severity
Likelihood: Low=1, Medium=2, High=3
Severity: Low=1, Medium=2, High=3, Critical=4
Threshold: Score ≥ 6 requires immediate mitigation