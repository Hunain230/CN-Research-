# Phase 4: Offline incident-ranking investigation

**Status, 15 November 2026:** Three isolated traditional-ML ranking candidates were fitted and evaluated on the **same frozen v2 groups** as v7. The development-selected hard-negative LightGBM model is a **promising exploratory candidate on queues outside fitting**, but its all-499 Recall@20 gain is small and uncertain. The frozen v2+v7 method remains the research reference. No LLM or Qwen was called, and no frozen source, model, prediction, or result was modified.

## 1. Reference and training-data eligibility

The reference is entity-enabled candidates, v2 groups, and frozen v7 group scores. Its [metrics](outputs/submission_descriptor_ranker_v7_20261114_v1/metrics.json) give **Recall@20 49.82% (4,972/9,980)**, **P@10 61.58%**, **nDCG@20 0.4371**, and the [v2 group ceiling](outputs/submission_entity_time_pair_v2_20261114_v1/metrics.json) of **6,969/9,980 = 69.83%**. The 499 queues contain 334 historical training, 67 validation, 68 historical holdout, and 30 without one of these split labels. All 499 predictions remain in the descriptive comparison.

The 334 training organizations and their incident memberships/top-20 labels were available for **further exploratory fitting** under this phase's instruction. The 67 validation organizations were used only to select among three prespecified ranking candidates. Their labels, and the 68 historical holdout labels, had been accessed previously in the broader project. Thus neither subgroup is an untouched test. The 30 unassigned queues were prediction/evaluation only. Model feature construction used only the project's **local experimental** descriptor/entity/time view; no IncidentId, expert rank, grade, or outcome was an inference feature. The [official operational field allowlist](configs/field_policy.yaml) is empty, so this experiment supplies no production field authorization.

## 2. Why v7 misses recoverable incidents

The evaluator-side [Phase 2 diagnosis](PHASE2_RECALL_IMPROVEMENT_PLAN.md) identifies **1,997** complete, pure incident groups below position 20; **1,831 are singleton incidents**. The fixed groups can recover 6,969 labels under ideal ordering, leaving **1,997 ranking misses** after v7 reaches 4,972. This is separate from candidate and grouping losses.

I inspected the frozen [v7 source](src/submission_descriptor_ranker_v7.py), [prediction freeze](outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json), v2 group files, and v7 score files in read-only evaluator-side diagnostics. Across all 499 queues, **1,172 of 1,997 missed recoverable groups rank 21–40** and **1,843 rank within the first 120**. The top-20 positions contain **5,002 nonrelevant groups**, including **4,042 singletons**. Six queues have fewer than 20 predicted groups, so 9,974 top-20 slots are populated. A blanket singleton bonus would promote many existing false positives.

There is substantial score overlap: the median v7 score of a missed recoverable group is **0.476**, while the median of a nonrelevant top-20 group is **0.725**. The median cutoff gap for missed recoverable groups is **0.074**. These figures show an ordering problem, not its unique cause. On the 135 queues outside model fitting, an evaluator-side check found **1,945 positive recoverable groups among 186,431 groups** (1.04% prevalence), and mean within-queue binary AUC **0.904 across 133 queues with both classes**. V7 has useful broad discrimination yet still makes consequential near-cutoff ordering errors.

V7 is **not a calibrated incident probability**. It blends a tenfold-positive-weighted logistic output with a tree output selected for ranking. In an exploratory reliability check on those 135 queues, groups with v7 scores 0.9–1.0 had **mean score 0.946 but 63.0% observed recoverable-positive frequency**. This is evidence of probability miscalibration, but top-20 ranking depends on order; recalibrating a single score monotonically would not fix ordering. Calibration could matter where two models' scores are blended. The saved development table selected blend **0.75**; pure descriptor weight 1.0 was slightly worse there on Recall@20. There is no evidence that simply increasing the blend weight solves the 1,997 misses.

## 3. Feature and model assessment

V7's [feature code](src/submission_descriptor_ranker_v7.py) combines the [v4 numeric group features](src/submission_group_ranker_v4.py)—group size, BM25 and prior scores, within-queue score positions, queue size, time span, and unique detector/category/technique/entity-type/evidence-role/entity counts—with binary hashed **identities** for five descriptor fields. V7 uses 131,072 hash bins and a logistic model trained on **157,072 groups from 334 organizations**, with **4,624 positive recoverable-top-20 groups** weighted tenfold. Its independent binary training objective does not optimize query-wise top-20 ordering directly.

