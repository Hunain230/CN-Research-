# False merge and queue safety audit

All three development candidates and the selected fresh-holdout candidate are rank permutations of the original groups. The audit compares the sorted group partition and eligible alert IDs queue by queue, then verifies exact equality of true pairs, false pairs, and mixed groups in the official evaluator output.

Development: 1,970 groups, 236 false pairs, 127 mixed groups, and 98.5784% grouped-pair precision are identical for baseline and selected candidate across all 15 queues. Fresh holdout: 3,974 groups, 306 false pairs, 252 mixed groups, and 99.0532% grouped-pair precision are identical across all 30 queues. There are **zero additional false pairs and zero additional mixed groups**, including at queue level. No new union or promotion was performed.

The existing baseline has false merges; this experiment does not repair them. The hard gate is no *increase* relative to the matched baseline. Phase 28's seven unsafe holdout promotions and 35 additional false pairs are prior evidence against reusing its promotion rule here. Pair precision by itself is not treated as sufficient safety evidence.

The full paired queue counts are in `HOLDOUT_RESULTS.csv`; the exact partition assertions are in `audit.py` and `artifacts/post_evaluation_audit.json`.
