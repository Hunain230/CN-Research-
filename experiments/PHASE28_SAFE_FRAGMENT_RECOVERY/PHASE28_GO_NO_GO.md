# Phase 28 decision: NO-GO

Development selection passed all predeclared gates for component-aware promotion: recoverability and Recall@20 107/400 → 207/400, P@10 43/200 → 78/200, pair precision 100%, zero false pairs and zero mixed groups in all 20 queues. Code, model, thresholds, selected rule, holdout generator and evaluator were hashed in `v2/pre_evaluation_protocol.json` before the holdout existed. Only the selected component rule and same-cohort baseline were predicted on holdout; prediction hashes were written before private truth was opened once.

The holdout failed a hard gate: false grouped pairs **41 → 76**, including seven queue-level regressions of one to six false pairs each. Grouped-pair precision remained above 90%, but that does not permit promotion. Recoverability and Recall@20 rose 171/600 → 291/600, P@10 rose 98/300 → 125/300, and mixed groups stayed 25. The seven false accepted promotions account for all 35 additional pairs. The frozen candidate is rejected; no threshold or alternative was tested on the opened holdout.

The initial `phase28a` pilot was development-only and produced no promotions because of an overconservative global threshold. A training-only guarded calibration was then evaluated on a separate fresh `phase28b` cohort. This change preceded the authoritative development prediction freeze and holdout generation.