Existing numeric features provide size and diversity but not within-group agreement, pair-score distribution, bridge reliability, or evidence consistency. Those are plausible future rank signals only if they are label-blind, available at the relevant decision time, and assessed on fixed groups. Time span and entity diversity are currently local retrospective sensitivity features; arrival-time availability remains unproven. Separate singleton and multi-alert logistic specialists were previously tested and rejected on development queues in the [v8 negative control](submission/SPECIALIST_RANKER_NEGATIVE_CONTROL_20261114.md).

For this small study, both tree rankers use the same 13 numeric features and 4,096 hashed descriptor bins. This compact representation keeps a CPU experiment feasible but differs from v7's 131,072-bin sparse representation. It does **not** isolate the effect of ranking objective from representation. LightGBM's LambdaMART implementation expects query group sizes; XGBoost provides NDCG and pairwise ranking objectives with query grouping, so a plain binary XGBoost classifier was not used. See the [official LightGBM ranker API](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRanker.html) and [official XGBoost ranking guide](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html).

The fitted LightGBM hard-negative model's highest numeric split counts were entity diversity, technique diversity, prior group score, BM25 position and BM25 magnitude. These are **model split counts, not causal explanations**; hash collisions also limit interpretation of identity-bin importance. They suggest that relative score plus group evidence diversity may help, but a controlled feature ablation would be needed to attribute a gain.

## 4. Controlled experiment

The separate [implementation](src/submission_ranking_ltr_v1.py) and [fixed configuration](configs/ranking_ltr_v1.json) leave all 499 v2 groups, 400,039 alerts, **1,942,648 candidate pairs**, the **9,980-label denominator**, 80% completeness/purity rule, and tie-aware evaluator unchanged. Organization queues are ranking queries; training examples from different organizations are never mixed into one query. No broad hyperparameter search was run. The [prediction freeze](outputs/submission_ranking_ltr_v1_20261115_v1/prediction_freeze.json) records source hashes, versions, development choice, all 499 feature and score hashes, and resource use. All fitted models and feature files have separate versioned private paths.

| Candidate | Training input and objective | Prespecified treatment |
|---|---|---|
| LightGBM full | All **157,072** training groups, 334 query groups; binary recoverability relevance, LambdaMART/NDCG-oriented objective | 80 shallow trees, queue grouping, 4,096 identity bins. |
| XGBoost full | The same full groups and labels; **rank:ndcg**, not binary classification | 80 shallow histogram trees; query grouping and four sampled pairs per item. |
| LightGBM hard-negative | **29,478** training groups, still separated into 334 queries; all positives plus up to 40 highest-scoring negatives by the old frozen v2 score and 40 seeded random negatives per queue | Train on hard/background negatives; select/evaluate on **full queues**. The old v2 score avoids using in-sample v7 scores for mining. |

The full and hard-negative LightGBM settings also differ in minimum child samples (60 versus 40). Consequently, their difference **cannot be credited to negative sampling alone**; a same-parameter follow-up would be required for that causal claim. Both still constitute separate, fully specified ranking candidates against the frozen reference.

The development-only rule required at least **+1.0 percentage point Recall@20** versus v7, no more than **0.5 point P@10 loss**, and no more than **0.005 nDCG@20 loss**; it selected **LightGBM hard-negative** on the 67 validation queues. This decision was frozen before the separate [evaluator](submission/evaluate_ranking_ltr_v1.py) opened the 68 historical holdout labels. The [metrics](outputs/submission_ranking_ltr_v1_20261115_v1/metrics.json) report every candidate regardless of selection. No choice was made from the 499-queue aggregate.

## 5. Matched exploratory results

| All 499 queues, macro metric | Frozen v7 | LightGBM full | LightGBM hard-negative, dev selected | XGBoost full |
|---|---:|---:|---:|---:|
| Recall@20 | **49.82%** | 49.29% | **50.18%** | 40.98% |
| P@10 | 61.58% | 62.06% | **62.76%** | 53.64% |
| nDCG@20 | 0.4371 | 0.4732 | **0.4744** | 0.4514 |
| Fixed-group oracle ceiling | 69.83% | 69.83% | 69.83% | 69.83% |

