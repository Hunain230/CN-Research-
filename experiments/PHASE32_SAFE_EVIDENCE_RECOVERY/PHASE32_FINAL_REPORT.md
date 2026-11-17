# Phase 32 final report — NO-GO

Phase 32 pursued **85% Incident Recall@20** on the unchanged Phase 31 v2 controlled synthetic cohort. The Phase 16 historical **407/600 (67.83%)**, later opened **444/600 (74%)**, and Phase 31 v2 **158/200 (79%)** findings remain separate and unchanged. The original Phase 15 evaluator and all prior datasets, predictions and reports were used read-only.

The Phase 31 verifier required process, identity-provider and network attestations from three roots. Development diagnosis identified a narrow case where the explicit process claim was missing but existing endpoint observations independently recorded the process-parent relationship. Phase 32 allowed that endpoint observation to supply the process-family witness **only** alongside timely original identity-provider and network claims. It kept the three-root requirement and rejected available contradictory process claims. Two fixed ranking bonuses (+1 and +2 per verified union) were tested; no broader search or generator change occurred.

| Matched Phase 31 v2 development, 10 queues | Recall@20 | Recoverability | P@10 | Pair precision | False pairs | Mixed groups | New unions | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Frozen Phase 31 best | 158/200 (79.0%) | 166/200 (83.0%) | 73/100 (73%) | 100% | 0 | 0 | — | Reference |
| Endpoint fallback, +1 bonus | **169/200 (84.5%)** | **177/200 (88.5%)** | **73/100 (73%)** | **100%** | **0** | **0** | **14** | **Fail: one short of 85%** |
| Endpoint fallback, +2 bonus | 168/200 (84.0%) | 177/200 (88.5%) | 73/100 (73%) | 100% | 0 | 0 | 14 | Fail: two short |

The better candidate made 11 additional incidents recoverable. It gained 12 recalled incidents and lost one to ranking, for a net gain of 11. Eight recoverable incidents remain outside top 20; 23 are still unrecoverable. All 14 new unions were evaluator-correct, with zero new false grouped pairs or mixed groups in every queue. P@10 was unchanged in aggregate, but fell in two queues and rose in two; the paired queue file exposes these changes. The verifier continues to reject 100 false relationship tokens and abstain on 36 genuine tokens lacking sufficient usable evidence. Temporal and private-feature audits found zero violations.

The predeclared development gate required **at least 170/200** Recall@20, **at least 170/200** recoverability, P@10 at least 73/100, pair precision at least 90%, zero additional false pairs and mixed groups per queue, and no temporal or truth leakage. The best candidate met every requirement except recall. Therefore **no candidate was selected and no fresh holdout was generated or evaluated**. `HOLDOUT_RESULTS.csv` is intentionally absent. The measured 84.5% is a development result, not a generalization or production claim.

Reproducibility: `PHASE32_PLAN.md` fixes the two candidates and gate; `BASELINE_FREEZE.json` verifies historical hashes; `artifacts/development_pre_evaluation_seal.json` hashes both predictions before scoring; `DEVELOPMENT_RESULTS.csv` and `QUEUE_LEVEL_AUDIT.csv` contain exact paired measurements; `audit.py` verifies 14 fallback unions and incident deltas. Four controlled tests passed. The endpoint process witness relies on simulated sensor independence and has not been validated against real SOC common-mode failures.
