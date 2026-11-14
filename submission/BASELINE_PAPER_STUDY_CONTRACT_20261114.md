# Baseline-paper study contract

**Status:** prepared, not a new evaluation. The existing GUIDE_Test labels have already been used during method development. This contract describes what the next independent study must hold fixed. It does not revise the Phase 3 final report or PDF.

## Research claim and task boundary

The primary claim to test is whether evidence-grounded C/P/V improves **end-to-end recovery of expert top-20 incidents from raw alerts** over matched offline and LLM controls. A predicted top-20 group recovers a gold incident only when it contains at least 80% of that incident's in-scope alerts and is at least 80% pure. The primary endpoint is organization-macro Recall@20 with all 20 expert labels per eligible queue in the denominator.

Keep a **ranking-only** benchmark separate: existing incident groups supplied to every ranking method, with P@5, P@10, P@20, Recall@20, and rank-direction sensitivity for nDCG@20. The [AIP paper](https://arxiv.org/html/2607.16963v1) evaluates ranking of already existing incidents and reports P@K; its published P@10 must not be compared directly with our predicted-group end-to-end Recall@20.

## Source and cohort gate

The local queue-ranking CSV is [byte-identical to a fresh Kaggle download](../outputs/submission_kaggle_queue_alignment_20261114_v1.json). Its local columns are `OrgId,IncidentId,QueueRank`, while the AIP paper describes `OrgId,IncidentId,Rank,Split`; the exact local split mapping and rank direction still need clarification. The [corrected source audit](../outputs/submission_absent_rank_scope_audit_20261114_v2.json) finds all 9,980 ranked incident pairs in raw GUIDE_Test. Of these, 855 lack an unambiguous alert under the current exclusion policy but do have ambiguous source rows. They remain in all present denominators. A provider-validated rule is needed before assigning those rows in prediction.

No untouched ranked cohort exists in the current workspace. For a confirmatory paper, obtain a new expert-ranked queue cohort or a documented previously sealed release, along with matching alert/evidence rows, source hashes, queue snapshot time, rank direction, and evidence-arrival times. Freeze cohort eligibility and all exclusions before opening its labels. Repartitioning the current GUIDE_Test file does not make it new.

## Matched methods and budgets

Run every method on the same organization queues, alert scope, evidence policy, ranking directions, and evaluator:

| Method | Required role |
|---|---|
| B0 | Simple entity/time or descriptor rule groups with count/severity-like priority if source fields permit. |
| B1 | Same frozen groups with retrieval ranking, including a faithful public BM25-style comparator. |
| B2 | One local LLM call path under the same evidence budget. |
| B3 | Repeated independent local LLM calls with a matched call/token budget. |
| B4 | C+P without V. |
| Proposed | C/P/V with identical C and P inputs to B4; record V review flags, supported citations, and any permitted revision. |
| Offline reference | Frozen v2 entity/time groups plus v4 priority model, separately labeled as a statistical method rather than an LLM C/P/V result. |

Record candidate pair counts, per-method model calls, tokens, elapsed time, peak memory, review flags, and abstentions. If the full LLM comparison is infeasible, use a **predeclared bounded cohort** and report it separately from the full offline cohort. Do not silently compare a 20-queue model result with a 499-queue offline result.

## Metric table to fill after the new run

For every method report: organization count; alert count; 20-label denominator; candidate positive-pair recall and candidate coverage; pair TP/FP/FN, precision, recall, F1, false merges and splits; group purity/completeness; P@10; nDCG@20 under both rank directions if unresolved; end-to-end Recall@20; high-priority misses; review fraction; p50/p95 decision time; and resource use. Give matched method differences with organization-level paired confidence intervals and describe whether they include zero. The [NeurIPS paper checklist](https://neurips.cc/public/guides/PaperChecklist) calls for reproducible main experiments, training and selection details, uncertainty, and compute resources.

Prespecify the primary comparator and any minimum practical gain before the new labels are opened. Treat 80% Recall@20 as the project's aspirational target, **not** a paper acceptance threshold. Report the observed candidate and group ceilings alongside achieved recall so a high number cannot be mistaken for actual model performance.

## Current exploratory anchor

The selected offline statistical reference achieves [42.23% macro end-to-end Recall@20](../outputs/submission_group_ranker_v4_20261114_v1/metrics.json) on all 499 current queues and 41.06% on 135 historical training-disjoint queues. Its groups have a 69.83% oracle-order ceiling. The later hard-negative ranker improves the training-heavy all-499 descriptive score to 43.99% but has no training-disjoint Recall@20 gain, so it is not selected. These are development findings on previously accessed labels. They do not establish the proposed C/P/V advantage or an operational SOC benefit.
The [bounded matched-Qwen control study](MATCHED_20_QUEUE_CONTROL_STUDY_20261114.md) shows 14.43% C+P Recall@20 versus 16.00% for a no-link singleton/rarity control on the same 20 queues and 240 selected pairs. V only supplied review flags. This negative result is part of the baseline record, not evidence of LLM superiority.
