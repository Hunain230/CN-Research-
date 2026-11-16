# Failure cascade and category reconciliation

The original E1 evaluator reports 855 outside scope, 487 candidate-disconnected, 1,451 candidate-connected incomplete, 218 complete but impure, 1,903 recoverable below top 20, and 5,066 recovered at top 20. These integer fields total 9,980. **The stored recall rate corresponds to 5,066.5 expected labels**, while the evaluator rounds the displayed count with Python's ties-to-even rule to 5,066. Thus 1,903 is a derived integer residual; the corresponding expected ranking miss is 1,902.5. Phase 13's per-row group positions do not establish binary rank success for every label. The aggregate split must not be assigned to individual rows without tie probabilities.

Phase 14 gives every row one primary structural category, prioritizing scope and the mathematical cap before graph and grouping diagnostics:

| Primary category | Labels | Percent of 9,980 |
| --- | ---: | ---: |
| A: outside eligible scope | 855 | 8.57% |
| E: component cap (>125 in-scope alerts) | 62 | 0.62% |
| B: true-edge candidate-disconnected, cap-feasible | 467 | 4.68% |
| C: candidate-connected but fragmented, cap-feasible | 1,409 | 14.12% |
| D: impure predicted group | 218 | 2.18% |
| Recoverable group; ranking outcome aggregate only | 6,969 | 69.83% |
| **Total** | **9,980** | **100%** |

The 62 cap-limited rows comprise 20 previously counted in B and 42 previously counted in C. Thus the original 487 and 1,451 counts reconcile exactly. Structural misses total 3,011. The last 6,969 rows split into 5,066.5 expected top-20 recovered and 1,902.5 expected ranking-only missed. The full keyed classification, secondary causes, and incident-level details are in `PHASE14_ERROR_CLASSIFICATION.csv`.

The 1,514-label gap is **the net gain required to move 6,969 to 8,483**, not a single observed failure category. Current data does not establish how many of the 2,094 cap-feasible structural misses are safely recoverable. In particular, 1,445 of the 1,451 incomplete connected incidents have no true cross-fragment edge scoring at least 0.75; 36 of these are over cap and six over-cap cases do have such an edge. The Phase 13 row field `grouping_rejection_reason` gives cap precedence, which explains its 1,409 `no_genuine_edge_at_0.75` and 42 cap rows. Score overlap with false edges prevents treating a lower threshold as supported recovery.
