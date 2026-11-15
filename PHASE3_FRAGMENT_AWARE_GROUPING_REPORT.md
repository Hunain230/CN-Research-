# Phase 3: Fragment-aware grouping experiment

**Status:** Completed isolated, retrospective **exploratory** comparison, 15 November 2026. The variant produced a small all-queue point-estimate increase but did **not** establish a robust improvement. **Keep frozen v2 grouping + v7 ranking as the reference method.** GUIDE_Test labels were accessed previously; this run is not a confirmatory test or an operational SOC validation.

## A. Prerequisites and allowed scope

The existing organization split contains **334 train, 67 validation, and 68 historical holdout** queues, all drawn from GUIDE_Test. The project contains no independent non-GUIDE empirical incident labels. Under the instruction **not to use GUIDE_Test labels for fitting or tuning**, this experiment fitted **no new model**, selected **no parameter from GUIDE_Test results**, and used a single fixed grouping rule recorded before its predictions were evaluated. It reused the already fitted v2 pair scorer and v7 ranking stack as required. GUIDE_Test incident memberships and expert ranks were opened only in the evaluator after the new 499-queue predictions were frozen. The method design was informed by earlier exposed GUIDE analyses, so no independent generalization claim follows. Synthetic fixtures were used only for a three-assertion rule check.

The old [future-cohort contract](outputs/future_cohort_study_contract_20261114_v3.json) names **v2 threshold 0.75 with cap100 plus v4 ranking**. The actual historical [v2 grouping function](src/submission_entity_time_pair_v2.py) applies the 0.75 threshold **without a component cap**, and the strongest descriptive ranking is v7. These are different references. This experiment compares the **actual frozen v2+v7 historical method** and does not amend, replace, or claim to execute the old prospective contract. A future new-cohort registration must reconcile that mismatch explicitly.

Prior [bridge](submission/INCIDENT_MISS_AND_PRIORITY_ITERATION_20261114.md), [adaptive-link](submission/ADAPTIVE_LINKS_NEGATIVE_CONTROL_20261114.md), and [learned group-merge](submission/GROUP_MERGE_MODEL_STUDY_20261114.md) studies failed their development purity/recoverability gates. The current variant differs by using **no new fitted merge model or label-selected threshold**, requiring two cross-group edges, a shared low-frequency entity, category/technique agreement, and mutual-best pairing, then allowing each fragment to merge at most once. It tests a narrow structural hypothesis; it does not erase the prior negative evidence.

## B. Isolated implementation and frozen lineage

The new [fragment-aware implementation](src/submission_fragment_aware_v1.py) reads the **same frozen 1,942,648 entity-enabled candidate pairs** and v2 pair probabilities. It starts from frozen v2 groups. The fixed [configuration](configs/fragment_aware_v1.json) considers cross-group pair scores at least 0.50, requires two distinct supporting alert pairs and two touched alerts on the larger side, a maximum pair score at least 0.65, a shared entity appearing in at most 10 groups, shared category or technique, and a combined group size at most 10. It selects only mutual-best group partners in a **single noncascading pass**. There is no training-label access or GUIDE_Test-based parameter search in prediction.

When groups changed, the variant recomputed group features and scores through the **same already fitted** transferred ranker, v4 model, v7 model, feature hasher, and v7 blend. Unchanged groups used the verified frozen v7 score file. Candidate generation, 400,039-alert scope, 499 queues, 9,980 expert top-20-label denominator, 80% completeness/purity rule, and tie-aware evaluator were held fixed.

The [prediction freeze](outputs/submission_fragment_aware_v1_20261115_v1/prediction_freeze.json) records source/model/config hashes, per-queue private-output hashes, zero label access in prediction, and resources. It records **428 accepted fragment merges** across 499 queues and **370,422 resulting groups**. The [metrics report](outputs/submission_fragment_aware_v1_20261115_v1/metrics.json) contains the complete paired comparison and anonymized per-organization differences. The [run manifest](outputs/submission_fragment_aware_v1_20261115_v1/run_manifest.json) passed the repository's read-only hash verifier with **5 source/output hashes**.

**Evaluator correction:** The new source's initial evaluator reached its final consistency gate but counted the recoverable-label category twice in a summary Counter. It wrote no metrics. The predictor source and freeze were left intact. The separate [corrected evaluator](submission/evaluate_fragment_aware_v1.py) removes that duplicate category addition, keeps the original hash checks and metric formulas, and produced the frozen metrics. Its source hash and the correction are recorded in [evaluation_correction.json](outputs/submission_fragment_aware_v1_20261115_v1/evaluation_correction.json) and the run manifest. This is an accounting correction, not a change to predictions or outcomes.

## C. Matched results

