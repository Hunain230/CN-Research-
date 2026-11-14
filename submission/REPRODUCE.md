# Reproduce the Phase 3 hybrid evaluation

Run from the repository root on Windows PowerShell. Use the existing Python environment and local raw files. The recorded runs are immutable: use **new unique run IDs** for replication, and do not overwrite their output directories. The raw GUIDE files, prediction rows, model-call audit, and evaluator stores are ignored private artifacts; do not submit them.

## One-command full suite

The [PowerShell runner](../run_submission_suite.ps1) checks the synthetic software cases, verifies local Ollama, reruns the 499-organization offline pipeline under a fresh run ID, and then runs the 20-organization local Qwen v2 prediction and separate evaluation. Keep the PowerShell window open until it prints both public metrics paths. The model portion can take hours on CPU.

```powershell
.\run_submission_suite.ps1 -RunTag self_20261113_v1
```

The recorded paper run used `-RunTag paper_20261113_v1`; its full offline and Qwen v2 metrics are linked below. If you want to reuse the already recorded full offline run and run only checks plus a new local Qwen study, use `-SkipOffline`. Use a new `-RunTag` if any output path already exists. `-ChecksOnly` validates the software and prints the Qwen sample plan without inference. The v2 result is exploratory; it is not a full-dataset model score.

## Inputs and environment

- Python: the project `.venv` (the recorded environment uses Python 3.12).
- Dependencies: `requirements.txt`; aggregate figures additionally need the installed `matplotlib` and `numpy` packages.
- Raw local files: `data/raw/GUIDE_Test.csv` and `data/raw/GUIDE_Test_Queue_Rankings.csv`. Their recorded SHA-256 values are in the [paper-run full manifest](../outputs/submission_full_guide_paper_20261113_v1/run_manifest.json).
- Local model: Ollama serving `qwen2.5:3b` at `http://127.0.0.1:11434`. The [Qwen v2 freeze](../outputs/submission_qwen_v2_paper_20261113_v1/prediction_freeze.json) records the exact installed model digest and call totals. No hosted provider call is part of this replication.
- Model-visible content is restricted to five local-assumption descriptors. Review [the field policy](../configs/empirical_field_policy.yaml) before changing that boundary.

## Verify the recorded artifacts

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_guide self-test
.\.venv\Scripts\python.exe -m src.submission_local_qwen_v2 self-test
.\.venv\Scripts\python.exe -m submission.measure_local_operations
.\.venv\Scripts\python.exe -m submission.generate_submission_figures
.\.venv\Scripts\python.exe -m submission.generate_qwen_v2_figure
.\.venv\Scripts\python.exe -m submission.verify_package
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_full_guide_paper_20261113_v1 submission_qwen_v2_paper_20261113_v1
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_rank_fusion_20261114_v1 submission_trained_ranker_20261114_v1
```

The first two commands check local invariants. Figure generation checks aggregate metric hashes against run manifests and writes only PNGs and hash records. Package verification checks local document links, frozen runs, figures, and dashboard hashes. The [full metrics](../outputs/submission_full_guide_paper_20261113_v1/metrics.json) and [Qwen v2 metrics](../outputs/submission_qwen_v2_paper_20261113_v1/metrics.json) are the recorded paper-run results.

The operations command reads the ignored local call audit, verifies its SHA-256 against the prediction freeze, and writes only [aggregate local batch diagnostics](../outputs/submission_qwen_v2_paper_20261113_v1/operational_diagnostics.json). It makes no model call and does not change frozen predictions or accuracy metrics. Per-call p95 is not an alert-to-decision p95.

To regenerate the [five-page report PDF](PHASE3_IMPLEMENTATION_REPORT.pdf) from [the editable report](FINAL_REPORT.md), install its small [PDF-only dependency list](report_pdf_requirements.txt) and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r submission/report_pdf_requirements.txt
.\.venv\Scripts\python.exe -m submission.build_report_pdf
```

The [PDF manifest](PHASE3_REPORT_PDF_MANIFEST.json) records SHA-256 hashes of the Markdown source, embedded aggregate figures, build script, and resulting PDF. No raw or restricted row-level data enters the PDF.

## Replicate the full offline pass

The prediction stage scans all 4,147,992 GUIDE_Test evidence rows and may need substantial time, memory, and disk space. It writes a private prediction file under ignored `data/derived/` and a public prediction freeze. Evaluation opens membership/rank labels only after that freeze exists.

