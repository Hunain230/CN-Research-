# Pair scoring experiments and limits

The frozen v2 scorer uses 30 numeric descriptor, shared-entity, time-gap, and route features; the fixed 0.75 grouping threshold was development-selected in the earlier pipeline. Phase 13 reuses its fitted model and tests thresholds 0.80, 0.85, and 0.90 on **exactly the regenerated frozen candidate graph**, keeping the 100-alert cap. No scorer was refitted or calibrated. Raising the threshold is a conservative pair-decision sensitivity, not a new model and not evidence that the probabilities are calibrated.

| Threshold | Recoverable | Pair precision | False grouped pairs | Mixed groups | Newly / lost recoverable versus E1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.75 | 6,969/9,980 (69.83%) | 90.4148% | 28,606 | 4,841 | — / — |
| 0.8 | 6,877/9,980 (68.91%) | 95.0366% | 11,203 | 3,222 | 60 / 152 |
| 0.85 | 6,678/9,980 (66.91%) | 96.8039% | 2,836 | 1,130 | 102 / 393 |
| 0.9 | 6,501/9,980 (65.14%) | 97.4217% | 801 | 500 | 131 / 599 |

At 0.80, false grouped pairs fall by 17,403 and mixed groups by 1,619, while 60 incidents become recoverable and 152 lose recoverability, net −92. At 0.85 and 0.90 the safety counts fall further but net recovery losses deepen. These are group outcomes, not pair precision-recall curves; class-conditional pair-score histograms and calibration remain in the [Phase 9F audit](../../PHASE9F_CROSS_FRAGMENT_PAIR_SCORE_AUDIT.md). That audit found true and hard false cross-fragment scores overlap. The Phase 9G hard-negative model was previously measured at 54.98% pair precision and 137,884 false grouped pairs, so it is not a successful replacement. Logistic regression, new boosted models, graph-context scoring, and calibrated probabilistic scoring were not fitted here: previous GUIDE_Test exposure and absent operational field availability prevent a defensible new model-selection claim. The only new pair-score experiment is this fixed threshold sensitivity.
