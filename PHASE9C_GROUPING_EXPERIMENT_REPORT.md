# Phase 9C: bounded small-fragment grouping experiment

**Status: NO-GO; retain frozen v2 grouping + v7 ranking.** This is one retrospective exploratory experiment on previously accessed GUIDE_Test labels. It is not independent validation or operational SOC evidence. The grouping variant was fixed in `configs/phase9c_small_fragment_heuristic_v1.json` before the evaluator opened labels. The fitted v7 ranker, candidate graph, alert scope, 80% completeness/purity rule, and tie-aware evaluator were unchanged. No new model was trained and no threshold was changed after evaluation.

## Objective, baseline and scope

The frozen reference covers **499 organization queues, 400,039 unambiguous alerts, 1,942,648 candidate pairs and 9,980 expert top-20 labels**. Its end-to-end Recall@20 is **4,972/9,980 = 49.82%**; 6,969 labels have a complete/pure frozen group (69.83%). Phase 8 identified **1,244** candidate-connected but incomplete 2–10-alert incidents. Among them, **624** have one cross-fragment candidate edge, **429** had no Phase 7 proposal at its 0.40 floor, and **712** were one-merge recoverable only in an evaluator oracle. These retrospective counts motivated a narrow heuristic; they were **not** used as inference inputs or as a parameter search target.

The required `REPOSITORY_CLEANUP_AUDIT.md` was absent from the workspace when this experiment began; its earlier contents had been reviewed in this chat. No cleanup action was attempted. `PHASE9B_EVIDENCE_AND_DATA_READINESS.md`, `PHASE8_RESEARCH_DESIGN.md`, and `src/submission_small_fragment_recovery_v1.py` were inspected. The Phase 9B gate remains blocked for independent source provenance, evidence-arrival timing and authorized fresh data. This Phase 9C run is a **retrospective heuristic only** under the user's explicit exploratory instruction. Different alert endpoints, entity keys, detector names, or CSV rows are **not** treated as verified independent observations.

## Fixed method and prediction freeze

The versioned predictor `src/phase9c_small_fragment_heuristic_v1.py` reads the **441,000 frozen Phase 7 cross-group proposals** and their previously fitted boundary probabilities. Their inherited admission floor is **0.40**, so this first experiment cannot address the 429 historical no-proposal cases. It does not create new candidate pairs or retrain the pair/fragment models. The new rule requires a Phase 7 boundary probability ≥0.70, at least two cross-group candidate edges touching at least two distinct alerts **on each** side, a shared entity occurring in at most ten original groups, shared category or technique, no joint category/technique conflict, ≤48 hours of retrospective alert-time gap, combined fragment size ≤10, and the hard 100-alert cap. It considers at most 1,000 structurally eligible proposals per queue, then requires mutual-best partnership and a ≥0.05 margin over alternative neighbors. Each original group merges at most once; there is no cascading. Single-edge boundaries go to review only. These numeric settings are **fixed exploratory choices**, informed by the already exposed Phase 8 diagnosis rather than independent development selection; they cannot justify confirmatory claims.

The predictor read no incident membership or expert rank. It verified frozen per-organization group, score and Phase 7 decision hashes, applied the label-blind rule, recomputed group features and scores with the **same fitted v7 ranking stack** only for changed groups, and froze 499 versioned prediction files before evaluation. Its [prediction freeze](outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json) records all output hashes and the 499-queue census. It selected **38** noncascading merges; **430,111 proposal boundaries** were marked single-edge review (a proposal count, not the 624 expert-incident count). The selected rule is explicitly marked `exploratory_heuristic_prediction_not_provenance_verified`.

## Matched results

The separate evaluator `submission/evaluate_phase9c_small_fragment_heuristic_v1.py` opened labels only after the prediction freeze and reproduced the exact frozen v2+v7 baseline. [Versioned metrics](outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json) contain all 499 pseudonymous per-organization comparisons.

| Metric, identical 499 queues | Frozen v2 + v7 | Phase 9C heuristic | Change |
|---|---:|---:|---:|
| Candidate pairs | 1,942,648 | 1,942,648 | 0 |
| Predicted groups | 370,850 | 370,812 | −38 |
| Group complete-and-pure recoverability | 6,969 / 9,980 = **69.83%** | 6,966 / 9,980 = **69.80%** | **−3 labels** |
| Incident Recall@20 | 4,972 / 9,980 = **49.82%** | 4,971 / 9,980 = **49.81%** | **−1 label** |
| Grouped-pair precision | **90.4148%** | **90.3682%** | −0.0465 points |
| Grouped-pair true positives | 269,832 | 269,966 | +134 |
| False-positive grouped pairs | **28,606** | **28,774** | **+168** |
| Mixed predicted groups | **4,841** | **4,831** | −10 net |
| Incomplete top-20 labels | 1,451 | 1,448 | −3 |
| Impure top-20 labels | **218** | **224** | **+6** |
| P@10 | **61.5832%** | **61.5832%** | 0 |
| nDCG@20 | **0.437101** | **0.436511** | −0.000590 |

