# Phase context index

The [Phase A progress audit](phases_outputs/PhaseA_Progress_2026-11-11.md) found 74 expert top-20 labels represented only by ambiguous alerts on the 57-organization exploratory cohort, limiting recoverable end-to-end Recall@20 to 93.51% under the current exclusion rule. The frozen candidate generator retrieved 81.52% of positive alert pairs while emitting 80.52% of all possible pairs. All 8,800 missed positive pairs share `EntityType` and `EvidenceRole`; none shares a parsed ATT&CK technique. Phase A needs more discriminative, approved evidence or a better retrieval design. Its 99% micro candidate-recall-at-affordable-volume target failed. No provider call was made; production readiness remains no.

The [three-phase completion plan](phases_outputs/Three_Phase_Completion_Plan_2026-11-11.md) defines the remaining data/retrieval, real-model comparison, and deployment/submission work with an evaluation and production verdict after each phase. It is prospective; none of its future quality gates has passed.

## Latest offline predicted-group comparison (2026-11-11)

The [offline joint comparison record](phases_outputs/Offline_Joint_Comparison_2026-11-11.md) describes a matched, exploratory run on 57 complete small, ambiguity-excluded GUIDE_Test organization queues. All four runnable methods use the same 11,219 alerts and 1,216,600 frozen candidate pairs; predicted groups feed the priority ranker. B0 rule/count and B1 rule/BM25 achieve micro pair F1 0.1364; the deterministic/statistical offline CPV proxy achieves 0.0872. Their end-to-end Recall@20 values are 0.0746, 0.0316, and 0.1175, respectively. B2, B3, B4, and the proposed **LLM** C/P/V were not run because the user selected an offline-only comparison. The CP/CPV proxies are not LLM results. These are previously accessed exploratory organizations, not a confirmatory test.

## Latest GUIDE_Test run (2026-11-09)

The [GUIDE rerun v2 report](outputs/guide_rerun_v2/report.md) supersedes older status summaries for the latest experiment. It used 334 training, 67 validation, and 68 exploratory holdout organizations from GUIDE_Test; the historical 30 test organizations stayed excluded. Candidate recall at K=500 was 97.21% on holdout, requiring up to 500 oracle-group incident candidates per queue. Final Recall@20 was 55.16% for local logistic ranking and 42.43% for 67 valid Groq GPT-OSS-120B responses plus one offline fallback. Bounded correlation sampled 500 alerts per organization and had 65.90% pair recall with 3.63% precision. The [protocol amendment](phases_outputs/GUIDE_RERUN_V2_PROTOCOL.md) records user authorization for the bounded Groq run, split, field restrictions, budget, and exploratory classification. The [new dashboard](dashboard/guide_rerun_v2.html) displays aggregate results. This is not military certification, a confirmatory benchmark, or a complete end-to-end C/P/V system.

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

Full-dataset correlation and joint evaluation remain closed. The older bounded ambiguity-excluded diagnostic has micro full-positive-pair recall 0.00845 and candidate coverage 0.00290. Its oracle-group priority Recall@20 was 0.3392; neither is an end-to-end or confirmatory result. A later bounded Groq rerun and the offline predicted-group comparison are summarized above. There are no empirical LLM end-to-end agent metrics. The 95% final-recall aspiration is not achieved or guaranteed. Severity-based B0 and timestamp-window claims are withdrawn. See [Phase6B-G.md](phases_outputs/Phase6B-G.md) for the historical handoff and remaining work.

## Readiness evidence review (2026-11-08)

The original source review remains historical evidence for what was verified. The dated protocol amendment above now adopts assumptions for rank direction, local query universe, ambiguous-key exclusion, narrow local fields, split freeze, and B0. It does not claim those facts were independently verified. See [readiness evidence review](phases_outputs/readiness_evidence_review.md), [gate register](phases_outputs/research_gate_register.csv), and [protocol freeze](phases_outputs/empirical_protocol_freeze.md).

Module 6A freezes the evaluation rules in [Phase6A_StudyProtocol.md](phases_outputs/Phase6A_StudyProtocol.md), configured by `configs/phase6_protocol.yaml`. The historical test cohort is exploratory because its labels and metrics were accessed. The existing split digest remains unchanged, but the repository does not enumerate a proven unused, label-independent remainder from which to freeze a fresh confirmatory cohort. QueueRank direction, exact queue snapshot, conflicting alert semantics, data provenance, and feature timing/privacy approval remain unresolved. Confirmatory real-data work is blocked; preserve earlier empirical results as exploratory.

Module 6B generated a reproducible data/label disposition audit. Modules 6C–6E organize and interpret only existing Phase 6 artifacts; they do not conduct new test-driven tuning. Module 6F froze an aggregate-only handoff package under `outputs/phase6/`. Module 6G built the static dashboard under `dashboard/index.html`. The dashboard is a report viewer, not an operational SOC system. A complete confirmatory LLM multi-agent research result still requires a new untouched cohort, valid feature/data approvals, resolved task semantics, and an authorized empirical model comparison.
