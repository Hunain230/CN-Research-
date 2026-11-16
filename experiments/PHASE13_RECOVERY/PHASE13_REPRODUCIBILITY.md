# Phase 13 reproducibility

Run from repository root with the existing `.venv` on Windows. Phase 13 is local retrospective research only. Code version at audit: `cd6efb7377d69c04386516a7574396208abd110b`; individual untracked Phase 13 script hashes and all frozen parent hashes are in `PHASE13_INPUT_HASHES.json`. The Phase 13 copy of `evaluate.py`, `reconstruct.py`, and `PHASE10_EXPERIMENT_CONFIG.json` is byte-identical to Phase 10. `predictions/` contains hard links to 500 frozen Phase 10 files; no file is rewritten through those links. To reproduce in a fresh directory, make read-only copies or hard links of the prediction files; do **not** run a generator that overwrites the original.

```powershell
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/evaluate.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/run_c_sensitivity.py --sample-queues 3
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/run_c_sensitivity.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/evaluate_c_sensitivity.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/compare_c_status.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/evaluate_rank_matrix.py
.\.venv\Scripts\python.exe -m unittest discover -s experiments/PHASE13_RECOVERY -p 'test_phase13.py' -v
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/run_bridge_split.py --sample-queues 3
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/run_bridge_split.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/evaluate_bridge_split.py
.\.venv\Scripts\python.exe experiments/PHASE13_RECOVERY/write_phase13_reports.py
```

Most scripts refuse to overwrite their outputs. Run the sequence in a fresh Phase 13 copy for reproduction. The exact Phase 10 E1 method object matched the reproduced Phase 13 method object; the 0.75 threshold partition matched every frozen v2 group and its TP/FP/mixed/recoverability totals. The full C prediction took 143.12 seconds with peak process RSS 574,357,504 bytes; C evaluation took 54.19 seconds with peak RSS 472,489,984 bytes. Ranking evaluation took 33.10 seconds with peak RSS 435,183,616 bytes. These are shared-pass measurements, not per-threshold or per-ranker estimates. The incident table has 9,980 data rows.
