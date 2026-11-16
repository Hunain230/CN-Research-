# Phase 17 reproducibility

Run from repository root with Python 3.12. No GPU, Docker, network access or new dependencies were used. All scripts refuse to overwrite their sealed inputs or predictions where applicable; reproduce in a fresh copy of this directory. Config, seeds, split counts, thresholds and safety-first selection rule are in `configs/study.json` and `METRIC_AND_SELECTION_CONTRACT.md`.

Commands executed:

```powershell
.\.venv\Scripts\python.exe experiments/PHASE17_INDEPENDENT_PROVENANCE/generate.py
.\.venv\Scripts\python.exe experiments/PHASE17_INDEPENDENT_PROVENANCE/train.py
.\.venv\Scripts\python.exe experiments/PHASE17_INDEPENDENT_PROVENANCE/run_study.py
.\.venv\Scripts\python.exe experiments/PHASE17_INDEPENDENT_PROVENANCE/audit_phase16.py
.\.venv\Scripts\python.exe experiments/PHASE17_INDEPENDENT_PROVENANCE/analyze.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE17_INDEPENDENT_PROVENANCE/tests -p 'test_*.py' -v
```

`models/reliability.json` contains 22 training evidence-signature bins from 1,164 positive and 457 negative fragment candidates, with Beta(1,1) smoothing. On 1,561 development candidate pairs, post-freeze evaluator diagnostics gave Brier score **0.03567** and five-bin ECE **0.01467**. These candidate-level values do not imply group-level calibration. The threshold-0.80 development run accepted 953 fragment links, 11 of which failed the pure-same-incident audit, and its false grouped pairs rose by 986 over baseline. Per-queue decisions and predictions are in `experiments/`; source/code hashes are in `experiments/selection_freeze.json`, input hashes in `dataset_hashes.json`, and execution output in `study_stdout.txt` and `analysis_stdout.txt`.

The exact Phase 15 synthetic evaluator is reused unchanged. Group outcomes are deterministic; serialized prediction artifacts contain runtime, so their byte hash can vary on rerun. The frozen prediction SHA-256 values bind the artifacts actually evaluated. Peak RSS was not measured. The locked test is now open and cannot be reused for new selection.
