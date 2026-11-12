# Task 2 Data and Claim Audit

## Goal

Create a precise, readable ledger of what the repository verifies, what it assumes, what remains unresolved, and which claims existing artifacts can support.

## Source records to inspect

At minimum inspect `phases_outputs/Phase1.md`, `Phase2.md`, `Phase6A_StudyProtocol.md`, `Phase6B-G.md`, `PhaseA_Implementation_2026-11-11.md`, `PhaseA_Progress_2026-11-11.md`, `Offline_Joint_Comparison_2026-11-11.md`, `test_evaluation_access_log.md`, relevant manifests, and the current README/context files.

## Steps

1. Verify data counts and hashes against existing manifests; do not expose raw rows or identifiers in public outputs.
2. Record the alert-key conflict issue, duplicate `Id` semantics, queue-rank direction/scope, provenance, feature policy, and test-label exposure status.
3. Classify each item as verified, assumed, unresolved, blocked, or exploratory. Cite the repository artifact that supports each classification.
4. Build a claim matrix with three columns: claim, evidence available, and safe wording. Include at least: correlation quality, priority retrieval, end-to-end recovery, LLM-agent superiority, robustness, operational latency/cost, human benefit, and production readiness.
5. Preserve the distinction between historical plans and later amendments. Use the latest governing protocol for current status, while retaining older records as historical context.
6. Do not attempt to “resolve” source semantics by majority vote, row order, best score, or model judgment. Do not silently drop labels to improve metrics.

## Required result

Write `submission/DATA_AND_CLAIM_AUDIT.md` with:

- a concise data description and provenance status;
- verified/assumed/unresolved/blocked table;
- test exposure and split explanation;
- an approved wording guide for the report;
- a list of gates that could not be cleared and their evidence.

## Acceptance checklist

- [ ] Every numeric statement has a source artifact and denominator.
- [ ] Exploratory results are never described as confirmatory.
- [ ] Synthetic stubs are never called empirical LLM results.
- [ ] No unsupported “state of the art,” superiority, or production claims appear.
- [ ] Open gates remain explicit rather than being concealed.

