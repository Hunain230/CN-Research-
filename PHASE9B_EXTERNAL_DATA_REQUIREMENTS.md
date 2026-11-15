# Phase 9B external evidence export request

**Purpose:** Obtain an authorized, point-in-time SOC export for alert correlation, incident prioritization, and independent evaluation. This document is a request and acceptance specification. It does not assert that any requested data or permission has been supplied. Do not place an unreviewed export in the repository.

## Requested delivery

Provide a documented schema and separate, access-controlled tables or files at these grains:

| Dataset | Required grain and key | Required content |
|---|---|---|
| `alerts` | One row per `(organization_id, alert_id)` | Stable alert ID, source product, generating detector/rule and version, alert creation and queue-entry times, alert revisions, and permitted alert descriptors. |
| `observations` | One row per `(organization_id, observation_id)` | Original telemetry record ID, source product and telemetry stream, event occurrence and ingestion times, immutable source reference, duplicate/correlation key if one exists, and record revision metadata. |
| `alert_observations` | One row per alert–observation attachment or revision | Both keys, evidence attachment/first availability time, removal/replacement time if applicable, extraction method/version, entity IDs and types, technique/category/role assignments, missingness and confidence where recorded. Preserve repeated attachments and changes rather than collapsing them into a final snapshot. |
| `observation_lineage` | One row per child–parent source relationship | Upstream observation/reference, relationship type (derived from, duplicate of, common source, enrichment of, etc.), derivation method/version, and effective time. Record unknown lineage explicitly. |
| `incident_labels` | One row per expert alert-to-incident assignment and revision | Organization, alert, expert incident membership, label creation/revision time, adjudicator or process provenance, adjudication status, ambiguity/conflict flag, and permitted research use. Keep this file outside inference access. |
| `queue_rankings` | One row per expert-ranked incident in a defined queue snapshot | Organization, queue snapshot/cutoff ID and time, incident ID, priority/rank, rank direction, eligibility/query-universe rule, label provenance, adjudication status, and completeness of the top-20 judgment set. Keep this file outside inference access. |
| `cohort_manifest` | One row per organization/snapshot | Development, selection/validation, or sealed confirmation assignment; prior training/selection/evaluation exposure; label-access history; alert/evidence counts; coverage dates; source/export hashes; and split authority. |
| `authorization_record` | One record per permission scope | Data owner, approval date and version, research purpose, allowed cohorts, approved inference fields, processing location, retention/deletion terms, privacy restrictions, permitted model/provider use, and whether point-in-time reconstruction is approved. |
| `export_manifest` | One immutable record per delivered file | File path/name, schema name and version, row count, byte size, SHA-256 hash, export timestamp, source-system snapshot identifier, exporter identity, and manifest version. Publish a manifest hash after all entries are finalized; any corrected delivery needs a new version. |
| `label_access_audit` | One append-only record per access to development or confirmation labels | Actor/service identity, cohort and file, access time, purpose, operation, approval reference, whether any data was exported, and destination if exported. Include denied attempts and subsequent access after prediction freeze. |

If the source cannot supply a field, mark it **unavailable with a reason**. Do not synthesize observation IDs, attachment times, source independence, or expert labels from existing GUIDE rows.

## Field and timestamp semantics to document

For each field in `alerts` and `alert_observations`—entity identifiers/types, ATT&CK techniques, categories, detector information, and evidence roles—identify the source system, whether the value is directly observed or inferred, extraction method and version, first availability time, subsequent revisions, null/missing codes, and reliability limits. Provide detector rule name/version and clarify whether multiple detectors may consume the same upstream telemetry.

Distinguish **event occurrence**, **telemetry ingestion**, **alert creation**, **evidence attachment/availability**, **queue entry or analyst-decision cutoff**, and **revision/enrichment** times. State time zone, clock source, known delays/noise, precision, and whether the export preserves historical values or only final values. A field counts as available for a decision only when its source observation and the field value existed at or before that decision cutoff. Missing availability time means the field cannot support an automatic point-in-time merge.