**False-merge analysis:** **25 of the 38** selected merges joined alerts from different expert incidents, adding exactly **168** cross-group false-positive alert pairs. The evaluator reconciled these 168 pairs with the overall FP increase. The net mixed-group count fell by ten because merging can replace two existing mixed groups with one; this count alone would conceal harmful merge decisions. Three expert labels gained a complete/pure group and six lost one, net **−3**. Recall@20 improved in two organizations, worsened in three, and was unchanged in 494. The 135 queues outside fitting remained at **45.52%** Recall@20; the previously exposed 68 holdout queues changed from **49.34% to 49.41%**, which does not rescue the full-cohort safety failure. All subgroup results remain exploratory.

## Acceptance decision

The prespecified gates require higher group recoverability and Recall@20, pair precision ≥90%, no added false-positive grouped pairs or mixed groups, and no P@10 loss. **Only pair precision, net mixed-group count and P@10 pass.** Recoverability and Recall@20 decline; false-positive pairs increase. Impure labels also increase. The rule is **rejected**. The 85% group-recoverability and 80% Recall@20 targets were not achieved. Neither the allowed 85–88% precision trade-off nor any relaxed threshold was invoked. No second variant was selected after seeing this result.

## Tests, resources, hashes and reproduction

Synthetic-only checks passed: **5** predictor assertions, **3** evaluator assertions, and **26** additional regression assertions covering single-edge review, repeated endpoints, common entities, descriptor/time conflicts, low scores, mutual-best and alternative-neighbor behavior, proposal budget, group cap and duplicate proposals. Compilation passed. Prediction took **45.24 s**, peak process RSS **795,324,416 bytes**; evaluation took **14.43 s**, peak process RSS **464,023,552 bytes**, on this local Windows Python environment. These are batch-run measurements, not live SOC latency. A matched same-pass v2+v7 resource measurement was not performed, so no percentage overhead claim is made. The experiment stayed below the three-hour limit.

Run from the repository root with the project virtual environment. `predict` and `evaluate` intentionally refuse to overwrite the already frozen run; the commands reproduce the original execution in a fresh copy where this Phase 9C run ID does not yet exist:

```powershell
.\.venv\Scripts\python.exe -m src.phase9c_small_fragment_heuristic_v1 self-test
.\.venv\Scripts\python.exe -m submission.test_phase9c_small_fragment_heuristic_v1
.\.venv\Scripts\python.exe -m submission.evaluate_phase9c_small_fragment_heuristic_v1 self-test
.\.venv\Scripts\python.exe -m src.phase9c_small_fragment_heuristic_v1 predict
.\.venv\Scripts\python.exe -m submission.evaluate_phase9c_small_fragment_heuristic_v1 evaluate
```

The first evaluator attempt stopped **without writing metrics** because its baseline assertion mistakenly treated per-organization Recall@20 as a count rather than a fraction. The evaluator assertion and aggregation divisor were corrected; the frozen predictor, policy, prediction files and prediction freeze were **not changed**. The final evaluator reproduced baseline and wrote one metrics file. This correction is documented to avoid implying a flawless first pass.

| Versioned file | SHA-256 |
|---|---|
| `configs/phase9c_small_fragment_heuristic_v1.json` | `7d11b9b576e7c2a435a9bcb8d0fa9d71f9e02125515dc83615ce550740759dee` |
| `src/phase9c_small_fragment_heuristic_v1.py` | `bbd8823da86aee80125bd09dfbef3415b2681ae803374245213cc604f87f3fb9` |
| `submission/evaluate_phase9c_small_fragment_heuristic_v1.py` | `6d99c0e509ad9282afd712f18046378d98cfee43b491ca7913ade2d5d61da1bf` |
| `outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json` | `a734427180521f852364650c78fe9fec6ef27cb7af0bbb6161b33adbfecfe78d` |
| `outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json` | `794a02d115d78f6a8a944e0e3c5090ffd962daeabc0b23909d40628d9b279c19` |

Eleven preserved v2/v7/Phase 7/candidate/Phase 9A implementation and freeze hashes were checked before and after the run and remained unchanged. The frozen per-organization hashes were checked during prediction and evaluation. `configs/field_policy.yaml` remains empty for operational features; no original dataset or prior experiment artifact was modified.

## Limits and next action

This heuristic is constrained by Phase 7's 0.40 proposal floor, excludes single-edge incidents from automatic merges, and uses retrospective entity/descriptor/time fields without authoritative observation provenance or evidence-arrival timestamps. The Phase 8 oracle opportunities are **bounds**, not predicted gains. The tested rule increased false merges while losing group recoverability, so the exact next action within this scope is **retain v2+v7 and stop this variant**. Any future variant should be preregistered as a new experiment and should address proposal coverage and false-merge discrimination without using these exposed evaluation outcomes for silent threshold selection. A new untouched labeled cohort remains necessary for a publishable confirmation claim.
