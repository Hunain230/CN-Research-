# Phase 13 repository and dependency audit

**E1 reproduced exactly** with the original Phase 10 evaluator and reconstruct code copied byte-for-byte into Phase 13, an identical config, and 500 read-only hard links to the frozen prediction files. The copied evaluator wrote only inside Phase 13. Its E1 method object equals the Phase 10 object field-for-field: 499 queues, 400,039 eligible alerts, 9,980 expert top-20 labels, 5,066 recovered, 6,969 recoverable, P@10 63.877756%, nDCG@20 0.469747097, grouped-pair TP 269,832, FP 28,606, mixed groups 4,841. Exact input/code hashes are in `PHASE13_INPUT_HASHES.json`; git HEAD at audit was `cd6efb7377d69c04386516a7574396208abd110b`. No frozen file was overwritten.

## Dependency map

| Metric/artifact | Producer and inputs |
| --- | --- |
| Eligible alert scope (400,039) and 499 queues | `data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl`, GUIDE preparation and ambiguity exclusions |
| Candidate edges (1,942,648) | `src/submission_full_entity_time.py` baseline Category+technique, bounded entity and technique time-neighbor routes; frozen candidate files and hashes |
| Pair probabilities | `src/submission_entity_time_pair_v2.py` 30-feature fitted gradient boosting model, reconstructed by `src/submission_group_merge_v10_v2.py:load_queue` |
| v2 groups | Pair score ≥0.75, descending order, 100-alert union cap; frozen `v2_*.pkl` |
| v7 and child40 scores | Frozen descriptor ranker and hard-negative ranker outputs; percentile fusion in `src/sprint_rank_fusion_v1.py` |
| E1 ranking | 75% child40 + 25% v7, frozen 499 queue score vectors |
| Incident Recall@20, P@10, nDCG@20 | `src/submission_full_guide.py:tie_aware_ranking` and `src/submission_group_merge_v10_v2.py:pair_group_metrics`; evaluator-only ranks from `src/guide_rerun_v2.py` |
| Group recoverability and cascade | 80% completeness and 80% purity in `src/submission_fragment_aware_v1.py:incident_outcomes`, evaluator truth from `src/offline_joint_comparison.py:read_truth` |
| Pair TP/FP, mixed groups | `pair_group_metrics` and `incident_outcomes` in `experiments/PHASE10_FRAGMENT_RECONSTRUCTION/evaluate.py` |
| Verification | `src/agents/verification.py` delegates to a provider; Phase 10 E4 applies offline label-blind consistency veto in `reconstruct.py`. Neither has original source-observation IDs or evidence-available time in GUIDE. |

The Phase 13 evaluator independently recomputed C pair/group counts and checked all four E1 totals against the original metric implementation. New C thresholds remain C-only; no ranking metric is inferred for changed groups. The Phase 13 error table uses opaque queue/incident keys and carries no raw entity values.

## Policy and history

`configs/field_policy.yaml` has `approved_model_fields: []`. Entity/time/descriptor experiments are local retrospective sensitivity only under `configs/entity_time_sensitivity_policy.yaml`. Evaluator-only fields include `IncidentId`, `QueueRank`, grades and outcomes. GUIDE_Test labels have been exposed, so no Phase 13 GUIDE result is independent confirmation. Prior Phase 9E candidate expansion and Phase 9G hard-negative model failed; Phase 10 E2–E5 fragment reconstruction failed the safety/recovery combination. All previous experiment configs remain in `configs/` and prior experiment directories; Phase 13 changes are isolated here.
