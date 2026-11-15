# Read-only cross-fragment pair-score audit

**Status: exploratory retrospective diagnosis, 15 November 2026.** No source code, model, candidate graph, threshold, group, prediction, configuration, or frozen artifact was changed. This report uses previously accessed GUIDE_Test expert membership **only in evaluator-side analysis**. It makes no independent-validation or operational SOC claim. The frozen reference remains entity-enabled candidates, v2 grouping at **0.75**, the **100-alert** cap, and v7 ranking.

## Scope and integrity

The cohort is the same **499 queues**, **400,039 unambiguous alerts**, **1,942,648 frozen candidate pairs**, and **9,980 expert top-20 labels** used in [Phase 6](PHASE6_GROUPING_FAILURE_ANALYSIS.md), [Phase 9D](PHASE9D_CANDIDATE_COVERAGE_AUDIT.md), and [Phase 9E](PHASE9E_CANDIDATE_RETRIEVAL_REPORT.md). The frozen [candidate](outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json), [v2](outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json), and [v7](outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json) freeze hashes still match `eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8`, `819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e`, and `40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743`. The v2 pair model matches its [fit freeze](outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json) SHA-256. For every queue, the diagnostic verified frozen candidate, group, and evidence-shard hashes; regenerated the exact candidate edge array; recomputed probabilities using the fitted v2 model; and reproduced the exact frozen 0.75-threshold group partition. No evaluator identifier or raw entity value is exported here.

The diagnostic uses three distinct edge populations:

1. **Missed genuine cross-group candidates:** same expert incident, endpoints in different frozen v2 groups, and the incident belongs to the **1,451 candidate-connected but incomplete top-20 labels**. This is evaluator-defined; a live model cannot identify this population.
2. **False cross-group candidates:** endpoints in different v2 groups and *different* expert incidents, across the full 499 queues. These were available to the scorer but were not grouped together in the frozen partition.
3. **High-score false edges inside a group:** endpoints from different expert incidents within the same frozen v2 group, with pair score ≥0.75. Such an edge is a high-confidence error candidate, but it need **not** itself have been the union edge that formed the group; other accepted paths can place its endpoints together.

These populations have different denominators. Edge counts are not incident counts, and many edges can belong to one incident. The 1,451 labels are **1,244 with 2–10 in-scope alerts**, **158 with 11–100**, and **49 with >100**. Their group-fragment counts are **714 in two**, **230 in three**, **115 in four**, **89 in five**, and **303 in six or more** groups. In **1,143**, the largest fragment holds just one of the label's alerts ([saved Phase 6 output](outputs/phase6_grouping_failure_analysis_20261115_v4.json)).

## Frozen-score separation

The following are **exact counts over all frozen candidates**, using the unchanged fitted v2 probabilities:

| Frozen pair score | Missed genuine cross-group edges | False cross-group edges |
|---|---:|---:|
| <0.25 | 68,133 | 767,301 |
| 0.25–<0.50 | 150,986 | 389,987 |
| 0.50–<0.65 | 49,035 | 61,643 |
| 0.65–<0.75 | 14,209 | 10,944 |
| 0.75–<0.90 | 5,023 | 137 |
| ≥0.90 | 6 | 0 |
| **Total** | **287,392** | **1,230,012** |

Thus **282,363/287,392 (98.25%)** missed genuine cross-group edges score below 0.75. The **5,029** above-threshold true edges are concentrated in only **six** incomplete expert labels; they cannot be read as 5,029 independently recoverable incidents. The 1,230,012 false cross-group edges include only **137** above threshold, yet they show why a global cutoff change could expose many more wrong links: **10,944** sit in the 0.65–<0.75 band alongside **14,209** missed genuine edges. Those edge-level counts do not account for group transitivity or purity after union.

At the **incident** level, the best genuine cross-fragment edge falls **below 0.25 for 138 labels**, **0.25–<0.50 for 639**, **0.50–<0.65 for 430**, **0.65–<0.75 for 238**, and **≥0.75 for six**. The first four bins sum to **1,445**: those incidents have **no** genuine cross-fragment edge reaching the fixed grouping threshold. All 1,451 have at least one genuine cross-fragment candidate edge; **827** have at least two. The absence of an accepted edge is therefore primarily a *score/decision* failure on the existing graph, not absence of every candidate. It does **not** prove that lowering 0.75 would create pure, complete groups.

