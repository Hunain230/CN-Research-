# Fixed-group ranking audit

The three ranking comparisons use **identical baseline group membership** on all 20 development queues:

| Ranker | Recoverable /400 | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |
|---|---:|---:|---:|---:|---:|
| Progression | 107 | 73 | 96 | 42 | 0.311 |
| Phase 27 selected | 107 | 107 | 107 | 43 | 0.354 |
| Hypothesis aware | 107 | 107 | 107 | 43 | 0.354 |

The small, explicitly unverified hypothesis bonus changed no development top-20 or P@10 result. It cannot make a fragmented incident officially recoverable. The holdout protocol evaluated only the selected component-aware pipeline and same-cohort Phase 27 ranker baseline; no ranker alternative was tested after holdout truth opened. Holdout nDCG@20 rose 0.388 → 0.539 because grouping changed alongside ranking order, so this is not a fixed-group ranking claim.
