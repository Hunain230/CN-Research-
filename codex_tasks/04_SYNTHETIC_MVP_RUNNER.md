# Task 4 End-to-End Synthetic MVP Runner

## Goal

Build the missing integration path that takes one small fictional alert scenario through candidate comparison, correlation, prioritization, verification, review routing, and synthetic evaluation. This proves that the software components can work together; it does not measure real-world SOC performance.

## Inspect first

Read the Stage 3 baseline fixture and runner, Stage 4 agent fixture and orchestrator, Stage 5 prediction schema/evaluator fixtures, and the corresponding phase reports. Reuse the existing components and contracts where possible. Do not copy evaluator truth into model-visible requests.

## Fixture design

Create a dedicated `fixtures/mvp/` scenario with:

- fictional alerts from at least two synthetic organizations;
- same-organization candidate pairs only;
- one obvious link, one clear non-link, one missing-evidence case, and one contradictory-evidence case;
- fictional source/evidence references;
- a separately stored evaluator truth file for incident membership and priority labels;
- a deterministic seed and a README describing each expected behavior.

Never use GUIDE rows, real identifiers, restricted derived data, or real evaluator labels. The model-facing request must not contain the synthetic truth file, gold incident IDs, or gold ranks.

## Runner behavior

Implement one documented command, preferably `python -m src.mvp_demo run --run-id <unique-id>`, that:

1. Validates the synthetic request and fixture hashes.
2. Runs the existing deterministic offline C/P/V provider over the candidate pairs.
3. Builds predicted components from LINK decisions only, respecting organization boundaries.
4. Produces a ranked queue from predicted components using the existing synthetic prioritization contract. If no valid ranking logic is available, implement and disclose a minimal deterministic synthetic scorer rather than implying it is a trained model.
5. Routes unresolved, unsupported, or conflicting cases to REVIEW.
6. Writes frozen predictions before the evaluator reads the separate truth file.
7. Adapts predictions to the existing Stage 5 evaluator schema, evaluates the same fixture, and writes aggregate metrics.
8. Exports a dashboard-safe event trace containing fictional fields only. Keep this file separate from research outputs.
9. Writes a manifest with code/config/fixture hashes, seed, command, timestamps, component versions, output hashes, and `classification: synthetic_end_to_end_demo_not_empirical`.
10. Refuses to overwrite a run directory and refuses any input path outside `fixtures/mvp/`.

The offline provider must remain deterministic and make zero network/model calls. Synthetic failure/retry behavior may be injected intentionally, but the run must disclose injected failures and must complete safely by abstaining or routing to review.

## Evaluation and checks

- Reuse existing metric definitions; do not invent metrics to improve the score.
- Include grouping, ranking, end-to-end recovery, review/abstention, and malformed/failure counts when supported by the fixture.
- Include a fixture with a known expected outcome and assert exact decisions/metrics where deterministic.
- Add one CLI self-check for deterministic replay, no label leakage, no cross-organization edge, and no overwrite.
- Run existing Stage 3, Stage 4, and Stage 5 synthetic self-checks plus the new MVP self-check.

## Required result

- `fixtures/mvp/` scenario, separate truth, expected behavior, and README
- `src/mvp_demo.py` or a comparably small, documented runner
- `outputs/mvp/<run-id>/` with prediction freeze, evaluation report/metrics, event trace, and run manifest
- updated root README with the exact run command and a clear synthetic-only warning
- a short completion record describing the end-to-end flow and any simplifications

## Acceptance checklist

- [ ] One command completes the fictional alert-to-ranked-queue-to-evaluation flow.
- [ ] Prediction generation cannot read the evaluator truth file.
- [ ] The evaluation adapter validates its inputs against the existing contract.
- [ ] All groups and pairs remain organization-scoped.
- [ ] Review behavior is visible for missing, conflicting, unsupported, or failed cases.
- [ ] Two runs with the same seed produce identical prediction and metric content (excluding timestamps/run IDs).
- [ ] The output and every report clearly say it is synthetic and not empirical model performance.
- [ ] No source dataset, historic output, or research protocol was changed to make the demo pass.

## Completion record

Completed on 2026-11-12. The implementation is `src/mvp_demo.py`; fixtures and instructions are under `fixtures/mvp/`; the reproducible run is `outputs/mvp/mvp-demo-20261112-v2/`; the summary is `submission/MVP_SYNTHETIC_RUN.md`. The new self-check passed 17 assertions. Phase 2, 3, 4, and 5 synthetic self-checks passed 23, 38, 34, and 64 assertions respectively. The output hash, evaluator-label separation, zero-call manifest, and overwrite refusal were verified. No GUIDE data or historical experiment output was changed.

