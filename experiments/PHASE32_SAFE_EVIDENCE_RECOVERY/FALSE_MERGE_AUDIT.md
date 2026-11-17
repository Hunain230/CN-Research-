# False merge and queue-level audit

The matched Phase 31 v2 development baseline has **0 false grouped pairs**, **0 mixed groups**, 12,702 true grouped pairs and 100% pair precision. Both Phase 32 candidates keep zero false pairs and zero mixed groups in aggregate and in each of the ten paired queues. The additional unions increase true grouped pairs to **13,050**. Pair precision remains 100% on this controlled cohort.

Evaluator-only relationship truth labels all **14 new fallback unions genuine**; fallback promotion precision is **14/14**. Across original and fallback unions, 460 accepted tokens are true and none false. The verifier rejects 100 false tokens and 36 true tokens with insufficient usable evidence. These classifications are conditional on the generator's challenges. They do not establish safety against an indistinguishable common-mode corruption affecting endpoint, identity-provider and network roots together.

`QUEUE_LEVEL_AUDIT.csv` gives paired recall, recoverability, P@10, false-pair and mixed-group counts for both candidates. `artifacts/post_evaluation_audit.json` records incident and union deltas. No holdout false-merge claim is made because no candidate crossed the predeclared 85% development gate.
