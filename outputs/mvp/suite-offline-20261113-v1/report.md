# Synthetic end-to-end MVP run

> **Fictional software demonstration only. These metrics are not GUIDE results or empirical model performance.**

## What ran

The deterministic offline C/P/V stub processed 12 fictional alerts across 2 organizations, compared 10 supplied candidate pairs, formed 8 components, and made zero live model calls.

Components touching an UNSURE or failed candidate pair were conservatively marked REVIEW. The synthetic prioritization scores are simple stub scores, not learned, calibrated, or operational risk estimates.

Each fictional organization yields only four predicted components, so the top-20 recovery cutoff includes every available component. This fixture does not test competition among 20 or more incidents.

## Fixture metrics

- Candidate-pair precision: 0.500 (2 TP, 2 FP).
- Candidate-pair recall: 1.000 (2 TP, 0 FN).
- Pair F1: 0.667.
- Candidate decision coverage: 0.600; abstentions: 4; failures: 0.
- Full pair universe: 30 pairs; candidate-generation coverage: 0.333.
- False merges: 2; false splits: 0.
- End-to-end fixture top-20 recovery: 6/10 = 0.600.
- Components sent to review: 6/8 = 0.750.

These values are expected to reflect the hand-authored edge cases, including deliberate false links and uncertainty. The tiny fixture is designed to validate integration and evaluator wiring, not to estimate system effectiveness.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m src.mvp_demo self-test
.\.venv\Scripts\python.exe -m src.mvp_demo run --run-id <new-unique-id>
```
