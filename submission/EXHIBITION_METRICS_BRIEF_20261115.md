# Exhibition metrics brief: offline GUIDE research prototype

## Main result to present

The retrospective offline system groups 400,039 unambiguous alerts from 499 GUIDE_Test organization queues and ranks predicted incidents for analyst review. Its selected v2 grouping plus v7 priority model recovers **4,972 of 9,980 expert top-20 incidents: Recall@20 = 49.82%**. **P@10 = 61.58%** and **nDCG@20 = 0.4371**. On the 135 queues outside ranker training, Recall@20 is **45.52%**. These values come from the [frozen matched evaluation](../outputs/submission_group_merge_v10_20261114_v2/metrics.json). The later group-merge model failed the development purity gates and was not adopted; the [matched study](GROUP_MERGE_MODEL_STUDY_20261114.md) records that negative result.

This is an incident recovery and ranking task. It is not equivalent to binary intrusion detection on individual flows or alerts. The result is exploratory: GUIDE_Test labels were accessed earlier in the project, and the point-in-time availability of entity/time evidence is unresolved. The current groups have an ideal-ordering ceiling of **6,969/9,980 = 69.83%**, so further ranking alone cannot reach 80%.

## Detector-style pair table: conditional on retrieved candidates

For a presentation table like a binary classifier report, the frozen pair model was evaluated on the **same 129,965 retrieved candidate pairs** in 68 historical holdout queues. The model was trained on different organizations. Thresholds below were chosen using only the 67 development queues; holdout labels were opened in the evaluator. The holdout labels had been accessed in earlier project work, so this is still exploratory. Full confusion counts, denominators, and threshold selection are in the [operating-point record](../outputs/submission_candidate_pair_operating_points_20261115_v1.json); the [frozen 0.75 score audit](../outputs/submission_candidate_pair_classification_20261115_v1.json) independently records AUC and baseline counts.

| Historical 68-queue candidate pairs | Recall | Precision | F1 | FPR | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| Conservative grouping threshold 0.75 | 16.46% | 67.58% | 26.47% | 3.06% | 0.7932 | 0.5676 |
| Threshold chosen for ≤1% FPR on development queues | 21.93% | 65.17% | 32.82% | 4.54% | 0.7932 | 0.5676 |
| Threshold chosen for maximum F1 on development queues | **87.99%** | 42.71% | 57.51% | **45.67%** | 0.7932 | 0.5676 |

The high-recall setting is a **sensitivity analysis, not the deployed or selected grouping rule**. Its false-positive rate is far too high to claim an acceptable SOC operating point. The development ≤1% FPR constraint also did not transfer to holdout: observed FPR was 4.54%. AUC and average precision summarize the frozen pair scores and therefore do not change with the reporting threshold. Average precision is the non-interpolated precision–recall summary, not a separately computed trapezoidal area.

Candidate-pair recall is **conditional on the retrieval stage**. Across all 499 queues, retrieval includes 699,790 of 159,186,107 positive within-organization pairs, only **0.4396%** of that exhaustive pair universe. The 87.99% holdout sensitivity result must never be described as recall over all alert pairs or as incident Recall@20. The selected end-to-end result remains **49.82% Recall@20**. The very large exhaustive pair denominator contains many same-incident pairs outside any local candidate window; report both stage and end-to-end denominators so the audience understands the task.

## Suggested slide wording

> On the 499-queue retrospective GUIDE benchmark, our offline incident grouping and prioritization pipeline recovered 4,972/9,980 expert top-20 incidents (49.82% Recall@20) with 61.58% P@10. A separate candidate-pair sensitivity analysis reached 87.99% recall on retrieved positive pairs in the historical holdout, but at 45.67% false-positive rate; that threshold was not selected for incident grouping. Results are exploratory because the benchmark labels were previously accessed, and live point-in-time evidence availability has not been established.

For the exhibition, show the first paragraph as the primary result and the pair table as an honest precision–recall tradeoff. Do not combine the 87.99% pair-stage sensitivity with the selected grouping precision or imply that it improves end-to-end recovery. The [full Phase 3 report](FINAL_REPORT.md) and PDF remain unchanged.
