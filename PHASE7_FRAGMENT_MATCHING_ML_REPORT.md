# Phase 7: LightGBM fragment-boundary experiment

**Status (15 November 2026):** Completed one isolated, versioned, retrospective offline experiment. The fixed LightGBM policy safely added three merges but **did not improve incident completeness or Recall@20**. Retain the frozen **v2 grouping + v7 ranking** research reference. All GUIDE_Test labels had been accessed in prior project work, so these comparisons are **exploratory**, including the historical holdout. This is not an operational SOC or C/P/V result.

## Research question and why this variant differs

Can a fitted boundary classifier match fragments more safely and more usefully than the frozen v2 linker? The [Phase 6 audit](PHASE6_GROUPING_FAILURE_ANALYSIS.md) identified **1,451 candidate-connected but incomplete top-20 incidents**, including **1,244 with 2–10 alerts**, alongside **218 impure** cases. The frozen reference uses the [v2 pair scorer and 0.75 threshold](src/submission_entity_time_pair_v2.py), a [100-alert union limit](src/submission_full_guide.py), and the [v7 ranker](src/submission_descriptor_ranker_v7.py).

The earlier [adaptive-link study](submission/ADAPTIVE_LINKS_NEGATIVE_CONTROL_20261114.md) lowered pair thresholds and gained little recall while adding false pairs and losing recoverability. The prior [learned group-merge study](submission/GROUP_MERGE_MODEL_STUDY_20261114.md) used a histogram gradient-boosted model on 16 group-pair summary features and a cascading thresholded union; lower thresholds damaged purity and its development selector retained base groups. The [Phase 3 fixed fragment rule](PHASE3_FRAGMENT_AWARE_GROUPING_REPORT.md) used mutual-best, rare entity and descriptor safeguards but recovered only **6** more oracle labels while adding **852** false-positive grouped alert pairs and **39** mixed groups; its all-queue Recall@20 gain was **3 labels** and its outside-fitting result worsened.

This version changes the *boundary decision*, not candidates, v2, or v7. It uses **LightGBM**, adds fragment-consistency, conflict, rarity, and bridge-risk features to the previous 16-feature proposal summary, fits on hard negatives, excludes ambiguous training groups, and applies a **single noncascading mutual-best pass** with a review band and explicit vetoes. It was fixed before the 499-queue evaluation. This tests a different hypothesis; it does not erase the prior negative controls.

## Frozen inputs, split, and label boundary

The method reads the identical entity-enabled candidate graph (**1,942,648 pairs**), frozen v2 groups (**370,850 before this pass**), frozen pair model, experimental evidence projections, and the same fitted v7 ranking stack. It covers **499 organization queues, 400,039 unambiguous alerts, and 9,980 expert top-20 labels**. All 499 candidate, group, and rank-score inputs are checked against their stored SHA-256 freezes before use. The [configuration](configs/fragment_matching_ml_v1.json) and [implementation](src/submission_fragment_matching_ml_v1.py) are separate from Phase 1–6 sources and outputs.

The 334 historical `train` organizations were used for **exploratory supervised fitting**, as explicitly authorized for this phase. `validation` (67), `holdout` (68), and 30 unassigned queues supplied no labels to fitting. An incident membership is used **only to construct the training target** and later by the separate evaluator. `IncidentId`, expert rank, grade, and outcome are absent from `fragment_features`, model input, and prediction. The predictor does not open evaluator labels. The same GUIDE_Test label history means neither this split nor a bootstrap interval establishes fresh generalization. The official [operational allowlist](configs/field_policy.yaml) remains empty; entity and time fields are [local sensitivity inputs](configs/entity_time_sensitivity_policy.yaml) without confirmed point-in-time availability or production approval.

## Training examples, features, and fixed model

For each training queue, candidate edges with frozen pair score at least **0.40** propose pairs of distinct frozen v2 groups. A group with at least **80%** majority membership receives a training incident target. A fragment pair is positive if both majority targets are the same incident, negative if both are known and different, and excluded if either group is ambiguous. No expert rank is used. The training sampler caps positives at **200 per organization**, takes up to **200 highest frozen-pair-score negatives** as hard negatives, and up to **200 additional seeded random negatives**. Organization boundaries remain intact.

