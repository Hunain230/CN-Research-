# Offline suite and local Qwen rerun — 2026-11-13

## Scope

The complete recorded 499-organization offline GUIDE_Test run was verified by raw input hashes and immutable run manifests. A fresh fictional MVP run exercised the offline C/P/V software path. A new, predefined local `qwen2.5:3b` study uses 20 previously accessed small organizations and 12 label-blind exact Category-plus-technique candidate pairs per organization, with C and B2 on the same 240 pairs followed by P/V on C groups. The local study is exploratory and does not replace a full-dataset model run.

## Software checks

| Command | Result |
|---|---|
| `python -m src.cli self-test-phase2` | 23 assertions passed |
| `python -m src.cli baseline-self-test` | 38 assertions passed |
| `python -m src.cli agent-self-test` | 34 assertions passed |
| `python -m src.cli evaluation-self-test` | 64 assertions passed |
| `python -m src.cli phase6a-self-test` | 7 checks passed |
| `python -m src.cli phase6b-self-test` | 4 assertions passed |
| `python -m src.mvp_demo self-test` | 17 assertions passed |
| `python -m src.offline_joint_comparison_v1 self-test` | 7 assertions passed |
| `python -m src.offline_joint_comparison self-test` | 7 assertions passed |
| `python -m src.submission_full_guide self-test` | 4 assertions passed |
| `python -m src.submission_local_qwen self-test` | 5 assertions passed |
| `python -m src.submission_local_qwen_v2 self-test` | 2 assertions passed |
| `python -m src.cli check-leakage --features data/derived/preprocessing/feature_view.csv --policy configs/field_policy.yaml --audit data/derived/preprocessing/leakage_audit.json` | Passed: zero feature rows, zero prohibited columns, zero sentinels |
| `python -m src.cli check-splits --manifest data/derived/preprocessing/split_manifest.json --expected 10,10,30` | Passed: 10/10/30 provisional split |

The fresh [fictional MVP run](../outputs/mvp/suite-offline-20261113-v1/metrics.json) completed with zero model/network calls. Its metrics match the previous fictional run exactly; these are software fixture checks, not GUIDE performance. `python -m submission.verify_package` passed 155 local links and frozen artifact hashes before the new Qwen result was added. The raw GUIDE_Test and queue-ranking hashes matched the recorded input baseline, and the full offline run still reports [499 organizations](../outputs/submission_full_guide_20261112_v1/metrics.json).

## New local model result

The Qwen prediction stage is running. Its result will be added here only after prediction freeze and separate truth evaluation. No paper metric is inferred from this software-check table.
