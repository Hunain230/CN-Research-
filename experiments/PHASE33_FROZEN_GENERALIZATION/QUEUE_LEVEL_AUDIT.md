# Paired queue audit

`HOLDOUT_RESULTS.csv` records the original Phase 31 verifier baseline and the frozen Phase 32 +1 candidate on each of the same 15 holdout queues. Both have **zero false grouped pairs and zero mixed groups in every queue**, so there is no queue-level merge-safety regression. Both have 100% grouped-pair precision. Aggregate P@10 improved by six credits: it rose in five queues, fell in two and was unchanged in eight. Aggregate Recall@20 improved by ten incidents, although two queues each lost one recalled incident. Those ranking changes are visible in the CSV; they do not conceal a false merge.

The post-evaluation incident audit found 18 newly group-recoverable incidents, 15 newly recalled incidents and five previously recalled incidents that fell out of the top 20, for net gains of 18 recoverable and 10 recalled. Under the candidate, 281/300 incidents are group-recoverable, 260/300 recalled, 21 recoverable but unranked, and 19 unrecoverable.
