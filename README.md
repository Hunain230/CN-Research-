# SOC threat correlation and incident prioritization

This repository is a **retrospective research implementation**, not a deployed SOC. It tests whether alerts can be grouped into incidents, ranked for analyst review, and checked for evidence support through correlate (C), prioritize (P), and verify (V) roles.

## Read this project in order

1. [CONTEXT.md](CONTEXT.md): research methodology, data, implementation, metrics, and unresolved gates.
2. [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md): what each stage and later iteration actually produced.
3. [Phase 3 report PDF](submission/PHASE3_IMPLEMENTATION_REPORT.pdf), [editable report](submission/FINAL_REPORT.md), [delivery checklist](submission/DELIVERY_CHECKLIST.md), and [known limits](submission/KNOWN_LIMITATIONS.md).
4. [Reproduction instructions](submission/REPRODUCE.md) and [experiment register](submission/EXPERIMENT_REGISTER.md).

The [matched ranking-baseline extension](submission/PERFORMANCE_BASELINE_STUDY.md) records the later 334/135 organization-split study and its negative rank-fusion control.

## Current evidence

| Evaluation | Scope | Observed result |
|---|---|---|
| Full offline baselines | 499 GUIDE_Test organizations; 400,039 unambiguous alerts | Candidate recall 37,018/159,186,107 = 0.0233%; best end-to-end Recall@20 0.1364 |
| Local `qwen2.5:3b` C/P/V | 20 previously accessed organizations; 240 selected pairs, 22 positives | C pair recall 1/22; B2 single-model recall 2/22; C+P end-to-end Recall@20 0.1443 on 400 expert labels |
| Local model operations | 188 localhost calls | Per-call p50 27.125 s, p95 43.617 s; 60.0% group review fraction |
| Trained offline ranker | Same frozen groups on 135 separate evaluation organizations | Recall@20 0.1542 vs matched BM25-like 0.1507; P@10 0.2351 vs 0.1971; candidate and pair metrics unchanged |

The full offline, trained ranking, and Qwen evaluations have different cohorts or candidate policies; compare only methods within the same recorded cohort. Predictions were frozen before the separate evaluator read evaluation labels, but earlier work had already accessed those labels. The proposed 95% end-to-end target was not met. The [capacity audit](outputs/submission_retrieval_bounds_20261114_v1.json) finds a 9,063/9,980 = 90.81% optimistic ceiling under the current exclusion and 100-alert component cap, and shows that the 20-neighbor rule cannot reach 99% positive-pair candidate recall on this dataset.

## Repository map

| Path | Purpose |
|---|---|
| `src/` | Validation, preprocessing, baselines, C/P/V agents, isolated evaluators, offline and local-model runners |
| `configs/` | Field policies, schemas, protocol, and method settings |
| `data/raw/`, `data/derived/` | Local GUIDE inputs and restricted records; ignored by Git |
| `fixtures/` | Fictional checks and frozen expected outputs |
| `outputs/` | Versioned metrics and run manifests; historical outputs retained |
| `phases_outputs/` | Dated phase records, amendments, and gate decisions |
| `submission/` | Report, figures, verification, and reproduction material |
| `dashboard/` | Saved aggregate viewer and separate fictional playback |

Historical phase specifications remain at the repository root. Historical run reports remain inside their versioned output directories. The root README and CONTEXT are the canonical starting points.

## Run and inspect

From PowerShell in the repository root:

```powershell
.\.venv\Scripts\python.exe -m submission.verify_package
.\.venv\Scripts\python.exe -m submission.measure_local_operations
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Open `http://127.0.0.1:8765/` for saved aggregate results or `http://127.0.0.1:8765/simulation.html` for clearly marked fictional events. For a new full offline and bounded local-model run, follow [REPRODUCE.md](submission/REPRODUCE.md); the Qwen stage can take hours on CPU. No hosted model call is authorized by the current field policy.

## Submission status

This is an **exploratory, partial Phase 3 submission**. The proposed held-out matched B0–B4/C/P/V comparison, perturbations, blinded citation review, and operational SOC evaluation remain incomplete. The Phase 2 methodology defines an offline study and reserves live SOC productivity for a later field study. Do not claim production readiness or that multiple agents improve recall.
