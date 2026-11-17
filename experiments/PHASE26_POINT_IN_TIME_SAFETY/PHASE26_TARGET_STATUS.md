# Phase 26 target status

All Phase 26 values below are development-only, with 400 incident opportunities and 200 top-ten slots. There is no selected candidate or Phase 26 holdout.

| Target | Same-cohort baseline | Highest-recall tested (unsafe) | Safe stress rule (`pit_selective/blend`) |
|---|---:|---:|---:|
| Recall@20 ≥80% | 35.25% (141/400) | 50.50% (202/400, orthogonal_veto/linear) | 28.50% (114/400) |
| Recoverability ≥85% | 38.50% (154/400) | 51.25% (205/400) | 28.75% (115/400) |
| P@10 ≥63.88% | 33.50% (67/200) | 37.50% (75/200, linear) | 27.00% (54/200) |
| Pair precision ≥90% | 91.74% | 99.24% | 99.97% |
| False pairs: no increase | 1,248 | 125 | 3 |
| Mixed groups: no increase | 46 | 81 | 1 |

The highest-recall tested rule improves Recall@20 by 15.25 percentage points over baseline but fails delayed-contradiction and queue-level mixed-group safety. No safe recall improvement was demonstrated. Queue-cluster bootstrap 95% percentile intervals for Recall@20: baseline 29.25–41.50%; orthogonal_veto/blend 43.75–54.75%; pit_selective/blend 23.25–33.75%. These intervals measure queue sampling uncertainty in this synthetic generator; they do not validate transfer to production.
