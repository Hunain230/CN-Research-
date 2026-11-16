# Versioned ground-truth package contract

The companion JSON schema defines the exchange format. An authorized SOC export can be transformed into this package inside its approved environment; the controlled lab can emit it directly. Each package is immutable after sealing, has a content hash, and records provenance of the collector, clock, adjudicators, and transformation code. Raw content is retained in the approved storage domain; research exports use opaque IDs and hashes.

## Distinct record types

| Record | Identity and required meaning | Truth/feature role |
| --- | --- | --- |
| `observations` | Original `observation_id`, source system, source-native record reference, event time, collection time, payload hash. A file path or IP alone is insufficient. | Source lineage; approved fields may become inputs only with availability proof. |
| `alerts` | `alert_id`, detector and version, alert generation time, detector payload hash. Alerts remain separate from original observations. | Candidate C/P/V input after approval. |
| `derivations` | `alert_id` → one or more `observation_id` links, method, confidence class, and independent verification status. | Provenance; unverified links never count as resolved source truth. |
| `availability_events` | Artifact type/ID, event kind (`available`/`corrected`/`retracted`), UTC time from the receiving system, version, and content hash. | Append-only eligibility ledger, never inferred from event time. |
| `incidents` | Opaque incident ID, independent origin (`soc_adjudication` or `lab_oracle`), onset/end estimates, and truth status. | Evaluator-only. |
| `memberships` | Alert-to-incident link or explicit `none`, judgment (`positive`, `negative`, `ambiguous`), adjudicator provenance and decision time. | Evaluator-only; absence of a row is **unknown**, not negative. |
| `actions` | Lab controller action ID, run, incident, step, start/end, original source references; absent for SOC track unless independently documented. | Evaluator-only; a time window is never sufficient to label an alert. |
| `priority_judgments` | At a declared queue cutoff, expert rank and rationale for each independently judged incident. | Evaluator-only; never imported from model queue rank or detector severity. |
| `splits` | Unit assignment to development, validation, or sealed test by whole scenario/run and incident lineage. | Evaluation control; opaque split labels unavailable to inference. |

## Time rules

All times are ISO 8601 UTC with `Z`. `event_time` is when an action or source event occurred; `collected_at` is source receipt; `generated_at` is detector alert creation; `available_at` is when the receiving correlator could access a particular artifact/version. These are distinct clocks. Every clock must have recorded source, synchronization method, offset bound, and known uncertainty. Validated source and alert versions must have an `available` ledger event. A field is eligible at cutoff `t` only when its specific version has an `available_at ≤ t` and no prior retraction supersedes it. Corrections generate a new version; backdating is forbidden. Negative latency is flagged and investigated, not silently clamped.

## Identity and adjudication rules

Identifiers are globally unique after source-namespace scoping. Raw person, host, and IP values are stored only in the authorized enclave; exported IDs are stable within the study and pseudonymized with a managed key. One alert may derive from several source observations, and one observation may trigger several alerts. That is recorded explicitly. A `positive` membership must cite an independently observed source or documented adjudication; `negative` means an independent reviewer affirmatively ruled out incident membership. Ambiguous cases remain counted in coverage and abstention rates. Two reviewers adjudicate independently, with disagreements preserved and resolved by a third reviewer or marked ambiguous. Lab oracle traces are captured outside the detector and never derived from alert timestamps alone.

## Privacy and integrity

Authorization must specify data categories, minimization, retention, access roles, transfer method, and deletion date. Encrypt at rest and in transit, log every read/export, and keep reidentification keys outside the analysis workspace. Package manifest records source authorization reference, collection period, transformation commit, schema version, per-file SHA-256, and seal timestamp. Training/evaluation copies are generated from the sealed package; labels and expert priority stay in a separate evaluation-only store. An audit trail records every exclusion and correction.
