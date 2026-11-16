# SOC performance sprint: measured outcomes

**16 November 2026 · retrospective exploratory GUIDE study.** This sprint evaluated the already frozen Phase 9G prediction, one new grouping control, and one fixed-group ranking fusion. It did not reach the proposed 80% Incident Recall@20 or 85% group-recoverability targets. All GUIDE_Test labels had been accessed in earlier project work, including the historical holdout. The 68 holdout queues provide an outside-fitting comparison, not independent confirmation.

## Selected result and frozen reference

The strongest **validation-selected, gate-passing exploratory candidate** keeps the entity-enabled candidate graph and v2 groups, and combines within-queue percentile ranks from v7 (25%) and the previously fitted hard-negative LightGBM child40 model (75%). The fusion weights were frozen for all 499 queues before this sprint's evaluator read labels. Among three prespecified weights, 0.75 was selected by highest Recall@20 on 67 historical validation queues subject to P@10 at least v7. Its historical 68-queue holdout also improved Recall@20 and P@10. The all-499 score was not used for selection.

| Same 499 queues, 9,980 expert top-20 labels | Frozen v2+v7 | Selected fusion | Change |
|---|---:|---:|---:|
| Incident Recall@20, tie-aware | 49.82% | **50.77%** | +0.95 points |
| Incident Recall@10, same 9,980 denominator | 30.79% | **31.94%** | +1.15 points |
| Group recoverability, oracle ordering | 69.83% | **69.83%** | 0 |
| P@5 | 68.26% | **71.82%** | +3.57 points |
| P@10 | 61.58% | **63.88%** | +2.29 points |
| nDCG@10 | 0.4158 | **0.4569** | +0.0411 |
| nDCG@20 | 0.4371 | **0.4697** | +0.0326 |
| Grouped-pair precision | 90.4148% | **90.4148%** | 0 |
| Grouped-pair recall, exhaustive pairs | 0.1695% | **0.1695%** | 0 |
| False grouped alert pairs | 28,606 | **28,606** | 0 |
| Mixed predicted groups | 4,841 | **4,841** | 0 |
| Complete-and-pure top-20 labels before ranking | 6,969 | **6,969** | 0 |

The selected fusion recovers **5,066.5 expected labels** under tie-aware scoring versus 4,972 for v7. Fractional counts result from uniform expected ordering within equal-score blocks; no fractional incident exists. Its all-499 paired queue bootstrap 95% interval for Recall@20 change is **−0.02 to +1.91 percentage points**, so this descriptive interval includes zero. P@10 change is **+0.95 to +3.67 points**; nDCG@20 change is **+0.0204 to +0.0444**. These intervals use 5,000 queue resamples and do not remove prior label exposure.

On the **135 outside-fitting queues** (2,700 expert labels), selected-fusion Recall@20 rose from **45.52% to 49.46%** (paired interval **+2.24 to +5.67 points**), P@10 from **55.56% to 59.07%**, and nDCG@20 from **0.4165 to 0.4608**. On the 68 historical holdout queues (1,360 labels), Recall@20 rose from **49.34% to 53.82%**, P@10 from **61.03% to 65.74%**, and nDCG@20 from **0.4389 to 0.4894**. These are exploratory sensitivity checks, since the labels were previously exposed.

The 50% hard40 blend yielded the **highest observed all-499 Recall@20, 51.03%**, with 64.31% P@10. It was **not selected**: choosing it from the all-499 result would override the frozen validation rule. The unblended hard40 ranker had already reached 50.18% Recall@20, but had mixed subgroup behavior. No grouping candidate in this sprint passed its gates.

## Experiments and decisions

| Experiment | Hypothesis and fixed change | All-499 Recall@20 | Recoverability | Pair precision | P@10 | Decision |
|---|---|---:|---:|---:|---:|---|
| Frozen v2+v7 | Accepted reference | 49.82% | 69.83% | 90.41% | 61.58% | Reference |
| Phase 9G boundary scorer | Replace v2 pair scores with train-only hard-negative scorer at fixed 0.75 | 43.59% | 63.38% | 54.98% | 54.59% | **NO-GO** |
| Consensus split | Split v2 groups of at most four alerts where Phase 9G partitions disagree | 45.13% | 64.59% | 92.07% | 56.51% | **NO-GO** |
| Rank fusion, hard40 weight 0.25 | Fixed v2 groups | 50.45% | 69.83% | 90.41% | 63.58% | Unselected |
| Rank fusion, hard40 weight 0.50 | Fixed v2 groups | 51.03% | 69.83% | 90.41% | 64.31% | Unselected |
| Rank fusion, hard40 weight 0.75 | Fixed v2 groups; validation-selected | **50.77%** | **69.83%** | **90.41%** | **63.88%** | **GO, exploratory only** |

