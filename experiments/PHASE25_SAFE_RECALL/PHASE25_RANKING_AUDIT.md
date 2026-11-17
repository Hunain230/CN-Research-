# Phase 25 ranking audit

Ranking was measured independently on fixed groups for each reconstruction rule. Five rankers were compared: progression, severity, a train-fitted pairwise linear model (`learned`), a fixed progression/pairwise blend, and a train-fitted linear relevance model (`linear`). Only train truth fitted weights; all development scores were written before development truth was opened. Alert/source identifiers, incident membership, template IDs, private family and future fields are not ranking features. Distinct source IDs deduplicate derived alerts; their text is not parsed into predictive variables.

| Fixed development groups | Ranker | Recall@10 / 400 | Recall@20 / 400 | P@10 / 200 | nDCG@20 |
| --- | --- | ---: | ---: | ---: | ---: |
| Context baseline | Progression | 67 | 96 | 54 | 0.3193 |
| Context baseline | Severity | 23 | 35 | 23 | 0.1372 |
| Context baseline | Pairwise | 84 | 107 | 54 | 0.3091 |
| Context baseline | Blend | 81 | 103 | 57 | 0.3401 |
| Context baseline | Linear | 82 | 106 | 54 | 0.3057 |
| Orthogonal-veto groups | Progression | 129 | 197 | 95 | 0.5881 |
| Orthogonal-veto groups | Pairwise | 145 | 214 | 81 | 0.5928 |
| Orthogonal-veto groups | Blend | 154 | 208 | 101 | 0.6257 |
| Orthogonal-veto groups | Linear | 146 | 214 | 82 | 0.5945 |

The final linear ranker wins the registered primary objective by reaching 214/400 Recall@20, tied with pairwise, and wins their P@10 tie break (82 versus 81). **On the same reconstructed groups**, it loses 13 P@10 matches relative to progression (95→82), a material ranking-only trade-off. Against the registered end-to-end baseline, P@10 rises 54→82 and satisfies the prewritten pipeline gate. This distinction is preserved rather than attributing all recall gain to ranking. The final locked comparison is only between the frozen end-to-end baseline and selected pipeline; no alternative locked ranker was run.

`PHASE25_RANKING_AUDIT.csv` records each group's position, score, source-event diversity, temporal span, available context, duplicate fraction and evaluator-only membership after freeze. `PHASE25_RECONSTRUCTION_AUDIT.csv` and `PHASE25_HOLDOUT_RECALL_AUDIT.csv` record qualifying positions by incident. The locked selected model recovered and ranked the same 331/600 incidents within top 20; the remaining 269 are reconstruction misses.
