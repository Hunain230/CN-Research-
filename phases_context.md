# Phase context index

## Completed

- [Phase 1 — Dataset validation](phases_outputs/Phase1.md): verified baseline, audit artifacts, results, and handoff gates.
- [Phase 2 — Leakage-safe preprocessing](phases_outputs/Phase2.md): implementation, provenance, evaluator isolation, provisional organization split, synthetic checks, and remaining research gates.
- [Phase 3 — Baseline systems](phases_outputs/Phase3.md): B0/B1/B2/B3 synthetic implementation and regression checks; no empirical results.
- [Phase 4 — Multi-agent system](phases_outputs/Phase4.md): C/P/V architecture, orchestration, schemas, offline provider and synthetic checks; no empirical results.
- [Phase 5 — Evaluation pipeline](phases_outputs/Phase5.md): isolated evaluator, metrics/statistics, synthetic fixtures and report; no empirical evaluation.
- [Phase 6 — Research experiments](phases_outputs/Phase6.md): exploratory assumption-based offline priority retrieval, five field ablations, ten masking conditions, tie-aware organization-bootstrap metrics, and aggregate figures; no empirical correlation or LLM comparison.

## Implementation status

- Phases 1–5 implementation and synthetic validation are complete for their specified boundaries. Phase 6 priority-only experiment has run; the full research experiment suite remains incomplete.
- Phase 3 baseline and Phase 4 agent outputs remain deterministic synthetic plumbing, not model performance.
- Phase 5 evaluator remains synthetic-only and fails closed for real data. Phase 6 uses a separate offline evaluator adapter; do not mistake this for general real-mode support in Phase 5.

## Empirical readiness

The gates have been converted to an **assumption-based local empirical path** under the user's direction to make conservative assumptions. The exact assumptions and limits are in [the empirical protocol freeze](phases_outputs/empirical_protocol_freeze.md). The existing 10/10/30 split digest and both raw input hashes were rechecked. The priority-only BM25 exemplar experiment and Phase 6 ablations ran on 30 test organizations under a tie-aware exploratory re-analysis. See [Phase6.md](phases_outputs/Phase6.md) and its aggregate outputs. This is not a verified reproduction of the publisher's exact active queue.

Full-dataset correlation and joint evaluation remain closed. A bounded ambiguity-excluded correlation diagnostic ran but had low pooled full-pair recall and candidate coverage. There are no empirical LLM or end-to-end agent metrics. Live LLM calls remain unauthorized. Severity-based B0 and timestamp-window claims are withdrawn; any count-only oracle-group ranking must be labeled as an oracle diagnostic. Test labels have been accessed; future runs are exploratory unless a new dataset/test split is obtained. See [UNBLOCKED.md](phases_outputs/UNBLOCKED.md) for next steps and remaining limits.

## Readiness evidence review (2026-11-08)

The original source review remains historical evidence for what was verified. The dated protocol amendment above now adopts assumptions for rank direction, local query universe, ambiguous-key exclusion, narrow local fields, split freeze, and B0. It does not claim those facts were independently verified. See [readiness evidence review](phases_outputs/readiness_evidence_review.md), [gate register](phases_outputs/research_gate_register.csv), and [protocol freeze](phases_outputs/empirical_protocol_freeze.md).
