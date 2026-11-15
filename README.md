# SOC Alert Correlation and Incident Prioritization

> **Retrospective research implementation — not a deployed SOC.**
> Tests whether alerts can be grouped into incidents, ranked for analyst review, and checked for evidence support through Correlate (C), Prioritize (P), and Verify (V) roles against the Microsoft GUIDE research export.

---

## Read this project in order

1. [CONTEXT.md](CONTEXT.md) — research methodology, data boundaries, implemented flow, and unresolved gates
2. [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md) — chronological record of every stage, decision, and negative result
3. [Phase 3 PDF report](submission/PHASE3_IMPLEMENTATION_REPORT.pdf) · [Editable report](submission/FINAL_REPORT.md) · [Delivery checklist](submission/DELIVERY_CHECKLIST.md) · [Known limits](submission/KNOWN_LIMITATIONS.md)
4. [Reproduction instructions](submission/REPRODUCE.md) · [Experiment register](submission/EXPERIMENT_REGISTER.md)

---

## Best current results (exploratory)

> [!IMPORTANT]
> All GUIDE_Test labels were accessed in earlier work. These results are **exploratory**, not confirmatory. The frozen method is **v2 grouping + v7 ranking**; v4 is the registered future-cohort comparator.

| Evaluation scope | Method | End-to-end Recall@20 | P@10 | nDCG@20 |
|---|---|---:|---:|---:|
| 499 organizations — full GUIDE (descriptive) | Rule/BM25-like baseline | 0.1364 | 0.1714 | 0.1542 |
| 135 training-disjoint organizations | Trained logistic ranker (v1) | 0.1542 | 0.2351 | 0.1776 |
| 499 organizations (exploratory) | v2 grouping + v4 ranker | 0.4223 | 0.5284 | — |
| **499 organizations (exploratory)** | **v2 grouping + v7 ranker (frozen)** | **0.4982** | **0.6158** | **0.4371** |
| 135 queues outside ranker training | v2 grouping + v7 ranker | 0.4552 | — | — |
| 20 organizations — local Qwen v2 | C + P (Recall@20) | 0.1443 | 0.1848 | — |

**Oracle-order ceiling with frozen v2 groups:** 6,969/9,980 = **69.83%**. Ranking alone cannot reach the 80% target.

**Candidate recall (full rule):** 37,018/159,186,107 = **0.0233%** — the dominant bottleneck. The 99% candidate-recall target is not met and is mathematically impossible under the current 20-neighbor cap.

**Structural end-to-end ceiling:** 9,063/9,980 = **90.81%** (under current exclusion and 100-alert component cap). The proposed 95% target is structurally unachievable under current rules.

---

## Iteration summary

| Iteration | Key result |
|---|---|
| Full offline baseline | Candidate recall 0.0233%; BM25-like Recall@20 0.1364 |
| Matched ranking extension | Trained ranker P@10 0.2351 vs 0.1971; Recall@20 gain uncertain (CI includes zero) |
| Learned pair grouping (57 queues) | Recall@20 **0.3179** vs 0.1678; pair F1 fell; oracle ceiling 58.51% |
| Entity/time sensitivity (499 queues) | Recall@20 **0.3095** vs 0.1413; pair precision improved; F1 fell |
| Entity/time pair model v2 | Recall@20 **0.3397**; pair precision 0.9041; ceiling 69.83% |
| Group priority v4 ranker | Recall@20 **0.4223** (all-499); **0.4106** (135 training-disjoint) |
| Hard-negative v6 ranker | Recall@20 **0.4399** all-499; no training-disjoint gain over v4 |
| Descriptor-aware v7 ranker (frozen) | Recall@20 **0.4982** all-499; **0.4552** (135 outside training) |
| Specialist v8 control | No development gain; retained v7 scores |
| Adaptive links v9 control | Tiny recall gain reduced P@10 and ceiling; v2 groups retained |
| Learned group-merge v10 | No actual merge met purity/recall gates; output identical to v2 + v7 |
| Component ablation | Entity route: −5.49 pp Recall@20 when removed; descriptor/technique drops uncertain |
| Bounded matched Qwen controls | Qwen C+P Recall@20 0.1443 vs singleton/rarity 0.1600; no C/P/V superiority shown |

Full chronology: [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md). Exhibition-ready result table: [EXHIBITION_METRICS_BRIEF_20261115.md](submission/EXHIBITION_METRICS_BRIEF_20261115.md).

---

## Repository map

| Path | Purpose |
|---|---|
| `src/` | Validation, preprocessing, baselines, C/P/V agents, isolated evaluators, offline and local-model runners |
| `configs/` | Field policies (`field_policy.yaml` — official allowlist empty; `empirical_field_policy.yaml` — local-only 5-descriptor assumption), schemas, protocol, and method settings |
| `data/raw/`, `data/derived/` | Local GUIDE inputs and restricted records — **ignored by Git** |
| `fixtures/` | Fictional checks and frozen expected outputs |
| `outputs/` | Versioned metrics and run manifests; historical outputs retained |
| `phases_outputs/` | Dated phase records, amendments, and gate decisions |
| `submission/` | Report, figures, verification, and reproduction material |
| `dashboard/` | Saved aggregate viewer (`index.html`) and separate fictional playback (`simulation.html`) |

