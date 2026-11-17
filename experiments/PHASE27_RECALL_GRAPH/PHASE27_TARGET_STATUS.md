# Phase 27 target status

| Metric | Fresh development baseline → selected | Frozen holdout baseline → selected | Target |
|---|---:|---:|---:|
| Official Recall@20 | 108/400 (27.00%) → 118/400 (29.50%) | 159/600 (26.50%) → 171/600 (28.50%) | ≥80% |
| Official recoverability | 118/400 → 118/400 | 171/600 → 171/600 | ≥85% |
| P@10 | 58/200 → 61/200 | 95/300 → 98/300 | ≥63.88% |
| Grouped-pair precision | 100% → 100% | 100% → 100% | ≥90% |
| False pairs / mixed groups | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 | No increase |
| New uncommitted incident hypotheses | 179 | 231 | Diagnostic only |

The holdout gap to 80% Recall@20 is 309 incidents (51.50 points); the gap to 85% recoverability is 339 incidents. The paired queue-bootstrap 95% interval for the holdout recall gain is 0.83–3.50 points. These intervals describe synthetic queue variation, not field transfer.
