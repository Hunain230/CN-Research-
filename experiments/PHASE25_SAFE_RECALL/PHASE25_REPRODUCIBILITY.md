# Phase 25 reproducibility and freeze record

The Phase 25 development dataset has 12 train queues (template variants 30–33) and 20 development queues (variants 40–41), each with 25 attack incidents and 75 interleaved benign observations. Train and development use seeds 250101 and 250211 in the `phase25a_` namespace. The independently generated synthetic holdout has 30 queues, variants 50–51, seed 250311 and `phase25h_` namespace. No complete scenario or template variant crosses splits. It is an internal simulator holdout, not real SOC validation. `datasets/manifest.json`, `datasets/locked_manifest.json` and `dataset_hashes.json` record the populations and file hashes.

The cutoff is minute 100. `predict.visible()` drops late alerts and masks each late field. `visible_receipts()` applies an independent receipt and receipt-field ledger. Development has 6,821 visible of 6,892 raw alerts, 397 late fields on visible alerts, and 4,640 visible receipts; the locked cohort has 10,039 of 10,112 alerts, 615 late fields and 6,766 visible receipts. Private truth, physical lineage and fault records are separate files. The selected inference rule does not access them.

`freeze_manifest.json` hashes the development model code, manifest, train-fitted rankers, all development predictions and decision logs **before** development truth audit. `selection_freeze.json` records the passing gates, selected rule/ranker and code hashes before the locked partition existed. `locked_prediction_freeze.json` hashes only the baseline and selected holdout predictions and decisions **before** locked truth audit. The selected method and weights were never changed after that freeze. All accepted unions are replayed from singleton alerts; final false-pair counts must equal the sum of per-union increments.

To reproduce on a fresh checkout with no Phase 25 generated files, run from the repository root:

```powershell
python experiments/PHASE25_SAFE_RECALL/forensics.py
python experiments/PHASE25_SAFE_RECALL/generate.py
python experiments/PHASE25_SAFE_RECALL/run_study.py
python experiments/PHASE25_SAFE_RECALL/select.py
python experiments/PHASE25_SAFE_RECALL/generate_locked.py
python experiments/PHASE25_SAFE_RECALL/evaluate_locked.py
python experiments/PHASE25_SAFE_RECALL/complete_locked_audit.py
python experiments/PHASE25_SAFE_RECALL/analyze.py
python -m unittest discover -s experiments/PHASE25_SAFE_RECALL/tests -q
```

The frozen `evaluate_locked.py` writes and hashes holdout predictions, then encounters a `KeyError` in its final summary because the historical queue evaluator does not return `ranker`. It has already opened the same locked truth at that point. `complete_locked_audit.py` verifies the existing prediction/decision hashes and finishes the **same** baseline-and-selected audit without repredicting, changing the model, or evaluating another candidate. This implementation error and recovery are preserved for auditability. On the existing workspace, generation and freeze commands refuse overwrite; run only the read-only analysis and tests.

The earlier Phase 16 v4 opened holdout, Phase 24 development data, and Phase 19/22 locked cohorts were never Phase 25 fitting inputs. Phase 24 Q014 is an explicitly opened design diagnostic only. The Phase 25 candidate comparison uses only the fresh development cohort; the one holdout run evaluates only the frozen baseline and selected method. Queue-cluster bootstrap intervals use 2,000 whole-queue resamples with seed 250425 and are descriptive. Python standard-library code runs on CPU without added dependencies.
