# Reconstruction audit

Nine rules were run against the identical `phase26b` development snapshots. All three rankers reuse each rule's frozen group membership. Full metrics and union counts are in `PHASE26_EXPERIMENT_COMPARISON.csv`; accepted union increments are in `PHASE26_UNION_PAIR_AUDIT.csv`, and queue-level counts are in `PHASE26_QUEUE_METRICS.csv`.

| Reconstruction / ranker | Recoverable /400 | Recall@20 /400 | P@10 /200 | Pair precision | False pairs | Mixed groups |
|---|---:|---:|---:|---:|---:|---:|
| context / progression | 154 | 141 | 67 | 91.74% | 1248 | 46 |
| context / blend | 154 | 150 | 68 | 91.74% | 1248 | 46 |
| orthogonal_veto / linear | 205 | 202 | 75 | 99.24% | 125 | 81 |
| orthogonal_veto / blend | 205 | 199 | 90 | 99.24% | 125 | 81 |
| pit_complete / blend | 90 | 88 | 45 | 99.97% | 3 | 1 |
| pit_selective / blend | 115 | 114 | 54 | 99.97% | 3 | 1 |
| pit_direct / blend | 106 | 105 | 51 | 99.42% | 63 | 21 |
| pit_group / blend | 90 | 88 | 45 | 99.97% | 3 | 1 |

Orthogonal veto creates more recoverable incidents than the baseline (+51/400) but fails controlled delayed-evidence safety. The complete and maturity rules eliminate those stress merges but lower recoverability by 64/400. Selective reconstruction recovers 25 more incidents than complete while preserving its controlled stress result, yet remains 39 below baseline recoverability. `pit_direct` tests whether two direct receipts retain recall; it still merges correlated benign observations and is unsafe. No rule reaches the joint objective.

One incident is recoverable when a predicted group reaches both 80% incident coverage and 80% group purity, with a cap of 100 alerts. Recall@20 further requires that qualifying group to rank in the first 20. Pair precision counts same-truth alert pairs inside predicted groups; singleton groups contribute no pair. False pairs and mixed groups are evaluated after prediction freeze. The baseline's 1,248 false pairs make its pair precision only 91.74%; reducing them alone is not evidence of improved recall.
