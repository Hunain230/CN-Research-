# Phase 27 reproducibility

The authoritative run is `v3/` (`phase27c`), train seed 272411 and development seed 272923, with 12 train and 20 development queues. Earlier root/v2 cohorts were diagnostic; v2's opened holdout was never reused after detecting duplicate-source witness counting. V3 deduplicates source pairs and requires root-disjoint witnesses before train/development selection. `v3/freeze_manifest.json` hashes development code, model and predictions before private audit. `v3/pre_evaluation_protocol.json` hashes the selected pipeline, weights, holdout builder and evaluator before holdout generation. `v3/locked_prediction_freeze.json` hashes public locked inputs and predictions before truth was opened once. The holdout is `phase27k`, seed 273571, 30 queues and unseen family labels with more delayed lineage evidence. Phase 19 and Phase 22 locked cohorts were not opened.

From a clean authoritative directory, run:

```powershell
python experiments/PHASE27_RECALL_GRAPH/v3/generate.py
python experiments/PHASE27_RECALL_GRAPH/v3/run_study.py
python experiments/PHASE27_RECALL_GRAPH/v3/freeze_holdout.py
python experiments/PHASE27_RECALL_GRAPH/v3/holdout.py
python experiments/PHASE27_RECALL_GRAPH/v3/holdout_run.py
python experiments/PHASE27_RECALL_GRAPH/analyze.py
python experiments/PHASE27_RECALL_GRAPH/write_reports.py
python -m unittest discover -s experiments/PHASE27_RECALL_GRAPH/tests -q
```

Generators refuse to overwrite existing cohorts. Do not rerun an opened holdout as a new model-selection opportunity. The frozen run evaluated only the selected pipeline and same-cohort baseline on holdout. All 51 relevant historical Phase 16, 19–23, 25 and 26 regression tests pass; Phase 27 adds seven tests.

Metric definitions: 20 oracle-priority incidents per queue. Official recoverability requires a predicted group with ≥80% eligible incident coverage and ≥80% group purity. Recall@20 also requires that group's first qualifying position ≤20. P@10 credits distinct oracle top-ten incidents in the first ten groups. Candidate-edge precision is same-incident alert edges divided by all candidate alert edges. Direct cross-group pair recall is true candidate alert edges crossing groups divided by all same-incident alert pairs across groups. Hypothesis precision is qualifying bounded multi-fragment hypotheses divided by all hypotheses; it is never counted as official group recovery. Paired confidence intervals use 2,000 queue-cluster resamples.
