# Test-label access log

## Phase 6 priority run — 2026-11-08

1. Predictions for `phase6-priority-20261108-v1` were frozen before test `QueueRank` values were read. The prediction manifest records test priority labels as unread.
2. Evaluator attempt 1 verified hashes, read the test labels, computed the per-condition organization metrics in memory, then exited with `KeyError: 'per_organization'` while assembling paired condition differences. It produced no metrics file/report and printed no metric values. No test-derived choice, tuning, or code change to the scorer was made from those values.
3. The failure was an evaluator report-assembly defect. The evaluator lookup was corrected to use the same in-memory per-organization records already used for each condition’s aggregate.
4. Because code/config hashes are bound into prediction manifests, the corrected implementation must create a fresh deterministic prediction run and evaluator run. This is a transparent re-execution of the same frozen method and config, not a new model-selection attempt. The first failed access is retained in this log.
5. Any successful report must link both run IDs and be described as a deterministic re-evaluation after a failed report-assembly attempt. Do not call it a pristine first test access.

## Re-execution comparison

The v2 candidate-universe SHA-256 exactly matches v1 (`de2af5fdc3064c191f5ff183be484ea709f3b199f847722b09a492e8a0e407dd`), and all 16 v1/v2 prediction-file hashes match byte-for-byte. The scorer outputs therefore did not change between the failed evaluator attempt and the successful evaluation. The corrected v2 evaluator produced aggregate results; see the run report and figure files. This establishes reproducibility of predictions across the evaluator-only fix, while the prior test-label access remains disclosed.

## Tie-aware re-analysis

The successful v2 metrics initially used opaque-key order to serialize equal BM25 scores. The post-run tie audit found primary-condition ties inside top-10 and top-20 in all 30 organizations (497 of 600 top-20 slots were tied). The tie-aware evaluator now reports expected cut-off metrics over uniform score-tie permutations. It did not change or refit any score or prediction. Its output is classified exploratory because test labels had already been opened. Primary tie-aware means: P@10 `0.4622`, Recall@20 `0.3392`, nDCG@20 `0.3924` under rank-1-highest and `0.1153` under rank-20-highest. Full intervals, robustness conditions, code and hashes are in the Phase6 output directory.
