# Phase 30 final report — NO-GO

Phase 30 investigated safe reconstruction as required. The previous `source_depth` result remains an unpromoted **74.00% (444/600)** finding on an opened holdout, with a P@10 regression. The original Phase 16 historical reference remains **407/600 = 67.83%**. Neither is replaced by this phase's development measurements.

The prior holdout's 137 unrecoverable incidents are all fragmented, with 110 lacking any direct visible cross-fragment process/auth/flow reference. Nineteen additional incidents are group-recoverable but rank-limited. Matching host and account occurs for 135/137 fragmented incidents, but it is not an independent attestation. The strict development recovery rule found two direct dual-reference group pairs; one lacked matching context and the other reused a reference. It accepted **zero** unions. The train-fitted ranking change improved development P@10 by one case but lowered recall.

| Phase 16 development, 15 queues | Recall@20 | Recoverability | P@10 | Pair precision | False pairs | Mixed groups | New unions | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Frozen `source_depth` reference | 220/300 (73.33%) | 233/300 (77.67%) | 93/150 (62.00%) | 98.5784% | 236 | 127 | 0 | Phase 30 P@10 floor unmet |
| Trained rank | 217/300 (72.33%) | 233/300 | 94/150 (62.67%) | 98.5784% | 236 | 127 | 0 | Fail: recall and P@10 |
| Strict recovery + `source_depth` | 220/300 (73.33%) | 233/300 | 93/150 (62.00%) | 98.5784% | 236 | 127 | 0 | Fail: no improvement, P@10 |
| Hybrid | 217/300 (72.33%) | 233/300 | 94/150 (62.67%) | 98.5784% | 236 | 127 | 0 | Fail: recall and P@10 |

The 64.33% P@10 requirement corresponds to **at least 97/150** on this development population. No candidate reached it, improved recall over 220/300, or increased recoverability. All candidates preserved grouped-pair precision, false pairs, mixed groups, queue-level false-merge safety, and minute-100 eligibility. The unchanged-group development recall ceiling remains **233/300 = 77.67%**. Phase 30 therefore selected no candidate and generated **no new holdout**. `HOLDOUT_RESULTS.csv` is intentionally absent.

The trained model fitted 15 Phase 16 train queues and used receiver-visible group features at inference. The strict recovery proposal required direct auth and flow references, distinct observation IDs, reference uniqueness, context and temporal agreement, a 100-alert cap, and noncascading unions. These checks did not establish genuinely independent upstream roots, which are absent from this data. Provisional links remain useful for discovery but do not count as officially recovered groups. No Phase 28 promotion rule was reused.

Reproduction and testing: `BASELINE_FREEZE.json` records SHA-256 hashes of 14 relevant historical files. `audit_results.py` confirmed all hashes, the historical 407/600 metrics, exact eligible sets on 15 development queues, and zero false-pair/mixed-group regression across 45 candidate-queue comparisons. The original Phase 15 evaluator measured all three candidates. Three focused recovery tests passed. Detailed failure, P@10, false-merge, and temporal analyses are in the accompanying reports; `DEVELOPMENT_RESULTS.csv`, `CANDIDATE_COMPARISON.csv`, and `QUEUE_LEVEL_AUDIT.csv` carry the machine-readable comparisons.

No safe official recall gain was demonstrated. Reaching 80% requires a real increase in group recoverability backed by evidence that distinguishes shared or corrupted upstream roots; those attestations are not present in the current receiver-visible Phase 16 fields. No further phase or holdout evaluation was started.
