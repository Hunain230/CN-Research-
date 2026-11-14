# Group-level merge model: matched offline study

## Question and design

The existing v2 groups plus v7 offline ranker reach **49.82% Recall@20** across 499 GUIDE_Test queues, while ideal ordering of those exact groups is capped at **69.83%**. This study tested whether a learned decision between two *predicted groups* could recover split incidents without losing pair precision, adding false merges, reducing P@10, or lowering recoverable-label coverage.

The [group-merge implementation](../src/submission_group_merge_v10_v2.py) starts from frozen v2 groups and the same 1,942,648 candidate alert pairs. It proposes cross-group pairs where the frozen pair model gives at least 0.4 probability. For each proposed group pair, it summarizes pair confidence, independent alert support, group sizes, shared entity rarity, five descriptor overlaps, and time separation. A gradient-boosted classifier was fitted only on 334 historical training queues. Its [fit freeze](../outputs/submission_group_merge_v10_20261114_v2/fit_freeze.json) records 43,133 sampled group-pair examples: 16,876 positive and 26,257 negative. Positive targets required both groups to have at least 80% majority membership in the same incident. The method did not use membership or rank labels as prediction features.

Six merge threshold/cap settings were tested on 42 development queues of at most 500 alerts. The prespecified selection required a **strict gain in both Recall@20 and recoverable top-20 labels**, with no decrease in pair precision or P@10 and no increase in false-positive pairs. The [calibration table](../outputs/submission_group_merge_v10_20261114_v2/calibration.json) selected **base groups**. A first, higher-threshold grid was retained as a [negative pilot record](../outputs/submission_group_merge_v10_20261114_v1/calibration.json); it made no group merges on the same development queues. The final v2 grid correctly requires an actual recoverability gain and uses frozen v7 scores whenever groups do not change.

## Development results

| 42 development queues | Recall@20 | P@10 | Pair precision | False-positive pairs | Recoverable labels / 840 |
|---|---:|---:|---:|---:|---:|
| Base v2 groups + v7 ranker | **47.62%** | 58.33% | **87.53%** | **340** | **610** |
| Merge score ≥0.5; cap 4 alerts | 45.83% | 57.14% | 81.99% | 566 | 584 |
| Merge score ≥0.6; cap 4 alerts | 47.38% | 57.86% | 86.30% | 384 | 608 |
| Merge score ≥0.7; cap 4 alerts | 47.50% | 58.57% | 87.15% | 353 | 610 |

The lower settings joined more true alert pairs, but also joined unrelated alerts. At 0.5, pair F1 increased from 0.0723 to 0.0776 while end-to-end Recall@20, purity, P@10, and ideal-order recoverability all fell. The 0.7 setting slightly improved P@10 but added 13 false-positive pairs and did not increase recoverable labels. None satisfied the selection rule.

## Frozen all-queue comparison

The selected base rule was run through the full prediction and separate evaluation stages on all **499 ranked organizations, 400,039 unambiguous alerts, and 1,942,648 candidate pairs**. The [prediction freeze](../outputs/submission_group_merge_v10_20261114_v2/prediction_freeze.json), [metrics](../outputs/submission_group_merge_v10_20261114_v2/metrics.json), and [run manifest](../outputs/submission_group_merge_v10_20261114_v2/run_manifest.json) hash the 499 frozen queue outputs and method artifacts. The retrospective full pass took **115.1 seconds**, with peak process RSS **669 MB**. Those measurements include candidate scoring and group-pair proposal work despite the base rule being selected; they are batch diagnostics, not live SOC latency.

| Matched all-499 measure | Selected group-merge rule | Frozen v2 groups + v7 ranker |
|---|---:|---:|
| End-to-end Recall@20, macro | 49.82% | 49.82% |
| P@10, macro | 61.58% | 61.58% |
| Pair precision, micro | 90.41% | 90.41% |
| Pair false positives | 28,606 | 28,606 |
| Recoverable top-20 labels with ideal ordering | 6,969/9,980 (69.83%) | 6,969/9,980 (69.83%) |

The full selected output is **identical to the reference** because the learned merge rule failed the development gates. The 135 queues outside model training remain at **45.52% Recall@20**; the 68 historically exposed holdout queues remain at **49.34%**. No grouping performance gain is claimed.

## Paper interpretation

This is a reproducible **negative control** that tests a specific route for improving the offline model. A paper can list the matched all-499 metrics and this development tradeoff as *exploratory retrospective findings*, with the training, selection, and denominator details above. The paper should not describe the merge model as improving performance, claim C/P/V superiority from this statistical study, or treat the previously exposed GUIDE_Test labels as an untouched test. The five descriptors and entity/time evidence still lack confirmed point-in-time operational availability. A new sealed ranked cohort remains necessary for a confirmatory comparison, and later shadow-mode measurements are needed for operational SOC claims. The final report and PDF were not changed.
