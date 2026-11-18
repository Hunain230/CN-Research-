# Phase 38 final report — integrated recall NO-GO

Phase 37 found no new independently supplied telemetry and no validated reconstruction improvement. Accordingly Phase 38 kept the Phase 32 endpoint-fallback +1 C/V and grouping unchanged; there was no reconstruction integration (Candidates A or C). One predeclared Candidate B tested hard-negative pairwise ranking using only prior receiver-visible features: source depth, source count, severity, criticality, event diversity, group size, time span, verified unions, original observations, distinct accepted roots, accepted family coverage, verified alert coverage and claim delay. The first ten ranks and all groups were fixed. A fresh eight-queue train split supplied 780 positive/negative pairs; a separate 15-queue development cohort was evaluated once with the original Phase 15 evaluator.

| Phase 38 fresh development | Frozen matched baseline | Candidate B | Requirement |
|---|---:|---:|---:|
| Incident Recall@20 | **263/300 (87.67%)** | **262/300 (87.33%)** | ≥270/300 and above baseline |
| Recoverability | 279/300 (93.00%) | 279/300 (93.00%) | Non-inferior; 95% preferred |
| P@10 | 112/150 (74.67%) | 112/150 (74.67%) | Matched non-inferiority; global 76.67% target also missed |
| Pair precision | 100% | 100% | ≥99% |
| False grouped pairs / mixed groups | 0 / 0 | 0 / 0 | Zero additional |

The candidate gained four recalls and lost five relative to its matched baseline. It left **17 recoverable incidents outside the top 20** and **21 unrecoverable incidents**. Three queues declined in recall; no queue regressed on grouping, recoverability, P@10, false pairs, or mixed groups. The predeclared recall and baseline-improvement gates failed, so **Phase 38 is NO-GO and no fresh holdout was generated or opened**. Phase 33's **260/300 (86.67%)** remains the strongest confirmed synthetic holdout result; Phase 38's 87.33% is development-only on a different cohort.

Pairwise training loss was **0.189** on 780 training pairs and **0.221** on 1,452 development pairs; pairwise ordering accuracy was 92.18% versus 90.43%. The 0.032 loss gap is modest, while official recall regressed: the pairwise objective and top-20 incident recall do not align perfectly. A diagnostic 2/4/8-queue learning curve improved as more training data were used, so these measurements do not prove that a more complex model is needed. Post-hoc coefficient-zeroing in `FEATURE_ABLATION.csv` showed frozen source score, mean severity, and verified unions were influential for pairwise loss; these are **not** official Recall@20 ablations or candidate-selection trials. `RANKING_ERROR_ANALYSIS.csv`, `RECONSTRUCTION_ERROR_ANALYSIS.csv`, and `SCENARIO_DIAGNOSTICS.csv` record per-incident and scenario-family diagnostics using evaluator truth offline.

The separately reported Phase 37 stress tests show that missing identity or network telemetry collapses recoverability in this synthetic generator, and delayed claims reduce it. Post-hoc Phase 38 ranking on that **already opened development cohort** did not improve the original-evidence condition (254 versus 257 recalls), although it gained two recalls under each of the common-root and contradiction stress conditions; those are diagnostic measurements, not generalization claims. Derived copies remained unhelpful. No evidence was manufactured to bridge fragments, and abstention/verification rules remained intact.

Historical hashes, split isolation, prediction seals, point-in-time eligibility, provenance restrictions and queue-level false-merge checks passed. Synthetic root names cannot prove real-world independence. No production-readiness claim follows from these results.
