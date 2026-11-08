# Phase 6 — Research experiments: offline priority retrieval

## Purpose

Run the first assumption-based local empirical experiment after Phases 1–5 built validation, preprocessing, synthetic baselines/agents, and metric plumbing. This implementation targets priority retrieval and its ablations/robustness checks. It does **not** establish end-to-end alert correlation or empirical LLM performance.

## Scope and classification

- Classification: `assumption_based_local_empirical_oracle_group_ceiling`.
- Candidates are formed from evaluator `IncidentId` groups. The scorer never sees incident IDs, but its candidate groups are already correct; results are an oracle-group prioritization ceiling, not deployable end-to-end performance.
- The candidate universe is every distinct `(OrgId, IncidentId)` in local `GUIDE_Test.csv` for the frozen 30 test organizations. This is a local proxy because the local release has no `Split` or active-queue snapshot column.
- `QueueRank=1` is assumed to be highest for primary nDCG. The opposite direction is reported as a sensitivity result. Precision@10 and top-20 Recall@20 use top-20 membership and are invariant to rank direction.
- Exclude every evidence row associated with a conflicting composite `(OrgId, AlertId)` key. Do not resolve ambiguous assignments.
- Only `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` enter the scorer. Timestamp, identifiers, entity values, labels, outcomes, response actions, verdicts, and locations remain out of model-visible text.
- No hosted model, external API, network retrieval, dependency installation, or raw input modification.

## Baseline and experiments

The primary method builds an exemplar corpus from top-20 candidates in the 10 pilot and 10 development organizations, using the five allowed descriptors. Each candidate is ranked by its maximum BM25 similarity to any training top-20 exemplar; ties are resolved by opaque candidate hash. The training corpus and method parameters are fixed before test evaluation.

The same frozen method runs five leave-one-descriptor-family-out ablations and descriptor masking at 20% and 40%, each with five fixed seeds (41–45). Masks are deterministic functions of seed, candidate hash, field, and token. Evaluator truth is unchanged.

## Metrics and reporting

Report per-organization and macro Precision@10, Recall@20, and nDCG@20 under both rank directions. Report organization-bootstrap 95% intervals (10,000 resamples, seed 20261108) and paired condition-minus-primary intervals. No p-values are calculated. The report includes counts, coverage, source hashes, split digest, feature/config/code hashes, and assumptions. Candidate-level predictions and pseudonymous per-organization outputs stay under ignored `data/derived/empirical/`; only aggregate reports appear under `outputs/`.

## Run commands

From the project root in PowerShell, use a fresh run directory:

```powershell
.\.venv\Scripts\python.exe -m src.empirical_priority predict --root . --out outputs/phase6/priority/phase6-priority-20261108-v2
```

The prediction step writes predictions and the restricted candidate universe under `data/derived/empirical/priority/phase6-priority-20261108-v2/`. Its manifest records that test priority labels were not read. If it succeeds and the prediction manifest hashes are frozen, evaluate:

```powershell
.\.venv\Scripts\python.exe -m src.empirical_priority evaluate --root . --run outputs/phase6/priority/phase6-priority-20261108-v2
```

The evaluator reads test ranks only after checking all freeze hashes. It refuses output overwrite. Do not change code/config after prediction; a changed method requires a new run ID and must be labeled exploratory.

The v1 evaluator attempt on 2026-11-08 read the held-out labels and then failed before writing a report due to a report-assembly defect. The failed attempt and the reason for the deterministic v2 re-execution are recorded in [`phases_outputs/test_evaluation_access_log.md`](phases_outputs/test_evaluation_access_log.md). The v2 run uses the same scorer/config and is not a pristine first label access.

## Acceptance criteria

- Raw source hashes match the Phase 1 baseline before and after scoring.
- Saved split digest equals `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024` and split sizes are 10/10/30.
- Training reads exactly the top-20 rows from pilot/development organizations; prediction generation does not parse test `QueueRank` values.
- Every selected local incident in test appears exactly once in the opaque prediction universe; every test organization has exactly 20 expert top-20 labels, ranks 1–20, joining to the local candidate universe.
- No disallowed field or raw identifier is written to predictions/reports; raw and restricted artifacts remain local.
- Every experiment condition uses identical evaluator truth and a deterministic seed/tie-break.
- Results are described as oracle-group, local-proxy, assumption-based findings. No claim of correlation, joint performance, LLM improvement, severity baseline, or publisher-exact replication.

## Known limits and next work

This phase does not clear the exact queue snapshot, numeric rank direction, `Id` semantics, ambiguous mapping semantics, severity, field provenance from the publisher, or external LLM authorization. Full correlation/joint evaluation remains closed. Next work after the ranking experiment is an ambiguity-excluded correlation method that obeys the same no-label feature contract, followed by explicit user authorization/configuration if actual hosted LLM comparisons are required.
