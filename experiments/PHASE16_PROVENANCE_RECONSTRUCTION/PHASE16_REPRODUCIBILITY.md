# Phase 16 reproducibility log

Phase 16 kept all GUIDE and Phase 15 artifacts untouched. The first `PHASE16_PROVENANCE_RECONSTRUCTION/` run was a failed simulator pilot; `v2/` fixed its flow-reference defect but retained identifiers shared with the first pilot; `v3/` explored a single-lineage plus context rule but reused identifiers with v2. Their opened test sets were not used as final independent evidence. `v4/` contains the final namespaced fresh cohort. New seeds 1641/1642/1643 and 15/15/30 queue counts are in `v4/configs/study.json`. No GPU, Docker, network access, or additional dependencies were required. Execution is CPU-only and processes one queue at a time.

Run from repository root in a **fresh copy of v4**; the generator and prediction/evaluation steps refuse to overwrite sealed artifacts:

```powershell
.\.venv\Scripts\python.exe experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/simulator.py
.\.venv\Scripts\python.exe experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/run_study.py
.\.venv\Scripts\python.exe experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/analyze.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/tests -p 'test_*.py' -v
```

`run_study.py` evaluates all six fixed C/V variants on development, applies the preregistered safety-first rule, writes `v4/experiments/selection_freeze.json`, and then evaluates only the process baseline and selected method on the new locked test. The unchanged Phase 15 evaluator defines the metrics. `v4/study_stdout.txt`, per-queue predictions, decision logs, evaluations, `dataset_hashes.json`, and `analysis_summary.json` preserve inputs and outputs. Prediction group membership is deterministic; serialized prediction files include measured runtime, so their bytes can vary across reruns. The freeze stores the exact evaluated prediction hashes. Peak process RSS was not measured and is not claimed.

The original Phase 15 failure diagnosis command was `.\.venv\Scripts\python.exe experiments/PHASE16_PROVENANCE_RECONSTRUCTION/diagnose_phase15.py`. It is retrospective and uses no new holdout. The v4 locked test is now open; do not tune against it or call subsequent reuse independent validation.
