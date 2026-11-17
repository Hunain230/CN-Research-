# Phase 28 target status

| Metric | Fresh development baseline → selected | Frozen holdout baseline → selected | Target |
|---|---:|---:|---:|
| Recoverability | 107/400 (26.75%) → 207/400 (51.75%) | 171/600 (28.50%) → 291/600 (48.50%) | ≥85% |
| Official Recall@20 | 107/400 (26.75%) → 207/400 (51.75%) | 171/600 (28.50%) → 291/600 (48.50%) | ≥80% |
| P@10 | 43/200 (21.50%) → 78/200 (39.00%) | 98/300 (32.67%) → 125/300 (41.67%) | ≥63.88% |
| Pair precision | 100% → 100% | 99.78% → 99.71% | ≥90% |
| False pairs | 0 → 0 | 41 → **76** | No increase |
| Mixed groups | 0 → 0 | 25 → 25 | No increase |

The selected holdout Recall@20 is 189 incidents (31.50 points) below 80%; recoverability is 219 incidents below 85%. The holdout gain of 120 incidents is **unsafe**. Paired queue-bootstrap 95% intervals for Recall@20 gain: development 21.25–28.75 points, holdout 18.00–22.33 points. These intervals measure synthetic queue variation and cannot override the false-pair gate.