There are also **9,586 high-score false candidate edges already inside frozen groups**: **8,998 score 0.75–<0.90** and **588 score ≥0.90**. Their presence is consistent with the baseline's **28,606 false-positive grouped alert pairs**, but the two quantities count different things. One wrong union can produce many false grouped pairs, and some high-score false edges may be redundant within an already mixed group. The [Phase 6 impurity diagnosis](outputs/phase6_grouping_failure_analysis_20261115_v4.json) found **218 impure top-20 labels**; each selected group had a direct high-score cross-incident edge, with **125** selected groups having exactly one such edge and **916** direct false edges across the selected groups. This is why false positives remain a serious constraint even though just 137 high-score false edges stay *between* groups.

## Feature distributions and likely error mechanisms

The v2 [feature builder](src/submission_entity_time_pair_v2.py) supplies **30 numeric features**: for each of five descriptor fields, Jaccard overlap, any overlap, and exact-set equality (**15**); six typed shared-entity indicators; shared-entity count and rarity proxy; log alert-time gap and two time-window indicators; and four candidate-route flags. `IncidentId`, expert rank, grade, and outcome are not input features. The fitted GBM was trained on up to **200 positive and 400 negative candidate pairs per historical training organization**, with **31,294 positive and 92,466 negative** sampled training pairs over 334 organizations ([fit freeze](outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json)). Its training objective is sampled pair classification, not complete-and-pure incident recovery.

For descriptive feature comparison, the audit took deterministic encoded-edge subsamples of the first two populations: **13,789/287,392** missed genuine cross-group edges (edge code divisible by 20) and **23,139/1,230,012** false cross-group edges (divisible by 50). It retained all **9,586** high-score false edges inside groups. These are **edge-weighted**, correlated within incidents and queues, and are not a random organization-level test. Values below are fractions of sampled edges with that feature present, except the mean log-hours and rarity proxy. The rarity proxy is `1/log(1 + minimum shared-entity frequency)` when the minimum frequency exceeds one, otherwise zero; a larger value generally indicates a less common shared entity under this implementation.

| Feature or score | Missed genuine cross-group | False cross-group | High-score false inside group |
|---|---:|---:|---:|
| Median pair score (sample) | 0.3818 | 0.1717 | 0.8075 |
| Shared device ID | 9.10% | 7.46% | **74.14%** |
| Shared account object ID | 49.42% | 42.76% | **64.17%** |
| Shared SHA-256 | 16.83% | 17.83% | **44.68%** |
| Shared IP address | 41.64% | 31.41% | 6.90% |
| Shared category | 85.35% | **90.35%** | 69.31% |
| Shared detector | 55.22% | **67.44%** | 51.71% |
| Shared technique | 42.56% | 39.07% | 17.22% |
| Common-entity route flag | **84.10%** | 69.94% | 45.64% |
| Rare-entity route flag | 10.39% | 10.81% | **70.56%** |
| Shared-entity count, mean | 1.536 | 1.225 | **2.384** |
| Entity-rarity proxy, mean | 0.262 | 0.241 | **0.552** |
| Log-hours gap, mean | 1.270 | **2.272** | 1.150 |
| Within one hour | 36.40% | 20.32% | 26.48% |

The missed genuine edges and false cross-group edges overlap substantially in common-entity, category, detector, and timing signals. Shared category is even *more common* in false cross-group candidates in this edge-weighted sample; it cannot serve as a standalone merge certificate. High-score false edges inside groups look strong to the existing model—many share rare entities, devices, accounts, and hashes with relatively short time gaps. Those signals can also arise from common infrastructure, detector output, or duplicate upstream observations. The dataset has no authoritative observation IDs or evidence-arrival timestamps ([Phase 9B](PHASE9B_EVIDENCE_AND_DATA_READINESS.md)), so feature overlap is **not independent corroboration**.

