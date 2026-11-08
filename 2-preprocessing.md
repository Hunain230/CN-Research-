# Phase 2 — Preprocessing, leakage control, and alert-pair preparation

Status: Codex implementation specification based on the completed Phase 1 findings in Phase1.md and the protocol in PROJECT_CONTEXT.md. This stage permits leakage-safe prioritization preprocessing development. Correlation and joint evaluation remain blocked while conflicting alert membership and label semantics remain unresolved.

## 1. Objective and scope

Create reproducible, traceable derived data from the read-only GUIDE evidence and queue ranking files. Preserve source-row lineage, keep evaluator labels isolated, prepare eligible evidence representations, preserve ambiguous mappings, and prepare a deterministic provisional organization split.

Do not train models, run baselines, rank incidents, compute research metrics, or claim task validity. Do not create final correlation gold pairs, final evaluation-ready alert pairs, or ranking evaluation outputs. Candidate-generation plumbing may be developed for investigation only after evidence fields are approved; all outputs must be marked provisional.

## 2. Phase 1 baseline to preserve

Inputs and hashes recorded by Phase 1:

- data/raw/GUIDE_Test.csv: 4,147,992 rows; SHA-256 fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3
- data/raw/GUIDE_Test_Queue_Rankings.csv: 9,980 rows; SHA-256 e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6

Findings:
- 303,220 composite (OrgId, IncidentId) keys; 637,320 composite (OrgId, AlertId) keys.
- Id has no missing rows but is not unique at CSV row grain: 291,595 duplicated values and 3,844,772 rows beyond first occurrence. Its meaning is unverified; never treat Id as a unique source-row or citation key.
- 623,841 alert-key groups span multiple evidence rows; 70,702 composite alert-key groups have conflicting incident assignments. Preserve all conflicting assignments; do not choose first, last, majority, or arbitrary incident.
- All 9,980 ranking keys matched a GUIDE incident on the composite key; 293,240 GUIDE incidents are unlabeled. Unlabeled does not mean negative.
- 499 organizations met the implemented numeric criteria (at least 50 incidents, at least 10 detectors, and 20 observed rank values). This does not prove complete expert top-20 labels.
- QueueRank had no observed nulls, duplicate composite keys, conversion errors, ties, or gaps; numbering restarted at 1 within organizations. Its meaning, direction, query universe, and completeness are unverified.
- All fields remain denied or pending review. No model-visible allowlist exists.
- Correlation and joint evaluation are no-go; ranking evaluation is blocked until authoritative label semantics are confirmed.

Re-read current audit files before running. If input hashes or counts differ, stop and report the change. Never overwrite raw data.

## 3. Protocol authority

Use PROJECT_CONTEXT.md and FINAL (1) (1).pdf for the project-specific protocol; use Phase 03 - Implementation (1).pdf for course deliverables. If the actual data conflicts with assumptions in the PDFs, report the discrepancy and propose an explicit amendment. Do not silently change the study design.

Phase 2 target split: 10 pilot, 10 development, and 30 final-test organizations selected by a published deterministic hash of OrgId, not outcomes. Require at least 50 eligible organizations; keep all alerts for selected orgs. If eligibility or label requirements fail, stop and propose an amendment rather than changing counts.

## 4. Data boundaries and storage

Implement three logically and physically separated data domains.

### 4.1 Restricted evidence ledger
One record per parsed source CSV row. Assign stable source_row_ordinal based on physical data-row order. Preserve original source fields in restricted storage; record raw file hash and parser version. Keep Id as opaque source content and preserve its duplicate statistics. Do not use Id as row identity or citation ID.

Retain original and normalized values separately, plus normalization version, parse status, source row, and field provenance. Avoid printing raw IPs, URLs, account/device identifiers, hashes, or entity values in reports or logs.

### 4.2 Model-visible feature view
Only fields explicitly approved in a version-controlled allowlist may be exported. Phase 1 has no approved fields, so an empty or schema-only feature view is valid until provenance and sensitivity review is complete.

Do not include IncidentId, QueueRank, IncidentGrade, ActionGrouped, ActionGranular, any aliases or derivatives, label-derived group IDs, rank percentiles, label presence indicators, or outcome-derived signals. OrgId and AlertId are control-plane keys, not semantic features. Source row ordinals and Id are lineage only, not model features.

