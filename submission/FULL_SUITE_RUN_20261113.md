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

The user-operated [suite runner](../run_submission_suite.ps1) completed the new [499-organization offline run](../outputs/submission_full_guide_paper_20261113_v1/run_manifest.json) and [20-organization local Qwen v2 run](../outputs/submission_qwen_v2_paper_20261113_v1/run_manifest.json). Both run manifests were rechecked against every recorded source/output SHA-256. The new full offline `metrics.json` SHA-256 exactly matches the prior full run (`e6ac81358f6d8eef06c23b574055aa194a1b62fa09085fbca5ccbee0e97d3a94`); no historical run was overwritten.

Qwen v2 froze predictions before evaluator truth access. It made 188 localhost calls with zero recorded call failures and zero hosted calls. The 240 label-blind selected exact-match pairs contained 22 positives. [Aggregate metrics](../outputs/submission_qwen_v2_paper_20261113_v1/metrics.json) show C correlation TP 1, FP 16, FN 21, pair recall 0.0455 and F1 0.0513; the paired B2 single-model baseline had TP 2, FP 20, FN 20, pair recall and F1 both 0.0909. C/P/V end-to-end organization-macro Recall@20 was 0.1443 over all 400 expert labels in the selected organizations, with an exploratory 95% organization-bootstrap interval [0.0800, 0.2118]. The model saw only 391 selected alerts out of 4,668 unambiguous alerts in these organizations, so the result is a bounded prototype diagnostic rather than full-queue model performance. It does not establish a gain over B2 or the full offline baselines.

The current suite runner also provides `-ChecksOnly`; it passed the included checks and reported 20 organizations, 240 selected pairs, and 391 selected alert occurrences without starting inference. The runner checks local Ollama availability and refuses to overwrite run paths.
