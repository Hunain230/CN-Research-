# Phase 6 tie-aware priority evaluation

**Classification:** `exploratory_tie_aware_reanalysis_after_failed_evaluator_attempt`  
**Organizations:** 30  
**Candidates:** 14,139  
**Gold top-20 labels:** 600

Metrics take the expectation over uniformly permuted orderings within each equal-score block. This prevents the opaque identifier used only to serialize output rows from deciding cut-off relevance.

## Results

| Condition | P@10 | Recall@20 | nDCG@20 (rank 1 highest) | nDCG@20 (rank 20 highest) |
|---|---:|---:|---:|---:|
| leave_out_Category | 0.4700 | 0.3469 | 0.3660 | 0.1087 |
| leave_out_DetectorId | 0.4717 | 0.3366 | 0.4424 | 0.0919 |
| leave_out_EntityType | 0.4977 | 0.3422 | 0.4211 | 0.1118 |
| leave_out_EvidenceRole | 0.4822 | 0.3411 | 0.3837 | 0.1182 |
| leave_out_MitreTechniques | 0.4033 | 0.2897 | 0.2801 | 0.1338 |
| mask_20_seed_41 | 0.4212 | 0.3044 | 0.3561 | 0.0868 |
| mask_20_seed_42 | 0.4363 | 0.3015 | 0.3258 | 0.1089 |
| mask_20_seed_43 | 0.3856 | 0.2902 | 0.3849 | 0.0731 |
| mask_20_seed_44 | 0.3426 | 0.2544 | 0.2845 | 0.0765 |
| mask_20_seed_45 | 0.3625 | 0.2597 | 0.2635 | 0.1043 |
| mask_40_seed_41 | 0.3383 | 0.2416 | 0.2293 | 0.0936 |
| mask_40_seed_42 | 0.3294 | 0.2384 | 0.2138 | 0.0909 |
| mask_40_seed_43 | 0.2935 | 0.2309 | 0.2727 | 0.0614 |
| mask_40_seed_44 | 0.2958 | 0.2462 | 0.2548 | 0.0796 |
| mask_40_seed_45 | 0.3126 | 0.2384 | 0.1675 | 0.1004 |
| primary | 0.4622 | 0.3392 | 0.3924 | 0.1153 |

## Tie impact

Primary predictions had top-20 score ties in 30 of 30 organizations and top-10 ties in 30 organizations. 497 of 600 top-20 slots were in tied score blocks.

## Disclosure and limits

Initial evaluator used opaque key ordering inside equal scores. Audit found many cutoff ties. No predictor, configuration, feature, or score changed; all 16 frozen prediction files are byte-identical across v1/v2.

This is a post-access metric correction, so treat the tie-aware results as exploratory. The frozen scores and all prediction files are unchanged. It remains an oracle-group ranking ceiling on the assumed local candidate universe; it is not end-to-end correlation or an LLM comparison. The primary nDCG assumes rank 1 is highest; the inverse direction is reported because the publisher's numeric direction remains unresolved.

The governing metric amendment is [`metric_tie_amendment.md`](../../../../phases_outputs/metric_tie_amendment.md); prior access history is in [`test_evaluation_access_log.md`](../../../../phases_outputs/test_evaluation_access_log.md).

95% organization-bootstrap intervals and paired condition differences are in `metrics.json`. No p-values are reported.

## Figures

![Precision@10 and Recall@20 with organization-bootstrap intervals](figures/priority_precision_recall.png)

![nDCG@20 sensitivity to numeric rank direction](figures/priority_ndcg_direction_sensitivity.png)
