# Incident miss audit and priority iteration

**Status:** exploratory retrospective extension, 2026-11-14. The final Phase 3 report and PDF were not changed. GUIDE_Test labels had been accessed in earlier project work; historical training/development/holdout separation does not restore an untouched confirmatory cohort.

## Where the frozen v2 method misses

The [aggregate evaluator-only audit](../outputs/submission_v2_incident_miss_audit_20261114_v1.json) classifies each of 9,980 expert top-20 labels once, using frozen [v2 groups](../outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json) and [candidate edges](../outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json):

| Primary reason | Expert labels |
|---|---:|
| Recovered under deterministic score/index order | 3,391 |
| Pure, sufficiently complete group ranked below 20 | 3,578 |
| Split by linker or component cap despite candidate connectivity | 1,451 |
| No sufficiently connected candidate component | 487 |
| Sufficiently complete group but impure | 218 |
| Absent from unambiguous alert scope | 855 |

The diagnostic uses a deterministic order to assign ranking failures. The official end-to-end Recall@20 uses tie-aware expected ordering, so its 33.97% is slightly different from the 3,391/9,980 diagnostic count. Of the 3,578 ranking misses, 3,006 are singleton incidents. Of the 1,451 linker/cap splits, 1,244 contain 2–10 alerts. This identifies two distinct development needs: priority discrimination for singletons and cleaner joining of multi-alert incidents.

## Train-only group priority model

The [v4 group priority model](../src/submission_group_ranker_v4.py) trained on **334 historical training organizations**, 157,072 frozen v2 groups, including 4,624 recoverable top-20 positive groups. It uses the existing rank score, group count and rarity score, within-queue score positions, queue size, field diversity, entity diversity, and time span. Only training-organization memberships and expert ranks were opened during fitting. All 499 v2 groups and candidates were held fixed; [v4 scores were frozen](../outputs/submission_group_ranker_v4_20261114_v1/prediction_freeze.json) before evaluation labels were read by the separate evaluator. [Metrics](../outputs/submission_group_ranker_v4_20261114_v1/metrics.json) and the [run manifest](../outputs/submission_group_ranker_v4_20261114_v1/run_manifest.json) record the comparison.

| Same v2 groups and queues | Earlier priority ranker | V4 group ranker |
|---|---:|---:|
| All 499: macro end-to-end Recall@20 | 0.3397 | **0.4223** |
| All 499: P@10 | 0.4233 | **0.5284** |
| All 499: nDCG@20 | 0.3198 | **0.4162** |
| Training-disjoint 135: Recall@20 | 0.3420 | **0.4106** |
| Previously exposed holdout 68: Recall@20 | 0.3902 | **0.4697** |

The training-disjoint paired Recall@20 difference is **+0.0686**, with descriptive organization-bootstrap 95% interval **[+0.0492, +0.0894]**. This supports a strong exploratory ranking signal in these files, not a fresh inferential p-value. The all-499 result includes training organizations. Pair precision, recall, and group recovery ceiling are unchanged because the groups are identical. The model fit and 499-score prediction pass took 87.6 seconds in this local batch; this is not SOC alert-to-decision latency.

## Link bridging with a purity constraint

A separate [42-queue development experiment](../outputs/submission_development_bridge_links_20261114_v1.json) tried lower-probability edges only when corroborated by two shared entities or by a rare shared entity plus category/technique agreement. The development-selected rare-entity/descriptor rule at 0.65 passed a predeclared **0.80 pair-precision floor** and raised development Recall@20 from 0.3602 to 0.3670. Predictions for all 499 were then frozen and separately [evaluated](../outputs/submission_bridge_group_v5_20261114_v1/metrics.json).

On all 499 queues, bridge grouping yielded **0.3421 versus 0.3397** Recall@20, paired difference **+0.0024** with interval **[-0.0004, +0.0054]**. The historical holdout changed from 0.3902 to 0.3887. Pair precision changed from 0.9041 to 0.9002; the observed-group oracle-order ceiling fell from **6,969/9,980** to **6,934/9,980**. The full run does not support adopting the bridge. It remains a negative tradeoff, and no further bridge setting was chosen from these test results.

## Evidence timing and next evaluation

The [point-in-time field assessment](POINT_IN_TIME_EVIDENCE_STATUS_20261114.md) records what the [GUIDE publisher paper](https://arxiv.org/html/2407.09017v4) and [Kaggle release](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction/data) establish. `Timestamp` is alert creation time, but evidence-arrival timing and operational field approval remain unproven. The official field allowlist is still empty.

The selected next-cohort method is **v2 grouping at threshold 0.75/cap 100 plus v4 priority ranking**, frozen in the [prospective v3 contract](../outputs/future_cohort_study_contract_20261114_v3.json). It has not been run on a new, untouched expert-ranked cohort because none is available. Its current observed groups have a 69.83% oracle-order ceiling, so **80% absolute Recall@20 remains unmet**; a future grouping improvement and independent test are needed. No operational SOC claim follows from these batch results.
