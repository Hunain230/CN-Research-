# Synthetic MVP Run Record

**Run:** `mvp-demo-20261112-v2`  
**Classification:** synthetic end-to-end software demonstration; not empirical.  
**Live model or external network calls:** zero.

## What the run demonstrates

The runner processes 12 fictional alerts in two synthetic organizations. It passes each organization separately through the existing deterministic offline C/P/V stub, builds predicted components from LINK decisions, sorts components by the stub's relative evidence-count score, and routes components touching UNSURE/failed pairs to REVIEW. It freezes the prediction JSON before opening the separate synthetic truth file, then calculates evaluator metrics and exports a UI-safe event trace.

The fixture deliberately includes a clear link, a clear non-link, contradictory evidence, missing evidence, and a benign shared-entity link that causes a false merge. The false merge is intentional and tests whether the evaluator and error reporting expose it.

## Results on the hand-authored fixture

| Measure | Fixture result | Meaning |
|---|---:|---|
| Candidate-pair precision | 0.500 (2 TP, 2 FP) | Includes two deliberately false shared-entity links. |
| Candidate-pair recall | 1.000 (2 TP, 0 FN) | Both fixture positive pairs were supplied and linked. |
| Candidate-set F1 | 0.667 | A deterministic fixture check, not a system estimate. |
| Candidate decision coverage | 0.600 (6/10) | Four contradictory/missing-evidence decisions abstained as UNSURE. |
| Candidate generation coverage | 0.333 (10/30) | Ten supplied candidates out of the full fictional within-organization pair universe. |
| False merges / false splits | 2 / 0 | The two false merges were seeded intentionally. |
| End-to-end top-20 recovery | 6/10 (0.600) | The fictional queues contain only four predicted components each, so the top-20 cutoff includes all components and does not simulate a 20+ item ranking competition. |
| Components sent to review | 6/8 (0.750) | Components touching unresolved pairs or missing evidence are reviewed. |

The scores are expected to match these constructed cases. They do not estimate performance on GUIDE, SOC data, or future incidents. The prioritization score is an uncalibrated deterministic stub score; token counts and latency were not measured.

## Artifacts

Run output directory: `outputs/mvp/mvp-demo-20261112-v2/`

- `predictions.json` — prediction-only artifact, validated against the Stage 5 schema.
- `prediction_freeze.json` — prediction hash and ordering record.
- `dashboard_events.json` — fictional event trace for the dashboard simulation.
- `metrics.json` and `report.md` — synthetic-only evaluation results.
- `run_manifest.json` — fixture/config/code/output hashes and run classification.

The evaluator-only answer key remains in `fixtures/mvp/truth.json`; it is not copied into the prediction or dashboard-event artifacts.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m src.mvp_demo self-test
.\.venv\Scripts\python.exe -m src.mvp_demo run --run-id <new-unique-id>
```

Task 4 checks passed: the new runner self-check (17 assertions), Phase 2 synthetic self-check (23), Phase 3 baseline self-check (38), Phase 4 agent self-check (34), and Phase 5 evaluator self-check (64). The repeated fixture pipeline produced deterministic predictions, and the actual run recorded zero live model/network calls. These checks validate software contracts only.

