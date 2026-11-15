# Phase 5: Matched hard-negative sampling ablation

**Status, 15 November 2026:** Completed two controlled, versioned, offline LightGBM comparisons. This study asks whether **training-example sampling alone** improves ranking at each fixed minimum-child setting. The answer is **mixed and inconclusive for generalization**. Preserve frozen v7 as the research reference; keep the Phase 4 hard-negative model as an exploratory candidate, not a confirmed replacement. All GUIDE_Test labels were previously accessed.

## 1. Prerequisites and design

The [Phase 4 ranking freeze](outputs/submission_ranking_ltr_v1_20261115_v1/prediction_freeze.json) contains **499 hash-verified feature files** with exactly **13 numeric columns and 4,096 hashed descriptor bins**. The historical split has **334 training, 67 validation, 68 holdout, and 30 unassigned prediction-only queues**. The 334 training organizations provide **157,072 frozen v2 groups**, including **4,624 recoverable top-20 positive training groups**. These labels can be reused for explicitly **exploratory fitting** under this phase's instructions. No validation, holdout, or all-499 labels were read during prediction, and no parameter was selected from their outcomes.

The new [configuration](configs/hard_negative_ablation_v1.json) fixes the **same LightGBM LambdaMART objective, 80 trees, 15 leaves, learning rate 0.05, truncation level 25, seed 181, four CPU workers, feature files, relevance rule, and organization-query boundaries** for all four models. The [implementation](src/submission_hard_negative_ablation_v1.py) changes only training-example selection **within** each pair:

| Matched pair | Full strategy | Hard-negative strategy | Identical within-pair setting |
|---|---|---|---|
| A | All 157,072 training groups | All positives plus up to 40 highest old-v2-score negatives and 40 seeded random negatives per organization | min_child_samples = **40** |
| B | All 157,072 training groups | The same **29,478** sampled groups | min_child_samples = **60** |

The hard-negative sample retains **all 4,624 positives**, plus **13,301 high-scoring negatives** and **11,553 random negatives**. The full set has **152,448 negatives**. The sample totals vary by organization; the [prediction freeze](outputs/submission_hard_negative_ablation_v1_20261115_v1/prediction_freeze.json) and [metrics](outputs/submission_hard_negative_ablation_v1_20261115_v1/metrics.json) include pseudonymous per-organization counts of full groups, positives, selected hard/random negatives, and sampled groups. Some training queues contain no recoverable positive group; they remain separate queries. The frozen old v2 score, rather than an in-sample v7 score or evaluator-only field, orders candidate negatives for sampling.

The evaluator verifies that the two fitted LightGBM models in **each pair have identical parameters**. As a further control, the new **full_60** and **hard_40** scores reproduce the corresponding Phase 4 score vectors for all 499 queues with **maximum absolute difference 0.0**. The new **full_40** and **hard_60** cells complete the factorial comparison. Models, 499 score files, prediction freeze, metrics, and [run manifest](outputs/submission_hard_negative_ablation_v1_20261115_v1/run_manifest.json) are under the new run ID. The [evaluator](submission/evaluate_hard_negative_ablation_v1.py) uses the same frozen v2 groups, **1,942,648 candidate pairs**, **400,039 alerts**, **9,980 expert top-20 labels**, 80% completeness/purity rule, and tie-aware ranking code as the reference.

## 2. Matched all-499 results

| Method | Recall@20 | P@10 | nDCG@20 | Expected recovered top-20 labels / 9,980 |
|---|---:|---:|---:|---:|
| Frozen v7 reference | **49.82%** | 61.58% | 0.4371 | 4,972.00 |
| Full, child 40 | 49.16% | 61.97% | 0.4721 | 4,906.55 |
| Hard-negative, child 40 | **50.18%** | **62.76%** | **0.4744** | **5,008.28** |
| Full, child 60 | 49.29% | 62.06% | 0.4732 | 4,919.04 |
| Hard-negative, child 60 | 49.74% | 62.52% | 0.4712 | 4,964.43 |

