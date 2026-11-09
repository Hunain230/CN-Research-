# Module 6A — Frozen Study Protocol

**Protocol:** `phase6a-study-protocol-v1`  
**Created:** 2026-11-09  
**Status:** frozen with explicit open gates; prior real-data findings remain exploratory.  
**Machine-readable settings:** [`configs/phase6_protocol.yaml`](../configs/phase6_protocol.yaml)

## Project, data, and evidence status

Project: *Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization*. Inputs are the local Microsoft GUIDE test evidence and AIP queue-ranking files. The Phase 1 validation and Phase 2 preprocessing manifests hold source hashes and row counts. Recorded SHA-256 values are `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` for `GUIDE_Test.csv` and `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` for `GUIDE_Test_Queue_Rankings.csv`. Local hashes match earlier project baselines. Original download receipt and publisher byte checksums are unavailable (**unresolved provenance**).

Evidence inspected includes Phases 1–6 specifications and completion records, `UNBLOCKED.md`, readiness review, gate register, test-label access log, empirical protocol amendments/manifests, Phase 1/2 manifests and validation/preprocessing/leakage/split artifacts, Phase 6 prediction/evaluation manifests, configs, evaluator store/API, and model-facing code. See [`Phase6A_audit.json`](Phase6A_audit.json) for paths and hashes. The Phase 2 organization assignment has digest `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024`; it is preserved unchanged. It records 10 pilot, 10 development, and 30 test organizations, but only 50 of the 499 reported eligible organization IDs are present in the manifest (**verified artifact fact**).

Status vocabulary: **verified** means supported by a repository artifact; **assumed for implementation** means a declared project convention without independent evidence; **unresolved** means evidence is insufficient; **blocked** means the protocol disallows the action until a gate is cleared.

## Research questions and comparisons

The study asks whether evidence-grounded correlation and prioritization improve incident grouping and recovery of expert top-20 incidents over rule, retrieval, and matched single-model baselines on held-out organization queues, subject to evidence perturbation and operational constraints. Compare methods on identical frozen queries/candidate universes. B3, the repeated single-LLM baseline, remains the predeclared primary comparator only if an empirical model is separately authorized and available. No hosted calls are authorized by this protocol. Existing Phase 3–5 agents/baselines are synthetic plumbing, not empirical model results.

## Cohorts and split policy

- **Pilot:** feasibility and protocol development only.
- **Development:** model, prompt, feature, retrieval, threshold, and calibration selection.
- **Validation:** only a predeclared limited choice among configurations; its membership/purpose is not separately evidenced in the present split and therefore remains unresolved.
- **Confirmatory test:** evaluator-only after all choices and hashes are frozen. The existing 30-org cohort is **exploratory**: Phase 6 read test labels, emitted metrics, and later amended evaluation/reporting. The access log rules out treating it as untouched.

Keep the existing split exactly as recorded; do not move organizations or regenerate it. Organizations are the split and statistical unit. The prescribed fresh-cohort selector is SHA-256 of `seed`, NUL, and exact UTF-8 OrgId, ordered by digest then exact OrgId, applied only to an independently evidenced eligible and unused ID set. Seed: 0. The repository does not establish a complete unused/exposure-audited pool of IDs or label independence for the unassigned remainder. Accordingly, no fresh cohort is frozen; confirmatory evaluation is **unavailable**. A random row split is not a substitute.

## Feature, label, query, and ambiguity boundaries

The established `configs/field_policy.yaml` is deny-by-default and empty; its status is **verified**. It blocks real-data model execution. `configs/empirical_field_policy.yaml` names five descriptors as a user-directed local assumption, not a point-in-time/privacy approval. No new fields are approved here. The five assumed local-only descriptors are `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole`. Timestamp, direct/raw entity identifiers, join keys, outcomes, evaluator labels, and unapproved fields remain excluded. Preserve timestamps in restricted lineage; prove availability at prediction time before any future approval. Missing data are unknown, never negative evidence.

`IncidentId` membership and `QueueRank` are evaluator-only, along with `IncidentGrade`, `ActionGrouped`, `ActionGranular`, and derived outcomes. Model-facing code may not import evaluator stores/truth readers. Labels must not enter candidate generation, agents, prompts, retrieval, calibration, threshold selection, or dashboard inference. The evaluator store remains logically separate.

