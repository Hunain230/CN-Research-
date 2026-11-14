# Codex Work Plan for Research Cleanup and Submission

## Objective

Bring this repository to a clean, honest, reproducible research handoff, and provide a browser dashboard that can demonstrate the workflow with clearly labeled simulated activity. Work through the task files in numeric order. Do not skip a gate because the deadline is close.

This is a research prototype. The current evidence does not establish that the proposed LLM correlate-prioritize-verify (C/P/V) system outperforms baselines. Do not claim that it does unless new, valid measurements are actually produced.

## Execution order

1. [`01_REPOSITORY_CLEANUP.md`](01_REPOSITORY_CLEANUP.md) — inventory and safely simplify the repository.
2. [`02_DATA_AND_CLAIM_AUDIT.md`](02_DATA_AND_CLAIM_AUDIT.md) — establish what data and results can support.
3. [`03_MATCHED_EXPERIMENTS.md`](03_MATCHED_EXPERIMENTS.md) — run only valid experiments; record blocked comparisons honestly.
4. [`04_SYNTHETIC_MVP_RUNNER.md`](04_SYNTHETIC_MVP_RUNNER.md) — connect synthetic alerts through correlation, prioritization, verification, and evaluation in one reproducible run.
5. [`05_ANALYSIS_AND_FIGURES.md`](05_ANALYSIS_AND_FIGURES.md) — prepare metrics, error analysis, ablations, and research figures from valid outputs.
6. [`06_LIVE_DASHBOARD_SIMULATION.md`](06_LIVE_DASHBOARD_SIMULATION.md) — implement and run a clearly marked simulated dashboard demonstration using the runner's fictional events.
7. [`07_SUBMISSION_PACKAGE.md`](07_SUBMISSION_PACKAGE.md) — assemble the final submission report and reproducibility handoff.

Complete each task's acceptance checklist and write a short completion record before starting the next. If blocked, record the evidence, produce all independent work that remains possible, and continue to the next task without inventing a result.

## Project facts that must remain visible

- Phase 3 baseline and Phase 4 agent implementations are synthetic plumbing; they are not empirical LLM performance.
- Existing real-data runs are exploratory. Prior test labels have been accessed.
- The local records contain 70,702 conflicting `(OrgId, AlertId)` keys.
- Queue rank direction and exact local query scope remain assumptions or unresolved.
- The official model-input allowlist is empty. Any past five-field use was a local-only assumption, not independent approval.
- The latest offline joint comparison uses deterministic/statistical proxies. It did not run B2, B3, B4, or the proposed LLM C/P/V system.
- The 95% end-to-end Recall@20 target has not been achieved. Never change denominators to make it appear achieved.
- Dashboard simulation output is demonstration data and must never be mixed with research metrics.
- The synthetic end-to-end MVP is a software demonstration, not empirical evidence about GUIDE or LLM performance.

## Operating rules

- Read `CONTEXT.md`, `PROJECT_ITERATIONS.md`, the latest relevant phase reports, and existing configs before changing research behavior.
- Preserve raw data, restricted derived data, historical run outputs, and original reports. Do not delete or rewrite them as cleanup.
- Never expose `IncidentId`, `QueueRank`, `IncidentGrade`, action/outcome fields, raw identifiers, or restricted row-level data to a model or public dashboard.
- Do not make external model/API calls. No current approval exists for hosted inference.
- Use new, versioned output paths for any new run. Do not overwrite historical outputs.
- Keep documentation consistent with artifacts and manifests. State whether each result is synthetic, exploratory, proxy, or confirmatory.
- Run relevant validation checks after code changes and record exact commands and outcomes.

## Final deliverables

At minimum produce:

- a repository cleanup map and cleanup record;
- a data/claim/gate audit;
- reproducible experiment manifests and aggregate results where valid;
- analysis tables and figures with readable captions and denominators;
- an interactive dashboard with a visible synthetic-demo mode;
- a submission report that separates completed evidence from proposed or blocked work;
- a short README explaining how to open the dashboard and reproduce the report.

