# Phase 22 — Receipt verification robustness

**Decision: NO-GO for model promotion.** The Phase 21 `decide` verifier was copied unchanged and checked by AST equality. Phase 22 uses a fresh `phase22a_` synthetic cohort: four train queues, ten development queues, and 20 newly reserved locked queues. Neither the Phase 19 nor Phase 22 locked truth was read; no locked predictions or evaluations were produced. Phase 16 v4 remains the best safe synthetic holdout result on its separate population.

## Challenge

Each development queue has 12 incidents and six pairs of unrelated incidents sharing host, account, auth and network context. The ten queues rotate across five failure modes (two queues each): missing/delayed receipts, duplicate source observations and transformations, incorrect cross-incident parent claims, one corrupted sensor receipt, and two corrupted receipts with a shared upstream failure. Three causal graph shapes are represented: fork/merge, chain/cross, and three fragments. All alerts, claims, and receipts retain field-level receiver availability. Private physical events and fault records are kept separate from model-visible inputs. The challenge is intentionally constructed and is not independent real-SOC validation.

The frozen Phase 21 rule requires two distinct causal child roots from different sensors and validates each claimed parent relationship against a receiver-visible source receipt. A *development diagnostic* accepts one verified edge to examine the recovery cost of missing corroborating receipts. This partial rule was not selected or frozen for the holdout. Predictions for every rule and development/train queue were written and hashed before private truth was opened for audit.

## Development results

| Rule | Recoverable / 120 | False grouped pairs | Accepted unions | Unions with false physical claims |
| --- | ---: | ---: | ---: | ---: |
| Sensor labels only | 1 | 18,321 | 137 | 60 |
| Distinct roots only | 41 | 3,224 | 87 | 10 |
| Frozen Phase 21 verified edges | 44 | 300 | 72 | 2 |
| One verified edge diagnostic | 95 | 1,724 | 141 | 4 |

The frozen verifier's two false accepted unions occur in the **shared-upstream** queues. A later union into a contaminated group also adds false pairs, so three accepted unions account for all 300 false pairs. The worst development queue has 168. A single compromised receipt did not produce false pairs for the frozen two-edge rule in these two queues; the same failure mode *did* produce false pairs for the partial rule.

The partial rule reaches 95/120 (**79.17%**) recoverability, including gains in missing/delayed and three-fragment queues. It is unsafe: 1,724 false pairs, ten false-pair-creating unions, and a worst single union of 276 false pairs. Its apparent pair precision remains above 90% because the true-pair denominator is large; that aggregate number would conceal the queue-level failures. Recoverability from partial evidence therefore remains an open research problem. The Phase 21 rule itself drops from 46/96 on its own constructed challenge to 44/120 (**36.67%**) on this different challenge; these cohorts are not directly comparable.

## Mechanism and limits

Missing or late receipts cause the verifier to abstain, as intended. Duplicate source observations retain the same physical origin and are not independent causal roots. Incorrect claims without matching receipts are rejected. The trust boundary fails when two sensor receipts carry the same false upstream parent relationship: each claim passes local verification, and together they satisfy the two-edge rule. The simulator has private fault records and physical event truth to audit this failure, but the rule does not observe those private labels.

The experiment has only two development queues per failure mode, and the schedule correlates some graph shapes with failure modes. It does not establish a general failure rate. No candidate passes a development safety gate requiring no false-pair increase in every queue under common-mode corruption while retaining useful recoverability. **Do not open either locked cohort or claim the 85% target.** A future design must establish trust diversity across upstream sources, or a way to detect correlated receipt corruption, before using one or two receipts to recover more fragments.

## Reproduction

Run the generator only if `datasets/` is absent; it refuses overwrite. Then run:

```powershell
.venv\Scripts\python.exe experiments/PHASE22_RECEIPT_ROBUSTNESS/generate.py
.venv\Scripts\python.exe experiments/PHASE22_RECEIPT_ROBUSTNESS/run_study.py
.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE22_RECEIPT_ROBUSTNESS/tests -q
```

Artifacts: `datasets/manifest.json`, `freeze_manifest.json`, `summary.json`, `queue_audit.jsonl`, `union_pair_increments.csv`, rule-specific predictions and decisions, and `datasets/{train,development}/faults_private/`. Evaluator-only replay reconciles the final false-pair count to every accepted union. Eight tests pass, including the frozen verifier check, failure-mode coverage, availability, duplicate-root semantics, pair accounting, and both sealed-cohort checks.
