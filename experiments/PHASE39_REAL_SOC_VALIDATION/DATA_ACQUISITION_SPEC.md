# Request for an authorized, evaluation-ready SOC export

**Purpose:** test the unchanged Phase 33 endpoint-fallback +1 method against a matched frozen real-data baseline. A public research license or raw log dump alone is insufficient. Request the smallest de-identified, locally processable export that preserves original observation lineage and independent labels. No real organizational data should be placed in this repository before the owner approves location, privacy controls and retention.

## Required package

| File or table | Minimum contents |
|---|---|
| `authorization_record` | Named data owner, approval date/version, research purpose, allowed cohorts/fields, local/cloud/model-provider scope, privacy transformations, retention/deletion, access-control contacts and permitted publication of aggregates. |
| `queue_snapshots` | Organization and queue pseudonyms, immutable decision timestamp, active alert universe, all eligible incident identifiers, ranking task definition, timezone, and any queue-entry delay. |
| `alerts` | Stable alert ID, source product/detector/rule version, alert category and severity at decision time, asset criticality if available, host/account references, original event IDs, alert creation/ingestion/evidence-available times, and revisions. Mark unknown fields explicitly. |
| `source_observations` | Original endpoint process/parent-child records, identity-provider authentication/session records, network-flow records, observation ID, source system and upstream controller/trust domain, event/observed/ingested/available times, source quality flags, and the exact alert/relationship each record supports. |
| `derivation_and_contradictions` | Copy/derived-from links, repeated observations, common upstream roots, clock corrections, missing feeds, contradictions and sensor outage windows. Do not describe two records as independent solely because their IDs differ. |
| `adjudication_private` | Independent alert-to-incident membership, analyst versus automated provenance, uncertainty/disagreements, reviewer/adjudicator IDs or pseudonyms, label time and version, incident priority ranks and their scope. Keep physically separate from model inputs. |
| `manifest` | Schema version, row counts, file hashes, export query, collection period, original system/source snapshot, transformation log, deterministic pseudonymization rules, and train/development/external-evaluation assignment with label-exposure audit. |

## Acceptance checks before any prediction

1. Confirm authorization covers this exact model, cohort, field use, processing site, retention and label access. Obtain privacy/security review for sensitive IDs.
2. Resolve alert-to-incident conflicts or mark them uncertain under a frozen rule. Independently verify membership and priority judgments; define eligible queues and denominators before inference.
3. Prove original observation identity, derivation graph, upstream trust-domain mapping and field-level availability at each decision time. Preserve missing/delayed evidence and abstain where proof is insufficient.
4. Verify that a deterministic adapter can populate the **actual** Phase 31/32 receiver-visible schema without inventing causal IDs, roots, severity or timing, and without accessing private labels. Hash its code/configuration and test it on a separate permitted development set.
5. Check the original evaluator's assumptions: 25 ranked incidents per queue, complete eligible-alert membership, same cutoff and grouping limits. If a real workflow differs, perform a separate equivalence review before reporting an official comparable metric.
6. Freeze the cohort, adapter, baseline, candidate and predictions before evaluator access. Audit label exposure; previously inspected organizations cannot serve as untouched confirmation.
7. Predeclare uncertainty handling, queue/incident category strata, confidence-interval method and sample-size adequacy criterion. Preserve all exclusions and disagreements in the denominator/accounting record.

If a partner can provide only GUIDE-style alert/entity rows, that export can support a separate exploratory triage study, **not** the frozen Phase 33 provenance-based reconstruction claim. No automatic incident merge or response action is part of the requested study.
