# Final offline research handoff

**Classification:** exploratory, assumption-based, local offline analysis.

## Results included

- Priority retrieval: 30 previously accessed organizations; 14,139 oracle-group candidates. Primary tie-aware metrics are in `tie_aware_metrics.json`.
- Correlation: 30 organizations; 30,692 unambiguous alerts and 194,296 candidate pairs. Full-positive-pair recall is 0.008446; candidate-generation coverage is 0.002898.
- Interactive summary: `index.html`.

## Limits

The existing test cohort has been accessed, so these results are exploratory. Priority retrieval uses evaluator gold incident groups and is an oracle-group ceiling. The local queue universe and QueueRank direction are assumptions. Ambiguous alert mappings are excluded from correlation. Empirical LLM/multi-agent comparisons, valid 95% recall, a fresh confirmatory cohort, and production privacy/deployment validation are unavailable. No claim of model superiority, no-overfit guarantee, or deployment readiness is made.

No raw inputs, restricted per-organization metrics, prediction rows, evaluator mappings, or credentials are included in this bundle. Reproduce artifact generation from the project root with the commands in `Phase6G.md` and the original Phase 6 run records.
