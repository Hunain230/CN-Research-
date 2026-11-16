# Phase 19 status — development only

| Criterion | Result |
| --- | --- |
| Nonzero reconstruction in every train queue | **Pass: 15/15** |
| Nonzero reconstruction in every development queue | **Pass: 15/15** |
| Baseline development recoverability | **123/300 = 41.00%** |
| Baseline development pair precision | **100%**, 0 false pairs, 0 mixed groups |
| Candidate improves recoverability with safety gates | **No** |
| Common-mode hard-negative robustness | **Fail:** 1,181 added false pairs in stress |
| New locked cohort | **Reserved; no predictions or evaluation** |

The 85% group recoverability, 80% Recall@20, 63.88% P@10 and grouped-pair safety targets are **not claimed on Phase 19's locked cohort**, because that cohort was not evaluated. The baseline's standard development metrics cannot erase its adversarial safety failure. Phase 16 v4 remains the best **selected** safe synthetic result on its own cohort; numeric results are not pooled across cohorts.
