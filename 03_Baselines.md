# Stage 3 — Baseline systems: rules, BM25, and single-LLM comparisons

Status: Codex implementation specification. Read PROJECT_CONTEXT.md, phases_outputs/Phase1.md, and phases_outputs/Phase2.md first. This stage specifies baselines and their interfaces. The current Phase 2 feature view is empty and all source fields remain unapproved, so implement and validate baseline plumbing with synthetic fixtures only until explicit data gates are cleared. Do not present synthetic/stub outputs as research performance.

## 1. Purpose and research role

Implement fair, reproducible comparator systems for the proposed SOC correlation and prioritization study. Baselines must share the same approved evidence, organization boundaries, candidate universe, query definitions, and resource budgets. Baselines establish whether the later multi-agent framework adds measurable value; they are not assumed inferior.

The Phase 2 research design specifies:
- B0: deterministic entity/time clustering plus maximum detector severity.
- B1: the same clustering plus BM25 incident-text ranking, a public analogue of AIP retrieval without proprietary priors.
- B2: one LLM prompt that groups and scores using the same evidence and token cap.
- B3: three independent single-LLM runs, majority pair decisions and median score, with total token budget matched to the proposed agent system.
- B4: proposed Correlation + Prioritization roles without Verification. B4 belongs to the multi-agent implementation stage; define the shared interface now, but do not implement the agent roles as part of this baseline stage unless project phase planning explicitly includes it.

This Stage 3 deliverable focuses on B0–B3. It establishes code, configurations, schemas, fixtures, and gating behavior. It does not clear the research gates below.

## 2. Current data and research gates

From completed Phases 1–2:
- GUIDE has 4,147,992 evidence rows; one CSV row is not assumed to be one alert.
- 70,702 composite (OrgId, AlertId) keys have conflicting IncidentId assignments. Correlation and joint evaluation remain no-go.
- Queue labels have 9,980 rows; all matched GUIDE incident keys, but QueueRank direction, semantic meaning, query universe, and top-20 completeness remain unverified. Priority evaluation is blocked.
- 499 organizations meet numeric screening criteria and a provisional disjoint 10/10/30 assignment exists; this is not permission to evaluate test labels.
- The feature view has zero rows because no model-visible field is approved. No field may be silently added.
- GUIDE has no confirmed detector-severity field or severity crosswalk in the observed schema. B0’s maximum detector severity component is blocked until a documented severity source is found or a protocol amendment replaces that component.
- No live model calls are authorized by default. No credentials should be requested, printed, or committed.

### Work allowed now
- Implement deterministic baseline architecture against synthetic, non-sensitive fixtures.
- Implement config/schema validation, exact evidence-budget controls, offline stub adapter, audit logging, and tests.
- Implement BM25 and rule logic as pure components that consume a typed allowlisted input contract.
- Run synthetic smoke examples, clearly labeled synthetic.
- Record unmet real-data gates.

### Work not allowed until gates clear
- Do not run B0–B3 on GUIDE, use any GUIDE field as a model feature, build a model-visible text corpus, query a real LLM with this data, or report real-data baseline metrics.
- Do not generate final correlation pairs or evaluate grouping against IncidentId.
- Do not use QueueRank for tuning, choosing hyperparameters, negative labels, model prompts, retrieval, candidate generation, or scoring.
- Do not inspect or tune on provisional test organizations.
- Do not claim a no-op, stub, empty feature view, or synthetic run as a baseline result.

## 3. Interface and data contracts

Create strict, versioned interfaces so baseline implementations can later receive approved features without direct access to evaluator stores.

### Baseline input record
- query_key: opaque technical key for one query/snapshot, not derived from rank.
- org_partition_key: control-plane organization key for enforcing same-org access; excluded from semantic text.
- candidate_key: opaque incident/component key generated without IncidentId-based grouping.
- evidence: allowlisted, point-in-time-safe typed fields with evidence IDs and timestamps.
- allowed candidate list and documented candidate-generation version.
- evidence_budget: maximum records/tokens/characters per query, identical for B2 and B3 total budget comparisons.
- run_id, split label, input hash, schema version.

