# Phase 9E — bounded sixth-neighbor candidate retrieval

**Decision: NO-GO. Retain frozen v2 grouping + v7 ranking.** This is one prespecified exploratory retrospective experiment on previously accessed GUIDE_Test labels, not independent validation or an operational SOC result. The candidate expansion raised candidate connectivity by four top-20 labels but recovered **zero** additional complete-and-pure incidents and did **not** improve Recall@20. Grouped-pair precision fell. No second budget, neighbor count, score cutoff, or model was tried after evaluator access.

## Fixed question and method

The [Phase 9D audit](PHASE9D_CANDIDATE_COVERAGE_AUDIT.md) found **40 small candidate-disconnected incidents** with at least one route-prefilter-eligible missing pair. That is a diagnostic subset, not an expected gain. This experiment asks whether the **next, sixth** alert in an existing time-sorted entity or technique posting exposes useful missing candidates. It changes candidate retrieval alone. It does not infer incident membership or expert rank while proposing or scoring pairs.

The [versioned configuration](configs/phase9e_bounded_candidate_v1.json) was written before candidate generation or label-side preflight. The [versioned predictor](src/phase9e_bounded_candidate_v1.py) retains the original graph and adds only a posting's sixth forward time neighbor, subject to the existing **500-alert posting cap**, **48-hour entity window**, and **one-hour technique window**. New edges are deduplicated, sorted by encoded alert pair, and bounded to **four per alert, 500 per queue, and 10% of each queue's original candidate count**. Original candidate flags remain untouched. The predictor verifies that the original candidate graph regenerates exactly from the frozen inputs. These budgets are engineering containment choices, not fitted or validated optimums.

The existing frozen v2 gradient-boosted pair scorer evaluates the expanded graph; its **0.75** threshold and **100-alert** component cap remain fixed. The full group partition is rebuilt because a new high-score edge can affect the order of capped unions. Changed groups are scored with the **same fitted v7 ranker and blend**; unchanged queues reuse their frozen v7 scores. No pair model or ranker was retrained. The [separate evaluator](submission/evaluate_phase9e_bounded_candidate_v1.py) opens expert labels **after** the candidate and group predictions are frozen. Its negative-pair preflight was recorded before the final matched metric evaluation; it did not select a new setting.

## Frozen prediction and collision audit

The candidate stage generated **225,456** unique sixth-neighbor pairs before containment. The fixed budgets retained **49,455**, excluding **176,001**; the per-alert limit rejected **1,176** during the ordered scan before the queue limit stopped it. Route flags on retained edges: **47,002 entity**, **3,067 technique**; a pair may have both. Candidate pairs increased from **1,942,648 to 1,992,103** (+2.55%). Prediction changed group partitions in **three of 499 queues**. Among the added edges, **969** scored at or above the unchanged 0.75 pair threshold, though this does not mean each created a new union.

The [frozen preflight](outputs/phase9e_bounded_candidate_20261115_v1/negative_pair_preflight.json) compared added pairs with expert incident membership **only after prediction freeze**:

| Added-candidate diagnostic | Count |
|---|---:|
| Same expert incident | 14,117 (28.55% of additions) |
| Different expert incidents | 35,338 (71.45%) |
| Crosses original v2 groups | 47,777 |
| Same-incident added edges scoring ≥0.75 | 938 |
| Different-incident added edges scoring ≥0.75 | 31 |

These are candidate-pair collisions, **not** 35,338 false grouped pairs. The 31 high-score negatives did not produce a net increase in grouped-pair false positives under the frozen component rule. The outcome does not prove those edges are safe; it reflects this particular capped union order. No alert ID, entity value, or expert incident ID is exported in this public preflight.

## Matched all-499 results

The same **499 queues, 400,039 unambiguous alerts, 9,980 expert top-20 labels**, 80% completeness/purity rule, tie-aware ranking evaluator, fitted v2 scorer, and fitted v7 ranker were used on both sides. The source is the [frozen metrics file](outputs/phase9e_bounded_candidate_20261115_v1/metrics.json).

| Metric | Frozen v2 + v7 | Phase 9E | Change |
|---|---:|---:|---:|
| Candidate pairs | 1,942,648 | 1,992,103 | +49,455 |
| Positive candidate pairs | 699,790 | 713,907 | +14,117 |
| Exhaustive positive-pair candidate recall | 0.4396% | 0.4485% | +0.0089 percentage points |
| Expert labels candidate-connected at 80% | 8,638 | 8,642 | +4 |
| Complete-and-pure group recoverability | 6,969 / 9,980 (69.83%) | 6,969 / 9,980 (69.83%) | 0 |
| Incident Recall@20 | 4,972 / 9,980 (49.82%) | 4,972 / 9,980 (49.82%) | 0 |
| Grouped-pair true positives | 269,832 | 268,617 | **−1,215** |
| Grouped-pair false positives | 28,606 | 28,606 | 0 |
| Grouped-pair precision | 90.4148% | 90.3756% | **−0.0392 percentage points** |
| Mixed predicted groups | 4,841 | 4,841 | 0 |
| Incomplete expert top-20 labels | 1,451 | 1,455 | +4 |
| Impure expert top-20 labels | 218 | 218 | 0 |
| P@10 | 61.5832% | 61.5832% | 0 |
| nDCG@20 | 0.437101 | 0.437101 | 0 |

