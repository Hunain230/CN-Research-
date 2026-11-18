# Reproducibility and artifact integrity

## Scope

The manuscript reads historical artifacts; it does not rerun or modify frozen experiments. Phase 33 files are single-use/sealed. The official evaluator is `experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py`. Its code requires a qualifying group to cover at least 80% of an incident and be at least 80% pure. The same evaluator scored both Phase 33 arms.

The important machine-readable outputs are:

- `experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json`
- `experiments/PHASE33_FROZEN_GENERALIZATION/POST_EVALUATION_AUDIT.json`
- `experiments/PHASE33_FROZEN_GENERALIZATION/artifacts/{baseline,candidate}_predictions.jsonl`
- `experiments/PHASE39_REAL_SOC_VALIDATION/LOCAL_SOURCE_AUDIT.json`

## Verified SHA-256 values

All values below were recalculated from the existing files and matched `LOCAL_SOURCE_AUDIT.json` in this workspace.

| Frozen artifact | SHA-256 |
|---|---|
| Phase 16 v4 `predict.py` | `eaedbf92901413c5b6c5ef34a97755f578cee501b670cdf75364ac47a23c7f79` |
| Phase 31 `model.py` | `d42a6a1a8d83acee0ba541a80b1934346260c49eed23faa9c79efb9861bb2d0b` |
| Phase 32 `model.py` | `9d52beb006854ece8cb084072cfc21384d98d175ce29ce1f36d29a6beaf76532` |
| Phase 33 `config.json` | `85735ccf2162d02dc21470ae3d2e40bdadb2b69da32b2d98a858b486ba4d69bf` |
| Phase 33 `PHASE33_FREEZE.json` | `691691aabd5b298987b64484c1ddff2380f33a77c700d38f5b1a04e1208ac104` |
| Phase 33 baseline predictions | `27a5bf488f58bc9037f27830361c08868d944aa89c8a0b497f6332dacdad32d3` |
| Phase 33 candidate predictions | `b46b3ffd46355ebb1bdfcf54040fafad7047bd706f29371cdb4afb104901851c` |
| Phase 33 `HOLDOUT_SUMMARY.json` | `01c6a08af8598e02656d46420f4f29ae1e23ba27f343814b543057b52a24f866` |
| Original evaluator | `dbc3fbff327400fad9f999e74bb69e1ca1968b34be6d2990effc3438e7dc1dc3` |

Recheck locally with PowerShell `Get-FileHash -Algorithm SHA256 <path>`. The Phase 39 audit also records local GUIDE input hashes; raw data are not bundled into the paper.

## Cohort separation

Phase 31 v2 used 8 train and 10 development queues; its holdout was not generated in Phase 31. Phase 32 evaluated two fixed bonuses on the 10-queue development split. Phase 33 generated 15 new holdout queues with a separate seed/template variant, sealed both prediction files, and then used evaluator-only truth. Development results from Phases 34--38 use fresh cohorts and were not promoted. The absent Phase 29 and Phase 40 directories have no reconstructed results here.

## Build

See `paper/README.md` for the LaTeX/BibTeX build command. The output PDF is `paper/research_paper.pdf`. The diagrams and tables are editable in `paper/figures/` and `paper/tables/`.