Phase 9G's existing model, config and 499 prediction hashes were verified before its evaluator ran. Its all-499 false grouped pairs rose from **28,606 to 137,884** and its mixed-group count fell from 4,841 to 1,855. An evaluator-side pair-set audit found **136,565 newly coassigned cross-incident alert pairs** and **27,287 removed**, a net increase of 109,278. This counts wrong grouped alert pairs, not wrong union-edge decisions. The lower mixed-group count does not compensate for the much larger false-pair burden. Outside fitting, recoverable labels fell **1,945 to 1,773**, Recall@20 fell **45.52% to 40.07%**, and pair precision fell **78.73% to 38.93%**. Every prespecified Phase 9G gate except mixed-group count failed. The evaluator produced the previously missing `metrics.json` without refitting or changing predictions.

Consensus splitting changed 428 queues and split 13,871 small v2 groups. It cut false grouped pairs to **21,905** and mixed groups to **381**; the pair-set audit confirms **zero new** and **6,701 removed** cross-incident grouped alert pairs. It also removed 15,521 true grouped pairs and reduced recoverable labels **6,969 to 6,446**. Outside fitting, recoverable labels fell **1,945 to 1,826**, Recall@20 fell **45.52% to 41.52%**, and P@10 fell **55.56% to 51.70%**. Its purity gain came at an unacceptable completeness cost. It is retained as a negative control, not a replacement.

Rank fusion changes only ordering. The candidate graph remains **1,942,648 pairs** with **699,790 true candidate pairs** out of **159,186,107** exhaustive same-incident pairs (0.4396%); the gold-aware candidate-connected count remains **8,638/9,980**. Pair TP/FP/FN remain **269,832/28,606/158,916,275**. The ranking-failure count falls from **1,997** to about **1,902.5 expected labels**; all upstream failure counts remain unchanged. Thus the fusion's improvement does not establish improved incident reconstruction.

## Method and validity

The historical split has 334 training, 67 validation, 68 holdout and 30 earlier-test/unassigned queues. Phase 9G was fitted only on the 334 training queues. Consensus split used no new labels in prediction. Fusion used previously fitted v7 and hard40 score files; its three weights were fixed before evaluation. `IncidentId`, expert rank, grade, outcome, and group membership were never inference features in these sprint predictors. Each evaluator verified prediction and comparator hashes, reproduced the frozen baseline, and then wrote a separate immutable metrics file. The 80% completeness/80% purity recovery rule, tie-aware evaluator, 499 queues, 400,039 alerts, and 9,980-label denominator were kept fixed.

The training/validation/holdout separation limits direct fitting leakage but cannot create an untouched confirmation cohort after earlier GUIDE_Test exposure. Local entity/time inputs also lack authoritative source-observation lineage and evidence-arrival timestamps; the official operational inference-field allowlist remains empty. No live SOC latency, analyst impact, or deployment efficacy is established. Batch resources are recorded in each metrics file. Phase 9G fit/predict/evaluate took **102.85/585.42/117.30 seconds** at peaks of **392/615/447 MB**; consensus split predict/evaluate took **165.72/9.80 seconds** at **549/447 MB**; fusion predict/evaluate took **15.38/7.39 seconds** at **308/421 MB**. These are local batch measurements.

The fixed-group ceiling of **69.83%** prevents any rank-only method from reaching 80% Recall@20. The selected fusion does not meet the 80%/85% research targets. The strongest defensible next study needs a new, sealed ranked cohort and provenance-rich point-in-time evidence, or a separately authorized development set for a materially different group-reconstruction method. The [error analysis](FINAL_ERROR_ANALYSIS.md), [comparison CSV](FINAL_METRICS_COMPARISON.csv), [selected configuration](FINAL_BEST_PIPELINE_CONFIG.json), and [reproduction guide](FINAL_REPRODUCIBILITY.md) contain the detailed artifacts.
