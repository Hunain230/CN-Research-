# Phase 15 target status — controlled synthetic locked test

The development selection froze **exact trace grouping + progression ranking**. On the three locked-test queues (60 oracle top-20 labels), it scored:

| Gate | Target | Selected result | Status |
| --- | ---: | ---: | --- |
| Incident Recall@20 | ≥80% | **13/60 = 21.67%** | Fail |
| Group recoverability | ≥85% | **17/60 = 28.33%** | Fail |
| P@10 | ≥63.88% | **7/30 = 23.33%** | Fail |
| Grouped-pair precision | ≥90% | **1,196/1,206 = 99.17%** | Pass |
| False grouped pairs | ≤ exact baseline 10 | **10** | Pass |
| Mixed groups | ≤ exact baseline 6 | **6** | Pass |

The same-test exact/simple baseline had 6/60 Recall@20, 17/60 recoverability, and 3/30 P@10, with identical grouping safety. Thus only P improved in the selected pipeline. Remaining gaps are 35 top-20 recovered incidents to 48/60, 34 recoverable incidents to 51/60, and at least 13 predicted top-10 matches to the 63.88% threshold (integer requirement 20/30). The synthetic targets were **not achieved**. `PHASE15_TARGET_STATUS.csv` gives machine-readable gate arithmetic.

Selected-test failures were 43 incomplete incident groups, four recoverable incidents ranked below top 20, and 13 successes. There were no complete-but-impure top-20 incident failures, although six predicted groups were mixed. A 2,000-resample queue-cluster bootstrap, based on only three queues, gave descriptive 95% intervals: Recall@20 15–25%, recoverability 25–30%, P@10 10–40%. These are not strong population uncertainty estimates.