The selected LightGBM model's all-499 Recall@20 difference is **+0.36 percentage points**, with organization-bootstrap descriptive 95% interval **[−0.69, +1.43] points**. Its P@10 difference is **+1.18 points [−0.30, +2.74]** and nDCG@20 difference **+0.0373 [0.0220, 0.0524]**. XGBoost materially reduces Recall@20 and P@10 under this fixed setting; it is not selected.

| Historical subgroup | V7 Recall@20 | Selected LightGBM Recall@20 | Paired difference, descriptive 95% interval |
|---|---:|---:|---:|
| 67 validation queues used for selection | 41.64% | 45.18% | +3.54 points [1.26, 5.99] |
| 68 previously exposed holdout queues | 49.34% | 54.33% | +4.99 points [1.95, 8.06] |
| 135 queues outside fitting, including validation | 45.52% | 49.79% | +4.27 points [2.36, 6.25] |
| 334 training queues | 52.28% | 50.89% | −1.38 points; in-sample comparison |

On the 135 outside fitting, the selected model also reaches **P@10 59.33% versus 55.56%** and **nDCG@20 0.4743 versus 0.4165**. On the 68 historical holdout, P@10 is **65.19% versus 61.03%** and nDCG@20 **0.5090 versus 0.4389**. These are informative but **not independent test results** because the GUIDE labels had been accessed earlier.

The evaluator reports **tie-aware expected** recoveries. On all 499, v7 recovers exactly **4,972** labels; the selected tree ranker has **5,008.28 expected** recoveries because tied tree scores are uniformly randomized at the cutoff. Relative to v7, the evaluator estimates **640.29 newly recovered and 604.02 previously recovered lost**, net **+36.28 expected** labels. These are expected transition counts, not literal fractions of incidents observed in a single queue order. Singleton recoveries change from **4,373.00 to 4,390.75 expected**, and multi-alert recoveries from **599.00 to 617.53 expected**. Denominators are **6,342 singleton**, **2,783 multi-alert**, and **855 absent-from-scope** expert labels. Per-organization anonymized paired metrics and tie-aware transitions are in the metrics JSON. Recall@20 improved in **190 queues**, declined in **156**, and was unchanged in **153**; among the 68 historical holdout queues, the counts are **33 / 15 / 20**.

Feature preparation took **53.7 seconds**; model fitting took **1.17 seconds LightGBM full, 1.23 seconds XGBoost full, and 0.27 seconds LightGBM hard-negative**; scoring all queues took **13.8 seconds**. The whole prediction pass took **70.2 seconds**, with **743 MB peak process RSS**. The evaluator took about **9.0 seconds** and reached **440 MB peak RSS**. These are local batch measurements, not SOC alert-to-decision latency. The [run manifest](outputs/submission_ranking_ltr_v1_20261115_v1/run_manifest.json) passed hash verification; all **499 feature files, 499 score files, and three model files** matched the prediction freeze.

## 6. Acceptance and next step

**Retain frozen v7 as the reference.** The development-selected LightGBM hard-negative model is worth carrying forward as a **separate exploratory candidate**: its 135-queue and 68-queue descriptive comparisons improve all three ranking metrics. Its all-499 Recall@20 point gain is only **0.36 points** with an interval spanning zero, and the historical partitions are post-exposure. It does not overcome the **69.83% fixed-group ceiling**, and it does not demonstrate C/P/V superiority or operational performance.

The next controlled research step is a **same-parameter LightGBM full-versus-hard-negative ablation** on an eligible development source, followed by a frozen comparison on a **new untouched expert-ranked cohort**. That would isolate negative sampling and test generalization. Before operational use, establish point-in-time availability and approval for every model field; the production allowlist is still empty. Do not promote the selected model or its 54.33% historical-holdout result as confirmed performance.

To reproduce in a new run ID with the project environment and installed **LightGBM 4.7.0 / XGBoost 3.4.1**:

    .\.venv\Scripts\python.exe -m src.submission_ranking_ltr_v1 self-test
    .\.venv\Scripts\python.exe -m src.submission_ranking_ltr_v1 predict --run-id submission_ranking_ltr_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.evaluate_ranking_ltr_v1 --run-id submission_ranking_ltr_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_ranking_ltr_v1_NEW_ID
