# Group reconstruction experiments

Phase 13 reran the exact frozen v2 union algorithm on the full 499-queue graph at four thresholds. It applies the existing 100-alert cap, score-descending edge order, and deterministic ties. The 0.75 partition matched every frozen v2 group exactly. No group exceeds 100 alerts. The three stricter variants are **C-only**; changed groups were not rescored by the ranking models, so Recall@20, P@10 and nDCG@20 are intentionally blank in the comparison CSV.

| Threshold | Recoverable | Pair precision | False pairs | Mixed groups | New / lost recoverable |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.75 | 6,969/9,980 (69.83%) | 90.4148% | 28,606 | 4,841 | — / — |
| 0.8 | 6,877/9,980 (68.91%) | 95.0366% | 11,203 | 3,222 | 60 / 152 |
| 0.85 | 6,678/9,980 (66.91%) | 96.8039% | 2,836 | 1,130 | 102 / 393 |
| 0.9 | 6,501/9,980 (65.14%) | 97.4217% | 801 | 500 | 131 / 599 |

The paired alert counts are: 0.80 gained 85 alerts in newly recoverable incidents but lost 500 alerts in no-longer-recoverable incidents; 0.85 gained 127 and lost 1,556; 0.90 gained 143 and lost 2,186. These are counts of in-scope alerts belonging to gained/lost incidents, not pair metrics. Higher thresholds mainly turn impure groups into incomplete ones: incomplete labels rise from 1,451 to 1,622/1,895/2,119 while impure labels fall from 218 to 139/65/18. This is a genuine safety–recovery tradeoff, not a solution to the 85% target.

Phase 10 already tested mutual fragment matching, bounded hierarchy, and a verification veto (E2–E5). All had net recoverability losses and higher false grouped pairs. The earlier consensus splitter reached 92.07% pair precision but only 45.13% Recall@20. New unrestricted union-find, community, multi-hop, or cap relaxation was not run because the observed high-score cross-incident edges and missing provenance make uncontrolled growth unsafe. No merge provenance is claimed for the stricter threshold variants beyond the frozen edge, score, order, and cap; their exact partitions and edge probabilities are frozen in `c_predictions/`.

## Weak bridge graph split

A separate label-blind policy built each frozen group's ≥0.75 candidate-edge graph and removed only true graph bridges scoring <0.80. It cut **4,665** bridges and preserved all alerts. On identical 499 queues, group recoverability became **6,903/9,980 (69.17%)**, pair precision **91.3767%**, false grouped pairs **23,720**, and mixed groups **3,347**. It gained **59** and lost **125** recoverable incidents (net **-66**); alert counts were +109/−331. It improves safety counts but fails recovery. Ranking was not rescored. Three synthetic graph/count tests passed before the full run. Its exact predictions and freeze are in `bridge_predictions/`.
