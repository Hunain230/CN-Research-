# Reconstruction and union audit

Seven reconstruction modes were predicted on identical 20-queue development snapshots. Group recoverability requires ≥80% incident coverage and ≥80% group purity among cutoff-visible alerts; candidate paths do not count.

| Development pipeline | Recoverable /400 | Recall@20 /400 | P@10 /200 | False pairs | Mixed groups |
|---|---:|---:|---:|---:|---:|
| phase26_baseline / progression | 118 | 108 | 58 | 0 | 0 |
| phase26_baseline / train_fitted | 118 | 118 | 61 | 0 | 0 |
| phase25_veto / progression | 118 | 108 | 58 | 80 | 80 |
| graph_no_uncertain / progression | 118 | 109 | 59 | 0 | 0 |
| graph_no_uncertain / train_fitted | 118 | 118 | 61 | 0 | 0 |
| graph_selective / train_fitted | 118 | 118 | 61 | 0 | 0 |

The Phase 26 context baseline and all tested graph commit modes recovered 118/400. Graph conservative, selective, no-uncertain, component-risk and bounded variants differed in group composition but did not improve recoverability. The unchanged Phase 25 orthogonal-veto reconstruction created 80 false pairs and 80 mixed groups, four false-pair-creating unions per queue. It fails every queue-level safety comparison to the zero-error baseline.

`PHASE27_UNION_PAIR_AUDIT.csv` replays accepted unions against evaluator truth after prediction freeze; sums reconcile exactly to final pair counts in `PHASE27_FAILURE_CASCADE.csv`. No union in the selected pipeline creates a false pair. The benign collision fixture makes the veto's worst single increment one pair; this is not a large-component common-mode stress certificate.
