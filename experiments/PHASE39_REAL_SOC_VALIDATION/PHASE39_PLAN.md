# Phase 39 plan — frozen external validation readiness

Objective: determine whether the **unchanged Phase 33 candidate** (Phase 32 `endpoint_fallback_bonus1`) can be evaluated on authorized real SOC evidence, and whether its result could support a human-supervised shadow study. Do not fit, retune, adapt predictive logic, or open new labels merely to obtain a score.

1. Verify the frozen Phase 33 source chain, configuration, parameters, evaluator, historical hashes, and matched synthetic holdout claim. Inspect local source files and current field-use policy without running the model.
2. Register local and publisher-provided candidates. Confirm provenance, license/access, row grain, incident label quality, source observation identity, timing, and schema fit. Classify lab or mixed datasets separately from operational SOC telemetry.
3. Require a documented authorization and field allowlist, independently adjudicated membership/priority, original observation and upstream derivation records, event/ingest/availability/decision times, a sealed untouched cohort, and an evaluator-equivalent population definition before any external scoring.
4. If those prerequisites pass, freeze a deterministic adapter with no predictive logic, seal candidate and matched real-data baseline predictions, run the unchanged evaluator when its assumptions hold, audit errors and uncertainty, and assess supervised shadow readiness. Otherwise stop before prediction and report exact blockers. Empty or invented evaluation files are prohibited.

Predeclared real-data research targets: Recall@20 ≥90%, recoverability ≥95%, P@10 ≥85%, grouped-pair precision ≥99%, zero critical false merges, and zero temporal, provenance, or label-leakage violations. Report numerators, denominators, confidence intervals, queue/incident strata, and label uncertainty if an evaluation becomes valid. Historical synthetic percentages are context, not matched real-data comparisons.
