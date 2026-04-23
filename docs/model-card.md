# Model Card: DistilGPT-2 LLM Inference Server
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Version:** 1.0.0  
**Date:** April 2026  
**System:** IDS568 Final Project — Production LLM Inference API

---

## Model Details

| Field | Value |
|---|---|
| Model Name | DistilGPT-2 |
| Model Type | Causal Language Model (decoder-only transformer) |
| Parameters | 82 million |
| Architecture | 6-layer transformer, 12 attention heads, 768 hidden dim |
| Base Model | GPT-2 (distilled via knowledge distillation) |
| Developed By | Hugging Face |
| License | Apache 2.0 |
| Serving Framework | FastAPI + custom batching/caching layer |
| Hardware | CPU (Apple M-series or x86_64) |
| Inference Latency | 380-480ms cold (CPU), <8ms warm (cache hit) |
| Max Tokens | 50 (configurable) |
| Tokenizer | GPT-2 BPE tokenizer (50,257 vocabulary) |

---

## Intended Use

### Primary Use Cases
- Demonstrating LLM inference optimization techniques
  (dynamic batching, intelligent caching)
- Educational and research exploration of MLOps serving patterns
- Benchmarking inference server performance under various load profiles
- Prototype development for NLP text generation applications

### Out-of-Scope Applications
The following use cases are explicitly outside the intended scope
of this deployment:

- **Medical or clinical decision support:** Model lacks domain
  expertise and may generate plausible but incorrect medical content
- **Legal advice or document generation:** Outputs are not legally
  verified and should not be relied upon for legal decisions
- **Financial advice:** Model outputs are not validated against
  financial regulations or accuracy requirements
- **Safety-critical systems:** Any system where model errors could
  cause physical harm or significant financial loss
- **High-stakes automated decisions:** Hiring, lending, criminal
  justice, or other decisions with significant human impact
- **Production customer-facing applications:** This deployment is
  optimized for research and benchmarking, not production SLA
  requirements

---

## Performance Metrics

### Inference Performance (from Milestone 5 Benchmarks)

| Metric | Value | Condition |
|---|---|---|
| Cold Cache Avg Latency | 454.65ms | First inference, no cache |
| Warm Cache Avg Latency | 1.99ms | Repeated prompt, cache hit |
| Cache Speedup Factor | 228x | Warm vs cold |
| Peak Throughput (cached) | 734 rps | High concurrency, all hits |
| Peak Throughput (uncached) | ~2.1 rps | Cold inference only |
| P95 Latency (high load) | 17.84ms | Cached workload |
| Cache Hit Rate (65% repeat) | 100% | Mixed workload |

### Model Quality Metrics

| Metric | Value | Notes |
|---|---|---|
| Perplexity (WikiText-103) | ~21.1 | Standard benchmark |
| Perplexity (PTB) | ~60.8 | Standard benchmark |
| Parameters | 82M | 40% smaller than GPT-2 |
| Training Data | WebText | ~40GB internet text |
| Knowledge Cutoff | ~2019 | Pre-training data vintage |

---

## Training Data

### Data Description
DistilGPT-2 was trained by Hugging Face using knowledge distillation
from GPT-2 on the WebText dataset — a corpus of internet text
scraped from outbound links on Reddit with at least 3 karma points.

### Data Characteristics
- **Source:** Reddit outbound links (WebText corpus)
- **Size:** ~40GB of text
- **Language:** Predominantly English
- **Domain:** General internet text (news, forums, blogs, Wikipedia)
- **Time Period:** Pre-2019 content

### Known Data Limitations
- Overrepresents English-language content and Western perspectives
- Reddit link bias: content popular with Reddit users may not
  represent general population interests or knowledge
- Contains some offensive, biased, or factually incorrect content
  from internet sources
- No systematic filtering for privacy-violating content (PII,
  private communications)
- Knowledge cutoff of ~2019 means post-2019 events are unknown
  to the model

---

## Limitations and Failure Modes