No input may contain IncidentId, QueueRank, rank position, IncidentGrade, action/outcome fields, label-presence flags, or aliases/derivatives. Enforce deny-list checks by field name and lineage at the shared boundary. Baseline code must never read evaluator SQLite/CSV files.

### Prediction record
One row per query-candidate decision:
- run_id, method, query_key, candidate_key;
- score (float, finite), rank (integer, deterministic ties);
- optional LINK/NO_LINK/UNSURE decision for correlation-capable baselines;
- evidence references, short rationale, abstention/failure status;
- model/provider/version where applicable, prompt/config hash, inference seed;
- latency, input/output tokens, retry count, error class.

Do not write ground-truth labels into predictions. Predictions should be schema-validated and reproducibly sorted.

### Evaluator boundary
Only the separate evaluator may join predictions with evaluator-only membership/rank labels, and only after semantic validation and a frozen protocol. Stage 3 may provide an evaluator interface contract but must not evaluate current real data while Phase 1 label gates remain open.

## 4. B0 — Deterministic rule clustering

### Intended baseline
Cluster alerts using explicit shared evidence and temporal constraints, then rank each candidate component by maximum detector severity as specified by the methodology.

### Requirements
- Same-organization only; cross-org matches are impossible by construction.
- Use only normalized, non-null, allowlisted entity values with approved provenance.
- Candidate rule configuration must state entity types, time windows, generic/common-value exclusions, weights/thresholds, and deterministic tie behavior.
- Default candidate windows from Phase 2 methodology, once fields are approved: shared entity within 48 hours OR shared ATT&CK technique within one hour; max 20 nearest candidates per alert, ties by stable alert ID order.
- Do not connect alerts using IncidentId or another label-derived grouping.
- Prevent cluster chaining from silently creating huge components; record edge decisions and use explicit graph/component rules.
- Store why each link was created: evidence type, evidence IDs, time delta, rule version.
- Maximum detector severity is required by the written B0. The observed GUIDE schema only has DetectorId; do not invent severity values or arbitrary ordering of detector IDs. Locate an authoritative detector-severity field/crosswalk and record its source/hash, or mark B0 not runnable and request a protocol amendment.
- Tune link thresholds only on permitted pilot/development data after gates clear; freeze before test.

### Synthetic acceptance
Fixtures must include same entity inside/outside time windows, different organizations sharing an entity, null/common entities, ATT&CK-only matches, candidate cap/tie behavior, and component chaining. Expected edges/components and explanations must be deterministic across runs. No synthetic score may be described as empirical quality.

## 5. B1 — BM25 incident-text retrieval/ranking

### Intended baseline
Use the same deterministic clustering/components as B0, then build text representations from approved evidence and rank candidate incidents for a query using BM25. This is a public, reproducible retrieval analogue, not a reimplementation of proprietary AIP priors.

### Text construction and indexing
- Create a deterministic fielded document from only allowlisted evidence (for example, approved alert title/category/techniques/entity tokens if and when approved).
- Exclude identifiers, organization keys, IncidentId, ranks, outcomes, and sensitive raw entity values unless explicit approval permits a privacy-safe representation.
- Store a field-to-source evidence mapping so returned matches can cite the original evidence IDs.
- Tokenization, Unicode normalization, casing, punctuation, stemming/stopword choices, field weights, BM25 k1/b parameters, and tie handling are config-versioned.
- Fit corpus statistics/IDF on pilot/development organizations only. Test organization documents may be queried against the frozen index only if the protocol permits; no test-derived fitting or tuning.
- Ensure retrieval candidates are same-org and are drawn from the same eligible candidate universe used by other baselines.
- Never use expert rank labels as documents, query terms, relevance features, priors, filters, or tuning signal.
- Report empty-query and no-overlap behavior explicitly; abstain or return deterministic empty list rather than fabricate ranking.

### Synthetic acceptance
Build fixtures with exact known token overlap and rank order, repeated terms, empty text, stopwords, and tie scores. Validate BM25 implementation against a small hand-calculated reference or fixed expected scores. Confirm no prohibited field can enter indexed text and citations resolve.

