# Phase 6 correlation diagnostic — ambiguity-excluded

**Classification:** `exploratory_ambiguity_excluded_local_correlation_diagnostic`  
**Organizations:** 30  
**Unambiguous alert keys:** 30,692  
**Candidate pairs:** 194,296 / 67,048,813 within-org pairs  
**Positive gold pairs:** 6,142,793

## Pair metrics

| Metric | Micro | Macro organization mean [95% bootstrap CI] |
|---|---:|---:|
| Candidate-set precision | 0.267010 | 0.109267 [0.035194, 0.201889] |
| Candidate-set recall | 0.008446 | 0.866667 [0.733333, 0.966667] |
| Full-positive-pair recall | 0.008446 | 0.253478 [0.152522, 0.363327] |
| Full-positive-pair F1 | 0.016373 | 0.060273 [0.019724, 0.124542] |
| Candidate-generation coverage | 0.002898 | 0.061963 [0.035874, 0.091937] |

## Method and limits

For each unambiguous alert, candidates are limited to same-organization alerts sharing at least one ATT&CK technique. Jaccard similarity over the five assumed-safe descriptor fields selects at most 20 neighbors per alert. Every generated candidate is predicted LINK; all other pairs in the exhaustive within-organization universe are implicit NO_LINK. Time windows are omitted because timestamps are privacy-perturbed.

All 70,702 conflicting composite alert keys are excluded; this diagnostic covers only unambiguous alert keys in the 30 frozen test organizations. It is post-test-access and exploratory. It is not a full-dataset correlation result, joint prioritization result, or LLM evaluation. Fields remain project assumptions and no external calls were made.

Organization is the bootstrap unit (10,000 resamples); no hypothesis tests are reported.
