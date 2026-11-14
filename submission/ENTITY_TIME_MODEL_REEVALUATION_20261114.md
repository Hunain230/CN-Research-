# Entity/time model re-evaluation

**Date:** 2026-11-14. This is an additive exploratory study. The Phase 3 final report and PDF were not changed. All 499 GUIDE_Test queues and their labels were previously accessed during this project. The within-run training/development/evaluation separation improves the method audit but cannot create an independent confirmatory test.

## What the failure diagnostic showed

The [evaluator-only candidate/group diagnostic](../outputs/submission_full_candidate_bound_20261114_v1.json), using the frozen [full entity/time candidate route](../outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json), found **8,638/9,980** expert top-20 labels whose alerts have an oracle same-incident candidate-connected component covering at least 80% of that gold incident. This **86.55% candidate-connectivity upper bound** assumes perfect link decisions and ignores group purity. It is not achieved candidate pair recall or model Recall@20. The earlier observed groups made 6,143/9,980 labels recoverable with oracle ordering. Of 9,980 labels, 855 lacked an unambiguous in-scope alert; 2,379 were split below 80% completeness and 603 were in an impure group under that earlier method. The current candidate graph leaves room for better grouping, but the missing-evidence and size-cap constraints remain.

## New model and frozen evaluation

The [v2 pair model](../src/submission_entity_time_pair_v2.py) added shared entity type, entity rarity, timestamp gap, and candidate-route features to the five descriptor-overlap features. It trained on **334 historical training organizations** and 31,294 positive plus 92,466 negative sampled candidate pairs. No validation or holdout membership was read during fitting. A separate [42-organization development calibration](../outputs/submission_entity_time_pair_v2_20261114_v1/calibration.json) selected a **0.75** pair threshold by macro Recall@20 among six prespecified thresholds, with the 100-alert component cap retained. The full predictor then froze all 499 organization predictions before the separate evaluator opened their membership and expert ranks. The [fit freeze](../outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json), [prediction freeze](../outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json), [aggregate metrics](../outputs/submission_entity_time_pair_v2_20261114_v1/metrics.json), and [run manifest](../outputs/submission_entity_time_pair_v2_20261114_v1/run_manifest.json) record the lineage.

| Matched measure on all 499 queues | Earlier entity/time rule | V2 entity/time pair model |
|---|---:|---:|
| End-to-end Recall@20 macro | 0.3095 | **0.3397** |
| P@10 macro | 0.3860 | **0.4233** |
| nDCG@20 macro | 0.2816 | **0.3198** |
| Pair precision micro | 0.2157 | **0.9041** |
| Pair recall micro | 0.00122 | **0.00170** |
| Pair F1 micro | 0.00243 | **0.00338** |
| Pair false positives | 705,768 | **28,606** |
| Top-20 labels recoverable with oracle ordering of the observed groups | 6,143/9,980 (61.55%) | **6,969/9,980 (69.83%)** |

The candidate set is **identical** in the two rows: 1,942,648 pairs with 699,790 of 159,186,107 positive pairs (0.4396% micro candidate pair recall). On the 135 organizations outside both models' training split, v2 versus earlier-rule Recall@20 is **0.3420 versus 0.3085**, paired difference **+0.0336** with descriptive organization-bootstrap 95% interval **[+0.0211, +0.0465]**. On the previously exposed 68 holdout organizations, the values are **0.3902 versus 0.3538**. These intervals describe this exposed sample; they do not support a fresh p-value or independent generalization claim. The v2 full prediction pass took 101.5 seconds with peak process RSS about 522 MB after the label-free projection was built. These are retrospective batch diagnostics, not live SOC latency.

## Component-cap sensitivity and decision

An additional [development-only threshold/cap study](../outputs/submission_component_cap_calibration_20261114_v1.json) chose threshold 0.5 and a 10-alert component cap. Its frozen [v3 run](../outputs/submission_entity_time_cap_v3_20261114_v1/metrics.json) reached 0.3415 Recall@20 on all 499, versus 0.3397 for v2, but the paired interval **[-0.0051, +0.0087] includes zero**. It was slightly worse on the 68 historical holdout queues (0.3877 versus 0.3902), pair precision fell from 0.9041 to 0.6201, and the observed grouping ceiling fell from 69.83% to 66.68%. The small aggregate recall difference does not justify replacing v2. V3 remains a recorded negative tradeoff.

The selected method for a **future untouched cohort** is therefore v2, frozen in the [prospective contract](../outputs/future_cohort_study_contract_20261114_v2.json). Its 69.83% observed-group oracle-order ceiling means **80% absolute end-to-end Recall@20 was not achieved and cannot be achieved by reranking those exact groups**. Even the 86.55% candidate-connectivity bound would require near-perfect linking, purity, and ranking to reach 80%. Further tuning on these exposed labels would weaken a publication claim. A new expert-ranked queue cohort and point-in-time evidence-field confirmation are required before a confirmatory comparison. The [field and shadow-mode gate](FRESH_COHORT_AND_SHADOW_GATE.md) remains open.

## Reproduce with a new run ID

The fit and calibration artifacts are frozen. For a new prediction/evaluation of the v2 method in this checkout:

```powershell
.\.venv\Scripts\python.exe -m src.submission_entity_time_pair_v2 self-test
.\.venv\Scripts\python.exe -m src.submission_entity_time_pair_v2 predict --run-id submission_entity_time_pair_v2_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_entity_time_pair_v2 evaluate --run-id submission_entity_time_pair_v2_NEW_ID
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_entity_time_pair_v2_NEW_ID
```

The code expects the existing frozen training model and calibration under its recorded run ID. Full retraining needs versioned paths in an isolated checkout; do not overwrite historical artifacts.