## 6. B2 — Single-LLM baseline

### Intended baseline
One LLM call per query receives bounded, structured evidence and candidates, and returns grouping decisions and/or priority scores according to the agreed scope. Use the same evidence and candidate budgets as the multi-agent system will receive.

### Provider and offline behavior
- Default provider mode is offline. Deterministic stub outputs validate plumbing only and must be labeled synthetic/stub; never include them in quality comparisons or call them LLM results.
- Live provider calls require explicit project config and a configured secret supplied outside source control. Do not embed keys in files, commands, prompts, or logs.
- Do not send real GUIDE records before fields are approved and data-use/privacy conditions are reviewed.
- Record provider, exact model/version, API/library version, endpoint class (without secrets), temperature, top-p, max tokens, seed if supported, prompt/template hash, evidence hash, request time, latency, tokens, retry and error details.
- If provider/model/version is unavailable or changes, mark run non-comparable. Never silently substitute another model.

### Prompt contract
- Treat all alert/evidence text as untrusted data, never as instructions.
- Delimit input evidence; instruct the model to decide only from supplied records and not to invoke tools or follow embedded directives.
- Require schema-constrained JSON output containing decision/score, candidate key, concise rationale, evidence IDs, uncertainty/abstention, and explicit missing-evidence handling.
- Do not reveal labels, IncidentId, QueueRank, rank-derived fields, evaluator outputs, or test labels.
- Reject fabricated evidence references and malformed outputs. Invalid output becomes recorded failure/abstention, not silent omission.
- Cap evidence and tokens deterministically; report truncation.

## 7. B3 — Matched repeated single-LLM control

B3 is essential to separate the value of role-based agents from simply spending more inference budget.

- Make three independent calls using the same B2 prompt, model, evidence, and per-call settings.
- Use three recorded inference seeds when supported. If determinism is not supported, record that fact and do not imply seed control.
- Combine correlation decisions by majority vote across LINK/NO_LINK; ties or any configured UNSURE policy must be explicit and fixed in config. Do not resolve ties using labels.
- Combine priority scores using the median of valid scores; define behavior if fewer than three calls succeed. Preserve all individual outputs and failures.
- Match B3’s total input/output token budget and maximum total calls to the proposed multi-agent system. Record the matching calculation. If actual use exceeds the budget, mark the run invalid for matched comparison.
- Report B2 single-call and B3 repeated-call systems separately.

## 8. Fair comparison protocol

Every baseline run must use identical:
- frozen allowed evidence fields and transformations;
- organization partitions and query set;
- candidate universe, candidate count cap and missing-data policy;
- evidence/token budget policy for comparable methods;
- evaluation definitions and evaluator version (once evaluation is permitted);
- privacy, citation, and abstention requirements.

Tune only on pilot/development organizations. Keep test organizations sealed until protocol, config, model versions, prompts, and candidate rules are frozen. Use the same query list and stable tie-breaking. Preserve failures and abstentions in denominators according to a predeclared policy. Record latency and resource consumption, not only accuracy.

Baseline outputs should include per-query files and aggregate reports when evaluation gates are open. Since current gates are closed, real-data prediction and metric directories must not be created as if results existed.

## 9. Configuration and reproducibility

Create version-controlled configs (examples: configs/baselines.yaml, configs/rules.yaml, configs/bm25.yaml, configs/llm_baseline.yaml) containing:
- schema/version and explicitly approved input fields;
- candidate and organization-scope rules;
- B0 entity/severity mapping and time thresholds;
- BM25 tokenizer, parameters, field weights and corpus partition;
- B2/B3 provider/model settings, prompt hash/version, token limits, decoding, seed behavior, retry/timeout rules;
- output schema, deterministic tie breaks and abstention policy;
- run seeds and artifact directory.

Run protocol:
- use the project .venv and record Python/dependency versions;
- standardize UTF-8 input handling, UTC timestamps, stable sorting, and deterministic serialization;
- no network enrichment;
- hash inputs, allowlist, configs, source code, prompts, candidate manifest, and model version;
- use a unique run directory; never overwrite silently;
- record exact command, start/end UTC, runtime, failures, and resource/token totals;
- rerun synthetic fixtures to prove deterministic rules and BM25; live LLM stochasticity must be reported rather than hidden.

