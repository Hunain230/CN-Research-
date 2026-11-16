# Phase 13 final report — PARTIAL IMPROVEMENT (retrospective sensitivity only)

**Research decision:** no pipeline replacement. E1 reproduced exactly. A frozen 50/50 rank blend scores +26 Recall@20 labels and +0.4275 P@10 percentage points on the full exposed GUIDE cohort, but was not validation-selected and has lower nDCG. All newly run C threshold variants lose group recoverability despite safer pair counts. The original 80%/85% targets remain unmet; the 69.83% fixed-group ceiling was not broken. The classification **PARTIAL IMPROVEMENT** refers only to measured retrospective ranking metrics, not independent generalization or a successful reconstruction redesign.

## Completed work

- Audited C/P/V dependencies, feature policy, frozen artifacts and exact evaluators; reproduced Phase 10 E1 field-for-field on 499 queues and 9,980 labels.
- Ran label-blind full-population candidate-route ablations and four grouping thresholds, with evaluator-only truth opened after prediction freeze. Produced a 9,980-row incident-level error table.
- Implemented and tested a label-blind weak-bridge graph split; froze all 499 queue predictions before its evaluator opened truth.
- Reran exact tie-aware ranking for five existing frozen score vectors on unchanged groups.
- Compared paired recovery gains/losses, runtime, peak process RSS, and original safety gates. No new pair model or V model was trained; no Phase 10 artifact was changed.

## Main measured results

| C threshold | Recoverable | Pair precision | False pairs | Mixed groups | New / lost recoverable |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.75 | 6,969/9,980 (69.83%) | 90.4148% | 28,606 | 4,841 | — / — |
| 0.8 | 6,877/9,980 (68.91%) | 95.0366% | 11,203 | 3,222 | 60 / 152 |
| 0.85 | 6,678/9,980 (66.91%) | 96.8039% | 2,836 | 1,130 | 102 / 393 |
| 0.9 | 6,501/9,980 (65.14%) | 97.4217% | 801 | 500 | 131 / 599 |

| Frozen ranking, fixed E1 groups | Recall@20 | P@10 | nDCG@20 |
| --- | ---: | ---: | ---: |
| v7 | 4,972/9,980 (49.82%) | 61.5832% | 0.437101 |
| blend_0.25 | 5,035/9,980 (50.45%) | 63.5772% | 0.446895 |
| blend_0.5 | 5,092/9,980 (51.03%) | 64.3053% | 0.458297 |
| blend_0.75 | 5,066/9,980 (50.77%) | 63.8778% | 0.469747 |
| child40 | 5,008/9,980 (50.18%) | 62.7620% | 0.474352 |

For the stricter C policies, ranking metrics were **not measured** because changed groups were not rescored. The exact comparison CSV leaves them blank; no fabricated end-to-end result is attached to these C-only experiments. Candidate route counts, full cascade, paired gains/losses, and source hashes are in the accompanying files.

The weak-bridge graph split cut 4,665 edges and reached 6,903/9,980 recoverability, 91.3767% pair precision, 23,720 false grouped pairs, and 3,347 mixed groups. It gained 59 recoverable incidents but lost 125 (net -66); no ranking metric was measured for its changed groups.

## Targets

| Target | Outcome |
| --- | --- |
| Incident Recall@20 ≥80% | **Not achieved.** Best measured frozen-score sensitivity: 5,092/9,980 = 51.03%; validation-selected E1: 5,066/9,980 = 50.77%. |
| Group recoverability ≥85% | **Not achieved.** Best measured remains E1 6,969/9,980 = 69.83%; stricter C falls below it. |
| P@10 ≥63.88% literal | **Achieved only by unselected 50/50 sensitivity** at 64.3053%; E1 exact 63.8778% is marginally below literal 63.88%. |
| Grouped-pair precision ≥90% | **Achieved** by E1 and stricter C sensitivities; the latter lose recovery. |
| No increase in mixed groups | **Achieved** by E1 and stricter C sensitivities. |
| No increase in false grouped pairs | **Achieved** by E1 and stricter C sensitivities. |

The target set is not proven mathematically impossible under the current candidate graph: the optimistic cap-aware recoverability ceiling is 8,596/9,980 = 86.13%, slightly above 85%. However, attaining 85% requires net recovery of 1,514 labels while preserving safety, and current pair evidence cannot distinguish many true weak links from hard false links. GUIDE has no approved operational model fields or point-in-time evidence availability. All GUIDE_Test results are retrospective exploratory because labels were previously exposed. A new independent cohort is necessary for a defensible generalization claim.
