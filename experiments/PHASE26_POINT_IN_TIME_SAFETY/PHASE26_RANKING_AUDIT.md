# Ranking audit on fixed group membership

Progression, train-fitted linear and blended rankers were evaluated for every reconstruction rule without changing that rule's groups. Their features come from minute-100 snapshots. The trained ranker uses the 12 training queues; development truth is opened only after the predictions are frozen. The table below isolates ranking changes.

| Fixed reconstruction | Ranker | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |
|---|---|---:|---:|---:|---:|
| context | progression | 97 | 141 | 67 | 0.411 |
| context | linear | 115 | 153 | 62 | 0.417 |
| context | blend | 109 | 150 | 68 | 0.428 |
| orthogonal_veto | progression | 123 | 178 | 89 | 0.511 |
| orthogonal_veto | linear | 147 | 202 | 75 | 0.552 |
| orthogonal_veto | blend | 142 | 199 | 90 | 0.574 |
| pit_selective | progression | 77 | 107 | 50 | 0.318 |
| pit_selective | linear | 97 | 115 | 51 | 0.358 |
| pit_selective | blend | 93 | 114 | 54 | 0.354 |

On baseline groups, blend lifts Recall@20 from 141 to 150 (+9/400) while recoverability stays at 154/400 and P@10 moves 67 to 68. Linear reaches 153/400 but P@10 drops to 62. On orthogonal-veto groups, linear reaches 202/400 while blend reaches 199/400 with higher P@10 (90 versus 75). These are ranking effects only. Neither ranker can repair an unsafe union or restore an incident fragmented by reconstruction. The selected safety gate requires a recoverability improvement, so a ranking-only gain is insufficient for Phase 26 promotion.
