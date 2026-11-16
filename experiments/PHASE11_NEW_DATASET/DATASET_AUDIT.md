# Phase 11 dataset suitability audit

**Decision: unsuitable for independent incident-reconstruction evaluation; stop before download.** Audit date: 2026-11-16 (Asia/Karachi). Candidate: [WitFoo Precinct6 Cybersecurity Dataset](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity), published v2.1.0, current `main` commit `96311c2e29611d8ddbf1c0d59f531f6a362b8233` when inspected. No dataset file was downloaded. The [publisher's dataset card](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity) and [research page](https://www.witfoo.com/research/precinct-6-dataset/) are the primary sources for the field meanings and counts below; exact current commit and file metadata were read from the Hugging Face repository API.

## Stage 1: repository context

Phase 10 preserved C/P/V and tested mutual fragment matching, bounded hierarchical reconstruction, and a verification veto. None improved the frozen 69.83% group-recoverability ceiling safely. The best unchanged-group 75% child40 / 25% v7 blend reached 50.77% Incident Recall@20 and 63.88% P@10 on the previously exposed GUIDE_Test cohort. Phase 10's best verification variant fell to 69.53% recoverability and 89.66% grouped-pair precision. The official GUIDE field-policy allowlist remains empty. The Phase 11 directory did not contain a prior dataset download when this audit started. Local C: drive free space was about 55.8 GB; the machine has 16 GB RAM per the project brief.

## Stage 2: publisher and revision

The smaller repository reports 2,011,674 live signals from four organizations, 238,511 historical incident leads, 51,371 per-incident graphs, and a merged graph with 47,585 nodes and 1,740,438 edges. The live window is 2024-07-26 11:10:23 to 2024-08-01 06:00:03 UTC. Only 1,584 incidents have a matching lead in live rows; the other 49,797 have no matching live lead. The smaller subset includes every in-window malicious lead, all same-organization rows within ±5 minutes, and a seeded random fill, so it is incident-centered rather than a uniform prospective capture. Its files total approximately 8.41 GB; the 114-million-event repository is approximately 13.4 GB. The latter was **not** downloaded or processed. [Dataset card](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity), [publisher research page](https://www.witfoo.com/research/precinct-6-dataset/).

The declared license is Apache-2.0. Any redistribution or research report should retain its license/NOTICE conditions and attribute WitFoo, Inc., dataset version 2.1.0, and the repository URL. Version 1 was withdrawn after sanitization defects; v2.0.0 remains tagged, while the inspected `main` is v2.1.0. Reproduction must pin the exact commit above, not float on `main`. The dataset exposes configurations `signals`, `incident_signals`, `graph_nodes`, `graph_edges`, and `attack_reports`, each with a `train` split in the card. These are file access configurations, not defensible evaluation splits. [Dataset card](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity).

## Field availability and inference policy

“Safe for inference” means safe at a documented queue decision time. The card supplies some field meanings, but no field-level arrival/revision ledger. A raw event field marked *conditional* below would still require a prospective availability audit before use. “No” means directly label-derived or post-correlation. [Signal schema and graph description](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity).

| Field | Available | Meaning | Provenance | Safe for inference |
|---|---|---|---|---|
| `artifact_id` | Yes | Precinct artifact timeuuid; joins live/lead signal to graph edge | Precinct artifact record | Conditional; lineage key, not proof of distinct upstream observation |
| Original source-observation ID | Not established | Upstream product event identity distinct from Precinct artifact | Not documented in 38-column schema | No provenance-verification claim |
| `event_time` | Yes, nullable | Source product's reported event time | Source `starttimeutc` when available | Conditional; source clock and missingness require audit |
| `timestamp` on live `signals` | Yes | Precinct ingest/artifact timeuuid time | Precinct ingest | Conditional as queue cutoff proxy; not event time |
| `timestamp` on `incident_signals` | Yes | When Precinct correlation raised a lead, often hours/days after event | `lead.observed_at`, sometimes year-repaired | No as pre-correlation event feature |
| Independent ingestion/arrival per evidence field | Not established | When each extracted field became available | No revision or attachment ledger stated | No |
| `org_id` | Yes | Sanitized organization token | Dataset sanitizer | Yes for partitioning; token is not a label |
| `incident_ids` | Yes | UUID list of Precinct incident assignments | Precinct correlation engine | No; evaluator-only, circular ground truth |
| Graph node IDs | Yes | Sanitized host/credential/service/file/actor nodes | Merged live and incident graph | Conditional for signal-derived topology; incident-derived nodes excluded |
| Graph edge IDs / links | Edges available; independent edge identity unclear | Signal edges or `INCIDENT_LINK` edges | Graph exporter | Signal edges conditional; incident links no |
| `attrs.artifact_id` | Yes | Join from signal to graph edge | Graph exporter | Conditional lineage only |
| Evidence derivation / upstream dependency graph | Not established | Whether two fields stem from one original observation | No documented derivation graph | No independent-witness claim |
| Shared IP/host/username | Yes | Sanitized cross-event entities | Parsed signal fields | Conditional, org-scoped; not independent corroboration |
| `message_type`, `stream_name`, `product_name` | Yes | Event category and source product context | Source/Precinct parsing | Conditional |
| `attack_techniques`, `attack_tactics` | Yes | MITRE mappings | Includes incident set roles, MO, and framework metadata | No for reconstruction without row-level pre-correlation derivation proof |
| `label_binary`, `label_confidence` | Yes | benign/suspicious/malicious and rule-derived confidence | Precinct rules/incident assignment | No; evaluator or label-side only |
| `mo_name`, `suspicion_score`, `lifecycle_stage` | Yes | Parent incident conclusion and proprietary score | Precinct incident output | No |
| `disposition`, `is_false_positive` | Yes | Mostly engine-set status; rare analyst decisions | Precinct/analyst | No inference use; rare analyst statuses do not independently validate incident membership |
| Attack reports | Yes | Deterministic text from incident metadata | Precinct incident output | No; post-correlation conclusions |

## Time semantics

`event_time` is the source product's event time when present. For **live** rows, `timestamp` is Precinct ingestion time. For **historical incident leads**, the same column is lead observation/raise time, not the event time or ordinary live ingest time. `timestamp_source` distinguishes artifact timeuuid, lead observed time, and year-repaired lead time. No separate label-generation timestamp or per-field attachment/revision time was established. These clocks cannot be interchanged. A point-in-time reconstruction could be prototyped only from live rows with a clearly defined ingest cutoff and audited pre-cutoff fields; the incident labels still would not be independent. [Dataset card, signal columns](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity).

## Suitability conclusion

The dataset can support **descriptive research into Precinct's decisions** and possibly an imitation task explicitly labeled as such. It cannot support the requested independent claim that a new C/P/V method genuinely reconstructs expert incidents: incident IDs, malicious labels, incident graph links, and attack reports all derive from the same engine. There is no expert top-20 ranking equivalent, so GUIDE's Incident Recall@20 and P@10 are not directly defined. Organization holdout (four uneven organizations) or time holdout would test imitation transfer, not independent correctness. No Phase 11 download, preprocessing, E0–E6 model runs, GUIDE transfer, or target metric claim is justified under the stated gate.
