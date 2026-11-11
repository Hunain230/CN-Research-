# Offline predicted-group comparison — implementation record

**Status:** exploratory GUIDE_Test result, offline-only. This is a joint grouping-to-ranking measurement for deterministic methods and proxies, **not** the complete proposed LLM C/P/V versus B0–B4 comparison.

## What ran

The matched cohort comprises the 57 organizations from the previously accessed 68-organization exploratory holdout with at most 500 unambiguous alerts each. The selection uses alert count, not outcome values. The historical 30-organization test cohort is excluded. All four methods receive the same 11,219 alert records and 1,216,600 frozen, label-blind candidate pairs. Every method partitions all in-scope alerts into predicted components, then ranks those predicted components. No inference step uses `IncidentId` or `QueueRank`.

The B0 amendment uses deterministic shared-ATT&CK-and-category links and ranks by component alert count because the public files lack detector severity. B1 uses exactly the same predicted grouping, with a label-free queue descriptor profile and training-corpus IDF for fielded BM25. The offline CP and CPV proxies reuse the previously trained local pair classifier and incident-priority logistic model; the CPV proxy adds a deterministic descriptor-support link filter. They are not the proposed LLM roles, do not generate cited rationales, and cannot be substituted for empirical B4 or C/P/V results.

## Results

All values below are on the same 57 organization queues. Pair F1 micro pools alert pairs; P@10 and end-to-end Recall@20 are organization macro means. The 80% purity and 80% completeness test uses the unambiguous in-scope alerts of each gold incident. The denominator for Recall@20 is all 1,140 expert labels; only 1,066 labeled incidents have any in-scope unambiguous alert, so 74 are unrecoverable under this exclusion policy. The maximum possible recovery under that policy is 1,066/1,140 = **93.51%**, even with perfect predictions. Because every organization has exactly 20 labels, this is both the pooled and macro ceiling.

| Method | Pair precision micro | Pair recall micro | Pair F1 micro | Pair F1 macro | P@10 macro | End-to-end Recall@20 macro | nDCG@20 macro, rank 1 high |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 rule + count amendment | 0.0912 | 0.2698 | 0.1364 | 0.0684 | 0.0684 | 0.0746 | 0.0364 |
| B1 rule + label-free BM25 | 0.0912 | 0.2698 | 0.1364 | 0.0684 | 0.0298 | 0.0316 | 0.0062 |
| Offline CP proxy | 0.0458 | 0.3555 | 0.0811 | 0.0409 | 0.0421 | 0.0211 | 0.0395 |
| Offline CPV proxy | 0.0513 | 0.2923 | 0.0872 | 0.0588 | 0.2105 | 0.1175 | 0.1859 |

For the offline CPV proxy, the 95% organization-bootstrap interval for end-to-end Recall@20 is 0.0947–0.1421; for B0 it is 0.0491–0.1061. These intervals are descriptive because the cohort was previously accessed and the proxies do not represent LLM agents. The current results are far below a 95% final-recall target. The earlier 97.21% at K=500 measured **oracle-group candidate retrieval** and is not comparable to this end-to-end recall.

## Unavailable proposed methods

| Proposed method | Status |
|---|---|
| B0 detector-severity ranking | Unavailable: no severity field or authoritative crosswalk; the count amendment above is a different baseline. |
| B2 single-LLM grouping and ranking | Unavailable in this offline-only run. Synthetic stub outputs are excluded. |
| B3 three-call repeated single-LLM | Unavailable in this offline-only run. Synthetic stub outputs are excluded. |
| B4 C+P LLM roles | Unavailable. The local CP proxy above is deterministic/statistical. |
| Proposed C/P/V LLM workflow | Unavailable. The local CPV proxy above is deterministic/statistical and its filter is not citation verification. |

## Controls, reproducibility, and limits

- The prediction stage checked source hashes, selected organizations by label-blind alert count, verified the frozen correlation prediction hashes, constructed groups, and wrote private predictions and a freeze manifest **before** evaluator-only truth was read.
- The evaluation stage checked source and prediction hashes, loaded membership and queue labels separately, verified that every method partitioned the same alerts exactly once, and calculated pair and 80/80 recovery metrics. Ten-thousand organization-bootstrap draws use the existing seed-0 helper.
- The v1 prototype used a training-positive BM25 query profile and therefore was a supervised proxy, not the proposed B1. Its artifacts were preserved. The v2 run corrected B1 with a label-free queue profile; these are two analyses of the same exploratory cohort, not independent tests.
- The cohort excludes all ambiguous alert keys and is limited to organizations with at most 500 unambiguous alerts. Larger queues, the exact publisher active-queue snapshot, rank direction, field timing, and full-data performance remain unresolved. Only the primary rank-1-high nDCG is shown in this table; the reverse-direction sensitivity and all denominators are in `../outputs/offline_joint_v2/metrics.json`.
- No external model calls or new dependencies were used. Raw data, previous run artifacts, and historical split files were not changed. Private predictions are in ignored `data/derived/offline_joint_v2/`; aggregate outputs and checksums are in `outputs/offline_joint_v2/`.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.offline_joint_comparison self-test
.\.venv\Scripts\python.exe -m src.offline_joint_comparison predict
.\.venv\Scripts\python.exe -m src.offline_joint_comparison evaluate
```

The run refuses to overwrite existing outputs. Use a new versioned configuration and output path for another experiment. The executed [aggregate report](../outputs/offline_joint_v2/report.md), [metrics](../outputs/offline_joint_v2/metrics.json), and [manifest](../outputs/offline_joint_v2/run_manifest.json) are the result artifacts.
