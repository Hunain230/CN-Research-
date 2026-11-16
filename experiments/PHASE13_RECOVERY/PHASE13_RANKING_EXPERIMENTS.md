# Ranking experiments on fixed v2 groups

The exact existing tie-aware rank evaluator was rerun on five frozen vectors: v7, 25/50/75% child40 blends, and child40 alone. All use the **same 370,850 frozen groups** and 499 queues, so group recoverability (6,969), grouped-pair TP/FP (269,832/28,606), and mixed groups (4,841) are identical. No ranker was retrained.

| Frozen ranker | Incident Recall@20 | P@10 | nDCG@20 |
| --- | ---: | ---: | ---: |
| v7 | 4,972/9,980 (49.82%) | 61.5832% | 0.437101 |
| blend_0.25 | 5,035/9,980 (50.45%) | 63.5772% | 0.446895 |
| blend_0.5 | 5,092/9,980 (51.03%) | 64.3053% | 0.458297 |
| blend_0.75 | 5,066/9,980 (50.77%) | 63.8778% | 0.469747 |
| child40 | 5,008/9,980 (50.18%) | 62.7620% | 0.474352 |

The 50/50 blend gives 5,092 recovered labels, +26 versus E1, and P@10 64.3053% versus 63.8778%, but nDCG@20 falls to 0.458297 from 0.469747. This **full-cohort** advantage is retrospective; [the original sprint selection](../../24H_PERFORMANCE_SPRINT/README.md) chose 75/25 because validation Recall@20 was 45.04% versus 44.48% for 50/50, and the previously exposed holdout also favored 75/25. Selecting 50/50 now from the full GUIDE_Test outcome would violate the earlier selection rule. E1 remains the defensible frozen comparator. No ranking result breaks the 69.83% fixed-group recoverability ceiling or approaches 80% Recall@20.
