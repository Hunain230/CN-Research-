# Recovery opportunity audit

The authoritative baseline leaves **293/400** priority incidents unrecalled; all 107 recoverable incidents are already in the top 20 under the Phase 27 selected ranker. Each unrecalled incident is assigned one evaluator-only category in priority order, using frozen minute-100 hypotheses and evidence states:

| Category | Incidents |
|---|---:|
| B_edges_insufficient_hypothesis | 122 |
| B_hypothesis_incomplete | 5 |
| C_positive_evidence_needs_commit_check | 1 |
| E_pending_evidence | 162 |
| F_correlated_or_duplicate_witnesses | 3 |

No incident fell into no-candidate, visible-contradiction or ranking-only categories in this fixture. Pending evidence is an uncertainty state at minute 100, never a value read from the future. A pending-context incident can still have independent positive lineage witnesses; the component rule's development gains mostly came from this class. These categories are diagnostic and mutually exclusive by rule order, not intrinsic clinical or operational labels. Per-incident and per-family rows are in `PHASE28_RECOVERY_OPPORTUNITIES.csv` and `PHASE28_FAMILY_METRICS.csv`.
