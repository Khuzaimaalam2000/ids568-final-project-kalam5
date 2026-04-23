cat > README.md << 'READMEEOF'
# IDS568 Final Project: Monitoring, Governance & Reflection
**Author:** Khuzaima Alam | **NetID:** kalam5  
**Course:** IDS568 MLOps | **Date:** April 2026

---

## System Overview

This project implements a complete production operations framework
for a DistilGPT-2 LLM inference server, building on the batching
and caching optimizations developed in Milestone 5. The system
includes production monitoring, A/B testing, model governance,
drift detection, and comprehensive risk assessment.

**Base System:** FastAPI inference server with dynamic batching
(batch_size=8) and LRU caching (TTL=300s) from Milestone 5.

---

## Component Links

| Component | Description | Key Files |
|---|---|---|
| C1: Monitoring Dashboard | Prometheus metrics + Grafana dashboard | `src/monitoring/`, `dashboards/`, `screenshots/` |
| C2: A/B Test | EXP-001 baseline vs optimized server | `src/ab_test/`, `docs/experiment-specification.md` |
| C3: Governance Packet | Model card, lineage, risk register, audit trail | `docs/model-card.md`, `docs/risk-register.md`, `logs/audit-trail.json` |
| C4: Drift Detection | Feature drift across 8 production windows | `src/drift/`, `visualizations/`, `docs/drift-diagnostic-report.md` |
| C5: Risk Assessment | System boundary, risk matrix, CTO memo | `docs/governance-review.md`, `docs/risk-matrix.md`, `docs/cto-memo.md` |

---

## Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/Khuzaimaalam2000/ids568-final-project-kalam5.git
cd ids568-final-project-kalam5
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Verify Setup
```bash
python3 -m py_compile src/monitoring/instrumentation.py && echo "✓ OK"
python3 -m py_compile src/ab_test/simulation.py && echo "✓ OK"
python3 -m py_compile src/drift/drift_detection.py && echo "✓ OK"
```

---

## Reproduction Instructions

### Component 1: Run Traffic Simulation
```bash
python3 -m src.monitoring.simulator
python3 src/monitoring/generate_dashboard.py
```

### Component 2: Run A/B Test
```bash
python3 src/ab_test/simulation.py
```

### Component 3: Generate Lineage Diagram
```bash
python3 src/monitoring/generate_lineage.py
```

### Component 4: Run Drift Detection
```bash
python3 src/drift/drift_detection.py
```

### Component 5: Generate System Boundary Diagram
```bash
python3 src/monitoring/generate_boundary.py
```

### Generate All Visualizations at Once
```bash
python3 src/monitoring/generate_dashboard.py && \
python3 src/monitoring/generate_lineage.py && \
python3 src/monitoring/generate_boundary.py && \
python3 src/ab_test/simulation.py && \
python3 src/drift/drift_detection.py
```

---

## Repository Structure

ids568-final-project-kalam5/
├── src/
│   ├── monitoring/
│   │   ├── instrumentation.py    # Prometheus metrics
│   │   ├── simulator.py          # Traffic simulator
│   │   ├── generate_dashboard.py # Dashboard screenshot
│   │   ├── generate_lineage.py   # Lineage diagram
│   │   └── generate_boundary.py  # System boundary diagram
│   ├── ab_test/
│   │   └── simulation.py         # A/B test simulation
│   └── drift/
│       └── drift_detection.py    # Drift detection
├── docs/
│   ├── dashboard-interpretation.md
│   ├── experiment-specification.md
│   ├── recommendation-memo.md
│   ├── model-card.md
│   ├── risk-register.md
│   ├── lineage-diagram.png
│   ├── system-boundary-diagram.png
│   ├── drift-diagnostic-report.md
│   ├── governance-review.md
│   ├── risk-matrix.md
│   └── cto-memo.md
├── dashboards/
│   ├── prometheus.yml
│   └── grafana_dashboard.json
├── logs/
│   ├── audit-trail.json
│   ├── ab_test_results.json
│   ├── drift_results.json
│   └── simulation_results.json
├── visualizations/
│   ├── ab_test_results.png
│   ├── drift_analysis.png
│   └── anomaly_detection.png
├── screenshots/
│   └── dashboard_screenshot.png
├── requirements.txt
└── README.md

---

## Key Results

### Component 1: Monitoring
- 6 metric categories tracked: latency, throughput, cache,
  errors, drift, memory
- Dashboard shows 5 traffic phases with clear phase transitions
- Drift alert triggered at Window 5 (KS > 0.10)

### Component 2: A/B Testing
- Variant B achieves 65% latency reduction (420ms → 148ms)
- Throughput improvement: 367% (2.1 → 9.8 rps)
- All metrics statistically significant (p < 0.0001)
- Recommendation: SHIP B

### Component 3: Governance
- 20 risks identified across bias, robustness, privacy, compliance
- Complete audit trail with 8 documented events
- Model card covers all required sections

### Component 4: Drift Detection
- prompt_length drifts 144% by Window 7 (PSI > 0.20)
- Error rate escalates from 2% to 14%
- Cache hit rate drops from 65% to 20%
- Retraining recommended from Window 5

### Component 5: Risk Assessment
- 15 risks in risk matrix, 5 classified P1 (immediate action)
- System boundary covers all 4 inference pathway components
- CTO memo identifies 5 critical gaps before production deployment

---

## Lessons Learned Across All Milestones

### Milestone 4 (Spark ETL)
Distributed processing requires careful benchmarking to determine
whether the overhead is justified. Pandas outperformed Spark on
datasets under 10M rows on local hardware — a counterintuitive
result that required empirical validation rather than assumption.
The lesson: always measure before optimizing.

### Milestone 5 (LLM Inference)
Caching is the highest-leverage optimization for LLM serving,
delivering 228x latency improvement at near-zero cost. Dynamic
batching compounds this by improving throughput under concurrent
load. The combination enables single-server deployments that would
otherwise require GPU clusters.

### Final Project (Monitoring + Governance)
Operational AI is far more complex than model training. A model
that performs well on benchmarks can silently degrade in production
due to input drift, while appearing healthy from a system
availability perspective. Comprehensive monitoring — including
drift signals, not just latency and error rate — is essential
for responsible production deployment.

The governance artifacts (model card, risk register, audit trail)
revealed risks that were not obvious during development. Writing
a model card forces explicit acknowledgment of limitations and
failure modes that are easy to overlook when focused on
performance optimization.

---

## Component Integration

The components of this project are intentionally interconnected:

- The **monitoring dashboard** (C1) tracks the drift score
  that the **drift detection** (C4) computes
- The **A/B test** (C2) validates the optimization documented
  in the **model card** (C3)
- The **model card limitations** (C3) directly inform the
  **risk matrix** (C5) high-severity risks
- The **drift trigger** (C4) connects to the retraining event
  in the **audit trail** (C3)
- The **risk mitigations** (C5) reference monitoring
  capabilities in the **dashboard** (C1)

