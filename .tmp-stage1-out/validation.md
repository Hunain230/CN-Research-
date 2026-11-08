# Stage 1 dataset validation

Inputs: GUIDE 5 rows; queue 4 rows.

## Decisions

- Alert correlation: **no-go** until conflicting alert mappings are understood.
- Incident prioritization preprocessing: **allowed** with evaluator labels isolated and ambiguity preserved for investigation.
- Incident prioritization evaluation: **blocked** until rank scope and top-20 completeness are verified.
- Joint evaluation: **no-go**.

## Grain and key integrity

- GUIDE Id: 1 missing rows; 1 duplicated values across 1 excess rows.
- Repeated evidence-row groups per composite alert key: 1 (may be normal at evidence-row grain).
- Conflicting incident assignment groups per composite alert key: 1.
- Distinct GUIDE composite incidents: 4; distinct alert keys: 3.

## Joins and ranking

- Composite matched incidents: 3; unmatched GUIDE incidents: 1; unmatched ranking keys: 0.
- Qualified organizations: 0 (50 required by the proposed 10/10/30 split).
- Duplicate ranking keys: 1; missing rank rows: 1; conversion errors: 0; rank ties: 1; rank gaps: 1.
- Rank direction, scope, query universe, and top-20 completeness are unverified from the local files.

## Leakage and Stage 2 boundary

All fields default denied. IncidentId, QueueRank, IncidentGrade, ActionGrouped and ActionGranular are evaluator-only. Stage 2 may develop leakage-safe preprocessing with labels stored separately and ambiguous alert mappings preserved for investigation. Do not create final evaluation-ready alert pairs or ranking results until Stage 1 gaps and label semantics are resolved.

## Required evidence

Provide the source release/license citation, download record/date, documentation that QueueRank 1 is highest and ranks 1-20 are complete expert labels for a defined query universe, and point-in-time provenance for evidence fields.
