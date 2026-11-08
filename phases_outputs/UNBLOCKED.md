# Empirical work path opened under explicit assumptions

**Decision date:** 2026-11-08  
**Classification:** assumption-based local empirical work; not a publisher-confirmed reproduction.

The user directed the implementation owner to clear gates by making conservative assumptions where evidence is unavailable. This record adopts those assumptions and identifies the remaining limits. It does not rewrite what was verified in Phases 1–5.

## What is now usable

- **Priority retrieval:** may proceed as an offline local-GUIDE experiment using the frozen candidate universe (all distinct `(OrgId, IncidentId)` keys in eligible labeled organizations), rank 1 as the declared primary high-priority convention, and top-20 set metrics. Report rank-direction sensitivity for nDCG. Call it a local proxy, not exact reconstruction of the publisher's active queue.
- **Inputs:** for local non-generative experiments only, use `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` as assumed alert-time descriptors. Keep IDs, raw entities, timestamps, outcome fields and labels out of model features. No external transmission.
- **Split:** freeze the existing 10 pilot / 10 development / 30 test assignment. Its stored digest verified as `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024`; the assignment counts are 10/10/30. Raw hashes rechecked on 2026-11-08 match Phase 1.
- **Ambiguity:** exclude every evidence row for the 70,702 conflicting composite alert keys; do not resolve them by guess, majority vote, or incident ordering. Any scored correlation diagnostic must report the remaining coverage and cannot stand for the full dataset.
- **B0:** severity is formally removed. Do not claim a severity baseline. A count-only ranking over evaluator gold groups may be reported only as an oracle-group diagnostic.

## Still not cleared

- Publisher confirmation of rank direction and exact local queue snapshot; A1/A2 are explicit assumptions.
- Authoritative semantics for `Id` and conflicting alert keys.
- Independent publisher/privacy review of field timing; the five-field allowlist is a project-directed local-only assumption.
- Full-dataset correlation and joint metrics: remain closed because conflicting memberships are excluded and the empirical correlation method has not been implemented.
- Empirical hosted-LLM comparisons: remain unavailable; no live API/model calls are authorized. Synthetic stubs are not empirical LLMs.
- Severity-based B0, time-window conclusions, reviewer studies, and tariff-based API costs: unavailable.

## Next execution sequence

1. Review the completed priority-only Phase 6 analysis in [Phase6.md](Phase6.md) and use the tie-aware aggregate result as exploratory, with its access history disclosed.
2. Implement an ambiguity-excluded correlation diagnostic only if candidate generation can meet the same no-label/no-ID feature contract. Keep full correlation and joint evaluation closed.
3. Continue method development on pilot/development only. Any new test run is exploratory because test labels have already been opened and the tie-aware metric amendment followed that access.
4. If the core research question requires empirical LLM comparisons, obtain explicit provider/model authorization or identify an available local offline model; no hosted calls are made under the current protocol.

## Frozen records

- [Empirical protocol freeze](empirical_protocol_freeze.md)
- [Protocol freeze manifest](empirical_protocol_freeze_manifest.json)
- [Empirical local field policy](../configs/empirical_field_policy.yaml)
- [Updated gate register](research_gate_register.csv)
- [Adopted B0 amendment](proposed_B0_protocol_amendment.md)

The completed priority experiment created assumption-based real-data predictions and metrics; see [Phase6.md](Phase6.md). The existing Phase 3–5 real-mode runners remain synthetic-only and must not be invoked as if this new path had made their implementations empirical. Full multi-agent correlation/prioritization results remain unavailable.
