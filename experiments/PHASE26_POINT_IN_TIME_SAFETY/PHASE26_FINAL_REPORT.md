# Phase 26 final report — NO-GO

The authoritative fresh development cohort is `v2/phase26b`: 12 scenario-disjoint training queues and 20 development queues, with 25 incidents per development queue (400 incident opportunities) and 75 interleaved benign source observations per queue. Pilot `phase26a` was diagnostic and was superseded before the authoritative run. No Phase 26 locked holdout was generated or opened because no development candidate met the predeclared improvement and safety gates.

## Same-cohort development result

| Reconstruction / ranker | Recoverable /400 | Recall@20 /400 | P@10 /200 | Pair precision | False pairs | Mixed groups |
|---|---:|---:|---:|---:|---:|---:|
| context / progression | 154 | 141 | 67 | 91.74% | 1248 | 46 |
| context / blend | 154 | 150 | 68 | 91.74% | 1248 | 46 |
| orthogonal_veto / linear | 205 | 202 | 75 | 99.24% | 125 | 81 |
| orthogonal_veto / blend | 205 | 199 | 90 | 99.24% | 125 | 81 |
| pit_complete / blend | 90 | 88 | 45 | 99.97% | 3 | 1 |
| pit_selective / blend | 115 | 114 | 54 | 99.97% | 3 | 1 |
| pit_direct / blend | 106 | 105 | 51 | 99.42% | 63 | 21 |
| pit_group / blend | 90 | 88 | 45 | 99.97% | 3 | 1 |

The same-cohort baseline is context reconstruction plus progression ranking: **141/400 Recall@20 (35.25%)**, **154/400 recoverability (38.50%)**, 1,248 false pairs and 46 mixed groups. Orthogonal veto plus blend reached 199/400 Recall@20 (49.75%, +14.50 percentage points) and 205/400 recoverability, but created **80 controlled delayed-contradiction false merges** and regressed mixed-group safety in 16 of 20 queues. Its 99.24% pair precision does not offset those failures. The safest selective rule (`pit_selective` plus blend) had only 3 false pairs and 1 mixed group, but fell to 114/400 Recall@20 (28.50%) and 115/400 recoverability. None was eligible for holdout.

The 80% Recall@20 target is 320/400 on this development denominator. The baseline is 179 incidents (44.75 points) short; the highest-recall unsafe candidate is 121 incidents (30.25 points) short. These figures do not replace the historical Phase 25 locked 331/600 (55.17%) or Phase 16 v4 selected holdout 67.83%; cohorts differ. Phase 24's 48.44% was development recall.

## Mechanism and decision

The point-in-time ledger exposes only receiver-visible observations at minute 100. It distinguishes supported, contradicted, pending, unavailable, unknown, and unverified fields. A future correction does not change the minute-100 snapshot hash. This fixes the *temporal access path* but cannot make insufficient current evidence safe to merge. Unchanged Phase 25 orthogonal-veto logic still accepts process-only relationships before host contradiction arrives. Requiring completeness or maturity abstains on those cases, but fragments genuine incidents. Two apparent direct receipts can share a corrupted upstream controller; `pit_direct` still made 20 controlled false merges.

The original C-P-V architecture needs a component-aware, point-in-time evidence sufficiency layer before a union is committed. A better ranker cannot recover incidents that reconstruction fragments, and ranking never repairs an unsafe component. Next study: estimate calibrated relationship risk under delayed evidence and common-mode controller failure on training data, then test selective deferral or reversible provisional links with component-wide risk accounting. Holdout remains sealed until a fresh development candidate improves recoverability and passes every gate.

See the focused audits and `PHASE26_GO_NO_GO.md` for limits, exact definitions and gates.
