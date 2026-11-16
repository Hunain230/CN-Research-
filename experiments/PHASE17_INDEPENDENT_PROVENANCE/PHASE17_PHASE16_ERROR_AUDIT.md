# Opened Phase 16 error audit, kept separate from Phase 17 selection

The 10 Phase 16 cross-incident accepted lineage links were replayed from the frozen v4 decision log. **All 10 shared both host and account**, showing why context agreement alone cannot prevent common-mode false merges. Exact synthetic endpoint IDs and whether auth/flow references matched are in `PHASE17_PHASE16_FALSE_LINK_AUDIT.csv`. This audit is retrospective evaluator analysis and was not used as Phase 17 training data.

The 44 Phase 16 incidents that were recoverable but missed predicted top 20 are listed in `PHASE17_PHASE16_RANKING_MISSES.csv`; their median first qualifying group position was **24**. They are ranking failures separate from the 146 incomplete C-stage incidents. On Phase 17 development data, the alternative sensor-priority ranker reduced Recall@20 and P@10 relative to the progression ranker at each tested C threshold; it was not selected. No Phase 16 test ranking was tuned.
