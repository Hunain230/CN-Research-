# Synthetic end-to-end MVP fixture

This fixture is fictional and exists only to exercise software integration. It contains two synthetic organizations with six alerts each. No GUIDE rows or real identifiers are used.

Each organization request has the same intended edge cases:

- a clear same-incident pair (`a1` and `a2`);
- a clear non-link (`a1` and `a3`);
- contradictory evidence (`a1` and `a4`), which should be UNSURE and reviewed;
- missing evidence (`a1` and `a5`), which should be UNSURE and reviewed;
- a benign shared entity (`a1` and `a6`), which causes a deliberate false LINK and demonstrates a false merge.

`truth.json` is evaluator-only. The prediction command reads only `scenario.json`, the per-organization request files, and `configs/agents.yaml`. It writes and hashes `predictions.json` before the evaluation stage opens `truth.json`.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.mvp_demo self-test
.\.venv\Scripts\python.exe -m src.mvp_demo run --run-id mvp-demo-20261112-v1
```

All resulting scores are checks of this tiny, hand-authored fixture. They are not GUIDE results, empirical model performance, or evidence of SOC effectiveness.