At **child 40**, hard-minus-full Recall@20 is **+1.02 percentage points**, descriptive organization-bootstrap 95% interval **[+0.19, +1.84]**. P@10 is **+0.79 points [−0.29, +1.90]**, and nDCG@20 is **+0.0022 [−0.0083, +0.0131]**. The tie-aware expected transition is **540.86 newly recovered** versus **439.13 previously recovered lost** incident labels, net **+101.72**.

At **child 60**, hard-minus-full Recall@20 is **+0.45 points [−0.38, +1.29]**. P@10 is **+0.46 points [−0.64, +1.62]**, while nDCG@20 is **−0.0020 [−0.0124, +0.0086]**. Expected transitions are **532.18 newly recovered** versus **486.78 lost**, net **+45.39**. The score difference favors hard negatives in aggregate at both settings, but only the child-40 all-queue recall interval excludes zero. The all-499 cohort contains training and previously used selection queues; these intervals are descriptive, not confirmatory.

## 3. Historical subgroup comparisons

All rows below are **exploratory**. The 67 validation queues were used in Phase 4 model selection and the 68 historical holdout labels had been accessed earlier. The 135-queue subset is outside **this fitting pass**, not an untouched test.

| Cohort and matched setting | Full Recall@20 | Hard Recall@20 | Hard-minus-full Recall@20; descriptive 95% interval | P@10 full → hard | nDCG@20 full → hard |
|---|---:|---:|---:|---:|---:|
| Train 334, child 40 | 49.48% | 50.89% | +1.41 points [0.38, 2.40] | 63.05% → 64.43% | 0.4741 → 0.4692 |
| Train 334, child 60 | 49.77% | 50.60% | +0.83 [−0.19, 1.85] | 63.03% → 64.24% | 0.4690 → 0.4665 |
| Validation 67, child 40 | 43.96% | 45.18% | +1.22 [−0.92, 3.38] | 53.45% → 53.38% | 0.4277 → 0.4390 |
| Validation 67, child 60 | 43.88% | 44.38% | +0.50 [−1.95, 2.89] | 53.14% → 53.90% | 0.4354 → 0.4421 |
| Historical holdout 68, child 40 | **54.40%** | 54.33% | −0.07 [−2.25, 2.02] | **66.82% → 65.19%** | 0.4988 → 0.5090 |
| Historical holdout 68, child 60 | **54.18%** | 53.59% | −0.59 [−3.19, 1.81] | **68.04% → 64.78%** | **0.5172 → 0.5032** |
| Outside fitting 135, child 40 | 49.22% | 49.79% | +0.57 [−0.97, 2.06] | 60.18% → 59.33% | 0.4635 → 0.4743 |
| Outside fitting 135, child 60 | 49.06% | 49.02% | −0.05 [−1.80, 1.63] | 60.65% → 59.38% | 0.4766 → 0.4728 |

For child 60 on the 68 historical holdout queues, hard-minus-full P@10 is **−3.26 points**, descriptive interval **[−6.69, −0.10]**. The hard-negative model therefore does **not** preserve P@10 consistently across settings. Hard-minus-full Recall@20 improves in **189 of 499 queues** and worsens in **127** at child 40; at child 60 it improves in **178** and worsens in **141**. On the historical holdout queues, the respective improved/worsened/unchanged counts are **22/19/27** and **23/20/25**. The metrics JSON contains all 499 pseudonymous paired organization rows and intervals.

## 4. Singleton, multi-alert, and remaining errors

The expert top-20 denominator includes **6,342 singleton**, **2,783 multi-alert**, and **855 absent-from-unambiguous-scope** labels. Since v2 groups are fixed, the oracle recoverability ceiling remains **6,969/9,980 = 69.83%** for every ranker. The following are tie-aware **expected** recovered labels, not integer counts from one arbitrary tie order:

