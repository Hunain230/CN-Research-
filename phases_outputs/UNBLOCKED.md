# Readiness gate review — 2026-11-08

This review checked authoritative dataset/ranking documentation, current Phase 1–5 records, the aggregate audit, Phase 2 preprocessing summaries, and the restricted conflict-provenance artifact. Raw GUIDE and evaluator label records were not modified or opened for outcome analysis. No models, baselines, agents, real metrics, rankings, or test-set analysis were run.

## Newly verified

- **Publisher and release:** Microsoft publishes *Microsoft Security Incident Prediction* on Kaggle. Current publisher metadata lists version 2, updated 2026-07-18, CDLA-Permissive-2.0, and the same two filenames and byte sizes as the local raw files. Local SHA-256 values still match Phase 1. The local download receipt/date and a publisher-published checksum are unavailable, so byte provenance is supported by file names/sizes and local baseline hashes, not an origin checksum.
- **Prioritization label meaning:** the publisher and primary AIP paper describe queue-relative expert priority, distinct from triage outcomes. They document an expert sweep of the full eligible queue and a complete expert top-20 selected from that queue for each of 499 eligible GUIDE test-split organizations (at least 50 incidents and 10 detectors). Local structure is consistent: 499 numeric-eligible queues, 9,980 rank rows, 20 distinct rank values per queue, and all rank keys join to distinct composite incident keys. This verifies the published top-20 set construction for the release; the remaining unlabeled incidents are not negatives.
- **Conflict diagnostics:** the restricted ledger contains 70,702 conflicting composite alert keys, 150,743 distinct alert-to-incident assignment groups, and 830,109 evidence rows. Of the assignment groups, 149,239 repeat across multiple rows; 69,982 keys have at least one repeated assignment; 720 keys have one row per assignment. Repetition does not explain why multiple incidents are assigned to one alert key. No assignment was resolved or turned into a pair label.
- **Feature status:** no model-visible field is approved. The feature view remains empty; labels and outcomes remain evaluator-only.

## Current gate register

| Gate | Status | What remains |
|---|---|---|
| Release, source, license | Verified at publisher; local download event unresolved | Obtain download receipt/date or authoritative file checksum if available. |
| Rank task meaning and expert top-20 construction | Verified in the publisher documentation and primary paper | Do not count unranked incidents as negatives. |
| Numeric rank direction | **Unresolved** | Obtain explicit statement of which numeric rank is highest/first. Do not infer from numbering. |
| Local schema and query-universe mapping | **Unresolved** | Publisher describes `Rank`/`Split`; local file exposes `QueueRank` and no `Split`. Confirm exact release mapping, snapshot/active filter, and eligible candidate incident universe. |
| Alert-to-incident conflicts | **Unresolved; correlation and joint evaluation no-go** | Obtain publisher/data-owner semantics or researcher-approved defensible exclusion/adjudication rule. Preserve all source-row assignments meanwhile. |
| Feature allowlist | **Requires researcher/data-owner/privacy decision** | Approve fields individually with timing, meaning, provenance, privacy/data-use rationale, and leakage audit. |
| Organization split/protocol | **Provisional** | Approve and hash split-selection method, query/candidate universe, missing-label policy, metrics and denominators, method versions, and test seal before test access. |
| GUIDE `Id` semantics | **Unresolved** | Phase 1 found 291,595 repeated value groups and 3,844,772 excess rows. Obtain its definition; never use it as a unique row/citation key. |
| B0 severity | **Unavailable; amendment proposed only** | Provide authoritative severity field/crosswalk or approve [proposed B0 amendment](proposed_B0_protocol_amendment.md). |
| Real-data evaluation | **Blocked** | Clear all prerequisites applicable to the task and freeze protocol before opening test labels. |

## Allowed work and hard boundaries

Leakage-safe preprocessing development can continue under Phase 2 boundaries, with the empty feature view, evaluator isolation, and preserved ambiguous memberships. Synthetic Phase 3–5 plumbing remains synthetic only. Correlation, joint evaluation, real priority scoring/ranking, real baseline/agent execution, empirical metrics, p-values, and test-label inspection remain blocked. No field was allowlisted and no split was frozen.

## Files changed and reproducibility

- Added `src/investigate_ambiguous_memberships.py`, a streaming aggregate-only diagnostic that reads only the restricted Phase 2 ambiguity ledger and emits counts, not identifiers.
- Added ignored aggregate artifact `data/derived/preprocessing/review/conflict_investigation_aggregate.json`; the identifier/provenance source artifact is unchanged and remains under Git-ignored `data/`.
- Added `phases_outputs/readiness_evidence_review.md`, `phases_outputs/research_gate_register.csv`, and the unapproved `phases_outputs/proposed_B0_protocol_amendment.md`.
- Updated `phases_outputs/Phase1.md`, `phases_outputs/Phase2.md`, and `phases_context.md` with the findings and narrowed research status.
- This file records the requested outcome summary.

Run the aggregate with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m src.investigate_ambiguous_memberships
```

It completed successfully with the counts above. Python 3.12.10; standard library only; no dependency changes. Raw hashes remained `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` (`GUIDE_Test.csv`) and `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` (`GUIDE_Test_Queue_Rankings.csv`). Detailed source links, evidence statements, and code/config/artifact hashes are in [readiness_evidence_review.md](readiness_evidence_review.md).

## Authoritative sources reviewed (accessed 2026-11-08)

- [Microsoft publisher dataset and release documentation](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction)
- Freitas, Gharib, and Magenheim, [primary AIP paper, Sections 5.1 and 5.5](https://arxiv.org/html/2607.16963v1)
- [CDLA-Permissive-2.0 license](https://cdla.dev/permissive-2-0/)

**Outcome:** some source and label-construction questions are now verified, but empirical readiness has not been reached. Numeric rank direction, local query-universe/schema correspondence, alert mapping, field approvals, split/protocol freeze, and B0 severity remain open. Real-data evaluation is not permitted.
