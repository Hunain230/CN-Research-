# Phase 33 final report — GO within the controlled synthetic cohort

The frozen Phase 32 endpoint-fallback +1 candidate was evaluated **once** on a new, untouched 15-queue Phase 31 v2-family holdout. It reached **260/300 = 86.67% official Incident Recall@20**, exceeding the predeclared 85% target. All predeclared metric and safety gates passed. This is a controlled synthetic generalization result, not production validation or a replacement for historical benchmarks.

Phase 32 had stopped at **169/200 = 84.5% development Recall@20**, one incident below its own development gate. The user's subsequent Phase 33 instruction explicitly called for an unchanged-candidate holdout test. This result does not retroactively make Phase 32 a GO or imply that its opened development score was an independent test.

| Matched Phase 33 holdout | Frozen Phase 31 baseline | Frozen Phase 32 candidate | Change | Gate |
|---|---:|---:|---:|---|
| Incident Recall@20 | 250/300 (83.33%) | **260/300 (86.67%)** | +10, +3.33 pp | Pass: ≥85%, improved |
| Group recoverability | 263/300 (87.67%) | **281/300 (93.67%)** | +18, +6.00 pp | Pass: ≥85%, improved |
| P@10 | 107/150 (71.33%) | **113/150 (75.33%)** | +6, +4.00 pp | Pass: ≥73%, non-inferior |
| Grouped-pair precision | 19,459/19,459 (100%) | 20,117/20,117 (100%) | unchanged | Pass: ≥90% |
| False grouped pairs | 0 | 0 | 0 | Pass: no increase |
| Mixed groups | 0 | 0 | 0 | Pass: no increase |

All 15 queues passed the false-pair and mixed-group safety gates. Aggregate P@10 improved despite decreases in two queues; Recall@20 also fell by one incident in two queues. The paired queue details are in `HOLDOUT_RESULTS.csv`. Post-evaluation truth audit found **28/28 new fallback unions genuine** and **711/711 total accepted unions genuine** under the simulator's truth. It also counted 150 false token rejections and 35 genuine token abstentions. No temporal or private-feature violation was found.

The holdout was generated once with the previously specified seed 31103 and template variant 2, using byte-identical copies of the Phase 31 v2 generator and config. The frozen Phase 31 baseline and frozen Phase 32 candidate both predicted the same 5,018 eligible alerts. Their prediction and decision artifacts were sealed before the unchanged Phase 15 evaluator accessed private ground truth; each pipeline was evaluated once. `PHASE33_FREEZE.json`, `artifacts/pre_evaluation_seal.json`, `HOLDOUT_SUMMARY.json`, and `POST_EVALUATION_AUDIT.json` record the hashes, gates and audit.

Historical results remain separate: Phase 16 selected **407/600 = 67.83%**; the later opened `source_depth` holdout found **444/600 = 74.00%** but failed P@10; Phase 31 v2 best development was **158/200 = 79.00%**; Phase 32 best development was **169/200 = 84.50%**. None is directly paired with the new Phase 33 holdout. The paired comparison in this report is only the **250/300 versus 260/300** result on the same new population.

The result supports the narrower research conclusion that existing receiver-visible endpoint process context, combined with independent identity-provider and network claims, improved safe reconstruction within this controlled generator family. The simulator itself defines the three trust roots and challenge distribution. A real SOC may have coordinated corruption or missing provenance that this holdout does not represent. **GO is limited to the Phase 33 synthetic research gate; production promotion remains unassessed.**
