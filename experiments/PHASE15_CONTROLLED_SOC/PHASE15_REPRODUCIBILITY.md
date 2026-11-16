# Reproducibility

Run from repository root with Python 3.12; no additional packages, GPU, Docker, network, Kafka, or Spark are required. The run used seeds **1501 train, 1502 development, 1503 locked test**, with a separate queue-cluster bootstrap seed **1515**. The config and split allocations are in `configs/study.json`. The simulator refuses to overwrite an existing dataset, and the pipeline/evaluator refuse to overwrite prediction/evaluation files. `run_study.py` resumes from existing per-config artifacts. Code/config hashes at selection are in `experiments/selection_freeze.json`; all generated data-file hashes are in `dataset_hashes.json`. The complete command output is `study_stdout.txt`.

Commands executed:

```powershell
.\.venv\Scripts\python.exe experiments/PHASE15_CONTROLLED_SOC/simulator/generate.py
.\.venv\Scripts\python.exe experiments/PHASE15_CONTROLLED_SOC/run_study.py
.\.venv\Scripts\python.exe experiments/PHASE15_CONTROLLED_SOC/analysis.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE15_CONTROLLED_SOC/tests -p 'test_*.py' -v
```

`run_study.py` first executes exact/simple, exact/progression, multi/simple, multi/progression, multi+V/simple, and multi+V/progression on development data. It writes all metrics and a Pareto frontier, freezes the selected configuration, and then evaluates only the frozen selection plus exact/simple on locked test. Per-queue predictions and evaluations, including runtime, are in `experiments/`. Predictions' group membership and rank ordering are deterministic; serialized files include measured runtime, so their byte hashes vary across reruns. The frozen prediction hashes bind the particular evaluated artifacts. The simulator is CPU-only and processed one queue at a time; a hardware memory counter was unavailable in this Windows session, so no peak RSS is claimed.

The train split was generated and validated for disjointness but no learned model was fitted: the tested methods are fixed rules. Existing GUIDE E1/v7/child40 rankers require incompatible GUIDE feature schemas and cannot be transferred without new adaptation and validation. No production field approval follows from this synthetic cohort.
