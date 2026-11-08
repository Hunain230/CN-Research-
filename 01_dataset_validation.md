# Stage 1 — Dataset validation (Codex implementation specification)

## Purpose and gate
Verify that GUIDE evidence and AIP expert queue labels support the offline organization-held-out study before modeling. Produce separate go/no-go decisions for alert correlation, incident prioritization, and joint evaluation. Stop if keys, label scope, split feasibility, or leakage remain unresolved.

The PDFs are project methodology/course instructions; the observed CSV schemas below are facts from the user’s project thread. If actual files differ, report the mismatch and amend protocol before experiments.

## Confirmed context and observed data
Project: retrospective, offline comparison of evidence-grounded correlation and incident ranking; no autonomous response. Phase 2 proposes GUIDE incident IDs as retrospective grouping truth and AIP top-20 expert ranks as priority truth. Models must not see those labels.

The user observed GUIDE_Test.csv columns: Id, OrgId, IncidentId, AlertId, Timestamp, DetectorId, AlertTitle, Category, MitreTechniques, IncidentGrade, ActionGrouped, ActionGranular, EntityType, EvidenceRole, DeviceId, Sha256, IpAddress, Url, AccountSid, AccountUpn, AccountObjectId, AccountName, DeviceName, NetworkMessageId, EmailClusterId, RegistryKey, RegistryValueName, RegistryValueData, ApplicationId, ApplicationName, OAuthApplicationId, ThreatFamily, FileName, FolderPath, ResourceIdName, ResourceType, Roles, OSFamily, OSVersion, AntispamDirection, SuspicionLevel, LastVerdict, CountryCode, State, City, Usage.

Queue file observed columns: OrgId, IncidentId, QueueRank; 9,980 rows reported. QueueRank is the actual rank field; no Split column was observed. Join only on composite (OrgId, IncidentId). Do not assume one CSV row equals one alert.

Phase 2 specifies eligibility of >=50 incident IDs, >=10 detector IDs, complete expert top-20 labels; 10 pilot / 10 development / 30 final-test organizations selected by published hash of OrgId, not outcomes. If fewer than 50 qualified organizations survive, revise before viewing test results. These are protocol requirements to validate, not facts about the downloaded data.

## Inputs and outputs
Inputs, read-only: data/raw/GUIDE_Test.csv and data/raw/GUIDE_Test_Queue_Rankings.csv. Record source/release, license, download date, SHA-256, bytes, and exact rows.

Write:
- data/derived/audit/validation.json (checks/counts/status)
- data/derived/audit/validation.md (findings, limitations, task go/no-go)
- data/derived/audit/schema.json (headers and inferred types)
- data/derived/audit/field_disposition.csv (column, null rate, cardinality summary, allow decision, rationale)
- data/derived/audit/join_summary.csv (aggregate org-level coverage; no raw identifiers in public report)
- data/derived/audit/run_manifest.json (input/config hashes, versions, command, timestamp)

Never print actual account identifiers, IPs, URLs, hashes, device names, or entity values in logs/reports.

## Required checks

### A. File integrity and schema
- Confirm paths, nonzero size, full parse, exact headers, duplicate column names, inferred/explicit dtypes, malformed rows, nulls, row counts and SHA-256.
- Stream GUIDE in bounded chunks; default 250,000 rows. Do not load its reported 1.09 GB wholly into memory.
- Compare headers against the observed lists; fail for missing required fields, report additional fields.
- Preserve identifier equality exactly; assess mixed types, whitespace, leading zeros and precision risk. No silent lossy casts.

### B. Grain, keys, and time
Measure: total evidence rows; null/duplicate Id; unique organizations; distinct (OrgId, IncidentId); distinct (OrgId, AlertId) and global AlertId; duplicate/null alert keys; evidence rows per alert; alerts per incident (min/median/p90/max); singleton/multi-alert incidents; AlertId appearing across orgs/incidents; incidents spanning AlertIds. Report Timestamp parse success, UTC min/max, invalid count. For all fields report non-null rates and cardinality counts only, never entity values. Resolve collisions before preprocessing.

### C. Rank-label integrity
For QueueRank report null keys/values, integer conversion errors, duplicate composite keys, ties, observed min/max, gaps, whether numbering restarts by organization, labels per organization, orgs with exactly 20 labels. Verify rank scope and meaning from the source: does rank 1 mean highest priority, are ranks 1–20 the expert top-20, and is the list complete? Do not treat absent incidents as negative judgments absent explicit complete-universe evidence.

