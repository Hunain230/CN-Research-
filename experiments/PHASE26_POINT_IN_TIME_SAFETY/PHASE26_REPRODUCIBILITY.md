# Reproducibility and freeze

Authoritative run: `v2/`, namespace `phase26b`, train seed 260501, development seed 260611, 12 training queues, 20 development queues, cutoff minute 100. Training templates 80–83 and development templates 90–91 are scenario-disjoint. `v2/datasets/manifest.json` enumerates queues. `v2/freeze_manifest.json` records source, configuration, model and frozen prediction hashes. `dataset_hashes.json` records every authoritative JSONL input and the manifest. `analysis_summary.json` and the CSV audits are evaluator-only outputs. Pilot root files are `phase26a` diagnostics and are not used for the decision.

Run from repository root with the same Python environment:

```powershell
python experiments/PHASE26_POINT_IN_TIME_SAFETY/v2/generate.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/v2/run_study.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/analyze.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/write_reports.py
python -m unittest discover -s experiments/PHASE26_POINT_IN_TIME_SAFETY/tests -q
python -m unittest discover -s experiments/PHASE25_SAFE_RECALL/tests -q
```

Regeneration rewrites the authoritative synthetic data and frozen artifacts; verify hashes against the committed freeze before doing so. The study runner writes development predictions and decisions, then freezes their hashes, then opens private development truth to audit. No Phase 26 locked cohort exists because all candidates fail development gates. Prior locked cohorts are not read by these scripts. This is a synthetic, CPU-only experiment. The interval estimates use 2,000 queue-cluster bootstrap resamples; denominator definitions and per-queue metrics are in the CSVs.
