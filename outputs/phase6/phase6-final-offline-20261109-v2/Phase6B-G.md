# Phase 6B–6G — Implementation handoff

## Overall status

Modules 6B and 6G are implemented in this repository. Modules 6C, 6D, and 6E are completed as evidence-backed execution/reporting modules by reusing the frozen Phase 6 result artifacts. Module 6F creates an immutable aggregate-only handoff bundle. The empirical study is **not complete as a confirmatory LLM multi-agent study**: the historical test cohort was accessed, there is no fresh confirmatory cohort, no empirical LLM call was authorized or run, and current correlation recall is low.

No result is presented as achieving the 95% recall goal. For correlation pair retrieval, full-positive-pair recall is 0.008446 and candidate coverage is 0.002898. For priority ranking, tie-aware Recall@20 is 0.3392, but this is an oracle-group ceiling on a local queue proxy and not candidate-generation recall. These scores are exploratory and not used to tune a new system.

## Module records

- [6B data/label disposition](Phase6B.md): 49-field provenance disposition, evaluator-label isolation, ambiguity exclusion, and current gate status.
- [6C candidate retrieval](Phase6C.md): existing candidate retrieval evidence and valid-denominator limits.
- [6D system comparison](Phase6D.md): comparability findings; empirical LLM/C/P/V comparisons remain unavailable.
- [6E robustness](Phase6E.md): existing ablations/masking results, labeled exploratory, with no test-driven tuning.
- [6F final package](Phase6F.md): aggregate-only package builder and reproducibility fingerprints.
- [6G dashboard](Phase6G.md): single-file interactive static dashboard.

## Commands

From the project root:

```powershell
.\.venv\Scripts\python.exe -m src.phase6b --root .
.\.venv\Scripts\python.exe -m src.phase6g_dashboard --root .
.\.venv\Scripts\python.exe -m src.phase6f_package --root . --run-id phase6-final-offline-new-id
```

The package command refuses to overwrite an existing run directory. It copies aggregate-only outputs and excludes raw evidence and row-level artifacts.

## What remains before the research project can claim full completion

1. Obtain a fresh organization-level test cohort with evidence that its labels have not affected method choices, or acquire an independent dataset.
2. Resolve data-use/privacy review for model-visible fields and establish point-in-time availability. The official field allowlist remains empty; prior five-field experiments used an explicitly local assumption only.
3. Obtain defensible evidence for local queue/query mapping and QueueRank direction if graded-ranking claims are required.
4. Resolve or formally scope ambiguous alert membership semantics before making full correlation or joint claims.
5. Decide whether hosted inference is allowed for this data. Under current repository policy no external model/API calls are authorized. If later approved, use a fixed provider/model/version and run only permitted, minimized evidence; free-tier availability is not a privacy approval or a quality guarantee.
6. Compare actual empirical LLM and C/P/V systems to matched baselines on the same frozen candidates and queries. Do not call synthetic stubs empirical models.
7. Improve retrieval and evaluate against a valid truth universe. The current 95% recall aspiration is not met and is not guaranteed.
8. Validate deployment with approved data handling, operational safeguards, latency/failure review, and a fresh evaluation. The static dashboard is deployable as a report viewer but is not an operational SOC decision system.

