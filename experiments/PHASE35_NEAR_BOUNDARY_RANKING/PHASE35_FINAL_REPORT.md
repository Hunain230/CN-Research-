# Phase 35 final report — NO-GO on fresh development

Phase 35 tested one narrow response to Phase 34's ten recoverable but misranked incidents. It kept the Phase 32 endpoint-fallback +1 C/V pipeline and all group decisions fixed, preserved positions 1–10 exactly, and reranked only positions 11–30 with a pairwise linear model fitted on a fresh train split. The original Phase 15 evaluator measured the matched baseline and candidate on a new 15-queue development split.

| Phase 35 fresh development | Frozen baseline | Pairwise boundary candidate | Required gate |
|---|---:|---:|---:|
| Incident Recall@20 | 258/300 (86.0%) | **258/300 (86.0%)** | ≥270/300 and above baseline |
| Recoverability | 273/300 (91.0%) | 273/300 (91.0%) | ≥255/300 and non-inferior |
| P@10 | 112/150 (74.67%) | 112/150 (74.67%) | Non-inferior |
| Grouped-pair precision | 100% | 100% | ≥90% |
| False grouped pairs | 0 | 0 | No increase |
| Mixed groups | 0 | 0 | No increase |

The new order produced three gained recalls and three lost recalls. It did not improve net recall. The 90% recall and matched-baseline improvement gates failed, so the result is **NO-GO**. No second ranker was fitted and the planned fresh holdout was not generated. The Phase 33 untouched holdout result of **260/300 = 86.67%** remains the strongest confirmed generalization result; the Phase 34 **267/300 = 89%** and Phase 35 **258/300 = 86%** are development results on different populations.

Generator validation and seven-cohort split isolation passed. Prediction seals, 179 Phase 34 historical file hashes, temporal eligibility, top-ten preservation, unchanged grouping and queue-level safety were verified after evaluation. See `DEVELOPMENT_RESULTS.csv`, `QUEUE_LEVEL_AUDIT.csv`, `CANDIDATE_COMPARISON.csv`, and the audit files in this directory. This result supports examining evidence or a more discriminating visible signal in a future predeclared study; it does not warrant opening a holdout for this candidate.
