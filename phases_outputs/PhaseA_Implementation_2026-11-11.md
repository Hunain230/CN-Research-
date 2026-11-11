# Phase A implementation and gate decision — 2026-11-11

## Scope and decision

Phase A audited the requested label coverage, tested two local retrieval routes, and rechecked the ranking and cohort contract. The work used the local `GUIDE_Test.csv` and `GUIDE_Test_Queue_Rankings.csv` hashes already recorded by Phase 1. **Phase A has not passed**: source semantics do not justify treating conflicting alert assignments as simultaneous truth, validation candidate recall is 80.37% rather than 99%, and no untouched ranked cohort exists in the two local files. The system is not production ready.

These are exploratory research results. The existing 57-organization joint cohort has already been evaluated. The 20 training and 67 validation organizations used for the new retrieval tests were selected from an existing exploratory split; no holdout was used for these new routes.

## 1. Conflicting alert membership and top-20 coverage

The [GUIDE dataset paper](https://arxiv.org/html/2407.09017) defines `AlertId` as an alert identifier and `Timestamp` as alert creation time. [Microsoft Defender correlation documentation](https://learn.microsoft.com/en-us/defender-xdr/alerts-incidents-correlation) describes assigning alerts to incidents, and its [move-alert documentation](https://learn.microsoft.com/en-us/defender-xdr/move-alert-to-another-incident) describes detaching an alert from one incident and attaching it to another. The product behavior is compatible with reassignment over time; it does **not** establish whether repeated `(OrgId, AlertId)` assignments in this exported GUIDE file mean a valid history, simultaneous membership, an anonymization collision, or a data error. The local file lacks a versioned membership event or reliable snapshot time to choose among those interpretations.

The primary rule therefore stays: **exclude every ambiguous composite alert key from correlation and joint scoring, retain all expert top-20 labels in the denominator, and never select one assignment by majority vote, row order, or model output.** The evaluator-only [sensitivity audit](../outputs/phase_a/multimembership_sensitivity_v1.json) represents all reported assignments as a many-to-many graph without changing primary truth. On the already accessed 57-organization cohort, the primary coverage numerator is **1,066/1,140 = 93.51%**; all-assignment *optimistic* coverage is **1,140/1,140**. The 74 extra labels are only potentially recoverable. At least 17 would need a source-validated rule to make 95% possible under the unchanged denominator. The sensitivity bound is not a measured model recall and cannot be promoted to the primary result.

The 57-cohort conflict graph contains 998 ambiguous alert keys with two incident assignments, 89 with three, 21 with four, and four with five. Of these, 256 connect to more than one top-20 incident, showing why a simple many-to-many scoring rule could also double-credit predictions. A valid rule needs the dataset owner to define the intended time/snapshot semantics and specify how multi-incident alerts count in pair labels and group recovery. Until then, the primary exclusion stands.

## 2. Candidate retrieval test

The existing frozen descriptor retrieval at K=200 was reconstructed on 20 fixed training organizations and 67 validation organizations, each capped at the same first 500 hashed alert keys per organization as the earlier correlation diagnostic. All candidate generation stayed inside organizations and did not read `IncidentId`, `QueueRank`, or any evaluator store. Candidate files were hashed before the evaluator read membership truth. The validation denominator is **336,754 positive pairs among 4,037,136 possible within-organization pairs**. These denominators were held fixed across routes.

Two additional routes were implemented under ignored, restricted `data/derived/` storage:

1. Exact shared entity values from 12 GUIDE fields, including device, account, file hash, message, IP, URL, and application identifiers. A token generates pairs only when it appears on 2–20 alerts in its organization. The raw value is held in process memory and never written to the candidate artifacts. This is a **local-only research assumption**, not a privacy or point-in-time approval.
2. Exact alert-title matches (up to 100 alerts per title) and shared words of at least four characters (up to 20 alerts per word), after a frozen small stopword list. Title text and tokens likewise remain in memory. This route also lacks independent field-timing and external-transfer approval.

| Validation route | Retrieved positive pairs | Candidate pairs | Micro candidate recall | Pair coverage |
|---|---:|---:|---:|---:|
| Frozen descriptor baseline | 269,857 | 2,699,442 | 80.13% | 66.87% |
| Baseline + local entity links | 270,652 | 2,704,304 | 80.37% | 66.99% |
| Baseline + entity + title | 270,652 | 2,704,341 | 80.37% | 67.00% |

Entity links added 795 positive pairs for 4,862 additional candidates. Titles added 37 candidates and no positives beyond that union. The final route still misses **66,102 positive pairs**. The target of 99% micro candidate recall at a substantially reduced workload was **not met**. No pair classification or final Recall@20 was computed from these new candidate files, and they must not be described as improved deployed model performance.

The entity generator took **40.9 seconds** on this machine, including a full raw-file scan and per-organization descriptor retrieval. This is research batch time for 87 organizations, not a production latency measurement. Full pipeline runtime, memory peak, title-route time, and service throughput were not measured.

## 3. Evaluation and data contract

The [AIP paper, Section 5.5](https://arxiv.org/html/2607.16963v1) supports the task meaning: expert queue-relative top-20 priority labels, selected after a full-queue review for 499 eligible GUIDE test organizations. The local ranking file has 499 organizations, 9,980 labels, and 20 unique values 1–20 per organization. The paper describes columns `OrgId, IncidentId, Rank, Split`; the local file has `OrgId, IncidentId, QueueRank` and no `Split` or active-queue snapshot. The reviewed source does not explicitly define whether numeric 1 or 20 is highest. Thus rank 1 highest and all local composite incidents as the queue universe remain **documented assumptions**, not verified dataset facts. Top-20 *set* recovery is direction independent; rank-sensitive nDCG should retain both directions until authoritative confirmation. Non-top-20 incidents remain unjudged for graded relevance.

The [GUIDE paper](https://arxiv.org/html/2407.09017) says timestamps are perturbed for privacy. It names alert creation time and alert title, and describes the entity fields, but does not prove that each evidence value was available at the exact inference cut-off for this project. The official [field policy](../configs/field_policy.yaml) still has an empty approved model-field list. Entity and title retrieval are restricted offline experiments only; no raw values, title text, or equality tokens may be sent to Groq, Gemini, or another hosted model on the basis of this audit. `IncidentId`, `QueueRank`, `IncidentGrade`, `ActionGrouped`, `ActionGranular`, source ordinals, and `Id` remain barred from model features. Missing values are unknown. The audit did not alter the Phase 2 evaluator stores or prior predictions.

The [contract audit](../outputs/phase_a/contract_audit_v1.json) checks raw hashes, ranking schema/counts, frozen candidate lineage, identical pair denominators, the unchanged 1,140-label denominator, and the official empty allowlist. Source-level truth is imported only in the separate evaluator commands after candidate manifests are written. These checks guard the recorded run; they do not validate undocumented field timing or source membership semantics.

## 4. Confirmatory cohort

All 499 locally ranked GUIDE_Test organizations are accounted for by the historical 50-organization split and the later 469-organization rerun assignment, with 20 pilot/development organizations appearing in both assignments. The historical 30 test organizations were already evaluated; the newer 68 holdout organizations were also evaluated in the GUIDE rerun. Repartitioning these same labels does not create an untouched confirmatory set. The local `data/raw/` directory contains only the GUIDE test evidence and queue ranking files. **New independent ranked data or a documented, independently sealed prospective cohort is required** for confirmatory claims. Until then, every real-data result remains exploratory.

## Reproduce and inspect

Run from the repository root with the project `.venv`. Each command refuses to overwrite its existing output, so use a new versioned artifact location if reproducing after a code change:

```powershell
.\.venv\Scripts\python.exe -m src.phase_a_multimembership_sensitivity
.\.venv\Scripts\python.exe -m src.phase_a_entity_retrieval generate
.\.venv\Scripts\python.exe -m src.phase_a_entity_retrieval evaluate
.\.venv\Scripts\python.exe -m src.phase_a_title_retrieval generate
.\.venv\Scripts\python.exe -m src.phase_a_title_retrieval evaluate
.\.venv\Scripts\python.exe -m src.phase_a_contract_audit
```

Public outputs are aggregate JSON in `outputs/phase_a/`. Candidate edges and hashed alert keys are restricted under ignored `data/derived/phase_a_*`. The immutable generation manifests record code/data and candidate hashes. No API call or new dependency was used.

## Remaining gates

- Obtain a publisher/data-owner definition of repeated alert membership and, if applicable, a valid snapshot-aware multi-membership evaluation rule. Recompute the 1,140-label coverage ceiling without dropping labels.
- Obtain a source mapping for the local `QueueRank` column, numeric direction, exact eligible queue snapshot, and the documented data-use/timing basis for every proposed feature.
- Design a new retrieval route with evidence that actually connects the missed positive pairs; tune on training and validation only, report candidate recall **and** pair workload, and freeze before any future untouched test.
- Acquire an independent ranked cohort for a confirmatory comparison. A key or larger LLM quota does not solve the current data and retrieval gates.
