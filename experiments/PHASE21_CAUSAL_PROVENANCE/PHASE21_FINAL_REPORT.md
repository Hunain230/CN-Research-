# Phase 21 — Independently auditable causal provenance

**Decision: simulator foundation demonstrated on a constructed development challenge; model promotion NO-GO.** Phase 19's locked cohort was not opened. Phase 16 v4 remains the strongest safe synthetic holdout result. This phase does not establish the 85% recoverability target or real-SOC performance.

## Foundation and trust boundary

`generate.py` creates a fresh `phase21a_` namespace with three train and eight development queues, 12 malicious incidents and six unrelated incident pairs sharing the same host, account, auth reference, and network reference per queue. It generates a private physical event graph, then four sensor simulators with separate random streams and separately written source records. Every alert has a source-record ID and transformation ID; duplicate alerts retain the same source root. Each causal claim names a parent event, child origin event, source record, and two fragments. Receiver-visible sensor receipts independently state which parent events the sensor observed for its child event. Alert, claim, and receipt fields have receiver-availability ledgers; inference uses only fields available by minute 100.

The private audit traces alert → transformation → sensor record → physical event, and claim → sensor record → physical parent/child edge. It also checks each receiver receipt against the physical graph. This is **independently auditable within the simulator**, because the decision rule sees neither private incident labels nor the physical graph. It is still one synthetic world generator; physical causal truth and sensor receipts are not external observations. The verified-edge rule assumes a sensor receipt faithfully records the parent relationship. Compromised or jointly erroneous receipts are outside this challenge.

The authoritative challenge is `datasets_v3/`. Earlier `datasets/` and `datasets_v2/` are retained exploratory fixtures; they are not included in the results below. The v3 fixture adds eight development pairs with two distinct but false resource-event roots, exposing errors that a distinct-root count alone misses.

## Predefined diagnostic decisions

All rules start with the same session fragments and use the same point-in-time inputs. `sensor_labels_only` accepts two sensor labels; `causal_roots` accepts two distinct event roots from two sensors; `verified_edges` first rejects a claim unless its source receipt independently confirms the named parent event and fragment, then requires two distinct verified child roots and two sensors. The three outcomes are accept, reject, and abstain. No thresholds were searched. All three prediction files were written and hashed before private truth was opened for the audit.

| Rule on fresh development challenge | Recoverable / 96 | False grouped pairs | Accepted unions | Accepted unions with false physical claims |
| --- | ---: | ---: | ---: | ---: |
| Two sensor labels | 0 | 16,391 | 94 | 48 |
| Two distinct causal roots | 37 | 3,288 | 54 | 8 |
| Two receiver-verified causal edges | 46 | 0 | 46 | 0 |

The verified-edge rule rejects **104** false development claims and abstains on 39 proposals with insufficient verified support. It recovers at least two incidents in every development queue, but only **47.92%** overall. The train result is 17/36 recoverable with zero false pairs. These are synthetic, within-cohort measurements on a deliberately structured challenge and cannot be compared directly with Phase 16's locked result.

The distinct-root rule's eight incorrect development unions create false pairs directly and contaminate later unions: **10** accepted unions add false pairs, totaling 3,288. The worst adds 667 and the top five add 2,040. The evaluator-only replay records the true/false pair increment after every accepted union and reconciles the final group counts for all rules and queues. This confirms that even independent physical roots do not prove a claim is correct; the asserted parent relationship must be checked.

## Research decision

Phase 21 establishes a workable *simulator audit mechanism*: separate sensor records and receiver receipts can be traced to distinct physical causal events, and a label-blind verifier can reject the constructed common-mode and independent-error claims. **It does not establish a general correlation solution.** The verified rule's 47.92% development recoverability misses 85%, and the challenge explicitly supplies clean parent relationships in trusted receipts. Before any model selection or locked testing, the next independent challenge should vary causal graph shapes, missing and delayed receipts, duplicate transformations, shared resources, and incorrect or compromised receipts. Those cases should be generated outside the rule's construction path and assessed by queue and union-level false-pair growth.

## Reproduction and artifacts

From the repository root, run `generate.py` only if `datasets_v3/` is absent; the builder refuses overwrite. Then run the study and tests:

```powershell
.venv\Scripts\python.exe experiments/PHASE21_CAUSAL_PROVENANCE/generate.py
.venv\Scripts\python.exe experiments/PHASE21_CAUSAL_PROVENANCE/run_study.py
.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE21_CAUSAL_PROVENANCE/tests -q
```

The primary artifacts are `datasets_v3/manifest.json`, `freeze_manifest.json`, `summary.json`, `queue_audit.jsonl`, `union_pair_increments.csv`, and the three rule-specific prediction and decision files. Nine tests pass, including source-root deduplication, receipt validation, receiver availability, union reconciliation, adversarial coverage, freeze hashes, and the Phase 19 locked-cohort guard.
