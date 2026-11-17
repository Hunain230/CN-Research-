# Recall-only experiment — NO-GO

The historical Phase 16 v4 selected reference was reproduced at **407/600 = 67.83% Incident Recall@20**. It remains a separate, opened historical result. The best development candidate, `source_depth`, passed the development gates at **220/300 = 73.33%** versus the matched baseline **196/300 = 65.33%**. One fresh synthetic holdout then measured **444/600 = 74.00%** versus its matched baseline **410/600 = 68.33%**, a gain of 34 incidents or 5.67 percentage points.

The holdout also measured a **P@10 regression of 193/300 to 190/300** (64.33% to 63.33%). This fails the required non-inferiority gate. The candidate did not reach 80%; its unchanged groups make 463/600 = 77.17% the holdout recall ceiling. No second holdout or post-holdout tuning was performed. The candidate is not promoted.

| Metric | Matched fresh baseline | Candidate | Change | Gate |
|---|---:|---:|---:|---|
| Incident Recall@20 | 410/600 (68.33%) | 444/600 (74.00%) | +34, +5.67 pp | **Fail:** below 80% |
| Group recoverability | 463/600 (77.17%) | 463/600 (77.17%) | 0 | Pass |
| P@10 | 193/300 (64.33%) | 190/300 (63.33%) | −3, −1.00 pp | **Fail** |
| Grouped-pair precision | 32,015/32,321 (99.05%) | same | 0 | Pass |
| False grouped pairs | 306 | 306 | 0 | Pass |
| Mixed groups | 252 | 252 | 0 | Pass |

Development comparison: `source_depth` 220/300 recall, 233/300 recoverability, 93/150 P@10, 98.5784% pair precision, 236 false pairs, 127 mixed groups. The matched frozen development baseline is 196/300 recall and identical on those other metrics. `diverse_depth` reached 218/300 but failed P@10 (91/150 versus 93/150). `temporal_depth` reached 217/300 and passed the development gates; `source_depth` was selected by the predeclared highest-recall rule. `DEVELOPMENT_RESULTS.csv` and `CANDIDATE_COMPARISON.csv` contain all three measured candidates.

Queue audit: recall rose in aggregate without a queue-level recall decline on the fresh holdout, but P@10 declined in seven queues (`q003`, `q004`, `q009`, `q019`, `q020`, `q021`, `q027`) and rose in four, yielding the net loss of three. All 30 queues had identical group partitions and identical false-pair and mixed-group counts. The complete paired counts are in `HOLDOUT_RESULTS.csv`.

The holdout was generated only after development selection because the Phase 16 historical holdout was already opened. The 30 new queues used the frozen Phase 16 generator family with seed 116437, namespace `recallh`, and template variant 6. Prediction files were sealed before private truth evaluation, and the unchanged Phase 15 evaluator was invoked exactly once for each matched pipeline. The study remains synthetic and shares generator structure with development; it is not operational evidence.

Reproducibility: `BASELINE_METRICS.json` records historical hashes and exact metrics; `artifacts/selection_freeze.json` records the selected code/config/prediction hashes; `artifacts/pre_evaluation_seal.json` records the final prediction hashes. `run_development.py`, `prepare_freeze.py`, `run_holdout.py`, and `audit.py` record the execution. The evaluator and original predictor were unchanged. The temporal audit found no future-evidence or private-label feature use. `FALSE_MERGE_AUDIT.md` details exact group and queue safety.

The genuinely measured safe development result is 220/300 Recall@20 with unchanged P@10 and group safety. The fresh holdout result is a measured recall improvement but **not a safe selected result** because P@10 regressed. To reach 80%, this cohort needs greater group recoverability; current receiver-visible lineage does not establish safe new unions under the zero-additional-false-pair gate. No further candidate or phase was started.
