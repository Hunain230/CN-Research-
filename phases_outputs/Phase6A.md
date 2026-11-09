# Module 6A — Implementation report

**Status:** protocol frozen; confirmatory evaluation unavailable; downstream confirmatory real-data experiments blocked. Prior real-data results remain exploratory.

## Work completed

- Added the frozen protocol and machine-readable policy in [`Phase6A_StudyProtocol.md`](Phase6A_StudyProtocol.md) and [`phase6_protocol.yaml`](../configs/phase6_protocol.yaml).
- Audited Phase 1/2 source and split manifests, Phase 6 priority/correlation run manifests, evaluator manifest, test-access log, ambiguity artifact, leakage report, gate register, readiness review, prior protocol freeze, phase specs/reports, evaluator interface and model-facing imports. Machine-readable evidence is in [`Phase6A_audit.json`](Phase6A_audit.json).
- Preserved the historical split digest and recorded its 10/10/30 counts and disjointness. The split manifest contains 50 assigned organization IDs; validation reports 499 eligible organizations. The rest are not evidenced as an unused, label-independent cohort, so none was frozen.
- Classified the existing test cohort as exploratory: Phase 6 test labels were read, results reported, and evaluation/report changes followed. Test-tuned selection and confirmatory access are blocked by protocol configuration.
- Specified whole-key ambiguity exclusion for all conflicting `(OrgId, AlertId)` keys; QueueRank direction, exact local query universe, GUIDE `Id` semantics, source download provenance, conflicting membership semantics, and feature timing/privacy approval remain unresolved.
- Added `phase6a-self-test` and `phase6a-audit` CLI commands. The audit writes the protocol hash, audit hash, split manifest hash, and preserved assignment digest to the generated run manifest under `outputs/phase6a/phase6a-protocol-20261109-v1/`.

## Checks

- `.venv` CLI help discovered supported command structure before invocation.
- `phase6a-self-test`: **passed** (synthetic deterministic label-blind cohort selector, split disjointness, ambiguous-key exclusion, evaluator import boundary, prior test status, and blocked test-tuning status).
- YAML parse and required-field/schema invariants: **passed** using the project venv.
- `phase6a-audit`: **passed**; verified recorded assignment counts, split manifest and run evidence, and 70,702 ambiguity keys without running any model/evaluator or opening raw data.
- Existing `check-splits`: **passed**, matching the preserved digest and 10/10/30 counts.
- Existing `check-leakage`: **passed**, with zero feature rows and zero approved fields; evaluator sentinels absent.
- No real test-set evaluation, new model run, raw-data edit, external call, or API-key use occurred.

## Decisions and remaining gates

The old test cohort is exploratory. A fresh confirmatory cohort is unavailable because an eligible unused membership list and complete exposure/label-independence evidence are not present. The current deny-by-default real-data field policy is empty; the five-field Phase 6 local descriptor set remains assumption-only, so real-data modeling remains blocked pending point-in-time and privacy approval. Correlation/joint evaluation remains blocked by unresolved alert membership semantics, despite the historical ambiguity-excluded exploratory diagnostic. Ranking direction and exact queue scope remain unresolved; report both directions for exploratory nDCG. Candidate-generation recall ≥95% remains a target, never a claim or guarantee.

**Downstream status:** confirmatory real-data work is **blocked**. Existing accessed test data can support only transparently labeled exploratory reporting within project controls. Synthetic protocol/schema work may proceed.
