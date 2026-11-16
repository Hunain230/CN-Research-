# Phase 18 reproducibility

This is evaluator-only retrospective analysis. It reads frozen Phase 17 train/development records and the already-opened locked **baseline**; it never predicts or evaluates the rejected candidate on locked test. It also reads the previously opened Phase 16 ranking diagnostic. Phase 15, 16, 17, GUIDE and all prior artifacts remain untouched. Input SHA-256 hashes are in `PHASE18_AUDIT_SUMMARY.json`.

From repository root with Python 3.12:

```powershell
.\.venv\Scripts\python.exe experiments/PHASE18_FAILURE_MECHANISM_AUDIT/audit.py *> experiments/PHASE18_FAILURE_MECHANISM_AUDIT/audit_stdout.json
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE18_FAILURE_MECHANISM_AUDIT/tests -p 'test_*.py' -v
```

`audit.py` replays the original point-in-time field gate and baseline partition from frozen Phase 17 code, verifies each development and locked partition and alert scope against its prediction file, and computes train/dev/test incident-level completeness. Its all-raw-field analysis is explicitly a retrospective upper diagnostic and never becomes a historical prediction. It then replays all 953 development accepted unions in order and asserts exact TP/FP differences against both frozen evaluations. All outputs are written only under this Phase 18 directory. No random seed, model fitting or threshold selection is used in this audit.
