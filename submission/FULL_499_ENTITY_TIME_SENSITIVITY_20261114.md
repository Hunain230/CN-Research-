# Full 499-queue entity/time correlation sensitivity

**Date:** 2026-11-14. This additive exploratory run does not revise the Phase 3 final report or its PDF. It uses the same 499 ranked GUIDE_Test organizations, 400,039 unambiguous alerts, expert top-20 denominator of 9,980, 80%-completeness/80%-purity recovery rule, and frozen ranking baselines as the earlier full offline study. No hosted or local LLM call occurred.

## Field evidence and approval status

The [Microsoft Kaggle dataset page](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction/data) describes the prioritization extension, lists CDLA-Permissive-2.0 as the dataset license, and encourages exploring additional GUIDE metadata. The [publisher GUIDE paper](https://arxiv.org/html/2407.09017v4) defines `Timestamp` as alert creation time, describes entity fields as alert evidence, and says identifiers were anonymized and timestamps noised. The Kaggle page and paper **do not establish when every evidence row or entity value became available relative to alert creation**. The released CSV has no separate evidence-arrival field. Therefore the [research-only policy](../configs/entity_time_sensitivity_policy.yaml) permits local sensitivity analysis but leaves the official [operational model-input allowlist](../configs/field_policy.yaml) empty. This is a field-meaning assessment, **not operational approval**.

The corrected [field inventory](../outputs/entity_time_field_audit_20261114_v3.json) scanned all 4,147,992 evidence rows and 637,320 composite alert keys. Every key had a parseable, evidence-row-consistent timestamp. Several entity columns had a dominant numeric-maximum value in a 100,000-row sample; that is **inferred**, not publisher-confirmed, to be a missing sentinel and excluded from matching. After this conservative heuristic, 636,140/637,320 alert keys had at least one non-placeholder entity value. The raw entity values remain in a private local [label-free projection](../outputs/submission_entity_time_shards_20261114_v1.json), not public run reports.

## Method and prediction boundary

The [full-run predictor](../src/submission_full_entity_time.py) verified the frozen full-run candidate/group baseline, development-selected pair model threshold (0.995), trained ranker, field audit, and projection hashes. For each organization it added label-blind candidate routes: rare shared entity within 48 hours and shared technique within one hour, with a nearest-neighbor and token-frequency bound. It then linked alert pairs by the frozen high-confidence descriptor model or a rare-entity plus descriptor agreement rule, enforced the 100-alert component cap, and scored resulting groups with the same transferred ranker. The candidate and grouping definitions are a **new local sensitivity amendment**, not the original 20-neighbor protocol. The [prediction freeze](../outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json) records 499 private prediction hashes before the separate evaluator opened membership and expert rankings. The [run manifest](../outputs/submission_full_entity_time_20261114_v1/run_manifest.json) and [metrics](../outputs/submission_full_entity_time_20261114_v1/metrics.json) provide the reproducibility record.

## Matched results

| All 499 organizations; same 9,980 top-20 labels | Frozen rule + BM25-like | Frozen rule + transferred ranker | New entity/time groups + same ranker |
|---|---:|---:|---:|
| End-to-end Recall@20, organization macro | 0.1364 | 0.1413 | **0.3095** |
| P@10, organization macro | 0.1714 | 0.2049 | **0.3860** |
| nDCG@20, organization macro | 0.1542 | 0.1859 | **0.2816** |
| Pair precision, micro | 0.1135 | 0.1135 | **0.2157** |
| Pair recall, micro | **0.00474** | **0.00474** | 0.00122 |
| Pair F1, micro | **0.00910** | **0.00910** | 0.00243 |
| Pair false positives | 5,888,793 | 5,888,793 | **705,768** |
| Top-20 labels recoverable with oracle ordering of those groups | 2,311/9,980 | 2,311/9,980 | **6,143/9,980** |

Candidate coverage rose from 314,576 to **1,942,648 pairs**. Positive-pair candidate recall rose from 37,018/159,186,107 = **0.0233%** to 699,790/159,186,107 = **0.4396%**; coverage of all possible within-organization pairs rose from 0.00894% to 0.05523%. Those percentages remain very low because the denominator contains 159 million same-incident pairs, including very large incidents. The new method improves top-20 group recovery and pair precision but **worsens positive-pair recall and F1 after grouping**. Do not describe it as an all-metric win or as 99% candidate recall.

For the all-499 comparison, the paired new-minus-frozen-rule/transferred-ranker Recall@20 difference is **+0.1683** with descriptive 95% organization-bootstrap interval **[+0.1495, +0.1872]**. On the 135 organizations outside the pair-model and ranker training split, new versus transferred-ranker Recall@20 is **0.3084 versus 0.1542**; the paired difference is +0.1543 [0.1172, 0.1917]. These organizations and their labels were accessed earlier in this project, so the split and intervals do **not** make this confirmatory. The 499 aggregate includes the 334 training organizations.

The new groups' oracle-order ceiling is **61.55%** (6,143/9,980) under the fixed 80/80 rule. That is an evaluator-only diagnostic, not measured model performance. Neither that ceiling nor the achieved 30.95% reaches the proposed 85% absolute Recall@20 goal.

## Resource observations and limits

The private label-free projection took **8.96 seconds** and occupied **40.6 MB** as 499 Parquet parts on this machine. The frozen full prediction pass took **84.42 seconds** for 400,039 alerts and 1,942,648 candidates, with p50/p95 per-organization times of 0.079/0.423 seconds and peak process RSS of **520 MB**. These are local retrospective batch measurements, not alert-arrival latency, sustained streaming throughput, queue backlog, or SOC service reliability. Hardware and I/O conditions are not standardized across labs.

The main threats to a publishable superiority claim remain prior label exposure, unverified evidence availability at alert time, no new sealed top-20 cohort, noisy timestamps, uncertain active-queue semantics/rank direction, exclusion of 70,702 ambiguous alert keys, and lack of matched full-queue Qwen C/P/V evaluation. The result is a stronger **exploratory offline correlation baseline** only. The [future-cohort and shadow-mode gate](FRESH_COHORT_AND_SHADOW_GATE.md) records the exact next evidence required.

## Reproduce without overwriting frozen results

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_entity_time self-test
.\.venv\Scripts\python.exe -m src.submission_full_entity_time predict --run-id submission_full_entity_time_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_full_entity_time evaluate --run-id submission_full_entity_time_NEW_ID
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_full_entity_time_NEW_ID
```

The private label-free projection and trained models are fixed upstream artifacts. The evaluator reads local membership and ranks after predictions freeze; it does not supply features to the predictor.
