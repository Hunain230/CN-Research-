# False-merge audit

The Phase 35 candidate reranks only baseline positions 11–30. The post-evaluation audit verified an identical eligible-alert set, group partition, first ten groups, positions 31 onward, accepted merge count, and pair true-positive count for every one of the 15 development queues. Thus the candidate introduced no new union.

The official evaluator found **19,923 true grouped pairs, zero false grouped pairs, zero mixed groups and 100% grouped-pair precision** for both matched pipelines. No queue had a false-pair or mixed-group increase. P@10 remained **112/150** because the first ten groups were fixed. These are results for the Phase 35 controlled synthetic development cohort only.
