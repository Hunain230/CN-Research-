# Phase 20 — Group-level common-mode safety study

**Decision: NO-GO. Development diagnostic only.** Phase 19's locked cohort was not read, predicted, or evaluated. Phase 16 v4 remains the best safe synthetic result on its own holdout (75.17% recoverability, 67.83% Recall@20, 98.61% grouped-pair precision); Phase 20 supplies no new locked-test evidence and makes no real-SOC claim.

## Study design

The evaluator copied the 15 Phase 19 development queues into a separate stress namespace and used private labels only to construct 103 disjoint incident-pair collisions: 26 shared host/account only, 27 shared host/account plus auth reference, 25 plus network reference, and 25 plus both auth and network references. The observations retain distinct `source_id` values. The predictor receives only cutoff-visible fields and no incident labels. This is label-designed adversarial development coverage, **not independent validation**. The original development data and the Phase 19 locked cohort remain separate.

The `group_guard` diagnostic examines the full proposed merged component. It rejects a merged component containing more than one visible host or account, abstains beyond two seed fragments or 250 cumulative cross-fragment pair exposures, and accepts only rare dual auth/network proposals with distinct source-event witnesses across at least three sensor labels. This tests source-event diversity. Because both lineage references can originate from one simulator controller, these checks **do not establish independent causal provenance**. The exposure count is a label-blind upper bound on possible new pairs; actual true/false pair increments are computed later by an evaluator-only replay.

## Results

| Development cohort and method | Recoverable / 300 | False grouped pairs | Mixed groups | Accepted cross-fragment unions | Worst queue false pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ordinary, frozen Phase 19 baseline | 123 | 0 | 0 | 624 | 0 |
| Stress, frozen Phase 19 baseline | 73 | 2,560 | 22 | 503 | 681 |
| Ordinary, group guard | 1 | 0 | 0 | 208 | 0 |
| Stress, group guard | 0 | 0 | 0 | 126 | 0 |

The stress baseline's 2,560 false pairs are exactly reconciled by 40 accepted unions; the worst union adds 168 and the top five add 704. Fourteen of 15 queues have false pairs, so an aggregate precision measure would conceal a broad queue-level failure. The guard has zero false pairs in this constructed stress set, but zero recoverable incidents in every stress queue and in 14 ordinary queues. It is not a usable reconstruction candidate. Its two-fragment limit also means this study does not isolate whether the cumulative exposure cap would work in larger components.

## Acceptance decision and limitations

For a development candidate to be eligible for future freezing, require nonzero reconstruction in every ordinary development queue, no loss of ordinary recoverability versus the ready Phase 19 baseline, no added false pairs or mixed groups in ordinary or adversarial development, no queue-level common-mode failure, and exact union-level pair reconciliation. The group guard fails the reconstruction conditions. The frozen Phase 19 baseline fails adversarial safety. **Neither is promoted.** No 85% target claim is made.

An independent sensor-origin study must record causal roots outside the shared controller before sensor agreement can support stronger merge claims. A fresh, independently generated development challenge is needed before any rule is frozen; the reserved Phase 19 locked cohort must remain sealed until a candidate passes development gates.

## Reproduction

From the repository root, generate the stress fixture only in a fresh Phase 20 output directory, then run the study and tests:

```powershell
.venv\Scripts\python.exe experiments/PHASE20_GROUP_SAFETY/build_stress.py
.venv\Scripts\python.exe experiments/PHASE20_GROUP_SAFETY/run_study.py
.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE20_GROUP_SAFETY/tests -q
```

The stress builder refuses to overwrite its frozen output, so skip its command when `stress/` already exists. The study runner reuses existing predictions, decisions and evaluations. Primary artifacts: `stress/injections.csv`, `study_summary.json`, `merge_increments.csv`, `ordinary_group_guard_decisions.jsonl`, `stress_group_guard_decisions.jsonl`, and both group-guard evaluation files. Replay assertions reconcile every reported false pair on all four method/cohort combinations. Five tests pass, and each evaluation's prediction hash matches its prediction file.
