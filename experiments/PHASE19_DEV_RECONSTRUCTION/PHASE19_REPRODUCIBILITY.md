# Phase 19 reproducibility

Run from the repository root with Python 3.12. No GPU, Docker, network access or new packages were required. Generate in a fresh directory: `generate.py` refuses to overwrite existing data; `run_development.py` refuses to replace its development freeze. Inputs, methods, cap, pair-exposure rule, seeds and acceptance gates were written to `configs/study.json` and `METRIC_AND_ACCEPTANCE_CONTRACT.md` before evaluation. Code/config/evaluator hashes and the `locked_truth_read=false` state are in `experiments/development_freeze.json`.

Commands executed:

```powershell
.\.venv\Scripts\python.exe experiments/PHASE19_DEV_RECONSTRUCTION/generate.py
.\.venv\Scripts\python.exe experiments/PHASE19_DEV_RECONSTRUCTION/run_development.py
.\.venv\Scripts\python.exe experiments/PHASE19_DEV_RECONSTRUCTION/analyze_development.py
.\.venv\Scripts\python.exe experiments/PHASE19_DEV_RECONSTRUCTION/stress_hard_negatives.py
.\.venv\Scripts\python.exe experiments/PHASE19_DEV_RECONSTRUCTION/stress_pair_audit.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE19_DEV_RECONSTRUCTION/tests -p 'test_*.py' -v
```

The reused Phase 15 synthetic evaluator computes all train/development C/P metrics. `analyze_development.py` independently reconciles every accepted merge's evaluator-only TP/FP increment. Stress construction and evaluation are isolated under `stress/`; its use of truth is disclosed and is never a model feature. No `locked_test_*.jsonl` prediction or evaluation file exists. Runtime is recorded in prediction/evaluation artifacts; peak RSS was not measured. Serialized predictions include runtime, so their byte hashes vary across reruns, while their group partitions are deterministic.
