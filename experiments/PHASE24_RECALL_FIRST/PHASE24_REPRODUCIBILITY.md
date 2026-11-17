# Phase 24 reproducibility

The authoritative development run is `v4/` (`phase24d_`). Earlier root, `v2/`, and `v3/` runs are exploratory pilots. Their development truth was opened and their observations informed later candidates. No holdout was used for candidate selection. Each version has its own namespace, seeds, code, manifest, predictions and audit outputs. The final v4 template variants are `v10`–`v13` on train and `v20`–`v21` on development; complete incidents and queues never cross splits. No locked partition was generated.

From the repository root, on a fresh copy **without** `v4/datasets/` or `v4/freeze_manifest.json`:

```powershell
python experiments/PHASE24_RECALL_FIRST/v4/generate.py
python experiments/PHASE24_RECALL_FIRST/v4/run_study.py
python experiments/PHASE24_RECALL_FIRST/analyze.py
python experiments/PHASE24_RECALL_FIRST/trust_stress.py
python -m unittest discover -s experiments/PHASE24_RECALL_FIRST/tests -q
```

The generator and study refuse to overwrite their frozen data/predictions. In this workspace, rerun `analyze.py`, `trust_stress.py` and tests only. The `v4/freeze_manifest.json` hashes config, generator, predictor, study code, manifest, trained ranker, train predictions, development predictions and decision logs. `dataset_hashes.json` hashes every dataset JSONL file. Analysis checks frozen hashes before reading development truth. The prediction process reads only `generated_alerts`, `evidence_ledger`, and `field_ledger`; train fitting reads only train truth. The evaluator opens development truth after every development prediction is materialized and hashed.

The raw point-in-time cutoff is minute 100; alert and field availability are checked separately. The 100-alert component cap, 80% completeness and 80% purity definitions match the earlier synthetic evaluator. Oracle top-20 and top-10 priority ranks are private evaluator inputs. P@10 credits predicted top-ten groups that qualify for an oracle top-ten incident, once per incident; nDCG@20 uses `(26 - oracle rank) / log2(position+1)` with ideal ranks 1–20. Sorting breaks tied model scores by the first alert ID. All queues have 20 oracle target labels, so micro and macro rates coincide for Recall@20; both are recorded.

Queue-cluster bootstrap uses 2,000 resamples of complete queues with seed 240424. Intervals are descriptive. The generator and ranker use Python's standard library on CPU, with no added package dependency. The tests verify the split, sealed boundary, hashes, point-in-time masking, decision scope and union reconciliation.

Artifacts: [comparison](PHASE24_EXPERIMENT_COMPARISON.csv), [queue metrics](PHASE24_QUEUE_METRICS.csv), [union audit](PHASE24_UNION_PAIR_AUDIT.csv), [failure cascade](PHASE24_FAILURE_CASCADE.csv), [feature availability](PHASE24_FEATURE_AVAILABILITY_AUDIT.csv), [ranking audit](PHASE24_RANKING_AUDIT.csv), [family/failure strata](PHASE24_FAMILY_FAILURE_METRICS.csv), [dataset hashes](dataset_hashes.json), and [freeze manifest](v4/freeze_manifest.json).