Use opaque technical keys where needed. A plain hash of low-entropy identifiers is not anonymization; use a keyed mapping if stable pseudonyms are required and keep the key outside model-visible data.

### 4.3 Evaluator-only store
Keep labels in separate files, schemas, reader modules, and access paths. Store composite incident labels, queue ranks, outcomes, and membership adjudication data only here. For each alert key, store mapping status as unambiguous, ambiguous, missing, or invalid. The ambiguous table must retain all incident assignments and supporting source_row_ordinals. Model code must not import or read evaluator data.

## 5. Preprocessing steps

### 5.1 Input verification and bounded processing
- Read Stage 1 schema and verify exact input headers and row counts.
- Verify SHA-256 before and after; fail if the raw files changed.
- Stream GUIDE with bounded memory; never load the full CSV by default.
- Preserve IDs as strings; do not coerce numeric-looking IDs.
- Record malformed rows and parse failures with row ordinal and reason; quarantine rather than silently dropping.
- Record source release, license, and download date only when evidence exists; otherwise keep them explicitly unknown.

### 5.2 Row identity, duplicates, and lineage
- Generate source_row_ordinal for every successfully parsed data row.
- Do not deduplicate by Id or AlertId.
- Detect exact duplicate full rows with a deterministic digest over canonical raw fields. Report exact duplicate groups separately from repeated alert keys and ambiguous mappings.
- If exact duplicate removal is used for downstream work, retain a no-dedup view and full lineage to every source row. Document whether the Phase 2 methodology's exact-row dedup rule changed counts.
- Do not remove rows with missing or unstable keys silently; preserve them in quarantine/unknown-key outputs.
- An alert-level evidence ledger may be aggregated only after defining how evidence rows map to alerts. Preserve row counts and per-field source references.

### 5.3 Key and membership handling
- All joins, partitions, entity comparisons, and candidate construction are organization-scoped.
- Incident key is the composite (OrgId, IncidentId), evaluator-only.
- Alert key is the composite (OrgId, AlertId), technical control key.
- For each alert key, enumerate distinct incident assignments and count provenance rows.
- If one key maps to multiple incidents, preserve each mapping and mark ambiguous. No arbitrary resolution, deduplication, or target assignment is allowed.
- Retain all ambiguous rows for investigation; do not use them as pair positives or negatives.
- Do not use IncidentId in candidate generation, feature aggregation, cache keys, prompts, or model-visible grouping.
- Preserve cross-organization reuse of IncidentId as separate composite keys.

### 5.4 Normalization and missing data
- Parse Timestamp with explicit formats and retain original text plus normalized UTC value and parse status. Assume UTC for timezone-naive values only if authoritative documentation supports that assumption; otherwise mark timezone unknown and block time-window pairing.
- Normalize IPs with a standard parser. Normalize hostnames, URLs, account identifiers, and ATT&CK technique IDs only using explicit typed, versioned rules. Retain source values in restricted storage.
- Do not lowercase, strip, or canonicalize untyped values without justification.
- Missing values remain null, optionally with explicit missingness flags. Never replace missing entities with a shared token such as unknown, which could produce false matches.
- Sort deterministically by OrgId, parsed UTC timestamp (nulls last), technical alert key, then source_row_ordinal.
- Exclude fields with unknown point-in-time availability. In particular, keep IncidentGrade, actions, LastVerdict, SuspicionLevel, Usage, ThreatFamily and other verdict-like fields denied absent evidence they existed before triage.

### 5.5 Field policy and leakage audit
Maintain a version-controlled field policy containing source field, transformation, purpose, source/timing evidence, sensitivity, destination, rationale, and approval state. Default is deny.

Always evaluator-only: IncidentId, QueueRank, IncidentGrade, ActionGrouped, ActionGranular and every derivative. Lineage/control only: Id, OrgId, AlertId, source_row_ordinal. Timestamp, DetectorId, AlertTitle, Category, MitreTechniques, entity/evidence fields and all other columns remain denied until provenance, privacy, and decision-time availability are documented.

