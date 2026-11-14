# Correlation and grouping iteration on complete small GUIDE queues

**Date:** 2026-11-14. This is an additive, exploratory development study. It does not revise the Phase 3 final report or PDF, does not change historical outputs, and does not use Qwen or a hosted provider.

## Question and method

The earlier frozen rule groups recover at most 287 of the 1,140 expert top-20 labels on 57 complete small organization queues under the fixed 80%-completeness/80%-purity rule. We asked whether a learned pair-link decision, applied to the **same 1,216,600 frozen candidate pairs**, could improve incident grouping and top-20 recovery. The candidate generator, alert cohort, 20 labels per organization, recovery rule, and transferred priority ranker remain matched. The 57-queue alert universe contains 11,219 unambiguous alerts.

The [training implementation](../src/submission_pair_model_grouping.py) fitted a histogram gradient-boosted pair classifier on 19,958 positive and 19,958 negative sampled pairs from **334 historical training organizations**, using only the five locally assumed descriptor fields: DetectorId, Category, MitreTechniques, EntityType, and EvidenceRole. Its first frozen [0.5-threshold run](../outputs/submission_pair_model_grouping_20261114_v1/metrics.json) failed: Recall@20 was 0.0086 and false merges rose sharply. That negative result is retained.

The separate [development calibration](../src/submission_pair_group_calibrate.py) examined six prespecified link thresholds on **42 complete small validation organizations** and selected **0.995** by macro end-to-end Recall@20, then pair F1, then higher threshold. The [calibration table](../outputs/submission_pair_group_calibration_20261114_v1.json) records all six outcomes and label access. The [follow-up predictor](../src/submission_pair_grouping_v2.py) applied that frozen threshold to the 57 queues using the preexisting candidate files, formed components under the unchanged 100-alert cap, scored them with the existing transferred ranker, and froze private predictions before the separate evaluator read the 57 labels. See the [prediction freeze](../outputs/submission_pair_grouping_v2_20261114_v1/prediction_freeze.json), [metrics](../outputs/submission_pair_grouping_v2_20261114_v1/metrics.json), and [run manifest](../outputs/submission_pair_grouping_v2_20261114_v1/run_manifest.json).

## Matched 57-queue result

| Metric | Frozen rule groups + transferred ranker | Learned pair groups + same ranker |
|---|---:|---:|
| End-to-end Recall@20, organization macro | 0.1678 | **0.3179** |
| P@10, organization macro | 0.2772 | **0.4087** |
| nDCG@20, organization macro | 0.1940 | 0.2056 |
| Pair precision, micro | 0.0912 | 0.1083 |
| Pair recall, micro | **0.2698** | 0.1338 |
| Pair F1, micro | **0.1364** | 0.1197 |
| Pair TP / FP / FN | 12,842 / 127,914 / 34,765 | 6,372 / 52,474 / 41,235 |
| Expert top-20 labels recoverable with oracle ordering of those groups | 287 / 1,140 (25.18%) | **667 / 1,140 (58.51%)** |

The paired new-minus-rule organization-bootstrap Recall@20 difference is **+0.1501** with descriptive 95% interval **[+0.0947, +0.2092]**. P@10 differs by +0.1315 [+0.0609, +0.2089]. The nDCG difference is +0.0116 [-0.0642, +0.0926]. The improvement comes from more usable pure groups and fewer false merges, while pairwise recall and F1 worsen. Do not report this as an all-metric win. The 58.51% oracle-order figure is a **ceiling for these particular new groups**, not achieved model performance. It shows that ranking alone cannot reach an 85% absolute Recall@20 target with this grouping.

## Publication boundary

The 57 holdout labels were accessed earlier in this project, so the within-run train/validation/prediction-freeze separation does **not** create a fresh confirmatory test. The 42 validation labels were used to select the threshold. The sampled pair training distribution differs from the operational candidate distribution; model probabilities are not calibrated incident probabilities. The 57 queues have at most 500 unambiguous alerts each and are not representative of all 499 ranked organizations. The five descriptors remain a **local-only field assumption**; the official point-in-time model-input allowlist is empty. There is no live arrival stream, analyst adjudication, or operational SOC performance measure here.

This result supports an exploratory claim that conservative learned linking can improve predicted-group top-20 recovery on these complete small queues relative to a matched rule baseline. It does **not** establish 85% absolute Recall@20, full-dataset performance, C/P/V or Qwen superiority, or paper acceptance. A future confirmatory study needs a frozen method, approved point-in-time evidence, and an untouched labeled cohort. The next engineering step is to improve candidate and group coverage without losing the false-merge control; the pairwise recall drop and 58.51% grouping ceiling quantify that remaining problem.

## Reproduce

The training model and calibration have fixed historical run paths. To reproduce the final prediction/evaluation with a fresh ID, use:

```powershell
.\.venv\Scripts\python.exe -m src.submission_pair_grouping_v2 predict --run-id submission_pair_grouping_v2_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_pair_grouping_v2 evaluate --run-id submission_pair_grouping_v2_NEW_ID
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_pair_grouping_v2_NEW_ID
```

For a full retraining from scratch, reproduce in an isolated checkout or change **all** fixed training and calibration paths to new versioned names; never overwrite these frozen results.
