# Phase context index

## Completed

- [Phase 1 — Dataset validation](phases_outputs/Phase1.md): verified baseline, audit artifacts, results, and handoff gates.
- [Phase 2 — Leakage-safe preprocessing](phases_outputs/Phase2.md): implementation, provenance, evaluator isolation, provisional organization split, synthetic checks, and remaining research gates.
- [Phase 3 — Baseline systems](phases_outputs/Phase3.md): B0/B1/B2/B3 synthetic implementation and regression checks; no empirical results.
- [Phase 4 — Multi-agent system](phases_outputs/Phase4.md): C/P/V architecture, orchestration, schemas, offline provider and synthetic checks; no empirical results.
- [Phase 5 — Evaluation pipeline](phases_outputs/Phase5.md): isolated evaluator, metrics/statistics, synthetic fixtures and report; no empirical evaluation.
- [Phase 6 — Research experiments](phases_outputs/Phase6.md): exploratory assumption-based offline priority retrieval, five field ablations, ten masking conditions, tie-aware organization-bootstrap metrics, and aggregate figures; no empirical correlation or LLM comparison.
- [Module 6A — Frozen study protocol](phases_outputs/Phase6A.md): prior test exposure audited; existing 10/10/30 split preserved; no fresh confirmatory cohort evidenced; confirmatory real-data work blocked.
- [Modules 6B–6G](phases_outputs/Phase6B-G.md): 6B field/label disposition audited; 6C–6E report existing retrieval, comparison limits, and exploratory robustness evidence; 6F creates an aggregate-only final handoff; 6G is an interactive static dashboard.

## Implementation status

- Phases 1–5 implementation and synthetic validation are complete for their specified boundaries. Phase 6 priority-only experiment has run; the full research experiment suite remains incomplete.
- Phase 3 baseline and Phase 4 agent outputs remain deterministic synthetic plumbing, not model performance.
- Phase 5 evaluator remains synthetic-only and fails closed for real data. Phase 6 uses a separate offline evaluator adapter; do not mistake this for general real-mode support in Phase 5.

## Empirical readiness

The older empirical amendment permits narrow, **assumption-based local offline exploratory analysis**. Module 6A supersedes it for confirmatory claims: the historical 30-organization test cohort is exploratory, and no fresh confirmatory cohort is evidenced. Module 6B records the distinction between the empty official allowlist and five prior local offline assumptions. Existing Phase 6 priority and correlation outputs are preserved as exploratory, not re-tuned. They are not a verified reproduction of the publisher's exact active queue.

Full-dataset correlation and joint evaluation remain closed. The bounded ambiguity-excluded diagnostic has micro full-positive-pair recall 0.00845 and candidate coverage 0.00290. Priority Recall@20 is 0.3392 under an oracle-group ceiling and local queue proxy; this is not an end-to-end or confirmatory result. There are no empirical LLM or end-to-end agent metrics. Hosted LLM calls remain unauthorized. The 95% recall aspiration is not achieved or guaranteed. Severity-based B0 and timestamp-window claims are withdrawn. See [Phase6B-G.md](phases_outputs/Phase6B-G.md) for the current handoff and remaining work.

## Readiness evidence review (2026-11-08)

The original source review remains historical evidence for what was verified. The dated protocol amendment above now adopts assumptions for rank direction, local query universe, ambiguous-key exclusion, narrow local fields, split freeze, and B0. It does not claim those facts were independently verified. See [readiness evidence review](phases_outputs/readiness_evidence_review.md), [gate register](phases_outputs/research_gate_register.csv), and [protocol freeze](phases_outputs/empirical_protocol_freeze.md).

Module 6A freezes the evaluation rules in [Phase6A_StudyProtocol.md](phases_outputs/Phase6A_StudyProtocol.md), configured by `configs/phase6_protocol.yaml`. The historical test cohort is exploratory because its labels and metrics were accessed. The existing split digest remains unchanged, but the repository does not enumerate a proven unused, label-independent remainder from which to freeze a fresh confirmatory cohort. QueueRank direction, exact queue snapshot, conflicting alert semantics, data provenance, and feature timing/privacy approval remain unresolved. Confirmatory real-data work is blocked; preserve earlier empirical results as exploratory.

Module 6B generated a reproducible data/label disposition audit. Modules 6C–6E organize and interpret only existing Phase 6 artifacts; they do not conduct new test-driven tuning. Module 6F froze an aggregate-only handoff package under `outputs/phase6/`. Module 6G built the static dashboard under `dashboard/index.html`. The dashboard is a report viewer, not an operational SOC system. A complete confirmatory LLM multi-agent research result still requires a new untouched cohort, valid feature/data approvals, resolved task semantics, and an authorized empirical model comparison.