Before every model-visible export, assert:
1. prohibited fields and aliases are absent by column name and data lineage;
2. no values originated in evaluator tables;
3. no label-derived field or label-presence signal is present;
4. every included evidence field is allowlisted and point-in-time approved;
5. rows and referenced evidence remain organization-scoped.

Write a lineage-based leakage audit. Use synthetic sentinel labels in fixtures and assert they never appear in feature outputs, prompts, retrieval material, or logs. Do not merely rely on column-name scans.

## 6. Provisional organization split

- Recompute eligible organizations from distinct GUIDE incidents and detectors; validate the Phase 1 count of 499.
- Use a deterministic, documented hash of a versioned salt plus canonical OrgId. Specify canonicalization, hash algorithm, version/salt, sort, and tie behavior.
- Select 50 qualifying organizations in hash order: first 10 pilot, next 10 development, next 30 test. Do not use labels or model performance to select organizations.
- Write a restricted manifest with IDs and assignments; publish only permitted hashes and aggregate counts.
- Assert no organization overlaps partitions and every row from a selected organization inherits the same partition.
- Mark assignments provisional until rank scope/completeness are verified. Do not inspect or use test labels to make preprocessing decisions. Fit any learned vocabularies, retrieval indexes, calibration, or thresholds on pilot/development only.
- Preserve all incident alerts for selected orgs.
- If fewer than 50 qualify or ranking-label requirements fail, stop and propose a documented protocol amendment; do not silently alter ratios.

The provisional split is for partition discipline, not permission to evaluate rankings.

## 7. Candidate-pair preparation boundary

The methodology's proposed candidate rules are:
- same organization only;
- shared approved entity within 48 hours OR matching approved ATT&CK technique within one hour;
- at most 20 nearest candidates per alert;
- ties resolved by alert ID.

These rules cannot be finalized until field provenance, time semantics, and alert mapping ambiguity are resolved. Until then:
- implement only interfaces/synthetic plumbing, or generate clearly marked investigation-only proposals from approved evidence;
- never assign pair labels where either membership is ambiguous;
- do not create final correlation training/evaluation pairs or report pair metrics;
- do not give candidate generation IncidentId or any ranking/outcome label;
- exclude null/generic entity values; record which evidence IDs and rule produced each proposal;
- canonicalize undirected pair keys and deterministically order/cap candidate lists;
- report candidate counts, truncation and ceiling only after valid truth and approved fields exist.

Unlabeled ranking incidents are not negatives. The queue-ranking table must not influence candidate generation.

## 8. Prioritization preprocessing boundary

Prepare only future-ready, evaluator-free evidence schemas. Do not train, calibrate, score or evaluate priority in Stage 2. Keep queue labels isolated. Preserve all GUIDE incidents, including unlabeled ones, and do not leak label presence via record selection, filenames, candidate counts, prompts, or logs. Do not treat missing QueueRank as irrelevance.

Any feature view used later must be generated without IncidentId-based grouping. Incident-centered records in this phase may exist in the evaluator/control domain only; do not represent them as model-predicted incidents.

## 9. Required deliverables

Write derived artifacts under data/derived/preprocessing/ (ignored by Git):
- evidence_ledger.csv or SQLite table: row-level restricted records, lineage and parse status.
- feature_view.csv or schema-only equivalent: approved model-visible fields only.
- evaluator/incident_membership.csv: composite membership labels and mapping status, isolated.
- evaluator/queue_labels.csv: composite rank labels, isolated.
- review/ambiguous_alert_memberships.csv: every conflicting key, candidate incidents and provenance row ordinals.
- review/exact_duplicate_groups.csv: exact-row duplicate groups and source lineage.
- quarantine/invalid_rows.csv or aggregate-safe equivalent with reasons and row ordinals.
- split_manifest.json: provisional 10/10/30 assignment, eligibility counts, algorithm version, seed/salt version and digest.
- preprocessing.json and preprocessing_report.md: row counts, transformations, exclusions, ambiguity, split status and blockers.
- leakage_audit.json and leakage_audit.md: field lineage, checks, pass/fail and sentinel results.
- run_manifest.json: input/output/config hashes, code revision, Python/platform/dependency versions, command, seed, parser/normalizer versions and UTC time.

