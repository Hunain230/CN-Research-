# Descriptor-aware group ranking: exploratory iteration

## Method and comparison

This iteration holds the 499-organization v2 candidate graph and predicted groups fixed. It compares the frozen v4 priority scores with a new group ranker on exactly those groups. The new ranker adds the identities of detector, category, ATT&CK technique, entity type, and evidence role to v4's numeric group features. A sparse logistic model was fitted on 157,072 frozen groups from 334 historical training organizations, of which 4,624 were positive top-20 recovery targets. Its score was blended with the v4 score. Among five fixed blends, a 0.75 weight on the new model maximized development Recall@20 while keeping P@10 at least as high as v4 on 67 development organizations. The scores for all 499 organizations were then frozen before the separate evaluator opened the historical holdout labels.

The method, score hashes, selection table, and 106-second local prediction wall time are in the [prediction freeze](../outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json). [Frozen metrics](../outputs/submission_descriptor_ranker_v7_20261114_v1/metrics.json) and the [run manifest](../outputs/submission_descriptor_ranker_v7_20261114_v1/run_manifest.json) identify the evaluated files. Reproduction code is [the v7 ranker](../src/submission_descriptor_ranker_v7.py). No local Qwen or hosted model was used in this iteration.

## Matched results

Scores are macro means over organizations. Recall@20 uses 20 expert labels per organization and the existing 80% completeness and purity recovery rule. P@10 and nDCG@20 use the same frozen groups and tie-aware evaluator. Intervals are 5,000 organization-level paired bootstrap resamples for v7 minus v4, in percentage points.

| Cohort | Metric | V4 | V7 | Paired difference, 95% interval |
|---|---|---:|---:|---:|
| All 499, descriptive; includes training and selection queues | Recall@20 | 42.23% | 49.82% | +7.59 [6.41, 8.77] |
| All 499 | P@10 | 52.84% | 61.58% | +8.74 [7.20, 10.27] |
| All 499 | nDCG@20 | 0.4162 | 0.4371 | +0.0209 [0.0061, 0.0349] |
| 135 outside model training; includes 67 blend-selection queues | Recall@20 | 41.06% | 45.52% | +4.45 [2.46, 6.63] |
| 135 outside model training | P@10 | 50.36% | 55.56% | +5.20 [2.48, 8.06] |
| 135 outside model training | nDCG@20 | 0.4290 | 0.4165 | -0.0125 [-0.0403, 0.0133] |
| Historical 68 holdout queues, previously exposed in this project | Recall@20 | 46.97% | 49.34% | +2.37 [-0.14, 4.91] |
| Historical 68 holdout queues | P@10 | 56.45% | 61.03% | +4.58 [0.83, 8.41] |
| Historical 68 holdout queues | nDCG@20 | 0.4754 | 0.4389 | -0.0366 [-0.0796, 0.0035] |

## Decision and limits

V7 is the strongest *descriptive* all-499 priority result on the existing v2 groups. It improves training-disjoint Recall@20 and P@10, but the 68-queue holdout recall interval includes zero and its nDCG point estimate is lower. The method does not improve candidate recall, link accuracy, group purity, or the fixed-group oracle-order ceiling of 69.83%. Therefore 80% Recall@20 remains unattainable with these exact frozen groups, even with ideal ordering.

All GUIDE_Test labels had been accessed in earlier project work; the historical holdout is not an untouched confirmation cohort. The descriptor and entity/time evidence still lacks documented point-in-time operational approval. This is a retrospective statistical ranking improvement, not evidence of C/P/V superiority or operational SOC performance. Keep v2 grouping plus v4 ranking as the previously registered future-cohort comparator; v7 is a frozen research candidate that must be compared on a new sealed cohort before any publication performance claim. The [study contract](BASELINE_PAPER_STUDY_CONTRACT_20261114.md) and [publisher clarification request](PUBLISHER_CLARIFICATION_REQUEST_20261114.md) describe those gates. The final submission report and PDF were not revised for this iteration.