Historical phase specs remain at the repository root. Run reports remain inside their versioned `outputs/` subdirectories.

---

## Run and inspect

**Prerequisites:** Python 3.12 standard library (all phases); `matplotlib==3.11.2`, `numpy==2.5.4` for figures.

```powershell
# Verify package integrity
.\.venv\Scripts\python.exe -m submission.verify_package

# Aggregate frozen local call timing
.\.venv\Scripts\python.exe -m submission.measure_local_operations

# Serve the research dashboard locally
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

- `http://127.0.0.1:8765/` — saved aggregate metrics viewer
- `http://127.0.0.1:8765/simulation.html` — clearly labelled fictional event replay

For a full offline and bounded local-model run, follow [REPRODUCE.md](submission/REPRODUCE.md). The Qwen stage can take **hours on CPU**. No hosted model calls are authorized by the current field policy.

---

## Pipeline overview

```
GUIDE_Test.csv (4,147,992 evidence rows)
        │
        ▼
  [Preprocessing]  ─── composite key deduplication, restricted evidence ledger,
        │               evaluator-only labels, field-gate enforcement
        ▼
  [Candidate generation] ─── exact Category + ATT&CK-technique ≤20 neighbors
        │                     (entity/time routes: local-only research amendment)
        ▼
  [Agent C — Correlate]  ─── LINK / NO_LINK / UNSURE per pair; evidence citations
        │
        ▼
  [Agent P — Prioritize] ─── uncalibrated group scores; top-20 recovery order
        │
        ▼
  [Agent V — Verify]     ─── PASS / REVISE / REVIEW; citation support check
        │
        ▼
  [Evaluator]  ─── isolated; reads incident membership and queue ranks after prediction freeze
                   Pair F1, P@10, Recall@20, nDCG@20, oracle-order ceiling
```

---

## Key references in the submission

| Document | Contents |
|---|---|
| [FINAL_REPORT.md](submission/FINAL_REPORT.md) | Full Phase 3 implementation report with numerators, denominators, figures, and limitations |
| [EXHIBITION_METRICS_BRIEF_20261115.md](submission/EXHIBITION_METRICS_BRIEF_20261115.md) | Stage-separated result table and suggested slide wording |
| [INDEPENDENT_COMPONENT_ABLATION_20261115.md](submission/INDEPENDENT_COMPONENT_ABLATION_20261115.md) | Candidate-route, grouping, and ranking ablations with matched denominators |
| [PERFORMANCE_BASELINE_STUDY.md](submission/PERFORMANCE_BASELINE_STUDY.md) | 334/135 organization-split matched ranking study |
| [DATA_AND_CLAIM_AUDIT.md](submission/DATA_AND_CLAIM_AUDIT.md) | Schema, evidence-row grain, composite keys, field gates, and provenance hashes |
| [REPRODUCE.md](submission/REPRODUCE.md) | Commands, immutable run IDs, and output paths |
| [KNOWN_LIMITATIONS.md](submission/KNOWN_LIMITATIONS.md) | 11 open gates; prevents any claim of 95% recovery or operational readiness |
| [FRESH_COHORT_AND_SHADOW_GATE.md](submission/FRESH_COHORT_AND_SHADOW_GATE.md) | What is still required for a confirmatory study and live evaluation |

---

## Submission status

This is an **exploratory, partial Phase 3 submission**.

> [!WARNING]
> **Do not claim:** 95% recovery, confirmatory model superiority, production/operational SOC readiness, or military certification. No retrospective score increase on previously accessed GUIDE_Test labels satisfies any of these claims.

Outstanding requirements:
- [ ] Fresh, sealed, untouched ranked cohort for confirmatory evaluation
- [ ] Official point-in-time model-input field allowlist (currently empty)
- [ ] Source-validated alert membership rule (70,702 ambiguous composite keys unresolved)
- [ ] Matched B0–B4 / C / P / V held-out comparison with equal candidate and evidence budgets
- [ ] Blinded citation review and analyst adjudication
- [ ] Shadow-mode SOC pilot (live arrival rates, per-alert latency p50/p95, sustained throughput, false-merge impact)

The [delivery checklist](submission/DELIVERY_CHECKLIST.md) maps available artifacts to Phase 3 assignment requirements.

---

## References

- [Microsoft GUIDE dataset paper](https://arxiv.org/abs/2407.09017)
- [Adaptive Incident Prioritization paper](https://arxiv.org/abs/2607.16963)
- [Local methodology and implementation context](CONTEXT.md)