To see which input columns the *frozen fitted model* relies on in this comparison, the audit balanced the two cross-group samples to **12,000 edges per class**, computed an in-sample ROC-AUC of **0.7358** on that retrospective comparison, then permuted each column once with fixed seed **901** without retraining. The largest increases in log loss were **log-hours gap +0.2284**, **entity-rarity +0.0336**, **technique Jaccard +0.0151**, **shared DeviceId +0.0144**, **shared AccountObjectId +0.0084**, **shared-entity count +0.0083**, **detector Jaccard +0.0080**, and **shared SHA-256 +0.0080**. Log-hours also had the largest AUC drop (**0.1604**). These are **descriptive model-reliance measurements on a label-selected, balanced edge sample**. Correlated fields and permutation-created unrealistic feature combinations prevent interpreting them as causal feature contributions, standalone feature quality, or a new performance estimate. In particular, they do not justify changing a feature weight or threshold on exposed GUIDE labels.

The combined evidence suggests two hypotheses for future authorized research: (1) true cross-fragment links using common entities and modest descriptor agreement often receive insufficient pair scores; (2) false links involving multiple or rarer shared entities and short gaps can receive overly strong scores. Neither hypothesis can be resolved safely by a blanket threshold reduction. An incident-level error objective, verified provenance, and hard negatives resembling the high-score false edges would be needed to test an alternative scorer on authorized development data.

## Effect of the 100-alert component cap

The [frozen union implementation](src/submission_full_guide.py) refuses any union whose combined component would exceed **100 alerts**. Replaying the frozen pair scores and union order reproduced all v2 group partitions. Exactly **six** of the 1,451 incomplete labels have a genuine cross-fragment candidate edge scoring ≥0.75; each is blocked because its two final groups would exceed 100 alerts when joined. Thus the cap is the **direct observed explanation for six** of these incident-level misses. This does not imply removing the cap is safe: it prevents oversized, potentially impure components and was held fixed in all baseline comparisons.

There is also a mathematical limit: an expert incident with **more than 125 in-scope alerts** cannot satisfy 80% completeness in any group capped at 100, since `100 / incident_size < 0.8`. The diagnostic found **62** such top-20 labels, including **42** in the candidate-connected/incomplete category; the other **20** are candidate-disconnected under the current graph. These 62 are inherently unrecoverable under the current cap and recovery rule, irrespective of pair score. Therefore the earlier **8,638/9,980 = 86.55% candidate-connectivity oracle** is loose under the hard cap; subtracting at least the 42 candidate-connected size-impossible labels gives a still optimistic **8,596/9,980 = 86.13%** cap-aware ceiling. This arithmetic bound ignores additional cap, purity, ranking, and false-merge losses. It does not authorize enlarging groups.

The [Phase 9E result](PHASE9E_CANDIDATE_RETRIEVAL_REPORT.md) further shows that adding candidates can change the order in which capped unions are attempted: candidate connectivity rose by four, but grouped-pair true positives fell by 1,215 without new false grouped pairs. An edge-level replay would be needed to attribute every lost true pair specifically to the cap; this report does not make that causal claim.

## Conclusion and limits

The principal **score-side** bottleneck is that **1,445/1,451** candidate-connected incomplete incidents have no genuine cross-fragment edge above 0.75. The principal **safety** bottleneck is that high-confidence false links already exist in mixed groups, and their feature profiles resemble strong shared evidence. The cap directly blocks six otherwise high-score incomplete incidents and makes 62 >125-alert labels impossible to recover under the current 80% rule. These are separate mechanisms; none is repaired by simply adding candidates or merging more groups. The baseline remains **69.83% group recoverability** and **49.82% Recall@20**; no metric was improved in this audit.

This analysis used the existing [Phase 6 diagnostic code](submission/diagnose_phase6_grouping_failures.py) for category definitions, [v2 scoring code](src/submission_entity_time_pair_v2.py) for features/probabilities, [candidate generator](src/submission_full_entity_time.py) for exact edge/route regeneration, and frozen per-queue candidates/groups. All exact score-bin counts were accumulated over all edges; feature fractions used the deterministic edge-code subsamples described above. No diagnostic output file or model artifact was written; this report is the sole new deliverable. The official [field policy](configs/field_policy.yaml) still has an empty operational inference allowlist, and GUIDE_Test labels have already informed past development. A new untouched, authorized cohort is required before a revised method could support a confirmatory claim.
