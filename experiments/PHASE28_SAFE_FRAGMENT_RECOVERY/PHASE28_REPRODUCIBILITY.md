# Phase 28 reproducibility

The authoritative experiment is `v2/` (`phase28b`): 12 training queues (seed 281231), 20 fresh development queues (seed 281677), and one post-selection `phase28h` locked cohort of 30 queues (seed 282251). Training/development variant names and seeds are disjoint; holdout family names and variants are new. The holdout adds one predeclared independent false dual-lineage challenge per queue. All are synthetic draws from the reused Phase 27 simulator, not external validation. The development-only `phase28a` pilot calibrated no promotions and is excluded from final selection.

`v2/development_freeze.json` hashes code, configuration, model and development predictions before opening development truth. `v2/pre_evaluation_protocol.json` hashes the selected component rule, thresholds, holdout builder and evaluator before holdout generation. `v2/locked_prediction_freeze.json` hashes public locked inputs, predictions, decisions and hypotheses before private truth was opened once. It also pins the unchanged Phase 27 graph, evidence layer and ranker model by hash. No Phase 27 holdout truth was used for training or tuning; earlier Phase 19 and Phase 22 locked cohorts remain sealed.

From a clean Phase 28 directory, run:

```powershell
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/generate.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/study.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/freeze_holdout.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/holdout.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/holdout_run.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/analyze.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/write_reports.py
python -m unittest discover -s experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/tests -q
```

Generators refuse to overwrite existing cohorts. Do not reuse the opened holdout for threshold selection. The exact official metric definition is the frozen Phase 27 evaluator: 20 oracle-priority incidents per queue; a group qualifies with ≥80% eligible incident coverage and ≥80% group purity, and Recall@20 requires its first qualifying position ≤20. P@10 credits distinct oracle top-ten incidents in the first ten groups. Hypothesis precision and promotion precision are separate retrospective metrics. Pair precision counts within-group same-incident alert pairs; false pairs and mixed groups are evaluated after predictions freeze. Paired intervals use 2,000 queue-cluster resamples.
