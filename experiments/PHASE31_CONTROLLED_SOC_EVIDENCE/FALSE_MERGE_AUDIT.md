# False merge and queue-level audit

The matched v2 development baseline has 0 false grouped pairs, 0 mixed groups, 4,102 true grouped pairs and 100% pair precision. The naïve richer-evidence arm made 511 one-lineage accepts and produced **2,580 false pairs**, **22 mixed groups**, and **84.23%** pair precision. All 10 queues had a false-pair or mixed-group regression. Its 77.5% recall is therefore unsafe despite a higher aggregate recall than the baseline.

The evidence-aware and final ranked arms each accepted **446** explicit unions, with **0 false pairs, 0 mixed groups, and 100% pair precision** on all 10 queues. Evaluator-only relationship truth labels all 446 accepted tokens genuine. A further 100 false tokens were rejected; 50 genuine tokens were also rejected because the required corroboration was absent or unusable. The ranked arm changes only group order, so its group safety metrics are identical to the verified arm.

`QUEUE_LEVEL_AUDIT.csv` contains all four paired pipelines by queue. `artifacts/post_evaluation_audit.json` records promotion counts and correctness. Zero measured development false merges is a synthetic-cohort observation, not a guarantee against coordinated, indistinguishable false attestations in production. No holdout safety evaluation occurred because the development recall target was missed.