| All 499 queues; same alerts and labels | Frozen v2 + v7 | Fragment-aware + same fitted v7 | Difference |
|---|---:|---:|---:|
| Candidate pairs | 1,942,648 | 1,942,648 | 0 |
| Candidate-connected expert labels | 8,638 / 9,980 | 8,638 / 9,980 | 0 |
| Pair true positives | 269,832 | 270,670 | +838 |
| Pair false positives | 28,606 | 29,458 | **+852** |
| Pair precision | 90.41% | 90.18% | −0.23 percentage points |
| Pair recall | 0.1695% | 0.1700% | +0.0005 percentage points |
| Mixed predicted groups | 4,841 | 4,880 | **+39** |
| Candidate-connected but incomplete top-20 incidents | 1,451 | 1,435 | −16 |
| Complete but impure top-20 incidents | 218 | 228 | **+10** |
| Group oracle recoverable labels | 6,969 / 9,980 (69.83%) | 6,975 / 9,980 (69.89%) | +6 labels |
| End-to-end Recall@20 | **4,972 / 9,980 (49.82%)** | **4,975 / 9,980 (49.85%)** | **+3 labels, +0.03 points** |
| P@10, organization macro | 61.58% | 61.72% | +0.14 points |
| nDCG@20, organization macro | 0.4371 | 0.4380 | +0.0008 |

**Incident-level false merge definition:** A *mixed predicted group* contains alerts belonging to at least two distinct expert incidents; each such predicted group is counted once. This yields 4,841 versus 4,880 across all in-scope incidents, including incidents outside the expert top 20. It is distinct from the **28,606 versus 29,458 false-positive alert-pair count**. The top-20 impurity count is a third, narrower measure: an 80%-complete group with less than 80% purity. The variant leaves the **855 absent** and **487 candidate-disconnected** top-20 labels unchanged. Incomplete decreases by 16, impurity increases by 10, and recoverable labels increase by a net 6.

The paired organization-bootstrap **Recall@20 difference is +0.000301**, with descriptive 95% interval **[−0.000802, +0.001403]**. For P@10 the difference is **+0.001403 [−0.000200, +0.003206]**; for nDCG@20 it is **+0.000849 [−0.001006, +0.003266]**. These intervals describe already exposed queues and all include zero. **11 organizations improved**, **8 worsened**, and **480 were unchanged** on Recall@20. All 499 pseudonymous per-organization paired rows are in the metrics JSON.

| Previously accessed subgroup | Frozen v2 + v7 Recall@20 | Fragment-aware Recall@20 | Interpretation |
|---|---:|---:|---|
| 135 queues outside model fitting | 45.52% (1,229/2,700) | 45.48% (1,228/2,700) | One fewer recovered label; this subgroup is still exploratory. |
| 68 historical holdout queues | 49.34% (671/1,360) | 49.26% (670/1,360) | One fewer recovered label; labels had previously been accessed. |

The fragment prediction pass took **120.0 seconds** and reached **607 MB peak process RSS**. The prior v2 prediction record reports **101.5 seconds** and **522 MB peak RSS**. These are retrospective local batch measurements from different passes, with different verification/scoring work; they are useful cost context, not a matched live latency benchmark.

## D. Acceptance decision

The prespecified [configuration](configs/fragment_aware_v1.json) checked strict point-estimate increases in group recoverability and Recall@20, plus minimum floors for pair precision, P@10, and nDCG@20 and maximum ceilings for false-positive pairs and impure top-20 labels. The metrics JSON records that **all mechanical gates passed**. Those gates permitted a 5% relative increase in false-positive pairs and top-20 impurity; the observed increases were **2.98%** and **4.59%**, respectively.

**Do not adopt the variant as the new research baseline.** The achieved gain is only **3 of 9,980 labels**, the paired Recall@20 interval spans a loss, both training-disjoint and historical-holdout point estimates decrease, and mixed groups and false-positive pairs increase. The result is a reproducible, informative **near-neutral trade-off**, not demonstrated generalization or a strong purity-preserving improvement. Frozen v2+v7 remains the reference for the next controlled study.

## Reproduction and limitations

In a fresh versioned run ID, the sequence is: run the synthetic self-test, run the predictor, then run the **corrected** evaluator module. The predictor refuses to overwrite an existing run. The evaluator opens labels only after the prediction freeze exists.

    .\.venv\Scripts\python.exe -m src.submission_fragment_aware_v1 self-test
    .\.venv\Scripts\python.exe -m src.submission_fragment_aware_v1 predict --run-id submission_fragment_aware_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.evaluate_fragment_aware_v1 --run-id submission_fragment_aware_v1_NEW_ID
    .\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_fragment_aware_v1_NEW_ID

This study reused previously GUIDE-trained pair and ranking models but **did not fit or tune a new model on GUIDE_Test labels**. Historical design was informed by exposed labels, so the all-499 and subgroup comparisons remain exploratory. Entity/time evidence arrival and operational field approval are unresolved; the official production allowlist is empty. A future untouched ranked cohort and point-in-time evidence contract are required before a confirmatory claim or operational SOC use.
