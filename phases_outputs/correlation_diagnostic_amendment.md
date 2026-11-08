# Phase 6 amendment: ambiguity-excluded correlation diagnostic

**Status:** Exploratory method amendment, adopted 2026-11-08 under the user's direction to clear gates conservatively.  
**Scope:** A limited correlation diagnostic on unambiguous alerts from the frozen 30 test organizations only. It does not resolve the 70,702 ambiguous alert keys and is not a full-data or joint-system result.

## Frozen method

- Read only `OrgId`, `AlertId`, and the five descriptors (`DetectorId`, `Category`, `MitreTechniques`, `EntityType`, `EvidenceRole`) during prediction. `IncidentId` and `QueueRank` are opened only by the separate evaluator.
- Exclude every row whose composite `(OrgId, AlertId)` key appears in the restricted ambiguity artifact. Ignore timestamps.
- Candidate pairs must be same-organization and share at least one parsed ATT&CK technique. For each alert, select at most 20 candidate neighbors by Jaccard similarity over field-prefixed descriptor tokens; ties use a fixed seed and pseudorandom hash independent of labels.
- Predict LINK for every generated pair; all other pairs in the exhaustive same-organization alert-pair universe are implicit NO_LINK. This intentionally simple rule measures the candidate/decision tradeoff without adding a model service.
- Evaluate candidate-set pair precision/recall/F1 separately from full positive-pair precision/recall/F1. Full positive-pair recall counts positive pairs missed during candidate generation. Candidate-generation coverage is generated pairs divided by all possible same-organization pairs.
- Report per-organization metrics and 10,000 paired-organizations bootstrap intervals; no p-values.

## Limits

The diagnostic uses the user-adopted local candidate/feature assumptions, removes all ambiguous alerts, and is post-test-access exploratory. Technique co-occurrence is not evidence that alerts belong to the same incident. Because every generated candidate is LINK, candidate-set decision recall is mechanically 1 when there is at least one positive generated pair; interpret full-pair recall and precision with coverage. The output must not be described as a multi-agent, full-dataset, publisher-reproducing, or joint priority-correlation result.