```powershell
.\.venv\Scripts\python.exe -m src.submission_full_guide predict --run-id submission_full_guide_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_full_guide evaluate --run-id submission_full_guide_REPLICATION_001
```

Expected public files: `outputs/<run-id>/prediction_freeze.json`, `metrics.json`, and `run_manifest.json`. The exact aggregate scores should be checked with the recorded input hashes and code version. The full run is deterministic apart from any change in the environment or source files.

## Replicate the bounded local Qwen v2 pass

Start Ollama locally and confirm that `qwen2.5:3b` is installed. Model calls are synchronous and can take hours on CPU. The script refuses to reuse an existing run path. It chooses 20 deterministic previously accessed small queues with sufficient exact Category-plus-technique candidates, then 12 hash-ordered candidate pairs per queue without consulting labels. C and B2 decide the same pairs; P/V process C groups. Predictions and call-level token/time records remain under ignored `data/derived/`.

```powershell
.\.venv\Scripts\python.exe -m src.submission_local_qwen_v2 self-test
.\.venv\Scripts\python.exe -m src.submission_local_qwen_v2 plan
.\.venv\Scripts\python.exe -m src.submission_local_qwen_v2 predict --run-id submission_qwen_v2_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_local_qwen_v2 evaluate --run-id submission_qwen_v2_REPLICATION_001
.\.venv\Scripts\python.exe -m submission.verify_run_manifests submission_qwen_v2_REPLICATION_001
```

The v2 evaluator computes incident completeness against all unambiguous alerts in each selected organization and retains all 400 expert labels in the end-to-end denominator. The model digest, source hashes, local-only flag, call counts, and private prediction hash are written to the public freeze/manifest. Different local model versions or runtime behavior can change predictions. This 20-queue batch is a bounded prototype; it is not a full-dataset model evaluation. The recorded sample contained 22 positive pairs out of 240 exact-match candidates. The earlier [two-queue v1 run](../outputs/submission_qwen_20261112_v1/metrics_full_membership_correction.json) remains historical and used an additive completeness correction.

## Replicate the matched ranking extension

The [baseline study](PERFORMANCE_BASELINE_STUDY.md) reuses frozen full-GUIDE groups. It performs no new model inference or candidate generation. It records an unsuccessful fixed RRF control on all 499 organizations and an organization-split trained logistic ranker on 334 training/135 evaluation organizations. Use new IDs; predictions are frozen before the evaluation command reads evaluation labels.

```powershell
.\.venv\Scripts\python.exe -m src.submission_rank_fusion self-test
.\.venv\Scripts\python.exe -m src.submission_rank_fusion predict --run-id submission_rank_fusion_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_rank_fusion evaluate --run-id submission_rank_fusion_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_trained_ranker self-test
.\.venv\Scripts\python.exe -m src.submission_trained_ranker predict --run-id submission_trained_ranker_REPLICATION_001
.\.venv\Scripts\python.exe -m src.submission_trained_ranker evaluate --run-id submission_trained_ranker_REPLICATION_001
```

The recorded [RRF](../outputs/submission_rank_fusion_20261114_v1/metrics.json) and [trained-ranker](../outputs/submission_trained_ranker_20261114_v1/metrics.json) artifacts use different evaluation cohorts, so compare each only with its own matched baselines. Both remain exploratory because GUIDE_Test labels were previously accessed.

The additive [capacity diagnostic](../outputs/submission_retrieval_bounds_20261114_v1.json) reads the frozen parent predictions and evaluator truth, then outputs aggregate upper bounds only. Its one-time command is `.\.venv\Scripts\python.exe -m submission.diagnose_retrieval_bounds`. It refuses to overwrite the recorded output; reproduce in a separate checkout or with an explicitly versioned new output path.

## Dashboard

```powershell
.\.venv\Scripts\python.exe -m src.build_simulation_dashboard
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Open `http://127.0.0.1:8765/` for the aggregate viewer and `http://127.0.0.1:8765/simulation.html` for fictional playback. The simulation rebuild verifies the frozen synthetic trace and does not read GUIDE rows or model outputs.

## Interpretation

This is retrospective exploratory analysis. The same GUIDE data and labels have been inspected before; rerunning does not create a fresh holdout. The full offline and bounded Qwen methods use different cohorts and candidate sets. Report their denominators separately and do not pool their metric values.