**No complete-and-pure labels were gained or lost.** The four newly candidate-connected labels remain unrecovered by the actual groups. The count of incomplete labels rose by four because those labels moved from the candidate-disconnected category into the incomplete-group category; it does not by itself mean four previously complete groups were broken. In the **135 queues outside model fitting**, exploratory Recall@20 stayed **45.52%**. That cohort was previously exposed and is not an independent test.

The three changed queues had grouped-pair true-positive changes of **+50, −576, and −689**, totaling **−1,215**, with zero grouped-pair false-positive change in each. Candidate expansion changes high-score edge ordering inside v2's **100-alert capped union**; the resulting partitions can lose true grouped pairs even when additional true candidate pairs are found. This is a mechanism consistent with the source code and observed paired counts; it is **not** a proof that every lost pair came from the cap without an edge-level replay audit. The pair-precision decline is from losing true grouped pairs, not from adding false grouped pairs.

## Safety decision

The prespecified gates required a net group-recoverability gain, an end-to-end Recall@20 gain, **no additional false-positive grouped pairs or mixed groups**, baseline grouped-pair precision or better, and no P@10 decline. The last three purity/count constraints except precision held: false-positive pairs **0 change**, mixed groups **0 change**, P@10 **0 change**. The variant failed recoverability, Recall@20, and pair precision. It is therefore **rejected**, even though the candidate graph covers four more labels. The target **85% group recoverability** and **80% Recall@20** remain unmet. The baseline remains v2 + v7, not Phase 9E.

## Runtime, integrity, and reproduction

On this local machine, candidate generation took **64.49 s** at **587.8 MB** peak process RSS; pair/group/rank prediction took **126.71 s** at **571.8 MB**; final evaluation took **21.19 s** at **357.0 MB**. The negative-pair preflight is a separate read-only label-side pass. These are retrospective batch measurements with duplicated input loading across stages, not alert-arrival latency or a clean matched runtime comparison with the old v2 run.

The predictor's synthetic self-test passed **five assertions**, and both new Python modules compiled. Before and after the run, the frozen candidate, v2, v7, Phase 7, and Phase 9C artifacts were hash-checked. Main new hashes: configuration `4b82e6583b0bfeefe0dbe5bcd0fce7cc2949dc9184592d5e0178a10a1786e4fc`; predictor `cfc39ee04746e211c4a18e955f42bf65a9afb965f363f326a197cacd6669d8db`; candidate freeze `e36a6f562ddf873993f637777e9b68742385e9870d6c17bde5d093c66b853efe`; prediction freeze `7f5d2d0b3372546d0d2028529f107038c04ea77da160d1f9cbf39907e8098f82`; preflight `1374d6662ac362f86f558ef37fc3a61f3afebc1006efb6cda3e2242023b4360b`; metrics `47c741e32f6588fae30b8e453f0d9473d1b0dfdeb1b314dbf82c31abab0bb178`.

The exact commands, in order, are:

```powershell
.\.venv\Scripts\python.exe -m py_compile src/phase9e_bounded_candidate_v1.py submission/evaluate_phase9e_bounded_candidate_v1.py
.\.venv\Scripts\python.exe -m src.phase9e_bounded_candidate_v1 self-test
.\.venv\Scripts\python.exe -m src.phase9e_bounded_candidate_v1 candidates
.\.venv\Scripts\python.exe -m src.phase9e_bounded_candidate_v1 predict
.\.venv\Scripts\python.exe -m submission.evaluate_phase9e_bounded_candidate_v1 preflight
.\.venv\Scripts\python.exe -m submission.evaluate_phase9e_bounded_candidate_v1 evaluate
```

The run ID is fixed and the runner refuses to overwrite these frozen outputs. Reproduce in an **isolated copy** with the Phase 9E output directories absent; do not delete this run to repeat it. The [candidate freeze](outputs/phase9e_bounded_candidate_20261115_v1/candidate_freeze.json), [prediction freeze](outputs/phase9e_bounded_candidate_20261115_v1/prediction_freeze.json), preflight, and metrics record all parameters and source hashes. Private per-queue candidate/prediction files reside in `data/derived/phase9e_bounded_candidate_20261115_v1/` and are listed by SHA-256 in the freezes.

## What the negative result establishes

The sixth-neighbor cap was indeed excluding positive candidate pairs, but adding this single bounded route did **not** make a recoverable incident or improve ranking. The pair scorer and capped grouping are still the decisive bottlenecks for these additions. A broader neighbor sweep on the same exposed outcomes would be post-hoc model selection. A future study should use authorized, provenance-rich development evidence to distinguish safe missing links and to examine cap-induced partitions, then freeze one method before an untouched confirmation cohort. The [Phase 9B audit](PHASE9B_EVIDENCE_AND_DATA_READINESS.md) records why entity/time fields cannot yet support point-in-time operational claims: source-observation provenance and evidence-arrival times are unavailable, and the official inference allowlist is empty.