| Method | Singleton recovered / 6,342 | Multi-alert recovered / 2,783 |
|---|---:|---:|
| Full, child 40 | 4,325.54 | 581.02 |
| Hard, child 40 | **4,390.75** | **617.53** |
| Full, child 60 | 4,332.60 | 586.44 |
| Hard, child 60 | **4,355.09** | **609.34** |

Hard-negative training raises both singleton and multi-alert expected recovery at each setting. At child 40, the absolute singleton gain is larger (**+65.22 versus +36.51**), while the relative gain against full training is larger for multi-alert incidents (about **6.3% versus 1.5%**). At child 60, the gains are roughly **+22.49 singleton and +22.90 multi-alert**.

The best all-499 hard model by Recall@20 is the previously frozen **hard_40**. Its expected recovery is **5,008.28**, leaving about **1,960.72 recoverable labels below top 20** even if its score tie order is averaged. Another **3,011** expert labels remain unrecoverable with the existing groups: 855 outside unambiguous scope, 487 candidate-disconnected, 1,451 split, and 218 impure under the Phase 2 diagnostic. Ranking changes cannot recover those 3,011. Hard_40 also has **640.29 expected newly recovered and 604.02 expected lost** labels versus v7, so its net all-queue improvement is only **36.28 expected labels**. The remaining error is both near-cutoff ordering and upstream group/evidence loss.

## 5. Runtime, reproducibility, and interpretation

Because this phase reuses the already frozen Phase 4 feature files, the new prediction pass measures **sampling, model fitting, and scoring**, not feature extraction. Full-data fitting took **1.15 s at child 40** and **1.10 s at child 60**; hard-negative fitting took **0.23 s and 0.26 s**. Scoring all 499 queues with all four models took **12.29 s**. The whole prediction pass took **16.01 s** with **414 MB peak process RSS**. Evaluator time was **10.39 s**, peak **444 MB**. The earlier Phase 4 feature preparation took **53.66 s** and must be included when comparing end-to-end research batch costs. None of these are live SOC alert-to-decision measurements.

The [run manifest](outputs/submission_hard_negative_ablation_v1_20261115_v1/run_manifest.json) passed the repository's SHA-256 verifier (**5 source/output hashes**). A direct read-only check found **zero mismatches among 499 score-file hashes and four model-file hashes**. The matched-pair parameter equality check passed in the evaluator. The [prediction freeze](outputs/submission_hard_negative_ablation_v1_20261115_v1/prediction_freeze.json) records exact training counts per organization and versioned model hashes. The [metrics](outputs/submission_hard_negative_ablation_v1_20261115_v1/metrics.json) record all cohort comparisons, expected recovered/lost labels, size strata, per-organization differences, intervals, and resources.

**Answer to the research question:** Hard-negative sampling raises all-499 Recall@20 at both child settings, with a stronger all-queue signal at 40. It does **not** show a consistent outside-fitting advantage at both settings, and P@10 can worsen, especially in the historical holdout at 60. The evidence supports a **conditional exploratory effect**, not a robust claim that hard-negative sampling is generally superior. Its smaller training set reduces fitting time, but the observed subgroup trade-offs do not justify promoting it as the preferred method solely because of sampling. Keep frozen v7 as the research reference and avoid choosing between the matched rankers using the exposed 499-queue aggregate. A new untouched expert-ranked cohort is needed for a reliable adoption decision.

To reproduce with a fresh versioned run ID in the existing environment:

    .\.venv\Scripts\python.exe -m src.submission_hard_negative_ablation_v1 self-test
    .\.venv\Scripts\python.exe -m src.submission_hard_negative_ablation_v1 predict --run-id submission_hard_negative_ablation_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.evaluate_hard_negative_ablation_v1 --run-id submission_hard_negative_ablation_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_hard_negative_ablation_v1_NEW_ID
