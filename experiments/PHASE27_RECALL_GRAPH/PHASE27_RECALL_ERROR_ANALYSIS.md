# Recall error analysis

Official Recall@20 cannot exceed group recoverability. On development, the selected ranker recalled all 118/400 recoverable top-20 incidents; **282/400** remained outside official recovery. On holdout, it recalled all **171/600** recoverable incidents; **429/600** remained outside official recovery. It removed the progression baseline's 12 holdout ranking misses, but could not turn the 231 newly discovered uncommitted hypotheses into official reconstructed groups.

The key bottleneck is now safe conversion of a useful hypothesis into a committed group. Simply ranking candidate-linked fragments higher worsened official recall in three development diagnostics. Permanent grouping would also expose the 179 nonqualifying holdout hypotheses to false-group risk. A reviewer-visible suggestion or reversible provisional group can exploit discovery information while new independent evidence is sought.

The holdout gaps are 309 more recalled incidents for 80% Recall@20 and 339 more recoverable incidents for 85% group recoverability. These are Phase 27 denominators only.
