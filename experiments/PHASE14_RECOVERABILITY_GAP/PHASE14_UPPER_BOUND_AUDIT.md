# Phase 14 upper-bound audit

**Finding: 8,596/9,980 (86.13%) is reproduced, but is not a valid general upper bound for the stated 80% completeness / 80% purity metric.** It is a true-edge-connected, cap-feasible diagnostic. The defensible cap-and-scope upper bound from the available row data is **9,063/9,980 (90.81%)**. Neither figure is achieved performance or proof of simultaneous feasibility.

## Population and independent arithmetic

The population is 20 expert-ranked incidents in each of 499 queues, or 9,980 labels. The evaluator's eligible alert universe contains 400,039 unambiguous alerts. Each of 855 expert incidents has zero alerts in that universe and is excluded from both bounds. The 100-alert cap and 80% completeness require `ceil(0.8 * in_scope_alerts) <= 100`, equivalent here to at most 125 in-scope incident alerts. Exactly 62 nonempty incidents exceed 125: 42 true-edge-connected and 20 true-edge-disconnected. The row-level calculation and exclusions are in `PHASE14_UPPER_BOUND_AUDIT.csv`.

Phase 13's arithmetic is `9,980 - 855 outside - 487 true-edge-disconnected - 42 connected but over cap = 8,596`. The independently recomputed values agree. The corrected cap-and-scope ceiling is `9,980 - 855 outside - 62 over cap = 9,063`.

## Why the Phase 13 ceiling is not a general upper bound

`connected_incidents` in `src/submission_fragment_aware_v1.py` removes candidate edges whose endpoints have different evaluator incident IDs, then checks whether one connected component holds 80% of an incident's in-scope alerts. This is a **pure true-edge graph**. The actual recoverability evaluator permits up to 20% of the predicted group to belong to competing incidents. A five-alert path `T1—T2—F—T3—T4`, with four alerts from incident T and one from F, is 80% complete and 80% pure for T, yet T's true-only subgraph is disconnected. Thus true-only connectivity is not necessary for recoverability under the stated definition. The 487 excluded incidents may include such cases. This counterexample invalidates 8,596 as a universal mathematical ceiling; it does not assert any such bridge is safe or present in GUIDE.

The corrected 9,063 figure uses only necessary scope and cap conditions. It does not test whether enough edges exist, whether 80% purity can be maintained, whether source evidence exists at decision time, or whether competing incident groups can coexist without conflicting alert assignments. It is an optimistic individual-label ceiling, not a constructive assignment or jointly achievable bound. Group purity, available edges, evidence provenance, assignment conflict, and simultaneous recovery remain unproven. A tighter graph-constrained bound would require a simultaneous partition optimization over frozen candidate edges and purity constraints, plus a point-in-time evidence policy. No source data supports a claim that 85% is achievable in practice.

The target is 8,483 recoverable labels; E1 has 6,969, leaving **1,514 net labels**. The cap-and-scope ceiling sits 580 above the target, but cannot establish that the target is feasible. Phase 13's 113-label headroom was conditional on its invalid true-edge necessity assumption.
