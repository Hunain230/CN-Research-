# SOC threat correlation and incident prioritization

This repository is a **retrospective research implementation**, not a deployed SOC. It tests whether alerts can be grouped into incidents, ranked for analyst review, and checked for evidence support through correlate (C), prioritize (P), and verify (V) roles.

## Read this project in order

1. [CONTEXT.md](CONTEXT.md): research methodology, data, implementation, metrics, and unresolved gates.
2. [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md): what each stage and later iteration actually produced.
3. [Phase 3 report PDF](submission/PHASE3_IMPLEMENTATION_REPORT.pdf), [editable report](submission/FINAL_REPORT.md), [delivery checklist](submission/DELIVERY_CHECKLIST.md), and [known limits](submission/KNOWN_LIMITATIONS.md).
4. [Reproduction instructions](submission/REPRODUCE.md) and [experiment register](submission/EXPERIMENT_REGISTER.md).

The [matched ranking-baseline extension](submission/PERFORMANCE_BASELINE_STUDY.md) records the later 334/135 organization-split study and its negative rank-fusion control.
The [full-GUIDE ranker extension](submission/FULL_GUIDE_RANKER_AND_GROUP_CEILING_20261114.md) adds an exploratory 499-queue ordering comparison and measures the frozen grouping ceiling.
The [correlation/grouping iteration](submission/CORRELATION_GROUPING_ITERATION_20261114.md) trains a pair scorer on separate organizations and evaluates a stricter development-selected link rule on 57 complete small queues.
The [full 499-queue entity/time sensitivity](submission/FULL_499_ENTITY_TIME_SENSITIVITY_20261114.md) extends candidate and grouping experiments to every ranked organization. The [future-cohort and shadow-mode gate](submission/FRESH_COHORT_AND_SHADOW_GATE.md) states what is still needed for confirmation and live evaluation.
The [entity/time model re-evaluation](submission/ENTITY_TIME_MODEL_REEVALUATION_20261114.md) records the later full-queue pair model, candidate bound, and component-cap tradeoff.
The [incident miss and priority iteration](submission/INCIDENT_MISS_AND_PRIORITY_ITERATION_20261114.md) audits why v2 misses expert labels, evaluates a stronger ranker on the same groups, and records a negative link-bridging control. The [point-in-time field assessment](submission/POINT_IN_TIME_EVIDENCE_STATUS_20261114.md) tracks evidence availability.
The [priority, grouping, candidate, and source-scope follow-up](submission/PRIORITY_GROUP_CANDIDATE_FOLLOWUP_20261114.md) records the later hard-negative ranker, constrained merge, wider candidate, and raw queue-scope audits.

## Current evidence

| Evaluation | Scope | Observed result |
|---|---|---|
| Full offline baselines and transferred ranker | 499 GUIDE_Test organizations; 400,039 unambiguous alerts | Candidate recall 37,018/159,186,107 = 0.0233%; transferred-ranker end-to-end Recall@20 0.1413 vs matched BM25-like 0.1364. The full cohort includes ranker training organizations. |
| Local `qwen2.5:3b` C/P/V | 20 previously accessed organizations; 240 selected pairs, 22 positives | C pair recall 1/22; B2 single-model recall 2/22; C+P end-to-end Recall@20 0.1443 on 400 expert labels |
| Local model operations | 188 localhost calls | Per-call p50 27.125 s, p95 43.617 s; 60.0% group review fraction |
| Trained offline ranker | Same frozen groups on 135 separate evaluation organizations | Recall@20 0.1542 vs matched BM25-like 0.1507; P@10 0.2351 vs 0.1971; candidate and pair metrics unchanged |
| Learned pair grouping, exploratory | 57 previously exposed complete small queues; 11,219 alerts; frozen 1,216,600 candidates | End-to-end Recall@20 **0.3179** vs matched rule groups **0.1678**; P@10 **0.4087** vs **0.2772**; pair F1 fell to 0.1197 from 0.1364 |
| Entity/time sensitivity, exploratory | All 499 ranked organizations; 400,039 alerts; local-only unapproved entity/time fields | End-to-end Recall@20 **0.3095** vs matched frozen-rule/transferred-ranker **0.1413**; candidate positive-pair recall 0.4396% vs 0.0233%; pair F1 fell to 0.00243 from 0.00910 |
| Entity/time pair model v2, exploratory | Same 499 queues and candidate set; training on 334 organizations, threshold selected on 42 development queues | End-to-end Recall@20 **0.3397** vs matched earlier entity/time rule **0.3095**; P@10 **0.4233** vs **0.3860**; pair precision **0.9041** vs **0.2157**; observed-group oracle-order ceiling **0.6983** |
| V4 group priority model, exploratory | Same frozen v2 candidates and groups across 499 queues; fit on 334 historical training organizations | End-to-end Recall@20 **0.4223** vs matched v2 ranker **0.3397**; on 135 training-disjoint organizations **0.4106** vs **0.3420**; pair metrics and grouping ceiling unchanged |

