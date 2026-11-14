# Priority, grouping, candidate, and source-scope follow-up

**Status:** exploratory development study on 2026-11-14. Earlier GUIDE_Test labels had been accessed in this project. The final Phase 3 report/PDF and historical outputs were not revised. The [prior iteration](INCIDENT_MISS_AND_PRIORITY_ITERATION_20261114.md) remains the selected v2-group/v4-ranker reference.

## Hard-negative and singleton priority study

The [v6 priority experiment](../src/submission_priority_focus_v6.py) kept all v2 groups fixed and trained three variants on the 334 historical training organizations: hard-negative weighting, singleton-positive weighting, and both at stronger weights. Its prediction stage read labels from the 67 development organizations to select a variant by macro Recall@20 while requiring P@10 at least as high as v4. The **hard-negative** variant won development selection; all 499 scores were then [frozen](../outputs/submission_priority_focus_v6_20261114_v1/prediction_freeze.json) before the separate evaluator read historical holdout labels. The [matched metrics](../outputs/submission_priority_focus_v6_20261114_v1/metrics.json) show:

| Same frozen v2 groups | V4 selected ranker | V6 hard-negative ranker |
|---|---:|---:|
| 67 development queues: Recall@20 | 0.3507 | 0.3568 |
| All 499 descriptive: Recall@20 | 0.4223 | 0.4399 |
| All 499 descriptive: P@10 | 0.5284 | 0.5593 |
| All 499 descriptive: nDCG@20 | 0.4162 | 0.4266 |
| 135 training-disjoint queues: Recall@20 | 0.4106 | 0.4106 |
| 68 historically exposed holdout queues: Recall@20 | **0.4697** | 0.4636 |

The training-disjoint paired Recall@20 difference is approximately zero, with descriptive 95% interval **[-0.0185, +0.0174]**. The all-499 gain includes the 334 model-training organizations. V6 is a negative generalization tradeoff and does **not** replace v4 in the [prospective method contract](../outputs/future_cohort_study_contract_20261114_v3.json). Pair and group metrics are unchanged because no groups moved.

## Multi-alert group merge test

The [development-only group experiment](../outputs/submission_development_group_merge_20261114_v1.json) examined frozen v2 groups on 42 queues. It proposed merges between small components only when at least two or three cross-group candidate edges shared a rare entity and agreed on category or technique, with a 100-alert cap and a minimum 0.80 pair-precision gate. The baseline Recall@20 was **0.3590**. All three merge variants reached **0.3572**, although pair F1 improved in two variants. The predeclared selection rule retained **base v2 grouping**. No holdout or all-499 merge run was launched.

## Candidate expansion cost

The [development-only candidate study](../outputs/submission_development_candidate_expansion_20261114_v1.json) varied nearest neighbors and time windows on the same 42 queues. Candidate-oracle connectivity assumes perfect link decisions and ignores purity and ranking.

| Candidate setting | Pairs | Oracle-connected top-20 labels / 840 |
|---|---:|---:|
| Current: 5 neighbors, 48h entity, 1h technique | 23,397 | 715 (85.12%) |
| Moderate: 10 neighbors, 72h entity, 2h technique | 34,234 | 716 (85.24%) |
| Wide: 20 neighbors, 96h entity, 4h technique | 49,943 | 718 (85.48%) |

The widest setting more than doubled candidate pairs for only **3 additional oracle-connectable labels** in these development queues. Candidate generation time alone was small; model scoring and downstream review costs were not included. The current route remains selected. These development numbers do not revise the separate all-499 86.55% optimistic candidate bound.

## Excluded alerts and rank-scope provenance

The [ambiguous-key provenance audit](../outputs/submission_ambiguous_provenance_audit_20261114_v1.json) confirmed 70,702 composite `(OrgId, AlertId)` keys with multiple incident assignments. Source row ordinals locate the evidence rows but do not provide a unique prediction-time assignment. We therefore did not assign those alerts using evaluation labels.
All 70,702 collisions share a single timestamp, detector, title, category, and technique value at the alert-key level, so those visible fields cannot resolve the assignment. The source `Id` distinguishes incident assignments but is evaluator-only and cannot be used as a model feature.

The [raw rank-scope audit](../outputs/submission_absent_rank_scope_audit_20261114_v1.json) checked every expert top-20 `(OrgId, IncidentId)` pair against the raw GUIDE_Test file. Of 9,980 labels, **9,125** have at least one unambiguous in-scope alert. The other **855** are absent from the raw file's incident pairs entirely; none is recovered by inspecting ambiguous-key assignments. This is a source-scope mismatch requiring a matching queue snapshot or alert export, not a labeling shortcut. **All 9,980 labels remain in the Recall@20 denominator.**

## Decision and remaining gates

Keep v2 grouping plus v4 priority ranking as the frozen exploratory method. Its all-499 Recall@20 is **42.23%**, far below 80%. Larger candidate windows, constrained merges, and hard-negative ranking did not demonstrate a reliable training-disjoint Recall@20 gain over that method in these tests. The [field-timing assessment](POINT_IN_TIME_EVIDENCE_STATUS_20261114.md) remains unresolved. A new untouched expert-ranked cohort with a matching alert snapshot and evidence-arrival ledger is needed before a confirmatory result or operational SOC claim.
