# Error analysis after the performance sprint

**Scope:** 499 historical GUIDE_Test queues, 400,039 unambiguous alerts, and 9,980 expert top-20 labels. All categories use the unchanged 80% incident completeness and 80% group purity rule. The selected rank fusion retains the frozen entity-enabled candidates and v2 groups, so it does not change candidate, grouping, pair, or mixed-group counts. All label-based diagnoses are evaluator-side retrospective analyses.

| Exclusive first failure or result | Frozen v2+v7 labels | Selected fusion |
|---|---:|---:|
| Outside unambiguous alert scope | 855 | 855 |
| Insufficient true candidate connectivity | 487 | 487 |
| Candidate connected, v2 group incomplete | 1,451 | 1,451 |
| Complete v2 group impure | 218 | 218 |
| Complete and pure group ranked below top 20 | 1,997 | About 1,902.5 expected |
| Recovered in top 20 | 4,972 | 5,066.5 expected |

The fractional selected-fusion outcomes are tie-aware expectations. The first four categories sum to **3,011 structurally unrecoverable labels under the current fixed groups**. Ranking can rearrange only the remaining **6,969**. This is why the selected method improves Incident Recall@20 from 49.82% to 50.77% while group recoverability stays 69.83%.

## Candidate failures: 487 labels

“Candidate disconnected” means no same-incident candidate component can cover 80% of an expert incident in the evaluator oracle; it does not mean zero candidate edges. Of the 487 labels, **350 have 2–10 in-scope alerts**, **112 have 11–100**, and **25 have more than 100**. Among the 350 small cases, 159 have no shared usable entity or technique across candidate components, while 40 have a route-prefilter-eligible missing pair compatible with the five-neighbor cap. Those counts are retrospective signal inspections, not predicted recoveries. Phase 9E previously added 49,455 candidate pairs and connected four additional labels without improving actual group recovery. Broader retrieval needs incremental coverage and false-merge evidence before adoption.

## Grouping failures: 1,451 split and 218 impure labels

All 1,451 candidate-connected but incomplete labels have at least one true cross-fragment candidate edge. **1,445** have no true edge at or above v2's fixed 0.75 threshold; the other six are blocked by the 100-alert component cap. Of the 1,451, **1,244** have only 2–10 alerts. The best-edge score and feature audits show substantial overlap between missed true boundaries and false links. A blanket threshold reduction is therefore unsupported. Phase 9G demonstrated the risk: pair precision collapsed to 54.98% and false grouped pairs rose almost fivefold.

The 218 complete-but-impure labels fail the 80% purity rule. The frozen groups contain **28,606** false grouped alert pairs across **4,841** mixed groups. Consensus splitting reduced those counts to **21,905** and **381**, respectively, with **zero new** and **6,701 removed** cross-incident alert coassignments, but removed **15,521 true grouped pairs** and lost **523 recoverable labels**. It provides evidence that a second partition can identify many false links, but this broad veto cannot distinguish them safely enough from true small groups. The number of mixed groups alone is an inadequate safety metric: Phase 9G reduced mixed groups while introducing **136,565** new false grouped pairs and removing 27,287 old ones, a net increase of **109,278**.

## Ranking failures and uncertainty

Frozen v7 left **1,997** recoverable labels below the first 20 positions. Validation-selected rank fusion reduces this to about **1,902.5 expected** labels. On all 499 queues, the Recall@20 gain is **0.95 percentage points**, with paired queue-bootstrap 95% interval **−0.02 to +1.91 points**. The 135 outside-fitting queue gain is **3.94 points**, interval **+2.24 to +5.67 points**. The historical 68-queue holdout gain is **4.49 points**. These intervals and subgroups are descriptive because the cohort was previously exposed; they are not independent significance tests.

The 50% fusion weight produced 51.03% all-499 Recall@20, above the validation-selected 75% weight's 50.77%. The 50% method remains unselected. Adopting it because of its all-499 result would use evaluation outcomes for post-hoc model selection.

## Scope and achievable limits

**855** expert labels have no alert under the current unambiguous-assignment rule, and **62** top-20 incidents exceed 125 in-scope alerts, making 80% completeness impossible with a 100-alert group cap. The gold-aware candidate-connectivity bound is **8,638/9,980 = 86.55%**; this is not an achieved result. The actual fixed-group bound is **6,969/9,980 = 69.83%**. Even a perfect ranking of current groups cannot meet the proposed 80% Recall@20 target. Improving all 1,451 split labels while preserving everything else would yield at most **8,420/9,980 = 84.37%** group recoverability, below the 85% group target. This arithmetic does not predict what a real method can achieve.

The data has no authoritative source-observation IDs or evidence-arrival times, and the operational feature allowlist is empty. Alert IDs, separate CSV rows, shared entities, and shared ATT&CK labels cannot by themselves certify independent supporting evidence. A future group-boundary study should obtain authorized provenance and a sealed validation cohort, target complete-and-pure incident recovery, and explicitly constrain false grouped pairs, pair precision, P@10, and mixed groups.
