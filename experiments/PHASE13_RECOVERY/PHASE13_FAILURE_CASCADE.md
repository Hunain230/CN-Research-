# Phase 13 failure cascade and feasibility

The exact reproduced E1 cascade is: outside unambiguous scope **855**; candidate-disconnected **487**; candidate-connected but incomplete **1,451**; complete but impure **218**; recoverable below top 20 **1,903**; successfully recovered **5,066**. Sum = **9,980**. The incident-level `PHASE13_ERROR_ANALYSIS.csv` has one opaque keyed row per expert top-20 label, with scope, fragments, candidate connectivity, cross-fragment edge counts and max true/false scores, grouping reason, deterministic group position, and recoverability. Its positions are a diagnostic, not the tie-aware expected metric itself. Missing evidence and insufficient information cannot be diagnosed per incident from GUIDE; they are **unresolved research limitations**, not assumed model failures.

| C-only grouping | Outside scope | Candidate disconnected | Incomplete | Impure | Recoverable | Ranked success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C threshold 0.75 | 855 | 487 | 1,451 | 218 | 6,969 | not measured |
| C threshold 0.8 | 855 | 487 | 1,622 | 139 | 6,877 | not measured |
| C threshold 0.85 | 855 | 487 | 1,895 | 65 | 6,678 | not measured |
| C threshold 0.9 | 855 | 487 | 2,119 | 18 | 6,501 | not measured |
| C weak bridge split | 855 | 487 | 1,582 | 153 | 6,903 | not measured |

| Frozen ranking | Outside scope | Candidate disconnected | Incomplete | Impure | Recoverable below 20 | Recovered in top 20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rank v7 on E1 groups | 855 | 487 | 1,451 | 218 | 1,997 | 4,972 |
| Rank blend_0.25 on E1 groups | 855 | 487 | 1,451 | 218 | 1,934 | 5,035 |
| Rank blend_0.5 on E1 groups | 855 | 487 | 1,451 | 218 | 1,877 | 5,092 |
| Rank blend_0.75 on E1 groups | 855 | 487 | 1,451 | 218 | 1,903 | 5,066 |
| Rank child40 on E1 groups | 855 | 487 | 1,451 | 218 | 1,961 | 5,008 |

Every row's six exclusive cascade states total 9,980 where ranking was measured; C-only rows stop at group recoverability because their new groups were not ranked. Their first four states plus recoverable also total 9,980.

The new row-level audit confirms **1,445/1,451** incomplete connected labels have no genuine cross-fragment candidate score ≥0.75. The remaining six have such an edge; Phase 9F's replay attributes their blocking to the 100-alert cap. Among the 1,451 incomplete labels, 42 have >125 in-scope alerts and cannot meet 80% completeness under the 100-alert cap. The 218 complete-but-impure labels show false unions already exist. The 1,903 recoverable-but-below-20 labels are a ranking limit, but ranking cannot repair the 3,011 grouping/scope failures.

A new graph bridge split cut 4,665 weak single-edge connections. It converted some impure groups into recoverable ones (59 gains), but caused 125 previously recoverable labels to fail, net -66. This supports the same causal diagnosis: removing suspect links alone cannot distinguish weak true continuity from false linkage.

For 85% recoverability, the integer target is **8,483/9,980**, requiring **1,514** net new recoverable labels beyond E1's 6,969. Frozen candidate connectivity yields an optimistic 8,638/9,980 ceiling; subtracting 42 connected size-impossible labels yields **≤8,596/9,980 (86.13%)** under the unchanged 100-alert cap. This is only **113** labels above the 85% target. Reaching 8,483 would require net recovery of **1,514/1,627 (93.05%)** of the remaining cap-feasible candidate-connected labels without losing any currently recoverable label or breaking safety. It is **not a proof** that 85% is mathematically impossible. For 80% Recall@20, the integer target is **7,984/9,980**, requiring **2,918** more than E1's 5,066; it also requires recovering and ranking nearly all newly reconstructed groups. No ranking-only policy can exceed fixed-group recoverability 6,969/9,980.

The literal P@10 target 63.88% is slightly above E1's exact 63.8777555% by **0.0022445 percentage points**. Calling E1 "at target" uses rounding; this programme applies the literal threshold in gates. The target contract has no mathematical contradiction, but the rounded baseline and exact gate are different statements. The Phase 13 50/50 blend passes literal P@10 retrospectively, yet its full-cohort recall advantage is not a valid new selection because the earlier validation rule selected 75/25.
