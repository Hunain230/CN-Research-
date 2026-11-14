# Full GUIDE ranker transfer and grouping ceiling

**Date:** 2026-11-14. This additive exploratory iteration leaves the Phase 3 final report, PDF, earlier predictions, and earlier metrics unchanged. It tests an already fitted offline ranker on the frozen full GUIDE_Test predicted groups. It makes no new local-Qwen or network calls.

## Method and evaluation boundary

The [prediction implementation](../src/submission_full_ranker_transfer.py) verifies the SHA-256 hashes of the full-run group predictions, the fitted ranker, and the historical organization split. It scores all 499 organizations using only the existing group alert-count and local BM25-like features, then saves a private score freeze. The separate evaluator reads incident membership and expert queue ranks only after the score freeze. Candidate pairs, predicted groups, the 80%-completeness/80%-purity recovery rule, and all 20 labels per organization remain fixed. [Run manifest](../outputs/submission_full_ranker_transfer_20261114_v1/run_manifest.json), [prediction freeze](../outputs/submission_full_ranker_transfer_20261114_v1/prediction_freeze.json), and [aggregate metrics](../outputs/submission_full_ranker_transfer_20261114_v1/metrics.json) record the lineage and results.

| Same frozen full-run groups | Count | Local BM25-like | Transferred ranker |
|---|---:|---:|---:|
| **All 499 organizations**, P@10 macro | 0.0492 | 0.1714 | **0.2049** |
| **All 499 organizations**, end-to-end Recall@20 macro | 0.0543 | 0.1364 | **0.1413** |
| **All 499 organizations**, nDCG@20 macro | 0.0364 | 0.1542 | **0.1859** |
| **135 organizations outside ranker training**, P@10 macro | 0.0518 | 0.1971 | **0.2351** |
| **135 organizations outside ranker training**, end-to-end Recall@20 macro | 0.0552 | 0.1507 | **0.1542** |
| **135 organizations outside ranker training**, nDCG@20 macro | 0.0345 | 0.1480 | **0.1776** |

The 135-organization row reproduces the previously recorded trained-ranker comparison on the same frozen full-run groups; it is a consistency check, not an independent new test. The 499-organization row extends scoring to the entire ranked export but **includes the 334 training organizations**, so it is descriptive, not a generalization estimate. Organization-bootstrap paired ranker-minus-BM25 Recall@20 differences are +0.0049 [0.0026, 0.0074] on all 499 and +0.0035 [-0.0001, 0.0076] on the 135 training-disjoint organizations. The latter interval includes zero. Prior project access to all test labels makes both comparisons exploratory.

## Where the remaining misses occur

The separate [group-ceiling diagnostic](../outputs/submission_full_group_ceiling_20261114_v1.json), produced by the [evaluator-only analysis](analyze_full_group_ceiling.py), inspects **all** frozen groups with ground truth. Of 9,980 expert top-20 labels, 855 have no unambiguous alert in scope, 6,814 have alerts but no predicted group meeting the 80/80 recovery rule, and only **2,311** are recoverable even with oracle ordering. Thus **23.16%** is an oracle-order upper bound for this exact frozen grouping, not achieved model Recall@20. The transferred ranker achieves 14.13% under the same evaluation. Improving order alone cannot solve the 6,814 grouping misses.

This diagnostic makes the next research priority clear: candidate construction and grouping require a redesigned, point-in-time approved evidence view. The official model-input allowlist is empty; the five descriptors in this study are local assumptions, and raw entity/time fields lack timing and privacy approval. The full 499-organization rule baseline is not the proposed entity/time C/P/V workflow, and the ranker improvement does not establish LLM superiority, operational SOC readiness, or the 95% Recall@20 target. A new untouched labeled cohort is required for a confirmatory publication claim.

## Reproduce

From the repository root, with a **new** run ID:

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_ranker_transfer predict --run-id submission_full_ranker_transfer_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_full_ranker_transfer evaluate --run-id submission_full_ranker_transfer_NEW_ID
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_full_ranker_transfer_NEW_ID
```

The group-ceiling output path is already occupied. Reproduce that evaluator-only diagnostic in a separate checkout or change its output to a new versioned path; do not overwrite the frozen result.
