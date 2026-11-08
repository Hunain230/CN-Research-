# Stage 1 dataset validation

Inputs: GUIDE 4 rows; queue 4 rows.

## Decisions

- Alert correlation: **no-go** (ambiguous alert memberships: 1).
- Incident prioritization: **no-go** (0 eligible organizations; 50 required).
- Joint evaluation: **no-go**.

## Integrity and joins

- Distinct GUIDE composite incidents: 3; distinct alert keys: 2.
- Composite matched incidents: 3; unmatched GUIDE incidents: 0; unmatched ranking keys: 0.
- Duplicate ranking keys: 1; missing rank rows: 1; conversion errors: 0; rank ties: 1; rank gaps: 1.
- Rank scope/completeness: unverified from local files; require dataset documentation or authoritative source metadata.

## Leakage and evidence

All fields default denied. IncidentId, QueueRank, IncidentGrade, ActionGrouped and ActionGranular are evaluator-only. IDs and sensitive entity values are never emitted. Candidate evidence fields need point-in-time/source review before allowlisting.

## Phase 2 gate

The 10/10/30 split requires 50 qualified organizations; observed qualified count is 0. No split assignments were created. Rank direction, query universe, source release/license/download date, and top-20 completeness require authoritative evidence.

## Required evidence

Provide the source release and license citation, download record/date, documentation that QueueRank 1 is highest and ranks 1–20 are complete expert labels for a defined query universe, and point-in-time provenance for evidence fields. Candidate feasibility remains unresolved until alert/entity and technique semantics are verified.
