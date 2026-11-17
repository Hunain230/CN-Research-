# Phase 25 — Safe recall recovery experiment

**Final decision: NO-GO for promotion.** Phase 25 achieved a large, measured recall improvement on a fresh development cohort and repeated it on one newly generated, previously untouched synthetic holdout. The holdout failed the strict queue-level safety gate by **one** false pair and **one** mixed group in a queue where the same-cohort baseline had zero of each. The selected rule and predictions remain frozen; no alternative was evaluated or tuned on that opened holdout.

## Populations and selection

Phase 16 v4 remains the historical selected synthetic holdout result: **67.83% Incident Recall@20**, 75.17% recoverability, 63.00% P@10, 98.61% pair precision, 440 false pairs and 257 mixed groups. Phase 24's **48.44%** was development recall on a different population, never a replacement for Phase 16. Phase 25 has its own generator, namespace and complete scenario-disjoint train/development/locked splits; percentages across phases are not directly comparable. Phase 19 and Phase 22 locked cohorts were not accessed.

Twelve train queues fitted two lightweight ranking models. Forty candidate pipelines (eight reconstruction rules × five rankers) were predicted on **20 new development queues** and hashed before development truth was opened. The prewritten acceptance code required improved Recall@20, competitive recoverability, ≥90% pair precision, no aggregate or per-queue false-pair/mixed-group increase, at most one lost P@10 match, and exact union reconciliation. Fifteen pipelines passed. The highest Recall@20 tied among rare-context and orthogonal-veto rules; the veto won the frozen tie break and `linear` won over the pairwise ranker by P@10. The selection was frozen before any locked data existed.

## Same-cohort results

| Split and method | Recoverable | Recall@20 | P@10 | Pair precision | False pairs | Mixed groups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development baseline, context + progression | 107/400 (26.75%) | 96/400 (24.00%) | 54/200 (27.00%) | 90.84% | 1,390 | 27 |
| Development selected, orthogonal veto + linear | 215/400 (53.75%) | 214/400 (53.50%) | 82/200 (41.00%) | 99.79% | 37 | 6 |
| Locked baseline, context + progression | 219/600 (36.50%) | 194/600 (32.33%) | 95/300 (31.67%) | 95.15% | 1,032 | 26 |
| Locked selected, orthogonal veto + linear | 331/600 (55.17%) | 331/600 (55.17%) | 134/300 (44.67%) | 99.996% | 1 | 1 |

On development, every selected queue had no more false pairs or mixed groups than its baseline queue. On the locked cohort, **29/30** queues met that local count comparison. In `phase25h_locked_test_q009`, the selected rule merged two unrelated benign observations on a shared process reference, raising false pairs **0→1** and mixed groups **0→1**. The host value contradicting the merge was recorded in the raw source but became receiver-visible at minute **106**, after the minute-100 decision. The rule treated the one visible host as coherent context and accepted. The false-pair increment is exactly one; there was no further contamination. This is a real point-in-time failure, not an evaluator bookkeeping discrepancy.

Development 95% queue-bootstrap descriptive intervals for selected Recall@20 and recoverability are **48.5–58.5%** and **49.0–58.5%**. Locked intervals are **51.83–58.33%** and **51.83–58.5%**. These intervals describe synthetic queue variation and do not override the queue-level safety failure. The absolute targets of 80% recall, 85% recoverability and 63.88% P@10 were not met.

## What was learned

The original Q014 Phase 24 failure was repaired on the opened diagnostic queue by the orthogonal veto, but that was design-set evidence. On fresh Phase 25 development, the veto made the same predictions as the rare-context rule. The selected pipeline's improvement mainly came from coherent process grouping and rare lineage selection; the fixed-group linear ranker moved Recall@20 from **197 to 214** on the selected grouping, while P@10 fell from **95 to 82** on those same groups. Relative to the registered pipeline baseline, P@10 improved from 54 to 82 and passed the prewritten gate. This fixed-group P@10 trade-off limits the ranking claim.

Receiver receipts, controller identities, corrupted claims, missing/delayed attestations and a private physical lineage audit were added to the new fixture. The receipt-based candidates did not win: two-receipt verification was too restrictive, while the one-receipt plus rare-reference diagnostic still produced unsafe mixed groups in a development queue. Controller diversity did not establish causal truth. The selected rule did not consume receipts, so it cannot claim validated causal provenance.

The [GO/NO-GO decision](PHASE25_GO_NO_GO.md), [Q014 forensics](PHASE25_Q014_UNION_FORENSICS.md), [recall analysis](PHASE25_RECALL_ERROR_ANALYSIS.md), [reconstruction audit](PHASE25_RECONSTRUCTION_AUDIT.md), [ranking audit](PHASE25_RANKING_AUDIT.md), and [reproducibility record](PHASE25_REPRODUCIBILITY.md) give the full evidence and limits.
