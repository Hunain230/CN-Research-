# Recall failure analysis

On historical Phase 16 locked test, 451/600 incidents are group-recoverable and 407/600 are recalled. The 44 recoverable but unranked incidents cannot be fixed by more merging. The remaining 149 are unrecoverable under the frozen groups. Ranking alone has a 75.17% historical ceiling, below the 80% target.

On comparable development, 233/300 are recoverable, 196/300 baseline-recalled, and 37/300 are rank-limited. The selected `source_depth` ranker recalls 220/300: 26 queue-level gained recall credits and two lost, for a net 24. It leaves 13 recoverable but unranked and 67 unrecoverable. The unchanged-group ceiling is 233/300 = 77.67%.

On the single fresh holdout, baseline recoverability is 463/600. Baseline recall is 410/600; 53 recoverable incidents are rank-limited and 137 are unrecoverable. `source_depth` recalls 444/600, a net 34 more, with no queue-level recall decline. Nineteen remain rank-limited. The unchanged-group ceiling is 463/600 = 77.17%, so 80% is unreachable on this cohort by ranking alone.

The chosen ranker advances larger source-supported groups using only receiver-visible fields. It does not recover genuine fragments missing from the selected groups. Phase 28 showed that apparently independent dual-lineage paths can still be false; this experiment found no new authenticated attestation in Phase 16 inputs that could justify an additional union under the zero-additional-false-pair requirement. Provisional relationships would aid discovery but do not count toward the official group metric without promotion.
