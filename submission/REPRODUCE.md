# Reproduce the Phase 3 hybrid evaluation

Run from the repository root on Windows PowerShell. Use the existing Python environment and local raw files. The recorded runs are immutable: use **new unique run IDs** for replication, and do not overwrite their output directories. The raw GUIDE files, prediction rows, model-call audit, and evaluator stores are ignored private artifacts; do not submit them.

## Inputs and environment

- Python: the project `.venv` (the recorded environment uses Python 3.12).
- Dependencies: `requirements.txt`; aggregate figures additionally need the installed `matplotlib` and `numpy` packages.
- Raw local files: `data/raw/GUIDE_Test.csv` and `data/raw/GUIDE_Test_Queue_Rankings.csv`. Their recorded SHA-256 values are in the [full-run manifest](../outputs/submission_full_guide_20261112_v1/run_manifest.json).
- Local model: Ollama serving `qwen2.5:3b` at `http://127.0.0.1:11434`. The [Qwen freeze](../outputs/submission_qwen_20261112_v1/prediction_freeze.json) records the exact installed model digest and call totals. No hosted provider call is part of this replication.
- Model-visible content is restricted to five local-assumption descriptors. Review [the field policy](../configs/empirical_field_policy.yaml) before changing that boundary.

## Verify the recorded artifacts

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_guide self-test
.\.venv\Scripts\python.exe -m src.submission_local_qwen self-test
.\.venv\Scripts\python.exe -m submission.generate_submission_figures
.\.venv\Scripts\python.exe -m submission.verify_package
```

The first two commands check local invariants. Figure generation checks the full metric hash against its manifest and writes only an aggregate PNG and hash record. Package verification checks local document links and the frozen run, correction, figure, and dashboard hashes. The [full metrics](../outputs/submission_full_guide_20261112_v1/metrics.json) and [Qwen metrics](../outputs/submission_qwen_20261112_v1/metrics.json) are the recorded results.

## Replicate the full offline pass

The prediction stage scans all 4,147,992 GUIDE_Test evidence rows and may need substantial time, memory, and disk space. It writes a private prediction file under ignored `data/derived/` and a public prediction freeze. Evaluation opens membership/rank labels only after that freeze exists.

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_guide predict --run-id submission_full_guide_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_full_guide evaluate --run-id submission_full_guide_REPLICATION_001
```

Expected public files: `outputs/<run-id>/prediction_freeze.json`, `metrics.json`, and `run_manifest.json`. The exact aggregate scores should be checked with the recorded input hashes and code version. The full run is deterministic apart from any change in the environment or source files.

## Replicate the bounded local Qwen pass

Start Ollama locally and confirm that `qwen2.5:3b` is installed. Model calls are synchronous and can take minutes. The script refuses to reuse an existing run path. It chooses two deterministic previously accessed small queues, then 10 high-score and 5 low-score frozen candidate pairs per queue without consulting labels. Predictions and call-level token/time records remain under ignored `data/derived/`.

```powershell
.\.venv\Scripts\python.exe -m src.submission_local_qwen predict --run-id submission_qwen_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_local_qwen evaluate --run-id submission_qwen_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_qwen_correction --run-id submission_qwen_REPLICATION_001
```

The correction command computes incident completeness against all unambiguous alerts in each selected organization. The initial `metrics.json` had used selected-alert membership only; use `metrics_full_membership_correction.json` for recovery/ranking fields. The model digest, source hashes, local-only flag, seeds, call counts, and private prediction hash are written to the public freeze/manifest. Different local model versions or runtime behavior can change predictions, even with the same seed. This two-queue batch is a bounded prototype; it is not a full-dataset model evaluation. The recorded 30 selected pairs contain no positives, so pair recall is unavailable.

## Dashboard

```powershell
.\.venv\Scripts\python.exe -m src.build_simulation_dashboard
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Open `http://127.0.0.1:8765/` for the aggregate viewer and `http://127.0.0.1:8765/simulation.html` for fictional playback. The simulation rebuild verifies the frozen synthetic trace and does not read GUIDE rows or model outputs.

## Interpretation

This is retrospective exploratory analysis. The same GUIDE data and labels have been inspected before; rerunning does not create a fresh holdout. The full offline and bounded Qwen methods use different cohorts and candidate sets. Report their denominators separately and do not pool their metric values.
