# Module 6F — Final offline run and release package

**Status:** aggregate-only handoff package generated from frozen prior runs. This is not a new confirmatory evaluation.

The package generator `src.phase6f_package` verifies its required inputs exist, computes their SHA-256 fingerprints, copies only aggregate reports/metrics, Module 6B–G records, and the static dashboard, then writes an immutable manifest and summary. It excludes raw evidence, row-level predictions, evaluator mappings, per-organization results, and secrets. The original Phase 6 run directories are not overwritten.

The handoff includes a priority-retrieval oracle-group ceiling and an ambiguity-excluded correlation diagnostic. These are exploratory because the historical test cohort was accessed. It includes no empirical LLM/multi-agent comparison. Pair retrieval is far below the 95% target; priority Recall@20 is also far below 95%. No overfit-free or deployment-ready claim is made.

Rebuild into a new run ID:

```powershell
.\.venv\Scripts\python.exe -m src.phase6f_package --root . --run-id phase6-final-offline-new-id
```

The generated package must not be used to tune model choices on the historical test cohort. A future confirmatory handoff requires an independently established fresh cohort and frozen evaluation protocol.

