# Phase 24 — Recall-first development study

**Decision: NO-GO for promotion.** Phase 24 made a measurable reconstruction and ranking attempt on a fresh, synthetic 16-queue development cohort (320 oracle top-20 incident labels). Its strongest aggregate candidate raised Incident Recall@20 from **92/320 (28.75%) to 155/320 (48.44%)** and group recoverability from **106/320 (33.13%) to 165/320 (51.56%)**. It improved P@10 from **45/160 (28.13%) to 70/160 (43.75%)**. It nevertheless failed the queue-level safety gate: one queue's false grouped pairs rose **63 to 120** through five false-pair-creating accepted unions. No candidate is frozen for locked evaluation. Phase 16 v4 remains the selected safe synthetic result on its different, already opened population.

## Cohort and stages

The final `phase24d_` cohort has ten train and sixteen development queues, 25 attack incidents and 75 benign source observations per queue, with disjoint complete scenarios, seeds, namespaces and template variants. There is **no Phase 24 locked cohort**. Receiver availability is applied at minute 100: 5,394 of 5,452 development alerts are visible, and 352 fields on visible alerts are delayed. Private incident truth, priority ranks, family and fault tags are opened only by the evaluator after development predictions and decisions are written and hashed.

The same-cohort baseline is `context` reconstruction with the historical-style progression ranker. Reconstruction variants test dual lineage, dual override, process-context coherence, rare-reference coherence, and partial evidence. Ranking variants hold each grouping fixed and compare severity, progression, a train-fitted pairwise linear ranker, and a fixed blend. Source IDs only deduplicate derived alerts and identify provenance endpoints; their characters are not ranking features. Host/account and time alone never propose a union.

## Main comparison

| Development method | Recoverable / 320 | Recall@20 / 320 | P@10 / 160 | Pair precision | False pairs | Mixed groups | Queue gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Context + progression baseline | 106 | 92 | 45 | 91.47% | 1,001 | 30 | reference |
| Context + blend, fixed groups | 106 | 102 | 44 | 91.47% | 1,001 | 30 | pass, reconstruction unchanged |
| Coherent + blend | 201 | 187 | 83 | 89.09% | 2,000 | 26 | fail |
| Coherent rare + progression | 165 | 142 | 68 | 99.11% | 120 | 1 | fail |
| **Coherent rare + blend** | **165** | **155** | **70** | **99.11%** | **120** | **1** | **fail** |
| Partial + blend | 137 | 131 | 58 | 91.87% | 1,113 | 30 | fail |
| Dual + blend | 19 | 18 | 9 | 99.84% | 8 | 8 | recall loss |

The coherent rare candidate's 95% queue-cluster bootstrap descriptive intervals are **43.13–54.06%** for Recall@20 and **45.94–57.19%** for recoverability. These intervals do not validate safety or generalization. The complete 28-row comparison, queue metrics, family and failure-mode stratification, and union increments are in the linked CSV artifacts.

## Why the candidate fails

One of 16 development queues (`phase24d_development_q014`) has **120 false pairs** under coherent rare versus **63** for the baseline. Five accepted `rare_context_lineage` unions add 42, 12, 6, 40 and 20 false pairs in sequence; the increments reconcile exactly to the final 120. Rarity and host/account agreement do not prove correct causal lineage. The larger coherent process groups magnify a false boundary into group contamination. This is the Phase 22–23 trust failure in another form. Aggregate pair precision and the aggregate false-pair reduction cannot override this queue-level failure.

Ranking alone is safer: the context/blend fixed-group comparison gains ten recalled incidents with one fewer P@10 match, but it cannot improve recoverability. The learned ranker alone recalled 105 versus 92 but reduced P@10 to 39; the fixed blend retained more top-ten utility. The strongest combined candidate improves both stages but fails safety. No candidate passes all development acceptance gates.

## Historical relationship and limits

Phase 16 v4's opened holdout remains **75.17% recoverability, 67.83% Recall@20, 63.00% P@10, 98.61% pair precision, 440 false pairs and 257 mixed groups**. Phase 24's new synthetic population has different construction and denominators; its percentages are not a direct regression or improvement against Phase 16. Phase 10 GUIDE is retrospective and is not a training or threshold-selection source here. Neither the Phase 19 nor Phase 22 locked cohort was opened.

The final generator's failure-mode labels are incomplete proxies: `registry_error` is a scenario tag without a full receiver-attested registry, and `compromised_sensor` perturbs lineage references without a separately audited physical receipt stream. The isolated [trust stress](PHASE24_TRUST_STRESS.csv) confirms that the Phase 23 domain check accepts false but internally consistent receipts with independent-looking or incorrectly split roots. It is a counterfactual unit fixture, not field validation. These limits reinforce the NO-GO decision.

See the [historical assessment](PHASE24_HISTORICAL_ASSESSMENT.md), [target status](PHASE24_TARGET_STATUS.md), [recall error analysis](PHASE24_RECALL_ERROR_ANALYSIS.md), [reconstruction audit](PHASE24_RECONSTRUCTION_AUDIT.md), [ranking audit](PHASE24_RANKING_AUDIT.md), [reproducibility record](PHASE24_REPRODUCIBILITY.md), and [decision record](PHASE24_GO_NO_GO.md).
