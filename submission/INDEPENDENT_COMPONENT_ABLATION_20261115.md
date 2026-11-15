# Candidate, grouping, and ranking component ablations

**Status:** exploratory retrospective study on previously accessed GUIDE_Test labels. This record extends the frozen offline baseline without changing the final Phase 3 report or PDF. The selected baseline remains **v2 grouping + v7 ranking** on 499 organization queues and 400,039 unambiguous alerts.

## Candidate-route ablation: fitted models held fixed

The [route-ablation implementation](../src/submission_candidate_route_ablation_v11.py) removed one candidate route at a time from the label-blind candidate graph. It kept the fitted v2 pair model, 0.75 link threshold, grouping algorithm, and v7 ranking method fixed; it recomputed scores when the proposed groups changed. Flags identifying the removed route were removed from the pair-model input as well. All 499 variant predictions were [frozen](../outputs/submission_candidate_route_ablation_v11_20261115_v1/prediction_freeze.json) before the separate evaluator read incident memberships and top-20 ranks. [Metrics](../outputs/submission_candidate_route_ablation_v11_20261115_v1/metrics.json) and the [run manifest](../outputs/submission_candidate_route_ablation_v11_20261115_v1/run_manifest.json) preserve the matched comparison.

| Candidate routes on all 499 queues | Pairs | Candidate-connected top-20 / 9,980 | Recoverable after grouping / 9,980 | Recall@20 | P@10 | Pair precision |
|---|---:|---:|---:|---:|---:|---:|
| All routes: frozen v2 + v7 baseline | 1,942,648 | **8,638 (86.55%)** | 6,969 (69.83%) | 49.82% | 61.58% | 90.41% |
| Remove descriptor route | 1,637,457 | 8,551 (85.68%) | **6,986 (70.00%)** | 49.85% | 61.90% | 89.32% |
| Remove entity route | 387,414 | 6,657 (66.70%) | 6,356 (63.69%) | 44.33% | 55.19% | 98.00% |
| Remove technique route | 1,893,668 | 8,618 (86.35%) | 6,969 (69.83%) | 49.81% | 61.66% | 90.42% |

The entity route contributes the largest observed connectivity and end-to-end gain. Its removal lowers Recall@20 by **5.49 percentage points** on all 499 queues, with a paired organization-bootstrap interval of **[-6.45, -4.58] points**; on the 135 queues outside model training the drop is **4.70 points** **[-6.30, -3.26]**. Removing the descriptor route yields a 0.03-point all-queue Recall@20 increase **[-0.14, +0.19]**, while pair precision falls by 1.09 points. This is an uncertain tradeoff, so it does not replace the frozen baseline. Removing technique has a negligible end-to-end effect under these particular routes and model settings; it should not be interpreted as evidence that technique information is generally useless, because the pair model and ranker still use technique features. Candidate-route effects are conditional on the other routes and are not additive.

The full prediction pass for four variants took **249.8 seconds**, with peak process RSS **632 MB**. These are local retrospective batch diagnostics, not live SOC latency. The full variant reuses the already frozen v2 groups and v7 scores; the evaluator reproduced its 49.82% Recall@20 and 69.83% group ceiling exactly.

## Grouping ablation: candidates and ordering method held fixed

The earlier [entity/time model study](ENTITY_TIME_MODEL_REEVALUATION_20261114.md) compares the same **1,942,648 candidates** with the same transferred ranker. Replacing the earlier entity/time rule groups with the trained v2 pair-model groups raised all-499 Recall@20 from **30.95% to 33.97%**, pair precision from **21.57% to 90.41%**, and the observed-group ideal-ordering ceiling from **61.55% to 69.83%**. Pair recall and false positives are reported in that study. This is a grouping comparison; it does not attribute the gain to candidate generation or the later v7 ranker.

The separate [learned group-merge study](GROUP_MERGE_MODEL_STUDY_20261114.md) tested further merging on development queues. No rule improved recoverability while preserving purity, false-positive pairs, and P@10, so its selected all-499 output is identical to the v2 groups. It is a negative grouping control.

## Ranking ablation: candidates and groups held fixed

On the **same frozen v2 candidates and groups**, the original v2 ordering reaches **33.97%** all-499 Recall@20. The train-only [v4 group priority model](INCIDENT_MISS_AND_PRIORITY_ITERATION_20261114.md) raises it to **42.23%**. Adding descriptor identities in [v7](DESCRIPTOR_RANKER_ITERATION_20261114.md) raises it to **49.82%**, with P@10 **61.58%** and nDCG@20 **0.4371**. On the 135 queues outside ranker training, v7 Recall@20 is **45.52%**. The v7 minus v4 all-499 paired recall difference is **+7.59 points [6.41, 8.77]**; the 135-queue difference is **+4.45 points [2.46, 6.63]**. Earlier access to GUIDE_Test labels prevents a confirmatory interpretation.

The [singleton/multi-alert specialist control](SPECIALIST_RANKER_NEGATIVE_CONTROL_20261114.md) did not improve development recall, so it retained v7 scores. No candidate or grouping metric changes when only priority scores change.

## Interpretation and next gate

These ablations separate three effects: the entity route supplies substantial candidate connectivity, v2 grouping improves purity and recoverability on the same candidates, and v7 ranking recovers more of the already recoverable groups. Their ceilings and achieved results are distinct metrics. The all-499 descriptive result includes training organizations. GUIDE_Test labels had been accessed before these studies, and entity/time evidence availability at alert creation remains unconfirmed. For a paper, present this as an exploratory component analysis with exact denominators, paired descriptive intervals, negative controls, and resource measurements. A frozen method needs a new untouched ranked cohort for a confirmatory generalization claim; live SOC claims need a later shadow-mode study.