| Training census, 334 organizations | Count |
|---|---:|
| Proposed group pairs | 99,464 |
| Label-eligible group pairs | 96,643 |
| Ambiguous-group pairs excluded | 2,821 |
| Available positive / negative pairs before sampling | 49,186 / 47,457 |
| Sampled positive | 16,876 |
| Sampled high-score hard negative | 18,207 |
| Sampled random negative | 7,269 |
| **Fitted rows** | **42,352** |

The [fit freeze](outputs/submission_fragment_matching_ml_v1_20261115_v2/fit_freeze.json) records **all 334 per-organization counts**, exact 32 feature names, model parameters, source hashes, and the private model hash. The 16 inherited proposal features cover maximum/mean frozen pair score, cross-edge and touched-alert counts, strong-edge count, group sizes, entity rarity, intergroup time gap, and five descriptor overlaps. Sixteen added features cover minimum/maximum shared-entity group frequency, shared-technique frequency, detector and evidence-role agreement, category/technique conflicts and Jaccard overlap, within-fragment category/technique consistency, combined size, and single-bridge/common-entity indicators. These are numeric summaries of the existing **local experimental projection**; raw entity values are not exported. The LightGBM classifier has **120 trees, 15 leaves, max depth 5, learning rate 0.05, minimum child samples 40, L2 2, seed 2718, and four workers**. LightGBM **4.7.0** was used locally. No threshold was fitted to validation, holdout, or all-499 outcomes.

## Prespecified decision policy and evidence trace

The [fixed decision policy](configs/fragment_matching_ml_v1.json) requires model probability at least **0.95**, at least **two distinct cross-fragment candidate edges**, at least **two touched alerts on the larger fragment**, a shared entity present in at most **10 groups**, shared category or technique, no simultaneous category-and-technique conflict, and combined size at most **100**. It then keeps only **mutual-best** partners and lets each original group participate in at most one merge. Scores **0.70–<0.95** enter an `abstain_review` outcome when other guards pass; this is a recorded research outcome, not an active analyst workflow. No transitive cascade occurs. An inference-time model cannot know whether a group is truly pure; the conflict and rarity vetoes are **surrogates**, not a guarantee against contamination.

The [prediction freeze](outputs/submission_fragment_matching_ml_v1_20261115_v2/prediction_freeze.json) hashes all **499 group predictions and 499 private decision files**. Each proposed pair's private record contains its original group indices, 32 numeric evidence values, model probability, and one accepted/rejected/review reason, with no raw entity string or evaluator label. Out of **441,000 proposed fragment pairs**, **3** were accepted, **740** were marked review, and the rest were rejected. The first applicable veto dominates the reason: **361,471** common-entity, **71,637** single-bridge, **3,894** no descriptor corroboration, **1,896** component cap, **1,301** low confidence, **50** insufficient touched-alert support, and **8** nonmutual/conflicting selections. These ordered reason counts are **not** independent cause frequencies.

## Matched all-queue result

The evaluator opens labels only after the prediction freeze, reuses the repository's 80% completeness/purity and tie-aware ranking implementations, recalculates group features and v7 scores when a group changes, and verifies the frozen v2+v7 baseline exactly. The main source is the [corrected metrics](outputs/submission_fragment_matching_ml_v1_20261115_v2/metrics_corrected.json); the [original metrics](outputs/submission_fragment_matching_ml_v1_20261115_v2/metrics.json) and [correction record](outputs/submission_fragment_matching_ml_v1_20261115_v2/evaluation_correction.json) remain available. The correction affects only the 30-queue subgroup and interpretation of memory; it does **not** alter predictions or the all-499 outcome.

