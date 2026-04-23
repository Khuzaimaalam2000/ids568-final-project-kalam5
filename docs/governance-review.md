---

## 2. Data Security

### 2.1 Data in Transit
All client-server communication occurs over HTTP on localhost
in the current deployment. For production deployment, TLS
(HTTPS) must be enforced at the load balancer or API gateway
level. No data is transmitted to external services during
inference — the model runs entirely on-premises.

### 2.2 Data at Rest
The in-process LRU cache stores only model-generated responses
indexed by SHA-256 hashed keys. No plaintext prompts, user
identifiers, or session tokens are persisted to disk. Cache
contents are lost on server restart, providing natural data
minimization.

Prometheus metrics are stored in-memory with a configurable
retention window (default: 15 days). Metrics contain only
aggregate statistics — no individual request content.

### 2.3 Authentication and Authorization
The current implementation has no authentication layer — all
endpoints are publicly accessible on the configured port. For
production deployment, API key authentication or OAuth 2.0
must be implemented before external exposure.

### 2.4 Secrets Management
No credentials, API keys, or secrets are hardcoded in the
codebase. Model weights are loaded from the Hugging Face Hub
public repository and cached locally. No proprietary data
sources are used.

---

## 3. Retrieval Risks

This system does not implement a retrieval-augmented generation
(RAG) pipeline. The model generates responses entirely from its
parametric knowledge (WebText pretraining). However, the
following retrieval-adjacent risks apply:

### 3.1 Training Data Contamination
The model's parametric knowledge was trained on WebText (2019),
which may contain:
- Personally identifiable information from public web pages
- Copyrighted content reproduced without license
- Factually incorrect information from unreliable sources
- Biased or offensive content from unmoderated forums

**Mitigation:** Output filtering layer to detect and redact PII
patterns (email, phone, SSN) before serving responses.

### 3.2 Stale Knowledge Risk
All model knowledge is frozen at the 2019 WebText cutoff.
Queries about post-2019 events, people, or technologies will
produce fabricated or outdated responses with high confidence.

**Mitigation:** Prepend knowledge cutoff disclaimer to all
API responses. Implement date-awareness check: if query
contains years after 2019, return explicit uncertainty notice.

### 3.3 Cache Staleness
Cached responses remain valid for TTL=300 seconds (5 minutes).
If the model is updated or a response is found to be incorrect,
cached stale responses will continue to be served until TTL
expiration or manual cache flush.

**Mitigation:** Implement cache versioning — include model
version in cache key so model updates automatically invalidate
all prior cached responses. Expose `/cache/clear` endpoint
for emergency invalidation.

---

## 4. Hallucination Risk Points

Hallucination is the primary reliability risk for this system.
DistilGPT-2 is a generative model optimized for fluency, not
factual accuracy.

### 4.1 High-Risk Hallucination Scenarios

| Scenario | Hallucination Type | Likelihood | Impact |
|---|---|---|---|
| Factual questions (dates, names, statistics) | Fabricated facts presented confidently | High | Medium-High |
| Technical documentation requests | Incorrect code or API descriptions | High | High |
| Medical or legal queries | Dangerous misinformation | Medium | Critical |
| Recent events (post-2019) | Completely fabricated responses | High | High |
| Mathematical calculations | Incorrect arithmetic | High | Medium |
| Citation requests | Fabricated citations | High | Medium |

### 4.2 Hallucination Detection Strategy
The current system has no automated hallucination detection.
Recommended mitigations in priority order:

1. **Confidence scoring:** Add log-probability scoring to flag
   low-confidence responses for human review
2. **Factual grounding:** Integrate with a retrieval system
   (RAG) to ground responses in verified documents
3. **Output classification:** Fine-tune a small classifier to
   detect likely hallucinated content patterns
4. **User disclosure:** Prepend all responses with explicit
   disclaimer about generative model limitations

---

## 5. Tool-Misuse Pathways

This system does not implement tool use or agentic capabilities.
The model cannot execute code, access external APIs, or modify
system state. However, the following misuse pathways exist at
the API level:

### 5.1 Prompt Injection
An adversary can craft prompts designed to manipulate model
outputs in unintended ways:
- Override implicit system instructions
- Extract training data through careful prompting
- Generate harmful content by circumventing safety measures

**Mitigation:** Input sanitization to detect and reject known
injection patterns. Output content moderation before serving.

### 5.2 Automated Abuse
The API has no rate limiting in the current implementation.
An adversary could:
- Generate spam or phishing content at scale
- Perform model extraction attacks through systematic querying
- Cause denial of service through request flooding

**Mitigation:** Implement rate limiting (100 req/min per IP),
API key authentication, and request logging for abuse detection.

### 5.3 Cache Exploitation
An adversary could intentionally submit prompts that poison
the cache with adversarial responses, which are then served
to other users who submit the same prompt.

**Mitigation:** Output validation pipeline before cache storage.
Content moderation score threshold required before caching.

---

## 6. Compliance Concerns

### 6.1 GDPR (EU General Data Protection Regulation)
**Applicable if:** Any EU residents submit requests to the API.

Key compliance gaps in current implementation:
- No mechanism to fulfill right-to-erasure requests for cached
  responses (hashed keys prevent targeted deletion)
- No data processing agreement or privacy notice displayed to users
- No consent mechanism for data collection via Prometheus metrics

**Required actions:**
- Implement user-to-hash-key registry for targeted cache deletion
- Add privacy notice to API documentation
- Configure Prometheus metric retention limits (max 30 days)

### 6.2 CCPA (California Consumer Privacy Act)
**Applicable if:** California residents submit requests.

Similar to GDPR: right to know and right to delete apply.
Same technical mitigations as GDPR apply.

### 6.3 EU AI Act (2024)
DistilGPT-2 as deployed here is a general-purpose AI model.
Under the EU AI Act, GPAI models with systemic risk (>10^25
FLOPs training compute) face additional requirements. DistilGPT-2
(82M parameters) falls below this threshold and is classified
as a limited-risk system.

**Requirements for limited-risk GPAI:**
- Transparency: disclose AI-generated content to users ✓ (planned)
- Technical documentation: model card maintained ✓
- Audit trail: structured logging implemented ✓

### 6.4 HIPAA (US Health Insurance Portability)
**Applicable if:** System processes protected health information.

Current deployment must not be used for medical queries without:
- Business Associate Agreement with hosting provider
- Encryption of all cached data at rest
- Audit logging of all PHI access
- Explicit endpoint restrictions for medical content

**Current status:** Not HIPAA compliant. Medical use prohibited.

---

## 7. PII Policy Adherence

The system implements the following PII controls:

| Control | Implementation | Status |
|---|---|---|
| No plaintext PII in cache keys | SHA-256 hashing | ✓ Implemented |
| No user ID storage | Hash-only keys | ✓ Implemented |
| Prompt not persisted to disk | In-memory cache only | ✓ Implemented |
| Metrics contain no PII | Aggregate stats only | ✓ Implemented |
| PII detection in outputs | Output filter | ✗ Not implemented |
| User consent for logging | Consent mechanism | ✗ Not implemented |
| Data retention limits | TTL only | ⚠ Partial |