### D. Join correctness
- Build distinct GUIDE incident keys before joining; never join labels to repeated evidence rows for coverage.
- Join on both OrgId and IncidentId. Compute IncidentId-only matching as a diagnostic only, never for labels.
- Count matched/unmatched ranking keys and GUIDE incidents, before/after row counts, duplicate label keys, per-org coverage. Assert one label per composite key unless documented otherwise.
- Determine qualifying orgs using Phase 2 criteria: >=50 GUIDE incidents, >=10 detectors, complete top-20 labels. Verify whether at least 50 qualify.
- Retain all alerts of selected organizations.
- Verify joins do not replicate labels according to evidence-row multiplicity.

### E. Evidence and leakage disposition
Classify every column as key/lineage, candidate evidence, label/outcome, potentially post-event, sensitive, temporal availability unknown, prohibited, or requiring source confirmation. Default deny model access until allowlisted.

Explicitly exclude IncidentId, QueueRank, IncidentGrade, ActionGrouped, ActionGranular and all derived rank/outcome signals from every feature, prompt, retrieval corpus, candidate filter, cache key and calibration input. Id is a lineage key and excluded from inference unless proven safe. Review Timestamp, DetectorId, AlertTitle, Category, MITRE and entity columns for point-in-time availability. Scrutinize SuspicionLevel, LastVerdict, ThreatFamily, Usage and verdict/action-like fields. Give each decision a reason.

### F. Correlation truth and candidate feasibility
Build membership truth only in evaluation boundary using composite incident identity. Confirm each distinct (OrgId, AlertId) has unambiguous IncidentId after repeated evidence rows are handled. Count eligible positive/negative pairs within org. A positive pair shares verified composite incident key; never expose this key or membership to the agent.

Assess Phase 2 candidate rules: shared entity within 48 hours OR matching ATT&CK technique within one hour; at most 20 nearest candidates per alert, ties by alert ID. Measure candidate-generation recall ceiling only. If alert membership is ambiguous, mark correlation no-go. Retrospective labels do not prove online discovery.

### G. Organization split feasibility
Validate protocol before creating model artifacts: count qualified orgs; determine if the 10/10/30 split is feasible. Select via published hash of OrgId, not outcomes; keep every alert for selected orgs. No organization crosses partitions. Record assignments and digest in restricted manifest; publish IDs/hashes only where license permits. If fewer than 50 eligible orgs or incomplete labels prevent target split, report counts and require protocol amendment before training or test inspection. Do not silently change split sizes.

### H. Reproducibility and privacy
Use bounded-memory deterministic processing, stable sort, UTC, explicit dtypes, fixed encoding/locale, pinned dependencies. Hash inputs/config; record command, software versions, seed and timestamp. No enrichment or model calls in Stage 1. Scan schemas and lineage for forbidden labels. Keep label store separate from feature store.

## Acceptance criteria
Pass only when required schemas parse and counts/hashes are recorded; grain and key collisions are characterized; rank scope/completeness is verified or explicitly blocked; composite join coverage is quantified without row multiplication; field allowlist and leakage audit are documented; correlation truth and candidate ceiling are assessed; qualified-org count and split feasibility are established before test analysis; and separate task go/no-go decisions cite evidence and unresolved questions.

### Current handoff clarification (2026-11-08)
The GUIDE row identifier `Id` must have explicit missing-row and duplicate-value counts; its cardinality estimate is not a uniqueness check. Distinguish repeated evidence-row groups for a composite `(OrgId, AlertId)` (which may be expected at evidence-row grain) from keys with conflicting incident assignments. Conflicting mappings keep correlation and joint evaluation at no-go.

Stage 2 may start as leakage-safe preprocessing development for prioritization, with evaluator labels stored separately and ambiguous alert mappings preserved for investigation. Do not produce final evaluation-ready alert pairs or ranking evaluation results until the Stage 1 key/mapping issues and rank scope/top-20 completeness questions are resolved.

## Command contract
```powershell
python -m src.cli validate --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --out data/derived/audit --chunk-rows 250000 --config configs/validation.yaml
```
Exit 0 when the audit completes even if scientific feasibility is blocked. Nonzero for execution/integrity failures (missing file, corrupt parse, required schema absent, output write error). Distinguish technical failure from scientific no-go. Re-running with same inputs/config must produce identical counts and stable findings.

## Suggested implementation units
Schema/config; streaming readers/hash; GUIDE profiler; queue profiler; composite join audit; field disposition/leakage scanner; pair/candidate feasibility; org qualification; JSON/Markdown reporting. Include fixtures for duplicate evidence, cross-org IncidentId collision, duplicate labels, missing ranks, rank ties/gaps, invalid timestamps, ambiguous alert membership and incomplete top-20 lists.