| Identical 499 queues and denominators | Frozen v2 + v7 | LightGBM fragment policy | Change |
|---|---:|---:|---:|
| Candidate pairs | 1,942,648 | 1,942,648 | 0 |
| Candidate positive / false pairs | 699,790 / 1,242,858 | Same graph | 0 |
| Predicted groups | 370,850 | 370,847 | −3 |
| Grouped alert-pair TP | 269,832 | 270,914 | **+1,082** |
| Grouped alert-pair FP | 28,606 | 28,606 | **0** |
| Grouped pair precision | 90.4148% | 90.4494% | +0.0346 points |
| Grouped pair recall, all positive pairs | 0.1695% | 0.1702% | +0.0007 points |
| Mixed predicted groups | 4,841 | 4,841 | 0 |
| Candidate-connected incomplete top-20 labels | 1,451 | 1,451 | 0 |
| Complete but impure top-20 labels | 218 | 218 | 0 |
| Complete and pure top-20 labels / oracle ceiling | 6,969 / 9,980 (69.83%) | 6,969 / 9,980 (69.83%) | 0 |
| **End-to-end incident Recall@20** | **4,972 / 9,980 (49.82%)** | **4,972 / 9,980 (49.82%)** | **0** |
| P@10 | 61.5832% | 61.5832% | 0 |
| nDCG@20 | 0.437101 | 0.437102 | +0.0000004, negligible |

Here a **mixed predicted group** contains alerts from at least two expert incidents, counted once. **False-positive grouped pairs** are alert pairs placed in the same predicted group but assigned different expert incidents; this is distinct from the unchanged false-positive *candidate* pair count. The **1,451 incomplete labels** are the top-20 false-split measure under the established 80% rule. The pair-recall denominator is **159,186,107** same-incident alert pairs across the unambiguous scope; it is not the 9,980-label Recall@20 denominator. Candidate-pair recall is unchanged because candidate generation is identical.

All **three** accepted merges were on historical training queues. Evaluator-only inspection found that each joined two pure fragments of the same incident, with original fragment sizes **66+10, 86+1, and 8+42**. Each touched a top-20 incident, but the incident was **already complete and pure** under the 80% rule. Thus the extra true grouped pairs did not raise top-20 recoverability. There were **no new mixed groups** in this run, but 4,841 baseline mixed groups remain. The 2–10-alert incidents and singleton incidents gained **zero** recovered labels. The [size-stratified metrics](outputs/submission_fragment_matching_ml_v1_20261115_v2/metrics_corrected.json) show identical expected top-20 recovery: singleton **4,373/6,342**, 2–10 alerts **588/2,420**, 11+ alerts **11/363**, and absent scope **0/855**. These are the tie-aware expected counts; their total is 4,972.

## Organization-level comparison and uncertainty

| Historical cohort | Queues | Reference Recall@20 | Fragment-ML Recall@20 | Paired change |
|---|---:|---:|---:|---:|
| Training | 334 | 52.28% | 52.28% | 0 |
| Validation, previously exposed | 67 | 41.64% | 41.64% | 0 |
| Holdout, previously exposed | 68 | 49.34% | 49.34% | 0 |
| **Outside this fitting pass** | **135** | **45.52%** | **45.52%** | **0** |
| Unassigned prediction-only | 30 | 41.83% | 41.83% | 0 |
| All 499 | 499 | 49.82% | 49.82% | 0 |

Every per-organization paired Recall@20 and P@10 difference is zero; the descriptive organization-bootstrap **95% interval for paired Recall@20 is [0, 0]** on all 499 and on the 135 outside-fitting queues. The tiny nDCG change appears only in the training cohort; the all-queue paired mean is about **+0.0000004** with descriptive interval **[0, +0.0000013]**. These intervals quantify this frozen comparison, not independent sampling uncertainty. All 499 pseudonymous per-organization rows and the full cohort intervals are in the corrected metrics.

## Resource and acceptance check

