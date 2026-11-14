# Matched ranking baseline extension (2026-11-14)

**Evidence class:** exploratory, post-exposure. This adds two immutable ranking experiments to the Phase 3 package. Neither changes the previously frozen full-GUIDE predictions, candidate set, groups, Qwen calls, or historical metrics. The method family was investigated after GUIDE_Test labels had already been accessed elsewhere in the project, so the results are descriptive rather than confirmatory.

## Research question and design

Can a stronger **ranking** baseline recover more expert top-20 incidents from the same predicted groups? This is separate from correlation: every compared ranker receives identical group membership and candidates. Full run alert-pair precision, recall, F1, and candidate recall therefore cannot improve through reordering alone.

The first experiment applies equal-weight reciprocal rank fusion (RRF, fixed `k=60`) to the frozen alert-count and local BM25-like group rankings, using average positions for raw-score ties. It has no fitted weights or labels. [Cormack, Clarke, and Buettcher's original RRF paper](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf) motivates this standard fixed-form ranking control; this project does not assume it will win on SOC queues. The [499-organization frozen run](../outputs/submission_rank_fusion_20261114_v1/run_manifest.json) reuses the exact 400,039 alerts and 9,980 expert-label denominator of the parent full offline run. Its [code](../src/submission_rank_fusion.py) freezes scores before truth evaluation.

The second experiment fits a balanced logistic ranker with a standard scaler and fixed `C=1`, `liblinear`, seed 0. Its five group features come only from frozen count/BM25-like scores and within-queue positions. Historical GUIDE rerun assignments give **334 training organizations** and **135 evaluation organizations** (67 validation plus 68 holdout); the old 30 test organizations are excluded from this split. The prediction stage reads membership and expert top-20 labels only for training organizations, fits on **1,522 positive groups** among its training groups, and freezes scores for the 135 evaluation organizations. The separate evaluator then opens their truth. All three ranking rows below use the same 135 organizations, 196,686 unambiguous alerts, 192,585 candidate pairs, 2,700 expert labels, and predicted groups. See the [frozen trained run](../outputs/submission_trained_ranker_20261114_v1/run_manifest.json) and [code](../src/submission_trained_ranker.py). The split is organization-disjoint within this run, but prior project exposure means it is **not** an untouched final test.

## Results with matched denominators

| Same 135 organization queues | P@10 macro | End-to-end Recall@20 macro | nDCG@20 macro, rank 1 high |
|---|---:|---:|---:|
| Rule/count ranking | 0.0518 | 0.0552 | 0.0345 |
| Rule/local BM25-like ranking | 0.1971 | 0.1507 | 0.1480 |
| Rule/trained logistic ranking | **0.2351** | **0.1542** | **0.1776** |

The [trained-run metrics](../outputs/submission_trained_ranker_20261114_v1/metrics.json) provide 10,000-resample **paired organization-bootstrap** intervals. Trained minus BM25-like P@10 was **+0.0380** [0.0228, 0.0544]; nDCG@20 was **+0.0296** [0.0122, 0.0476]; Recall@20 was **+0.00349** [-0.00012, 0.00748]. Thus ordering improved on this descriptive cohort, but the Recall@20 interval includes zero. No p-value or model superiority claim is made from this exposed cohort. Rank direction remains an assumption; the JSON also reports rank-20-high nDCG sensitivity.

The fixed RRF control on **all 499 organizations** did worse than the original BM25-like ranker: Recall@20 **0.1352 vs 0.1364**, P@10 lower by 0.0140, and rank-1-high nDCG lower by 0.0373. These [RRF metrics](../outputs/submission_rank_fusion_20261114_v1/metrics.json) are retained as a negative result. They are **not** directly compared with the 135-organization trained row; the latter table uses matched within-cohort baselines.

## Correlation and operational limits

On the 135 evaluation organizations, the inherited candidate set contains only **17,167/145,262,354 positive pairs = 0.0118% candidate recall**, while emitting **192,585/3,269,909,316 possible pairs = 0.00589% coverage**. Shared predicted-group pair confusion is TP **391,695**, FP **4,055,383**, FN **144,870,659**, micro F1 **0.00523**. These values are identical for count, BM25-like, and trained ranking because group membership is unchanged. The parent full-499 candidate result remains 37,018/159,186,107 = 0.0233%. These are different cohorts, not competing candidate methods.

The proposed 95% end-to-end Recall@20 target cannot be reached under the current full-run ambiguous-key exclusion: only 9,125/9,980 labels have unambiguous in-scope alert evidence. Even a perfect ranker cannot recover omitted or incorrectly grouped incidents. The bounded local Qwen result remains a separate 20-organization, 240-selected-pair diagnostic; this study does not improve or re-evaluate it. No inference was sent to a hosted service, and no live SOC alert-to-decision latency or analyst outcome was measured.

An additive [evaluator-only capacity audit](../outputs/submission_retrieval_bounds_20261114_v1.json), reproduced by [its script](diagnose_retrieval_bounds.py), shows why the stated 99% **positive-pair candidate recall** target conflicts with the current 20-neighbor cap on this dataset. For 400,039 alerts, a mutual undirected degree cap of 20 allows at most **4,000,390 pairs**; even if all were positive, that is at most **2.513%** of 159,186,107 positive pairs. A different policy allowing a union of 20 directed proposals per alert could emit at most 8,000,780 pairs, still only **5.026%** of the positive-pair denominator. These are capacity ceilings, not observed recall. Sparse correct edges can connect an entire incident transitively, so low candidate-pair recall is not by itself an end-to-end recall ceiling.

The implemented group cap of 100 alerts creates another hard limit: **62** expert top-20 incidents have more than 125 unambiguous in-scope alerts, so no capped group can contain the required 80% of each. Combined with **855** labels lacking any unambiguous alert, the optimistic full-run end-to-end ceiling is **9,063/9,980 = 90.81%** under the current exclusion and component-cap rules. This assumes perfect grouping and ranking for every remaining label; real errors can only lower it. A revised pair-retrieval metric or cap must be defined *before* a fresh evaluation, and any membership/cap change requires new versioned predictions rather than rewriting the existing run.

## Reproduce and cite

Run the additive experiments under **new** run IDs. The source parent run and split are hash-checked, and each stage refuses to overwrite an existing output:

```powershell
.\.venv\Scripts\python.exe -m src.submission_rank_fusion self-test
.\.venv\Scripts\python.exe -m src.submission_rank_fusion predict --run-id submission_rank_fusion_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_rank_fusion evaluate --run-id submission_rank_fusion_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_trained_ranker self-test
.\.venv\Scripts\python.exe -m src.submission_trained_ranker predict --run-id submission_trained_ranker_NEW_ID
.\.venv\Scripts\python.exe -m src.submission_trained_ranker evaluate --run-id submission_trained_ranker_NEW_ID
```

For a paper, describe the gain as an **exploratory ranking-baseline improvement on previously exposed GUIDE_Test organizations**. It does not establish an operational SOC or a benefit from the multi-agent model. A confirmatory comparison needs new sealed organizations or a prospective source, source-validated alert membership and queue semantics, approved point-in-time discriminative evidence, matched full-queue baselines and C/P/V, and analyst/operations measurement.
