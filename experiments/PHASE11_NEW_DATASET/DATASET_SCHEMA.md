# Phase 11 published schema inventory

Source: [pinned candidate repository](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity/tree/96311c2e29611d8ddbf1c0d59f531f6a362b8233) and its [dataset card](https://huggingface.co/datasets/witfoo/precinct6-cybersecurity). This is a documentation-level inventory, **not** a locally validated Parquet schema; no files were downloaded because the suitability gate failed.

| Published configuration | Source file | Declared role |
|---|---|---|
| `signals` | `signals/signals.parquet` | 2,011,674 live ingested signals, including 7,728 malicious leads |
| `incident_signals` | `signals/incident_signals.parquet` | 238,511 historical leads not present in live rows; different timestamp semantics |
| `graph_nodes` | `graph/nodes.parquet` | Merged host, credential, service, file, actor nodes |
| `graph_edges` | `graph/edges-00000.parquet` | Signal-derived edges plus incident links; incident links are post-correlation |
| `attack_reports` | `graph/attack_reports.parquet` | Deterministic incident-summary text, post-correlation |

The signal tables share a published 38-column schema. Important raw-context fields are `artifact_id`, `org_id`, `timestamp`, nullable `event_time`, `timestamp_source`, `origin`, `message_type`, `stream_name`, `pipeline`, `src_ip`, `dst_ip`, ports, protocol, `src_host`, `dst_host`, `username`, `action`, `severity`, `vendor_code`, `message_sanitized`, `product_name`, and `vendor_name`. Label or incident-output fields include `label_binary`, `label_confidence`, `attack_techniques`, `attack_tactics`, `defense_techniques`, `mo_name`, `suspicion_score`, `lifecycle_stage`, `disposition`, `disposition_category`, `is_false_positive`, `status_name`, `incident_ids`, `matched_rules`, and `set_roles`. The latter fields cannot be assumed to exist before correlation. The dataset card says graph signal edges carry `attrs.artifact_id`, whereas incident links and incident-derived node times encode assignments. Exact nullable types, cardinalities, graph edge identity, and source-observation provenance remain unverified locally.
