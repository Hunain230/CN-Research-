# Recall error analysis

The denominator is 400 eligible development incidents, 20 per queue. `PHASE26_RECONSTRUCTION_AUDIT.csv` labels each incident as recalled, ranking-only, fragmented candidate, absent candidate or impure. The counts below use blended ranking so reconstruction can be compared with the same ranker.

| Reconstruction | Recalled | Ranking-only | Fragmented candidate | Absent candidate | Impure |
|---|---:|---:|---:|---:|---:|
| context | 150 | 4 | 174 | 57 | 15 |
| orthogonal_veto | 199 | 6 | 106 | 89 | 0 |
| pit_selective | 114 | 1 | 250 | 35 | 0 |

Baseline blend has 154/400 recoverable and 150/400 recalled; only four recoverable incidents miss the top 20. Under selective reconstruction, 250/400 incidents remain fragmented and only one recoverable incident is a ranking miss. This identifies reconstruction, specifically safe linking under incomplete evidence, as the dominant recall bottleneck. Family and failure-mode counts are in `PHASE26_FAMILY_FAILURE_METRICS.csv`. The category figures are generator-specific and should not be treated as prevalence estimates.