Correlation truth joins on `(OrgId, AlertId)`; ranking labels join on `(OrgId, IncidentId)`. **Verified:** 70,702 conflicting composite alert keys are recorded. Exclude every such key and every associated evidence row from primary correlation and joint evaluation; report exclusion counts and retain restricted diagnostics. Never select an assignment by majority, ordering, prediction, or test outcome. Any future resolution must be documented, prediction-independent, and applied to all methods. Conflict semantics remain **unresolved**, so full-correlation and joint claims remain blocked.

QueueRank is an ordinal field; publisher numeric direction is **unresolved**. “Rank 1 highest” is an earlier **assumed for implementation** convention, not a verified fact. The exact local active-queue/query snapshot is also **unresolved**; all local composite incidents in eligible labeled organizations is only an assumed candidate universe. Top-20 membership is not evidence that the unjudged remainder is irrelevant for graded ranking. Show both rank directions for exploratory nDCG; never select direction based on metrics.

## Metrics and denominators

- **Candidate-generation recall:** eligible relevant truth items retrieved / all eligible relevant truth items. Give numerator, denominator, query count, excluded-label count, and uncertainty interval. The ≥95% value is a target only, measurable only with a valid truth universe. Report separately from Recall@20.
- **Pair classification:** precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = harmonic mean. Report candidate-set FN and full-eligible-pair FN separately with both denominators; distinguish candidate misses, abstentions, malformed/failed outputs, and missing queries. No silent removal.
- **Ranking:** Precision@10, Recall@20 against complete expert top-20 membership where applicable; nDCG@20 with gain `2^(21-r)-1` for expert rank r=1…20 and zero otherwise, discounted by predicted position `log2(position+1)`. State query universe, label completeness, ties, exclusions, and candidate counts. Show both plausible rank directions; ranking findings remain exploratory under current evidence.
- **Joint recovery:** end-to-end Recall@20 counts an expert top-20 incident recovered only when a predicted top-20 component has ≥80% completeness and ≥80% purity. Blocked until valid correlation truth is available.
- **Operational:** decision coverage, review rate, abstention rate, invalid-output rate, latency, and candidate-generation coverage only with the complete eligible universe. Include per-organization results and aggregate values.
- **Comparisons and uncertainty:** same frozen queries/universes; report missing/failed queries. Organization is the independent unit. Use organization-level paired bootstrap (10,000 resamples where feasible) for generalization intervals and report method/seed. Preserve the prior Phase 2 Holm comparison plan only if its methods become valid and executable. Do not treat pairs or model seeds as independent organizations.

## Selection, deterministic execution, and test access

Choose model, prompt, feature, retrieval, threshold, and calibration settings using development only. Validation is limited to its declared selection role. Freeze method, config, prompt/model hashes, candidate universe, metrics, and split before any confirmatory labels are opened. A future valid confirmatory evaluation runs once. An engineering failure may rerun the identical frozen configuration with both manifests retained. Any change prompted by test results makes results exploratory. Current test cohort access is permanently classified exploratory; test-tuned selection is blocked. Module 6A performs no real test-set evaluation.

Base seed is 0. Cohort ordering and method-specific ties must be deterministic and recorded. Each run records input, split, config, code, and protocol hashes, versions, seed, time, exclusions, and failures. Prior run artifacts are retained and never rewritten.

## Deviations, amendments, and claim limits

Record deviations in a dated, versioned amendment with evidence, rationale, impact, hashes, and classification. Do not silently revise a frozen rule. Existing Phase 6 ranking and ambiguity-excluded correlation results remain **exploratory**; the ranking result is an assumption-based local oracle-group ceiling, and the correlation result is a limited ambiguity-excluded diagnostic. Neither establishes confirmatory performance, model superiority, full-data correlation, deployment readiness, or guaranteed 95% recall.

Open gates: QueueRank numeric direction; exact query/active-queue snapshot; authoritative local release/download provenance; GUIDE `Id` meaning; conflicting alert assignment semantics; point-in-time/privacy approval for any feature (existing production allowlist is empty); complete unused-organization exposure evidence; confirmatory cohort membership. Until resolved, downstream real-data confirmatory experiments are **blocked**. Previously accessed test data may only support transparently labeled exploratory reporting under applicable project controls.
