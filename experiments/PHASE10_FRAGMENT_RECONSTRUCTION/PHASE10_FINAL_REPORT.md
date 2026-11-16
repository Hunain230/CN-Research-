# Phase 10: Fragment reconstruction result

**Decision: NO-GO.** On the matched 499-queue retrospective GUIDE_Test population, none of the new C policies improves net group recoverability or satisfies the safety gates. The 69.83% fixed-group ceiling was **not** exceeded. The 80% Recall@20 and 85% recoverability targets were not achieved. Prior GUIDE_Test label access makes all results exploratory, not independent confirmation or production evidence.

## Motivation and architecture

Frozen v2 grouping recovers 6,969/9,980 expert top-20 incidents as complete and pure groups, leaving 1,451 candidate-connected but incompletely grouped. Phase 9F found that 1,445 of those incidents have no genuine cross-fragment candidate edge at the frozen 0.75 threshold; high-scoring cross-incident edges and the 100-alert cap complicate direct threshold changes. Phase 9C, 9E, and 9G were unsuccessful. This experiment retains **C/P/V**: C reconstructs from coherent frozen fragments, P keeps the frozen v7 and selected 75% child40 / 25% v7 rankers, and E4/E5 add a label-free V consistency veto. The existing provider-based V remains unchanged and passed 34 synthetic assertions, but it could not verify GUIDE merges empirically because source-observation IDs are absent.

The label-free method aggregates all pair evidence on viable fragment boundaries. Its score is `0.20 max(pair) + 0.20 mean(pair) + 0.25 min(reciprocal coverage) + 0.15 shared entity + 0.10 category-or-technique agreement + 0.10 exp(-time gap/24h) - 0.30 joint descriptor conflict`. E2 applies mutual-best noncascading matching; E3 permits bounded hierarchical unions with all-cross-fragment direct support; E4 adds a verification veto for weak endpoint coverage, time gaps, and descriptor contradiction. Every union is capped at three original fragments and 100 alerts. Scores, evidence summaries, accepted merges, and rejection reasons are saved in the compressed provenance output. Full details and exact fixed thresholds are in `PHASE10_METHODOLOGY.md` and `PHASE10_EXPERIMENT_CONFIG.json`.

## Matched results

All experiments use 499 queues, 400,039 unambiguous alerts, 1,942,648 frozen candidate edges, 9,980 expert top-20 labels, and the existing 80% completeness/purity and tie-aware ranking definitions. E5 is the E4 verification grouping with the selected fixed ranking blend. Absolute counts accompany percentages; the CSV contains all required metrics and cascade states.

| Experiment | Recall@20 | Recoverability | P@10 | nDCG@20 | Pair precision | False pairs | Mixed groups | Merges / bad merges |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E0 frozen v2 + v7 | 4,972/9,980 = 49.82% | 6,969/9,980 = 69.83% | 61.58% | 0.437101 | 90.4148% | 28,606 | 4,841 | 0 / 0 |
| E1 frozen v2 + blend | 5,066/9,980 = 50.77% | 6,969/9,980 = 69.83% | 63.88%* | 0.469747 | 90.4148% | 28,606 | 4,841 | 0 / 0 |
| E2 mutual fragments + v7 | 4,968/9,980 = 49.78% | 6,944/9,980 = 69.58% | 61.72% | 0.434389 | 89.446% | 32,486 | 4,857 | 593 / 364 |
| E3 hierarchy + v7 | 4,959/9,980 = 49.69% | 6,938/9,980 = 69.52% | 61.72% | 0.435192 | 88.530% | 36,208 | 5,036 | 1,793 / 1,043 |
| E4 verified hierarchy + v7 | 4,961/9,980 = 49.71% | 6,939/9,980 = 69.53% | 61.60% | 0.434166 | 89.664% | 31,705 | 4,832 | 365 / 217 |
| E5 verified hierarchy + blend | 5,051/9,980 = 50.61% | 6,939/9,980 = 69.53% | 63.86% | 0.465193 | 89.664% | 31,705 | 4,832 | 365 / 217 |

*E1's exact P@10 is 63.8778%; 63.88% is the previously reported rounded benchmark. E5's exact P@10 is 63.8577%, lower than E1. Reconstructed incident counts above count accepted fragment unions, not newly recovered expert incidents. E2/E3/E4/E5 reject 112,769 / 111,569 / 112,997 / 112,997 viable fragment proposals respectively; no output group exceeds 100 alerts. Gross alerts in newly recoverable expert incidents are 74 / 159 / 57 / 57 respectively, before losses elsewhere. Prediction and evaluation took 197.26 and 33.39 seconds in shared batches, with peak process RSS 795.7 MB and 582.1 MB; per-policy resource attribution was not measured.

## Error cascade and interpretation

The full cascade is in `PHASE10_ERROR_ANALYSIS.md` and the CSV. E3 reduces incomplete connected incidents from 1,451 to 1,411, but complete-but-impure incidents rise from 218 to 289, so net recoverability falls by 31. E4's verifier reduces the accepted merges from 1,793 to 365 and cuts bad merges from 1,043 to 217, yet impurity still rises to 259 and recoverability falls by 30. The mixed-group count falls by nine in E4/E5 despite 217 bad merges; mixed-group count alone is therefore insufficient as a safety measure. E5 recovers 15 fewer top-20 labels than the unchanged-group E1. The outside-scope 855 and candidate-disconnected 487 labels are unchanged by these frozen-graph methods.

## Research objectives, classified for E5

| Target | Status | Measured E5 |
|---|---|---:|
| Recall@20 ≥80% | **Not achieved** | 50.61% |
| Group recoverability ≥85% | **Not achieved** | 69.53% |
| P@10 ≥63.88% | **Partially achieved** | 63.8577%, close to the rounded benchmark but below the exact threshold and E1 |
| Grouped-pair precision ≥90% | **Not achieved** | 89.6642% |
| No increase in mixed groups | **Achieved** | 4,832 versus 4,841, but does not imply safe merges |
| No material increase in false grouped pairs | **Not achieved** | 31,705 versus 28,606, +3,099 |

The secondary gates of Recall@20 >50.77% and recoverability >69.83% also fail. The 69.83% ceiling was **not genuinely exceeded** by any policy. No pipeline replacement is warranted.

## Limits and next experiment

The repository's official field policy approves no operational model fields. Shared entity, descriptor, candidate score, and noisy alert-creation time are retrospective research-only proxies; original source-observation IDs and evidence-arrival timestamps are absent. Distinct alert endpoints and entity keys can stem from the same upstream event. No threshold was selected from this Phase 10 outcome, but past GUIDE_Test exposure precludes an independent claim. The existing 100-alert cap makes >125-alert expert incidents mathematically unrecoverable under the 80% completeness rule; this run did not vary the cap.

**Single most valuable next experiment:** obtain a newly authorized development cohort with source-observation IDs, derivation links, and evidence-arrival times, then train and freeze a fragment-level complete-and-pure incident objective with explicit high-score cross-incident hard negatives. Evaluate once on a separate untouched cohort. This directly tests whether independent provenance can distinguish true continuity from shared infrastructure before considering a cap change or live use.