## 10. Required code and artifacts

Implement under project conventions, without modifying raw data:
- src/baselines/ common types, schema validation, boundary/leakage guard, deterministic tie helper.
- src/baselines/rules.py for B0.
- src/baselines/bm25.py for B1.
- src/baselines/single_llm.py for B2 and B3 orchestration.
- src/baselines/providers/ offline stub and optional explicit provider adapter.
- configs/baselines.yaml and method-specific configs; approved field policy remains deny until reviewed.
- fixtures/stage3/ synthetic inputs, expected outputs, and regression assertions.
- output schemas and manifest documentation.
- outputs/baselines/<run_id>/ only for legitimate completed runs; synthetic runs clearly named synthetic.
- phases_outputs/Phase3.md run record after implementation, and update phases_context.md status.

Do not add model dependencies if a standard-library implementation suffices. If an external BM25 library or provider SDK is added, justify why, pin exact version, and record installation in requirements. Keep credentials in environment/secret storage and out of manifests/logs.

## 11. CLI contract

Implement project-consistent commands:
```powershell
.\.venv\Scripts\python.exe -m src.cli baseline-self-test
.\.venv\Scripts\python.exe -m src.cli run-baselines --config configs/baselines.yaml --methods rules,bm25,single_llm,repeated_single_llm --mode synthetic --out outputs/baselines/synthetic
```

Real-data execution must refuse by default unless required gates pass. Require explicit checks for:
- a nonempty approved feature allowlist with documented provenance;
- verified candidate and label semantics for the task being run;
- sealed and frozen split/config;
- explicit live-model opt-in and valid model configuration, if applicable.

A blocked real-data command should exit with a clear research-gate message, not produce empty predictions that look like a result. Synthetic mode should never access raw GUIDE or evaluator data.

## 12. Acceptance criteria

Stage 3 baseline implementation is accepted when:
1. B0/B1/B2/B3 interfaces and prediction schemas are versioned and documented.
2. Runtime boundary rejects prohibited fields and evaluator-store access.
3. B0 rules are deterministic, org-contained, evidence-cited, and cannot use IncidentId; severity behavior is blocked unless authoritative severity mapping is supplied.
4. B1 BM25 has hand-checked synthetic scoring, frozen tokenization/parameters, train/dev-only fit statistics, same-org retrieval, and valid evidence citations.
5. B2 emits schema-valid structured output, citations, abstentions and explicit failures; prompt injection in evidence is treated as data.
6. B3 combines majority pair decisions and median valid priority scores, preserves each run, and demonstrates total-budget matching.
7. Offline stub is deterministic and clearly not empirical LLM performance.
8. Synthetic regression tests cover leakage sentinels, cross-org isolation, empty evidence, ties, malformed output, timeout/failure and reproducibility.
9. Real-data methods refuse to run while current Phase 1/2 gates are open.
10. No real-data metrics, correlations, rankings, or test analysis are produced prematurely.
11. Run manifests capture code/config/input/prompt hashes, environment, versions, seeds, runtime, failures and resource use.
12. Phase record accurately distinguishes implemented synthetic plumbing from real-data research results.

## 13. What must be resolved before empirical baseline results

- Approve specific evidence fields with point-in-time provenance and privacy treatment; current feature view is empty.
- Explain the 70,702 conflicting alert memberships before B0/B1 correlation or joint claims.
- Obtain authoritative documentation for QueueRank direction, meaning, query universe and complete expert top-20 status before priority evaluation.
- Find a documented detector severity field/crosswalk for B0 or approve a protocol amendment.
- Confirm source release/license and data-use conditions before any live model provider receives data.
- Freeze splits, candidate universe, token budgets, metrics and model/prompt versions before opening held-out test results.

Stage 3 can produce reproducible baseline code and synthetic demonstrations. It cannot yet produce valid research comparisons on the current real dataset.
