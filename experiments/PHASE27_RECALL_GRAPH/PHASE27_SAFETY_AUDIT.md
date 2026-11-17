# Group, edge and temporal safety audit

The selected pipeline and its same-cohort baseline share committed groups. Both have 100% grouped-pair precision, zero false grouped pairs and zero mixed groups on all 30 locked queues, with no queue-level regression. The same holds on all 20 authoritative development queues. Union increments exactly reconcile with final group-pair counts. The Phase 25 veto diagnostic had 80 false-pair-creating unions and 80 mixed groups on development, failing all 20 queue checks.

Candidate-edge errors remain separate: 80 development and 150 holdout false candidate edges produced no grouped-pair error. Nonqualifying hypotheses numbered 80 and 179; all appeared within their queues' first 20 confidence-ranked hypothesis slots. This is a false analyst-suggestion workload even when group safety is intact.

Every frozen graph, hypothesis, prediction and decision records minute-100 cutoff and snapshot hash. The access layer excludes later evidence; tests mutate future values and confirm an earlier snapshot's hash is invariant. V3 deduplicates source pairs and requires disjoint controller roots before counting multiple independent witnesses. The synthetic simulator still does not prove causal reliability or field calibration.