Use standard-library CSV/SQLite if sufficient. If adding Parquet or other packages, justify and pin exact dependencies. Never commit raw data, secrets, or raw entity values in reports.

## 10. Reproducibility rules

- Run through the project .venv; record Python version (Phase 1 used 3.12.10).
- Seed 0 for deterministic sampling; split assignment uses the documented hash algorithm, not random selection.
- UTF-8 with BOM support for input and UTF-8 output.
- Stable sorting and deterministic serialization.
- No network enrichment or model calls.
- Hash inputs before and after and fail if changed.
- Record code/config hashes. Never silently overwrite a previous run; use a unique run directory or explicit overwrite option.
- Repeated runs with identical bytes/config/code/environment must yield identical logical outputs, split assignments and derived hashes. Manifest timestamps may differ.
- Keep test organizations sealed from tuning, fitting, inspection of label-dependent results, and preprocessing decisions.

## 11. CLI contract

Add a project-consistent subcommand without changing Stage 1 validation behavior:

```powershell
.\.venv\Scripts\python.exe -m src.cli preprocess --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --audit data/derived/audit --config configs/preprocessing.yaml --out data/derived/preprocessing --seed 0
```

Also provide:
```powershell
.\.venv\Scripts\python.exe -m src.cli check-leakage --features data/derived/preprocessing/feature_view.csv --policy configs/field_policy.yaml --audit data/derived/preprocessing/leakage_audit.json
.\.venv\Scripts\python.exe -m src.cli check-splits --manifest data/derived/preprocessing/split_manifest.json --expected 10,10,30
.\.venv\Scripts\python.exe -m src.cli inspect-ambiguity --input data/derived/preprocessing/review/ambiguous_alert_memberships.csv --out data/derived/preprocessing/review/ambiguity_summary.md
```

A completed audit with unresolved scientific blockers should report the blocker distinctly from technical failure. Missing inputs, changed hashes, corrupt parse, failed assertions, or output write errors are technical failures.

## 12. Synthetic regression coverage

Fixtures must assert expected values, not merely generate files. Include:
- missing and repeated Id; verify Id is not used as row identity;
- exact duplicate rows vs repeated evidence rows;
- one AlertId across multiple evidence rows with same incident;
- one composite alert key with conflicting IncidentIds;
- same IncidentId reused across organizations;
- missing AlertId/IncidentId and invalid/naive timestamps;
- duplicate/null/tied/gapped queue ranks;
- incomplete top-20 labels;
- labels and sentinel strings never leaking to feature output;
- split disjointness and deterministic hash assignment.

Each test should check the expected output status/counts and prove ambiguous mappings are preserved. Retain the tiny fixture and its expected assertions in the repository.

## 13. Acceptance criteria

Phase 2 is accepted only when:
1. Phase 1 input hashes match and raw files remain unchanged.
2. Every parsed row has stable source_row_ordinal; Id is never treated as unique.
3. Exact duplicate rows, repeated evidence rows, and conflicting alert mappings are separately characterized.
4. All ambiguous mappings and source provenance are preserved with no arbitrary assignment.
5. Evaluator labels are isolated by storage, schema and code boundary; leakage assertions pass.
6. No unapproved or temporally unverified field is exported; empty feature view is acceptable.
7. Normalization is typed, versioned, null-safe and traceable.
8. Organization split is deterministic, disjoint, complete for selected organizations, and marked provisional as needed.
9. Test labels do not influence fitting or preprocessing decisions.
10. No final pair labels, correlation metrics, ranking evaluation or model results are produced while Stage 1 gates remain open.
11. Synthetic tests assert edge-case outcomes and sentinel leakage checks.
12. Reports avoid raw entity values and distinguish technical completion from research readiness.

## 14. Phase 2 completion report

Summarize exact command, input/config/code hashes, environment, outputs and row counts; unchanged raw hashes; duplicate and ambiguity handling; field allowlist and leakage results; split algorithm/counts/overlap and provisional status; fixture assertions; and what remains blocked.

Completion means preprocessing infrastructure is reproducible and data boundaries are sound. It does not clear correlation truth, ranking-label validity, or research evaluation.