The full offline, trained ranking, and Qwen evaluations have different cohorts or candidate policies; compare only methods within the same recorded cohort. Predictions were frozen before the separate evaluator read evaluation labels, but earlier work had already accessed those labels. The proposed 95% end-to-end target was not met. The [capacity audit](outputs/submission_retrieval_bounds_20261114_v1.json) finds a 9,063/9,980 = 90.81% optimistic ceiling under the current exclusion and 100-alert component cap, and shows that the 20-neighbor rule cannot reach 99% positive-pair candidate recall on this dataset.
For the **actual frozen full-run groups**, the [evaluator-only oracle-order diagnostic](outputs/submission_full_group_ceiling_20261114_v1.json) finds that just 2,311/9,980 top-20 labels are recoverable at all (23.16% ceiling). This is a diagnostic upper bound, not achieved recall.
For the **new 57-queue learned groups**, the oracle-order ceiling is 667/1,140 (58.51%). The 85% absolute Recall@20 target remains unmet; that small-queue result cannot be projected onto all 499 organizations.
The new full-run groups have an oracle-order ceiling of 6,143/9,980 (61.55%). Their 30.95% achieved Recall@20 remains exploratory because all labels were previously accessed and entity evidence availability at alert creation is unresolved. The official operational feature allowlist is still empty.
The later v2 model raises that observed-group ceiling to 6,969/9,980 (69.83%). A development-selected smaller-cap v3 run reached 34.15% Recall@20, but its 0.19-point paired gain includes zero and its pair precision and historical-holdout recall declined. V2 is the frozen method for any new cohort. Neither variant achieved the 80% target.
The latest v4 ranking run reaches 42.23% on all 499 with the same v2 groups. Its historical training-disjoint result is 41.06%, but all GUIDE_Test labels had previously been accessed. V2 grouping plus v4 ranking is now frozen for any new cohort. A corroborated bridge-link variant was not adopted because its small full-queue gain was uncertain and its historical holdout and group ceiling declined. The 80% target remains unmet.
The later hard-negative ranker reaches 43.99% descriptively on all 499, but does not improve the 135 training-disjoint queues or 68 historical holdout. Constrained group merges underperform on development queues. Wider candidates more than double pairs for three additional oracle-connectable development labels. The 855 top-20 labels absent from model scope are absent from raw GUIDE_Test incident pairs too; all remain in the denominator. The frozen v4 choice is unchanged.

## Repository map

| Path | Purpose |
|---|---|
| `src/` | Validation, preprocessing, baselines, C/P/V agents, isolated evaluators, offline and local-model runners |
| `configs/` | Field policies, schemas, protocol, and method settings |
| `data/raw/`, `data/derived/` | Local GUIDE inputs and restricted records; ignored by Git |
| `fixtures/` | Fictional checks and frozen expected outputs |
| `outputs/` | Versioned metrics and run manifests; historical outputs retained |
| `phases_outputs/` | Dated phase records, amendments, and gate decisions |
| `submission/` | Report, figures, verification, and reproduction material |
| `dashboard/` | Saved aggregate viewer and separate fictional playback |

Historical phase specifications remain at the repository root. Historical run reports remain inside their versioned output directories. The root README and CONTEXT are the canonical starting points.

## Run and inspect

From PowerShell in the repository root:

```powershell
.\.venv\Scripts\python.exe -m submission.verify_package
.\.venv\Scripts\python.exe -m submission.measure_local_operations
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Open `http://127.0.0.1:8765/` for saved aggregate results or `http://127.0.0.1:8765/simulation.html` for clearly marked fictional events. For a new full offline and bounded local-model run, follow [REPRODUCE.md](submission/REPRODUCE.md); the Qwen stage can take hours on CPU. No hosted model call is authorized by the current field policy.

## Submission status

This is an **exploratory, partial Phase 3 submission**. The proposed held-out matched B0–B4/C/P/V comparison, perturbations, blinded citation review, and operational SOC evaluation remain incomplete. The Phase 2 methodology defines an offline study and reserves live SOC productivity for a later field study. Do not claim production readiness or that multiple agents improve recall.
