# Phase 27 final report — PARTIAL

**The central graph hypothesis is supported for incident discovery.** Without committing uncertain edges, bounded candidate paths formed qualifying hypotheses for **179/400** development and **231/600** untouched holdout top-20 incidents that the committed baseline groups could not recover. Hypothesis precision was **215/295 (72.88%)** on development and **314/493 (63.69%)** on holdout. Those discoveries are separate from official group recoverability and Incident Recall@20.

The single frozen selected pipeline kept Phase 26 baseline groups and used a train-fitted ranker. On a fresh 30-queue holdout, official Recall@20 rose **159/600 → 171/600 (+12; +2.00 percentage points)**. Group recoverability remained **171/600**; P@10 moved **95/300 → 98/300**. Both pipelines had 100% grouped-pair precision, zero false pairs and zero mixed groups in every queue. The paired queue-bootstrap 95% interval for the recall gain is **+0.83 to +3.50 points**. The frozen holdout gate passed (`GO` in `v3/locked_result.json`). The final research decision is **PARTIAL**: official group recoverability did not improve, and the 80% recall target remains **51.50 points** away.

## Same-cohort development

| Development pipeline | Recoverable /400 | Recall@20 /400 | P@10 /200 | False pairs | Mixed groups |
|---|---:|---:|---:|---:|---:|
| phase26_baseline / progression | 118 | 108 | 58 | 0 | 0 |
| phase26_baseline / train_fitted | 118 | 118 | 61 | 0 | 0 |
| phase25_veto / progression | 118 | 108 | 58 | 80 | 80 |
| graph_no_uncertain / progression | 118 | 109 | 59 | 0 | 0 |
| graph_no_uncertain / train_fitted | 118 | 118 | 61 | 0 | 0 |
| graph_selective / train_fitted | 118 | 118 | 61 | 0 | 0 |

The selected development gain was **108/400 → 118/400 (+2.50 points)**, with recoverability unchanged at 118/400. Phase 25 orthogonal veto created 80 false pairs and 80 mixed groups, four unsafe unions per queue. The selected pipeline committed no uncertain edges.

## Mechanism and limits

Candidate alert-edge precision was **7299/7379 (98.92%)** on development and **11693/11843 (98.73%)** on holdout. Direct candidate-edge coverage of same-incident cross-group alert pairs was only **5587/15559 (35.91%)** and **8870/25995 (34.12%)**. Sparse edges still connected enough fragments to produce many hypotheses. The corrected v3 graph counts duplicate source pairs once and requires disjoint controller roots for multiple independent witnesses.

This did **not** prove that uncertain edges caused the official rank gain. On unchanged development groups, the historical Phase 25 linear and Phase 26 blend rankers tied the selected ranker at 118/400. Three hand-set graph rankers performed worse by promoting fragmented groups. The selected model mostly penalized candidate-rich fragments. No alternative candidate was evaluated on the opened holdout.

The next experiment should present hypotheses as a separate, calibrated analyst queue or provisional reversible groups, measure false hypothesis workload, and seek additional independent evidence before permanent unions. This synthetic study does not justify operational promotion. Phase 16 v4's 67.83% selected holdout, Phase 25's 55.17% holdout with safety failure, and Phase 26's development results are different populations and are not direct percentage comparators.
