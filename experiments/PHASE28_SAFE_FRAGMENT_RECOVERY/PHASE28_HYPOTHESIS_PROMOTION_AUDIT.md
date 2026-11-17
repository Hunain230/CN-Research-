# Hypothesis promotion audit

The Phase 27 graph and hypothesis builder are reused unchanged. A lightweight training-only naive Bayes model scores visible dual lineage, root-disjoint witnesses, context consistency, exposure, duplicate ratio, common roots and arrival time. The threshold is calibrated inside a predeclared structural guard. In the 12 training queues, **78 true and zero false** hypotheses met the guard; the earlier diagnostic global threshold admitted none. No development or holdout labels enter inference.

The promoter outputs PROMOTE, RETAIN AS HYPOTHESIS or REJECT. Every decision stores the complete proposed component, score, threshold, visible features, pair exposure, minute-100 snapshot hash and decision time. It recomputes the resulting component's context, witness features and exposure after each accepted union. Retained and rejected hypotheses remain available to the separate discovery track.

| Split | Qualifying hypotheses / all | Top-20 incidents hypothesized | Component promotions | True promotions | Promotion precision | Retained | Promotion coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | 208/287 (72.47%) | 166/400 | 127 | 127 | 100% | 160 | 61.06% of qualifying hypotheses |
| Holdout | 326/477 (68.34%) | 229/600 | 180 | 173 | 96.11% | 297 | 53.07% of qualifying hypotheses |

The abstention rate among evaluated component proposals was 55.75% on development and 62.26% on holdout. The calibrated score-only diagnostic accepted 287/287 development proposals, including 79 nonqualifying ones, creating 72 false grouped pairs. The component guard excluded those development errors but failed on seven holdout hypotheses with two independent-looking false lineage paths. A source-root diversity count is therefore useful but insufficient as a causal-truth certificate.