The export must preserve alert-to-observation-to-upstream-source links. Two CSV rows, alert IDs, entity keys, or detector IDs are not independent evidence merely because their identifiers differ. Independence requires a defensible trace to distinct underlying observations and a documented rule for shared-source or duplicate events.

## Cohort and access requirements

1. Identify which historical organizations, if any, are approved for further exploratory training. Document prior use of the 334 train, 67 validation, 68 holdout, 135 outside-fitting, 42 small-validation, and older 30 test queues. The 42 are already exposed and cannot be relabeled as independent.
2. Supply a **separate authorized development/selection cohort** whose labels can legitimately determine Phase 9D parameters. State whether any organization, alert, source observation, incident, or queue snapshot overlaps historical data. Document duplicate and shared-source relationships across cohorts.
3. Supply a **new sealed confirmation cohort** with separate organization-level labels and expert rankings. Before the method is frozen, allow only a label-free schema/quality check by the implementation team. Restrict confirmation labels and rankings to the isolated evaluator and record every access.
4. Keep `IncidentId`, membership, expert rank, grade, outcome, and adjudication findings out of inference tables, prompts, features, boundary proposals, and merge decisions. Historical membership may be used only for expressly authorized fitting; confirmation labels only after prediction freeze.
5. Include ambiguous alert-to-incident assignments with their adjudication status. Request an authoritative rule; do not resolve them by copying evaluator labels into inference.
6. Deny confirmation-label and ranking access to the implementation environment until the selected method, configuration, prompts, evaluator definition, and prediction freeze are recorded. Maintain an append-only audit of who accessed either development or confirmation labels, when, why, and whether any copy or export occurred. A file permission setting alone is not sufficient without an access record.

## Minimum acceptance checks before Phase 9C

- Every alert and evidence attachment has stable organization-scoped keys; referential integrity and duplicate semantics are documented.
- Source observations and upstream dependencies can be traced, or the affected evidence is explicitly barred from automatic independent-support claims.
- Event, ingestion, attachment, queue-entry, and revision times have documented meanings; a historical feature view can be reconstructed at each prediction cutoff without later evidence.
- Every field has a documented inference eligibility and processing/retention decision. Experimental-only fields remain separate from production-approved fields.
- Expert membership and ranking provenance, ambiguity handling, rank direction, and queue snapshot are documented.
- Development and confirmation organizations/snapshots are separated with exposure history. Confirmation labels are sealed and inaccessible until the method and evaluation protocol are frozen.
- Export files, schemas, authorization record, and cohort manifests have cryptographic hashes and version identifiers.
- The immutable export manifest lists **every** delivered file with schema version, row count, SHA-256, export timestamp, and source-system snapshot ID; its own final hash is recorded.
- Development-label access is audited. Confirmation-label access is technically denied to implementation until prediction freeze, and all later evaluator access is audited, including data exports.

## Explicit Phase 9C rejection criteria

Reject the delivery for Phase 9C if any of the following remains unresolved:

1. Critical source-observation provenance or evidence-availability timing is absent **without a documented exclusion that removes the affected evidence from automatic merging**. A CSV row ordinal or alert creation time does not fill either gap.
2. Development and confirmation cohort overlap, duplicate/shared-source relationships, or prior label exposure cannot be resolved. An exposed cohort cannot be made untouched by renaming its split.
3. The authorization record does not cover the intended research use, processing location, field use, retention, or label access.
4. Confirmation labels are reachable by the implementation environment before prediction freeze, or label access/export events cannot be audited.
5. The manifest is incomplete, mutable without versioning, or its recorded hashes, row counts, schema versions, or source snapshot identifiers fail verification.

Receipt of files alone does **not** clear Phase 9B. Record a reviewed pass/fail decision for every acceptance check before Phase 9C preparation.

**Current gate:** `PHASE9B_EVIDENCE_AND_DATA_READINESS.md` remains **BLOCKED**. The existing GUIDE projection and preprocessing ledger do not provide source-observation independence or evidence-arrival time; the historical 42-queue subset is exposed; no new confirmation cohort is in the workspace. Phase 9C data preparation begins only after the requested export, authorization, and access controls have been reviewed against these checks.
