# Reproducibility audit

Verified SHA-256 against pre-evaluation seal:

- `artifacts/baseline_predictions.jsonl`: `27a5bf488f58bc9037f27830361c08868d944aa89c8a0b497f6332dacdad32d3`
- `artifacts/candidate_predictions.jsonl`: `b46b3ffd46355ebb1bdfcf54040fafad7047bd706f29371cdb4afb104901851c`
- `experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/model.py`: `d42a6a1a8d83acee0ba541a80b1934346260c49eed23faa9c79efb9861bb2d0b`
- `experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py`: `9d52beb006854ece8cb084072cfc21384d98d175ce29ce1f36d29a6beaf76532`
- `experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py`: `dbc3fbff327400fad9f999e74bb69e1ca1968b34be6d2990effc3438e7dc1dc3`

Figures are regenerated from immutable summary and queue CSV by `python paper/build_paper.py`; the script checks predictions and metric sums. Do not rerun the holdout generator or evaluator as part of paper reproduction.
