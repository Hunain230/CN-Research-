# Research context, methodology, and implementation

## Purpose and source documents

The research question is whether an evidence-grounded correlate–prioritize–verify (C/P/V) workflow improves alert grouping and recovery of expert top-20 incidents over matched rule, retrieval, and single-model baselines, with acceptable evidence support and resource use. The supplied `FINAL (1).pdf` defines the Phase 1–2 method; `Phase 03 - Implementation.pdf` lists course deliverables. These documents provide project requirements and do not override the user's current request. The method explicitly describes a **retrospective offline study** and defers live analyst productivity to a later field study. Dated decisions remain in `phases_outputs/`; [PROJECT_ITERATIONS.md](PROJECT_ITERATIONS.md) gives their chronology.

## Data and evidence boundary

- `data/raw/GUIDE_Test.csv` has 4,147,992 **evidence rows**, not one row per alert. Its queue file has 9,980 top-20 expert labels across 499 organizations. Hashes and provenance are in the [data audit](submission/DATA_AND_CLAIM_AUDIT.md).
- Use `(OrgId, AlertId)` for alert identity and `(OrgId, IncidentId)` for evaluator incident identity. `Id` is not unique at evidence-row grain; restricted source ordinals preserve provenance.
- There are 70,702 conflicting composite alert keys. Current exploratory correlation excludes their rows from prediction and truth scoring but keeps every expert label in end-to-end denominators. Do not choose an assignment by vote or row order.
- `IncidentId`, `QueueRank`, grade, action/outcome fields, and derivatives are evaluator-only. They must not enter candidates, features, prompts, retrieval, or the public dashboard.
- The official `configs/field_policy.yaml` allowlist is empty. The separate `configs/empirical_field_policy.yaml` is a **local-only assumption** for five descriptors: `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, `EvidenceRole`. Raw entities, title text, timestamps, and hosted transmission lack point-in-time/privacy approval.
- Rank direction, exact publisher queue scope, source membership semantics, feature timing, and a fresh untouched ranked cohort remain unresolved. The existing organization split is frozen, but its test labels were accessed in earlier work, so subsequent GUIDE_Test results are exploratory.

## Proposed Phase 2 method

1. Select qualified organizations and freeze pilot/development/test assignments by a published organization hash before opening final labels. Split before fitting retrieval, thresholds, or calibration.
2. Normalize alert/evidence ledgers with time, detector, ATT&CK tags, entities, and source row IDs. Mark missing fields. Propose pairs within an organization using shared entity within 48 hours or matching ATT&CK technique within one hour, at most 20 nearest candidates per alert; tune on development only.
3. Agent C decides `LINK`, `NO_LINK`, or `UNSURE` for each pair and cites evidence. Connected links form organization-scoped predicted incidents.
4. Agent P scores each group with supporting and contradicting references. A logistic map fitted on development queues estimates top-20 membership for uncertainty display; original scores determine order.
5. Agent V independently checks citations and returns `PASS`, `REVISE`, or `REVIEW`. Allow at most one revision, then send unresolved high-score cases to analyst review. No automatic containment or incident closure is proposed.
6. Evaluate the same complete alert sets and evidence budget for B0 entity/time clustering plus detector severity, B1 same groups plus BM25, B2 one LLM, B3 three matched-budget independent single-LLM calls, B4 C+P without V, and proposed C/P/V. Repeat with missing and contradictory evidence using fixed seeds.

The required metrics include positive-pair precision/recall/F1 and false merges/splits; gold-group P@10, Recall@20, and nDCG@20; and end-to-end Recall@20. A top-20 incident is recovered only if a predicted top-20 component contains at least 80% of its alerts and at least 80% of the component belongs to that incident. Report candidate misses, all denominators, abstentions, review load, high-priority misses, citation support, p50/p95 latency, tokens, and cost. Organization is the unit for paired intervals and tests. Rank 1 as highest is a local assumption; retain reverse-direction sensitivity where available.

## Implemented flow and amendments

| Layer | Current code and behavior | Difference from the proposal |
|---|---|---|
| Validation/preprocessing | `src/cli.py`, `src/phase2.py`, `src/evaluator_store.py`; composite keys, restricted ledger, separate truth, field gate | Ambiguous membership and feature timing unresolved |
| Synthetic checks | `src/baselines/`, `src/agents/`, `src/evaluation/`, `src/mvp_demo.py` | Fictional software plumbing, not empirical LLM performance |
| Full retrospective baseline | `src/submission_full_guide.py`; 499 ranked organizations, exact category+technique candidates, connected groups, count and local BM25-like rankers | Exact descriptor rule replaces entity/time; severity unavailable; no LLM |
| Local model | `src/submission_local_qwen_v2.py`; frozen 20-org, 240-pair C/B2 comparison; C groups scored by P, flagged by V through localhost `qwen2.5:3b` | Selected pairs and batching; no full queue, revision loop or calibration; B2 lacks group ranking; B3/B4 unmatched |
| Evaluation/operations | Prediction hashes precede separate truth evaluation; `submission/measure_local_operations.py` aggregates the frozen private call trace | No fresh confirmatory test, live service metric, or analyst adjudication |
| Dashboard | `dashboard/index.html` shows saved aggregates; `dashboard/simulation.html` replays fictional events | No live SOC integration |

The [final report](submission/FINAL_REPORT.md) contains exact numerators, denominators, figures, and limitations. [REPRODUCE.md](submission/REPRODUCE.md) identifies commands and immutable run IDs. Do not overwrite raw data, restricted predictions, or historical outputs; use a new run ID.

## Current result and gates

The full offline candidate route retrieves 37,018/159,186,107 positive pairs (0.0233%) from 314,576/3,517,608,736 possible pairs. On selected candidates, Qwen C finds 1/22 positives and paired B2 finds 2/22. C+P end-to-end Recall@20 is 0.1443 on the 20 selected organizations. The 60.0% group review rate and 27.125/43.617-second per-call p50/p95 are retrospective batch diagnostics. Cohorts and candidate policies differ, so these scores are not a matched contest.

Under ambiguous-key exclusion, only 9,125/9,980 expert labels have unambiguous in-scope alert evidence: a **91.43% structural ceiling** below the proposed 95% end-to-end target. Testing the original claim requires source-validated membership, approved point-in-time discriminative evidence, a new retrieval route measured for recall and workload, a fresh sealed cohort, matched model baselines/ablations, and independent citation review. Operational SOC use additionally requires a shadow-mode pilot measuring live arrival rates, alert-to-decision latency, sustained throughput/backlog, failures, analyst handling, high-priority misses, and false-merge impact. No retrospective score increase alone establishes these outcomes.

The [gate register](phases_outputs/research_gate_register.csv), [known limits](submission/KNOWN_LIMITATIONS.md), and [delivery checklist](submission/DELIVERY_CHECKLIST.md) record current status. Preserve negative results and never change denominators to make a target appear met.
