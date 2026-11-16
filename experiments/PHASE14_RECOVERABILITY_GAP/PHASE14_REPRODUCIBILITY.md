# Phase 14 reproducibility log

Run from the repository root on Windows using `.venv/Scripts/python.exe`. Git status before work showed only untracked Phase 11, Phase 12, and Phase 13 experiment directories; no tracked modifications. Phase 14 is separately untracked. Seed: none is used by these deterministic evaluator and row-audit passes. Phase 10's original prediction configuration and seed remain in the copied `PHASE10_EXPERIMENT_CONFIG.json`. All frozen input and code SHA-256 values are recorded in `input_hashes.json`; the Phase 10 evaluator, reconstruction code, config, and prediction freeze hashes match the Phase 13 manifest. The 500 prediction files were copied, not regenerated. The E1 evaluator verifies each queue hash and every parent freeze before evaluation.

Commands executed:

```powershell
Copy-Item experiments/PHASE13_RECOVERY/evaluate.py,experiments/PHASE13_RECOVERY/reconstruct.py,experiments/PHASE13_RECOVERY/PHASE10_EXPERIMENT_CONFIG.json experiments/PHASE14_RECOVERABILITY_GAP/
Copy-Item experiments/PHASE13_RECOVERY/predictions/* experiments/PHASE14_RECOVERABILITY_GAP/predictions/
.\.venv\Scripts\python.exe experiments/PHASE14_RECOVERABILITY_GAP/evaluate.py *> experiments/PHASE14_RECOVERABILITY_GAP/phase14_e1_reproduction_stdout.txt
.\.venv\Scripts\python.exe experiments/PHASE14_RECOVERABILITY_GAP/audit.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE14_RECOVERABILITY_GAP -p 'test_audit.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE13_RECOVERY -p 'test_phase13.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE10_FRAGMENT_RECONSTRUCTION -p 'test_reconstruction.py' -v
```

The evaluator finished successfully in **131.11 seconds**, peak process RSS **577,265,664 bytes**. Its complete output is `PHASE10_EVALUATION.json`; `PHASE14_BASELINE_REPRODUCTION.json` stores the checked E1 method object. The original and reproduced E1 method objects were exactly equal. The actual first run redirected stdout to the pre-existing tracked `e1_reproduction_stdout.txt`; that file was restored byte-for-byte from HEAD (matching Git object hash `fbe8800b7c3535fa9581438ced21dbbbbea712f0`), while the complete new log was saved as `phase14_e1_reproduction_stdout.txt`. The command above shows the safe repeat location. `audit.py` reads only the frozen Phase 13 evaluator table and the reproduced Phase 14 baseline. It asserts 499 queues, 9,980 unique labels, all structural counts, and both bound arithmetic results before writing outputs. `audit_summary.json` records source hashes. Re-running `audit.py` deterministically overwrites only its own Phase 14 derived tables.

The original E1 prediction and rank vectors were not regenerated in Phase 14; their frozen queue files were independently re-evaluated. Phase 13's diagnostic table was reused rather than rebuilding all 499 C-stage graphs. Consequently the edge audit reports only incident-level aggregates, not individual source-observation provenance. No C/P/V candidate was run because the evidence gate failed.
