# Ranking audit on unchanged committed groups

| Ranker on fixed baseline groups | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |
|---|---:|---:|---:|---:|
| progression | 87 | 108 | 58 | 0.365 |
| phase25_linear | 118 | 118 | 61 | 0.395 |
| phase26_blend | 98 | 118 | 61 | 0.412 |
| candidate_graph | 18 | 38 | 18 | 0.101 |
| fragment_aggregation | 55 | 91 | 46 | 0.245 |
| graph_progression | 23 | 48 | 23 | 0.123 |
| train_fitted | 118 | 118 | 61 | 0.396 |

On fixed development baseline groups, Phase 25 linear, Phase 26 blend and Phase 27 train-fitted rankers tied at 118/400 official Recall@20; progression reached 108/400. The frozen tie break selected train-fitted. The three hand-set graph rankers performed worse because they promoted fragmented groups that could not satisfy official recoverability. Ranking hypotheses separately from official groups is therefore necessary.

The selected model has nine historical group features and six graph features, with deduplicated source-pair and disjoint-root counts. On holdout, graph features contributed a negative score to 3,966 of 5,543 groups and a positive score to 0. This is score decomposition, not a causal ablation. The frozen selected and progression baseline used identical holdout groups: Recall@20 159/600 versus 171/600, P@10 95/300 versus 98/300, nDCG@20 0.372 versus 0.385. Recoverability stayed 171/600.
