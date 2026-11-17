# Phase 27 decision: PARTIAL

The predeclared development gates selected one pipeline: Phase 26 baseline committed groups plus a train-fitted ranker. Code, configuration, weights, thresholds, selection and holdout evaluator were hashed in `v3/pre_evaluation_protocol.json` before generating the `phase27k` cohort. Only that pipeline and its same-cohort progression baseline were predicted. `v3/locked_prediction_freeze.json` hashed predictions and public inputs before private truth was opened once.

The frozen holdout gate passed: Recall@20 171/600 versus 159/600, grouped-pair precision 100%, zero false pairs, zero mixed groups and 30/30 queues without safety regression. `v3/locked_result.json` calls that narrow gate `GO`. The final scientific decision is **PARTIAL** because official recoverability stayed 171/600 (28.50%), hypothesis precision was only 63.69%, and absolute recall remains far below 80%. Candidate hypotheses must never be substituted for official reconstructed groups.

The holdout uses a new namespace, seed, ten unseen family labels, 30 queues, more benign activity and delayed lineage evidence. It is independently drawn from the same synthetic simulator family, not external validation. Earlier v1/v2 cohorts are diagnostic; v2's opened holdout was not reused after the provenance-count correction.
