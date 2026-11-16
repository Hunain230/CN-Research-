# Reproducing the performance sprint

## Environment and immutable inputs

Run from the repository root with the existing Python 3.12 virtual environment and `requirements.txt`. The historical raw GUIDE data, unambiguous alert projection, entity shards, 499 v2 group files, v7 score files, hard-negative child40 score files, and their freeze manifests must be present. Raw and per-queue data are git-ignored; the public repository alone cannot recreate the measurements. The official inference-field allowlist remains empty, so these are retrospective local research runs.

The accepted comparator is entity-enabled candidate generation + v2 grouping + v7 ranking. It covers **499 queues, 400,039 alerts, 1,942,648 candidates, and 9,980 expert labels**. No sprint command overwrites the comparator. The run IDs, source/config hashes, input freezes, per-queue hashes, prediction resources, and metrics are recorded under `outputs/` for each experiment. Evaluators independently reproduce the baseline before writing metrics.

## Existing Phase 9G freeze

The Phase 9G fit and prediction artifacts predated this sprint. The evaluator verified the model hash, source/config hashes, frozen comparator hashes, and all 499 per-queue prediction hashes, then created the previously missing metrics file. Do **not** refit to reproduce the reported evaluation:

```powershell
.\.venv\Scripts\python.exe -m submission.evaluate_phase9g_pair_boundary_v1 self-test
.\.venv\Scripts\python.exe -m submission.evaluate_phase9g_pair_boundary_v1 evaluate
```

The second command is intentionally one-shot and refuses to overwrite `outputs/phase9g_pair_boundary_20261115_v1/metrics.json`. To rerun it, use an isolated copy with all frozen inputs and predictions intact and only that metrics file absent. Do not delete the preserved result in this repository.

## New consensus-split control

The [config](experiments/24H_PERFORMANCE_SPRINT/consensus_split_v1.json) fixes the hypothesis, maximum v2 group size of four, and acceptance gates. Prediction reads no evaluator labels; evaluation reads labels after all 499 predictions are frozen.

```powershell
.\.venv\Scripts\python.exe -m src.sprint_consensus_split_v1 self-test
.\.venv\Scripts\python.exe -m src.sprint_consensus_split_v1 predict
.\.venv\Scripts\python.exe -m submission.evaluate_sprint_consensus_split_v1
```

The predictor and evaluator refuse to overwrite `outputs/sprint_consensus_split_v1_20261116/` and `data/derived/sprint_consensus_split_v1_20261116/`. Rebuild only in an isolated copy without those two sprint output directories. The comparator v2, v7, and Phase 9G artifacts must remain identical.

## New ranking fusion

The [config](experiments/24H_PERFORMANCE_SPRINT/rank_fusion_v1.json) fixes the 0.25/0.50/0.75 hard40 weights and validation selection rule. Prediction computes within-queue average rank percentiles from already frozen v7 and hard40 score vectors. It saves all three weights for all 499 queues before the evaluator opens labels. The evaluator selects on the 67 historical validation queues, reports the 68 historical holdout and all 499 queues, and verifies the reference score. The extended-metrics pass calculates P@5, Recall@10, nDCG@10, and paired bootstrap intervals without changing the selected method.

```powershell
.\.venv\Scripts\python.exe -m src.sprint_rank_fusion_v1
.\.venv\Scripts\python.exe -m submission.evaluate_sprint_rank_fusion_v1
.\.venv\Scripts\python.exe -m submission.sprint_extended_metrics
```

These are also one-shot runs. For a full rerun, use an isolated copy with the frozen baseline inputs intact and the two `sprint_rank_fusion_v1_20261116` output directories absent. Do not delete the preserved artifacts in this repository.

## Verification and interpretation

`FINAL_BEST_PIPELINE_CONFIG.json` contains SHA-256 hashes for the selected source freezes and sprint metrics. `FINAL_METRICS_COMPARISON.csv` contains all all-499 methods, including rejected and unselected candidates. `outputs/sprint_rank_fusion_v1_20261116/extended_metrics.json` contains pseudonymous per-queue results and paired 5,000-resample intervals (seed 20261116). The selected pipeline has fixed v2 groups, so pair TP/FP/FN, false grouped pairs, mixed groups, candidate coverage, and 6,969 recoverable expert labels are inherited exactly from the frozen comparator.

The read-only false-merge transition audit is reproduced with `.\.venv\Scripts\python.exe -m submission.sprint_false_merge_audit` in an isolated copy without `outputs/sprint_false_merge_audit_20261116.json`. It verifies frozen v2, Phase 9G, and consensus-split prediction hashes and counts cross-incident alert-pair coassignments newly introduced or removed relative to v2. Its result is also one-shot and preserved in this repository.

The evaluation is **retrospective exploratory**, including the historical holdout: GUIDE_Test labels were previously accessed. Organization separation prevents direct training on outside-fitting queues in this sprint, but does not restore an untouched test. No model-input point-in-time availability or live SOC result is established.
