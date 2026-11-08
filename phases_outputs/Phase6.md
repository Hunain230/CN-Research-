# Phase 6 — Research experiments (offline priority retrieval)

**Status:** Exploratory priority retrieval and ambiguity-excluded correlation diagnostics completed under explicit assumptions. This is not completion of the full correlation–prioritization–verification study.  
**Classification:** Exploratory tie-aware re-analysis after the first test-label access.  
**Run:** `phase6-priority-20261108-v2`.

## What ran

Implemented a separate local-only BM25 exemplar-retrieval experiment. It forms candidates with gold `IncidentId` groups, fits only from pilot/development top-20 exemplars, and scores all 14,139 test-organization candidate incidents without reading test `QueueRank` values in prediction. The evaluator then joined the frozen candidate hashes to all 600 test top-20 labels across 30 held-out organizations.

Every row for the 70,702 ambiguous composite alert keys was excluded from descriptor construction; among the 50 split organizations, this removed 128,177 evidence rows. No `IncidentId`, `QueueRank`, outcome, raw entity value, timestamp, or location entered model-visible descriptor text. Only `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` were used under project assumptions. There were no external API/model calls and no dependency installation. Raw input hashes matched before and after both prediction passes and were rechecked before evaluation.

Of the 400 top-20 examples from the pilot/development organizations, 358 had at least one usable descriptor and entered the primary BM25 exemplar corpus. In the primary test condition, 12,939 of 14,139 candidates had nonempty descriptors (91.5%); candidates with no usable text remained in the candidate universe and received zero BM25 score.

Conditions include the primary five-field scorer, five leave-one-field-family-out ablations, and 20%/40% token masking at five fixed seeds (41–45). The candidate-level predictions and per-organization metrics are restricted under ignored `data/derived/empirical/`; reports and aggregate figures are under `outputs/`.

## Tie-aware primary result

Equal BM25 scores occurred within the top 10 and top 20 for all 30 primary-condition organizations; 497 of 600 top-20 slots were inside tied blocks. The final report therefore takes expected metrics over uniform permutations within each score tie. This prevents the opaque key used to serialize prediction rows from selecting the relevant items at cutoffs.

| Metric | Mean across 30 organizations | 95% organization-bootstrap interval |
|---|---:|---:|
| Precision@10 | 0.4622 | [0.3509, 0.5734] |
| Recall@20 | 0.3392 | [0.2492, 0.4284] |
| nDCG@20, assuming QueueRank 1 is highest | 0.3924 | [0.2857, 0.5016] |
| nDCG@20, sensitivity assuming QueueRank 20 is highest | 0.1153 | [0.0676, 0.1680] |

The 20% masking conditions averaged P@10 0.3896, Recall@20 0.2820, and primary-direction nDCG@20 0.3230 across their five seeds. The 40% masks averaged 0.3139, 0.2391, and 0.2276, respectively. Removing `MitreTechniques` reduced Recall@20 by 0.0495 on average versus primary (paired 95% organization-bootstrap interval [-0.0823, -0.0204]); the P@10 paired interval included zero. These are descriptive exploratory comparisons, not evidence of statistical significance or causal feature importance.

## Ambiguity-excluded correlation diagnostic

The second diagnostic used 30,692 unambiguous alert keys and excluded every conflicting key. A same-organization shared-ATT&CK candidate generator selected at most 20 Jaccard-nearest neighbors per alert. It generated 194,296 links from an exhaustive universe of 67,048,813 possible within-organization pairs; 6,142,793 were positive same-incident pairs among the remaining unambiguous alerts.

| Metric | Micro | Macro per-organization mean [95% bootstrap interval] |
|---|---:|---:|
| Pair precision | 0.2670 | 0.1093 [0.0352, 0.2019] |
| Full-positive-pair recall | 0.00845 | 0.2535 [0.1525, 0.3633] |
| Full-pair F1 | 0.0164 | 0.0603 [0.0197, 0.1245] |
| Candidate-generation coverage | 0.00290 | 0.0620 [0.0359, 0.0919] |

The mean per-organization clustering diagnostics were 4.97 false merges and 50.47 false splits. The very low pooled recall and candidate coverage show that this technique-only candidate rule misses most full-universe positive pairs; it is a negative/limited diagnostic, not a competitive correlation baseline.

The corrected report omits candidate-set recall because the rule links every generated pair, making that measure mechanically 1 when positive candidate pairs exist. Full-positive recall counts candidate-generation misses. Pooled and macro values differ because the pooled metric weights organizations by pair counts, while macro treats organizations equally.

## Interpretation limits

- **Oracle-group ceiling:** true incident groups are used to form ranking candidates. This measures prioritization conditional on perfect grouping; it is not an end-to-end system result.
- **Local candidate proxy:** candidate universe is all distinct local GUIDE composite incidents in test orgs, not a publisher-confirmed active queue snapshot.
- **Rank direction:** rank 1 highest is assumed. P@10 and top-20 Recall depend only on top-20 membership; nDCG changes materially under the opposite direction.
- **Field provenance:** the five fields are treated as alert-time descriptors by project assumption; this is not independent source-owner/privacy approval.
- **Correlation and LLMs:** one ambiguity-excluded correlation diagnostic was produced, but full-dataset correlation/joint metrics, severity baseline, empirical LLM comparisons, model latency, API cost, and human-review results remain unavailable. Hosted model calls remain unauthorized.

## Evaluator incident disclosure

The v1 evaluator attempt read test labels and then failed before writing a report because of a report-assembly `KeyError`. It printed no metric values. The corrected v2 run used the same scorer and generated byte-identical predictions for all 16 conditions and the same candidate-universe hash. A later audit found substantial score ties, so the tie-aware evaluation is explicitly a post-access exploratory metric correction. The attempt history and hash comparison are recorded in [`test_evaluation_access_log.md`](test_evaluation_access_log.md); the metric decision is in [`metric_tie_amendment.md`](metric_tie_amendment.md).

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m src.empirical_priority predict --root . --out outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_priority evaluate --root . --run outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_priority_tie_eval --root . --run outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.plot_phase6_priority --run outputs/phase6/priority/new-run-id --tie-aware
```

Use a new run ID. The existing final artifacts are the [aggregate evaluation report](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/report.md), [metrics JSON](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/metrics.json), [Precision@10/Recall@20 figure](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_precision_recall.png), and [nDCG direction-sensitivity figure](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_ndcg_direction_sensitivity.png).

The bounded correlation result is in the [corrected aggregate report](../outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/report.md), [metrics JSON](../outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/metrics.json), and [correlation figure](../outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/figures/correlation_metrics.png). Its reporting amendment is in [`correlation_metric_report_amendment.md`](correlation_metric_report_amendment.md).

To reproduce the bounded correlation diagnostic under a new exploratory run ID:

```powershell
.\.venv\Scripts\python.exe -m src.empirical_correlation predict --root . --out outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_correlation evaluate --root . --run outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_correlation_report_fix --root . --run outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.plot_phase6_correlation --run outputs/phase6/correlation/new-run-id
```

![Phase 6 tie-aware Precision@10 and Recall@20](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_precision_recall.png)

![Phase 6 tie-aware nDCG rank-direction sensitivity](../outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_ndcg_direction_sensitivity.png)
