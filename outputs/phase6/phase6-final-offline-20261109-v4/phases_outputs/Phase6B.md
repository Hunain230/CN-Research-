# Module 6B — Data and label disposition

**Classification:** `assumption_based_local_offline_only; prior test results exploratory`  
**Official approved feature fields:** 0  
**Assumption-only local offline descriptors:** DetectorId, Category, MitreTechniques, EntityType, EvidenceRole  
**Feature-view rows at Phase 2:** 0  
**Conflicting alert keys excluded from primary correlation truth:** 70,702

## Decisions

The Phase 1 field inventory and Phase 2 leakage report were reconciled with the frozen Phase 6A policy and both field policies. The production allowlist remains empty. Five descriptors remain assumption-only for local offline descriptive experiments; that status is not point-in-time or privacy approval and does not authorize a hosted model. All evaluator labels remain evaluator-only.

All conflicting composite `(OrgId, AlertId)` mappings and associated evidence remain excluded from primary correlation and joint scoring. No mapping is resolved by majority vote, ordering, or model output. QueueRank direction and exact local query snapshot remain unresolved. Prior test results remain exploratory because labels were accessed.

## Gate status

- Local assumption-based offline work: permitted only as exploratory under the existing amended protocol.
- Confirmatory real-data evaluation: blocked; no fresh exposure-audited cohort is available.
- Hosted LLM comparison and external data transmission: unauthorized by the current project protocol.
- Production deployment with real evidence: blocked pending field timing/privacy approval and a valid deployment evaluation.

## Focused checks

- `phase6b-self-test`: passed (4 synthetic policy assertions).
- Phase 6A synthetic protocol self-test: passed (7 checks).
- Phase 6B audit reads aggregate audit/policy artifacts only; it does not scan raw evidence or open evaluator labels.

See `Phase6B_field_disposition.csv` for every source field and `Phase6B_audit.json` for label dispositions, hashes, and machine-readable gate status.

No raw data, split, evaluator store, previous run, or Phase 1–5 artifact was changed by the audit generator.
