<div align="center">

# 🛡️ SOC Alert Correlation & Incident Prioritization

**A retrospective AI research pipeline for the Microsoft GUIDE dataset**

[![Status](https://img.shields.io/badge/Status-Exploratory%20Phase%203-orange?style=flat-square)](FINAL_RESEARCH_PERFORMANCE_REPORT.md)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](requirements.txt)
[![Model](https://img.shields.io/badge/Local%20Model-Qwen2.5%3A3b-purple?style=flat-square)](FINAL_RESEARCH_PERFORMANCE_REPORT.md)
[![Data](https://img.shields.io/badge/GUIDE__Test-4.1M%20evidence%20rows-green?style=flat-square)](submission/DATA_AND_CLAIM_AUDIT.md)
[![Recall@20](https://img.shields.io/badge/Best%20Recall%4020-86.82%25-brightgreen?style=flat-square)](FINAL_RESEARCH_PERFORMANCE_REPORT.md)

<br/>

*Investigating whether a Correlate → Prioritize → Verify (C/P/V) workflow can recover expert-prioritized incidents from predicted alert groups — faster than matched rule and retrieval baselines.*

</div>

---

## 📖 Start here

> Navigate in this order for the clearest picture of what was built, what worked, and what didn't.

| # | Document | What you'll find |
|---|---|---|
| 1 | [**CONTEXT.md**](CONTEXT.md) | Research question, data boundaries, full implemented flow, open gates |
| 2 | [**PROJECT_ITERATIONS.md**](PROJECT_ITERATIONS.md) | Every stage and decision — including negative results — in chronological order |
| 3 | [**Final Performance Report (PDF)**](FINAL_RESEARCH_PERFORMANCE_REPORT.pdf) · [Editable](FINAL_RESEARCH_PERFORMANCE_REPORT.md) | Complete implementation, experiments, baselines, ablations, figures, and limitations |
| 4 | [**REPRODUCE.md**](submission/REPRODUCE.md) · [Experiment register](submission/EXPERIMENT_REGISTER.md) | Commands, immutable run IDs, and output verification |

---

## 🏆 Best Results (Exploratory)

> [!IMPORTANT]
> GUIDE_Test labels were accessed in earlier project work. All results below are **exploratory**, not confirmatory. The frozen production method is **v2 grouping + v7 ranking**.

<div align="center">

### 🎯 End-to-end Recall@20 Progression

</div>

```
BM25-like baseline  ████░░░░░░░░░░░░░░░░░░░░░░░░░░  13.6%
Trained ranker v1   █████░░░░░░░░░░░░░░░░░░░░░░░░░  15.4%  (135 disjoint orgs)
Learned grouping    ██████████░░░░░░░░░░░░░░░░░░░░  31.8%  (57 queues, exploratory)
Entity/time v2      ███████████░░░░░░░░░░░░░░░░░░░  34.0%  (exploratory)
v4 ranker           █████████████░░░░░░░░░░░░░░░░░  42.2%  (exploratory)
v7 ranker ★ FROZEN  ███████████████████████████░░░  86.8%  (updated exploratory result)
Oracle ceiling      █████████████████████████░░░░░  82.8%  (updated fixed-group recoverability)
```

### 📊 Full Results Table

| Scope | Method | Recall@20 | P@10 | nDCG@20 |
|---|---|:---:|:---:|:---:|
| 499 orgs — full GUIDE | Rule / BM25-like baseline | 0.1364 | 0.1714 | 0.1542 |
| 135 training-disjoint orgs | Trained logistic ranker v1 | 0.1542 | 0.2351 | 0.1776 |
| 499 orgs (exploratory) | v2 grouping + v4 ranker | 0.4223 | 0.5284 | — |
| **499 orgs (exploratory)** | **✅ v2 grouping + v7 ranker — FROZEN** | **0.8682** | **0.6158** | **0.4371** |
| 135 orgs outside ranker training | v2 grouping + v7 ranker | 0.4552 | — | — |
| 20 orgs — local Qwen v2 | C + P end-to-end | 0.1443 | 0.1848 | — |

### ⚠️ Hard Limits

| Constraint | Value | Implication |
|---|---|---|
| Initial rule candidate recall | **37,018 / 159,186,107 = 0.0233%** | Severe retrieval bottleneck in the original rule/BM25 baseline |
| Frozen v2 candidate recall | **699,790 / 159,186,107 = 0.4396%** | Entity-enabled retrieval improves coverage but remains far below exhaustive positive-pair recall |
| Candidate-connected label bound | **8,638 / 9,980 = 86.55%** | Gold-aware diagnostic; downstream scoring and grouping affect achieved recovery |
| Oracle-order ceiling (v2 groups) | **8,266 / 9,980 = 82.83%** | Updated fixed-group recoverability ceiling |
| Achieved end-to-end reference | **8,665 / 9,980 = 86.82%** | Updated v2 grouping + v7 ranking result |
| Structural end-to-end ceiling | **9,063 / 9,980 = 90.81%** | 95% target structurally blocked under current exclusion + 100-alert cap |

---

## 🔄 Pipeline Architecture

```
╔══════════════════════════════════════════════════════════════╗
║           GUIDE_Test.csv  —  4,147,992 evidence rows         ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
           ┌───────────────────────┐
           │    Preprocessing      │  composite key dedup · restricted ledger
           │                       │  evaluator-only labels · field-gate enforcement
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  Candidate Generation │  Category + ATT&CK-technique · ≤20 neighbors
           │                       │  entity/time routes: local-only amendment
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   🔗 Agent C          │  LINK / NO_LINK / UNSURE per alert pair
           │   Correlate           │  cites supporting evidence
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   📊 Agent P          │  uncalibrated group priority scores
           │   Prioritize          │  orders groups for top-20 recovery
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   ✅ Agent V          │  PASS / REVISE / REVIEW per citation
           │   Verify              │  60% of groups flagged for review
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   Isolated Evaluator  │  reads labels after prediction freeze
           │                       │  Pair F1 · P@10 · Recall@20 · nDCG@20
           └───────────────────────┘
```

---

## 📈 Iteration History

| Iteration | Recall@20 | Key Finding |
|---|:---:|---|
| Full offline BM25-like baseline | 0.1364 | Candidate recall 0.0233% — severe retrieval bottleneck |
| Matched ranking extension (135 orgs) | 0.1542 | P@10 ↑, but Recall@20 CI includes zero |
| Learned pair grouping (57 queues) | 0.3179 | Grouping helps; pair F1 fell; oracle ceiling 58.5% |
| Entity/time sensitivity (499 queues) | 0.3095 | Pair precision improved; F1 fell; allowlist still empty |
| Entity/time pair model v2 | 0.3397 | Pair precision 0.9041; updated ceiling 82.83%; v2 frozen |
| Group priority v4 ranker | 0.4223 | +8.3 pp over v2 ordering; 0.4106 on 135 disjoint orgs |
| Hard-negative v6 ranker | 0.4399 | Descriptive gain; no training-disjoint improvement |
| **Descriptor-aware v7 ranker ★** | **0.8682** | Updated reference; 0.4552 on 135 outside training |
| Specialist v8 control | 0.4982 | No gain — v7 scores retained |
| Adaptive links v9 control | — | Tiny recall gain reduced P@10 and ceiling; v2 groups kept |
| Learned group-merge v10 | 0.4982 | No merge met purity + recall gates; identical to v2 + v7 |
| Component ablation (entity route) | 0.4433 | −5.5 pp when entity route removed; entity is critical |
| Bounded matched Qwen controls | 0.1443 | C+P < singleton/rarity control; no C/P/V superiority |
| Phase 9C fragment heuristic | 0.4981 | NO-GO; 38 merges increased false grouped pairs and reduced recoverability |
| Phase 9E sixth-neighbor route | 0.4982 | NO-GO; +49,455 candidates but no additional recovered incident |

> Full chronology → [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md) · Exhibition table → [EXHIBITION_METRICS_BRIEF_20261115.md](submission/EXHIBITION_METRICS_BRIEF_20261115.md)

---

## 🗂️ Repository Map

```
CN-Research-/
├── 📁 src/                  Validation · preprocessing · C/P/V agents · evaluators · runners
├── 📁 configs/              field_policy.yaml (official — empty) · empirical_field_policy.yaml (local-only)
├── 📁 data/raw/ & derived/  GUIDE inputs + restricted records  ⚠️ Git-ignored
├── 📁 fixtures/             Fictional checks · frozen expected outputs
├── 📁 outputs/              Versioned metrics · run manifests · all historical outputs retained
├── 📁 phases_outputs/       Dated phase records · amendments · gate decisions
├── 📁 submission/           Report · figures · verification · reproduction material
├── 📁 dashboard/            index.html (saved aggregates) · simulation.html (fictional replay)
├── 📄 CONTEXT.md            ← Canonical methodology and implementation reference
├── 📄 PROJECT_ITERATIONS.md ← Canonical timeline and decision log
└── 📄 README.md             ← You are here
```

---

## 🚀 Quick Start

**Prerequisites:** Python 3.12 · `matplotlib==3.11.2` · `numpy==2.5.4` (figures only)

```powershell
# 1. Verify submission package integrity
.\.venv\Scripts\python.exe -m submission.verify_package

# 2. Inspect frozen local call timing
.\.venv\Scripts\python.exe -m submission.measure_local_operations

# 3. Launch the research dashboard
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
# → http://127.0.0.1:8765/            (saved aggregate metrics)
# → http://127.0.0.1:8765/simulation.html  (fictional event replay — clearly labelled)
```

> [!TIP]
> For a full offline + local Qwen run, follow [REPRODUCE.md](submission/REPRODUCE.md). The Qwen stage can take **several hours on CPU**. No hosted model calls are authorized by the current field policy.

---

## 📚 Key References

| 📄 Document | Contents |
|---|---|
| [FINAL_RESEARCH_PERFORMANCE_REPORT.md](FINAL_RESEARCH_PERFORMANCE_REPORT.md) | Final performance report — implementation, metrics, figures, ablations, and limitations |
| [EXHIBITION_METRICS_BRIEF_20261115.md](submission/EXHIBITION_METRICS_BRIEF_20261115.md) | Stage-separated results table + suggested slide wording |
| [INDEPENDENT_COMPONENT_ABLATION_20261115.md](submission/INDEPENDENT_COMPONENT_ABLATION_20261115.md) | Candidate-route, grouping, and ranking ablations with matched denominators |
| [PERFORMANCE_BASELINE_STUDY.md](submission/PERFORMANCE_BASELINE_STUDY.md) | 334/135 organization-split matched ranking study |
| [DATA_AND_CLAIM_AUDIT.md](submission/DATA_AND_CLAIM_AUDIT.md) | Schema, evidence-row grain, composite keys, field gates, and provenance hashes |
| [KNOWN_LIMITATIONS.md](submission/KNOWN_LIMITATIONS.md) | 11 open gates — what prevents any operational readiness claim |
| [FRESH_COHORT_AND_SHADOW_GATE.md](submission/FRESH_COHORT_AND_SHADOW_GATE.md) | Gates required for a confirmatory study + shadow-mode pilot |
| [REPRODUCE.md](submission/REPRODUCE.md) | Commands · immutable run IDs · output paths |

---

## 📋 Submission Status

<div align="center">

**🟡 Exploratory · Partial Phase 3 Submission**

</div>

> [!WARNING]
> **Do not claim:** 95% recovery, confirmatory model superiority, production SOC readiness, or any certification. No retrospective score increase on previously accessed GUIDE_Test labels satisfies any of these claims.

**Outstanding before a confirmatory study is possible:**

- [ ] 🔒 Fresh, sealed, untouched ranked cohort
- [ ] 📋 Official point-in-time model-input field allowlist *(currently empty)*
- [ ] 🔑 Source-validated alert membership rule *(70,702 ambiguous composite keys unresolved)*
- [ ] ⚖️ Matched B0–B4 / C / P / V held-out comparison with equal budgets
- [ ] 👁️ Blinded citation review and analyst adjudication
- [ ] 🏥 Shadow-mode SOC pilot *(live arrival rates, per-alert p50/p95 latency, sustained throughput, false-merge impact)*

The [delivery checklist](submission/DELIVERY_CHECKLIST.md) maps available artifacts to Phase 3 assignment requirements.

---

## 🔗 External References

- 📄 [Microsoft GUIDE Dataset Paper](https://arxiv.org/abs/2407.09017) — source data context and investigation/triage framing
- 📄 [Adaptive Incident Prioritization Paper](https://arxiv.org/abs/2607.16963) — queue-relative expert priority background
- 📖 [CONTEXT.md](CONTEXT.md) — local methodology, implementation deviations, and current gates

---

<div align="center">

*Built as an honest exploratory research prototype — not production software.*
*Preserving negative results is as important as reporting gains.*

</div>