Fit took **49.3 s** with **395 MB** peak process RSS. The 499-queue prediction pass took **138.5 s** with **965 MB** peak process RSS; within that same pass, loading and reproducing the frozen baseline inputs took **90.4 s**, and fragment proposal, model decision, changed-group rescoring, and recording added **48.1 s**. This is about **53%** additional batch time over the same-pass baseline load, exceeding the prospective **25%** runtime allowance. Evaluation took **17.8 s** with **469 MB** peak RSS. Same-process RSS is a shared high-water mark, so the **25% matched-memory gate cannot be established** from these measurements. None is live alert-to-decision latency.

The prospective gain gate was **at least 10 additional complete/pure labels per 840-label, 42-queue development cohort**. This policy achieved **zero** on all 499. Impurity, mixed groups, false-positive grouped pairs, P@10, and pair precision did not worsen; the recall/recoverability gain gate **failed**, the runtime gate **failed**, and the memory gate is **not evaluable**. These criteria are descriptive here because no untouched independent development cohort exists. No threshold was changed after inspection.

## Reproducibility and accounting correction

The final successful run ID is `submission_fragment_matching_ml_v1_20261115_v2`. An earlier `...v1` attempt froze a training model but stopped during prediction on an empty-proposal queue before creating any prediction freeze; it has **no valid evaluation result**. The v2 run uses the corrected empty-queue handling. The [run manifest](outputs/submission_fragment_matching_ml_v1_20261115_v2/run_manifest.json) passed the repository verifier for **six source/output hashes**; the prediction freeze records 499 private group and decision hashes. No Phase 1–6 artifact was overwritten.

The evaluator's optional unassigned subgroup originally looked for the literal split value `unassigned`. The split manifest omits those 30 organizations, so the original JSON showed a zero-sized subgroup and nonstandard `NaN` means. The separate [aggregate correction](submission/correct_fragment_matching_ml_v1_metrics.py) rebuilt that subgroup **only from frozen per-organization rows**, yielding 30 queues/600 expert labels, and marked the same-process memory comparison inconclusive. The main 499, training, validation, holdout, and outside-fitting figures are unchanged; the original metrics and its hash are preserved. Reproduce in a **new** run ID to avoid overwriting the completed run:

```powershell
.\.venv\Scripts\python.exe -m src.submission_fragment_matching_ml_v1 self-test
.\.venv\Scripts\python.exe -m src.submission_fragment_matching_ml_v1 fit --run-id submission_fragment_matching_ml_v1_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_fragment_matching_ml_v1 predict --run-id submission_fragment_matching_ml_v1_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_fragment_matching_ml_v1 evaluate --run-id submission_fragment_matching_ml_v1_NEW_ID
.\.venv\Scripts\python.exe -m submission.correct_fragment_matching_ml_v1_metrics --run-id submission_fragment_matching_ml_v1_NEW_ID
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_fragment_matching_ml_v1_NEW_ID
```

## Final research decision

1. **Completeness:** No top-20 incident gained 80%-complete/pure recoverability. The three safe merges joined incidents that already met the recovery rule.
2. **Purity:** The run added no false-positive grouped pairs, mixed groups, or impure top-20 labels. This is an observed property of three accepted merges, not a safety guarantee.
3. **Recall@20:** Unchanged at **49.82%** all-queue and **45.52%** outside fitting.
4. **Incident sizes:** No size stratum gained end-to-end recovery; the accepted merges involved larger fragments.
5. **False merges:** The **4,841** baseline mixed groups remain. No new false merge occurred under this policy.
6. **Earlier merge studies:** This LightGBM policy is safer in observed pair purity than the Phase 3 fixed fragment rule, but it delivers **no** incident-level advantage. Compared with the earlier learned group-merge study that selected base groups, it adds true pairs without improving the primary outcome. It does **not** establish superior grouping for SOC prioritization.
7. **Independent evaluation:** This result is **not strong enough to promote the model** for a new confirmatory test as a leading method. Preserve v2+v7. A new untouched ranked cohort, point-in-time evidence contract, and expert review of borderline fragment links are still required before any generalization or operational claim. A subsequent research design should focus on safe recovery of genuinely incomplete small incidents, rather than on already complete large incidents.