### Known Limitations

**1. Factual Accuracy**
DistilGPT-2 is a generative model trained to predict plausible
next tokens, not to retrieve factually accurate information. It
will confidently generate incorrect facts, false citations, and
fabricated statistics. All outputs must be independently verified
for factual applications.

**2. Temporal Knowledge Cutoff**
The model has no knowledge of events after approximately 2019.
Questions about recent events will produce outdated or fabricated
responses.

**3. Mathematical Reasoning**
The model has very limited mathematical reasoning capability. Simple
arithmetic and complex calculations are frequently incorrect.

**4. Context Length**
The model supports a maximum context of 1,024 tokens. Longer
documents must be truncated, potentially losing critical context.

**5. Repetition and Degeneration**
Without sampling strategies (temperature, top-p), greedy decoding
can produce highly repetitive outputs that loop on the same phrase.
This is mitigated in our serving layer by using do_sample=False
with fixed max_new_tokens=50.

**6. Multilingual Performance**
The model performs poorly on non-English languages, producing
grammatically incorrect or nonsensical outputs for most
non-English inputs.

### Failure Modes

| Failure Mode | Trigger | Probability | Impact |
|---|---|---|---|
| Hallucination | Factual questions | High | Incorrect information presented confidently |
| Repetition loop | Long generation, low temperature | Medium | Poor quality output |
| Prompt injection | Adversarial prompt crafting | Medium | Unexpected model behavior |
| Toxic content | Adversarial prompts | Low-Medium | Harmful generated text |
| PII leakage | Training data memorization | Low | Privacy violation |
| Language confusion | Mixed-language input | Medium | Garbled output |

---

## Ethical Risks and Considerations

### Bias and Fairness
The model inherits biases present in its internet-scraped training
data. These include:
- **Gender bias:** Tendency to associate certain professions with
  specific genders
- **Cultural bias:** Western and English-language centric worldview
- **Representation bias:** Underrepresentation of minority
  perspectives and non-Western cultures
- **Socioeconomic bias:** Content reflects Reddit demographics
  (predominantly young, male, English-speaking, technically literate)

### Misuse Potential
The model could be misused to:
- Generate misinformation or fake news at scale
- Produce phishing or social engineering content
- Automate spam or low-quality content generation
- Create content that impersonates real people or organizations

### Privacy Considerations
- The model may have memorized some training data including
  potentially private information present in WebText
- Cache implementation stores SHA-256 hashed keys only;
  no plaintext prompts are persisted
- No user identifiers are stored in any component of the system

---

## Lineage

See `docs/lineage-diagram.png` for the complete data-to-deployment
lineage diagram.

**Summary lineage:**
WebText Corpus (2019)
→ GPT-2 Pretraining (OpenAI)
→ Knowledge Distillation (Hugging Face)
→ DistilGPT-2 Weights (HuggingFace Hub)
→ FastAPI Inference Server (Milestone 5)
→ Dynamic Batching Layer
→ LRU Cache Layer
→ Production Monitoring (Final Project)

---

## Quantitative Analysis

### Latency by Cache State

| Cache State | Avg (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
|---|---|---|---|---|
| Cold (miss) | 454.65 | 456.84 | 473.09 | 481.20 |
| Warm (hit) | 1.99 | 1.73 | 3.19 | 3.85 |

### Throughput by Concurrency

| Concurrency | Throughput (rps) | Avg Latency | P95 Latency |
|---|---|---|---|
| 2 (low) | 575 | 3.05ms | 4.75ms |
| 5 (medium) | 677 | 6.43ms | 9.43ms |
| 10 (high) | 734 | 12.08ms | 17.84ms |

*Note: High throughput figures reflect cache-hit workloads.
Cold inference throughput is 2-3 rps on CPU hardware.*

---

## Feedback and Contact

For questions about this model card or the serving system:
- **NetID:** kalam5
- **Course:** IDS568 MLOps
- **Institution:** University of Illinois Chicago