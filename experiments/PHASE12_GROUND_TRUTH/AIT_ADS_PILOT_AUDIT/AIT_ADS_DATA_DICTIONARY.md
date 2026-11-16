# AIT-ADS data dictionary

Observed types and presence for every nested path in every member are in `AIT_ADS_SCHEMA_INVENTORY.csv`. The entries below distinguish observed structure from verified meaning. Source: [Zenodo v1](https://zenodo.org/records/8263181) and [author workflow at ce927dd](https://github.com/ait-aecid/alert-data-set/tree/ce927ddaeaa674f6909e1de676fa7dc293e393bd), especially `analyze.py`. "Input" means a possible future inference feature only after time-of-availability and feature-policy review; this audit trains no model.

| Field | Observed type and meaning | Permitted audit use | Pilot feature status |
| --- | --- | --- | --- |
| ZIP member/scenario name | String; author run/file organization | Stratification and scenario-disjoint evaluation | Exclude from model input; run identity leaks schedule |
| Wazuh `id` | String; Wazuh alert identifier, present in all Wazuh rows; numeric-looking values need not be source event times | Alert deduplication and audit key | Audit-only; exclude ID magnitude |
| AMiner `AMiner.ID` | String; observed example is host IP, not unique alert ID | Detector/host context with caution | Exclude raw ID until policy and availability established |
| Wazuh `location`; AMiner `LogData.LogResources` | String/list of source log paths | Source family and external dependency audit | Audit-only until source availability proven; path can leak scenario |
| Wazuh `full_log`; AMiner `LogData.RawLogData` | String/list of detector-carried raw log text | Potential matching against external original logs | Exclude from claims of independently verified provenance |
| Wazuh `data.flow_id` | String in Suricata-derived alerts; not globally unique in this audit | Structural flow-reference count | Audit-only; original flow absent |
| Wazuh `data.timestamp`, `@timestamp`, `predecoder.timestamp` | Strings; different source/parsed timestamp channels | Time-semantic inspection; no ingest clock inferred | Conditional input only after point-in-time proof |
| AMiner `LogData.Timestamps`, `DetectionTimestamp` | Numeric lists; all inspected alerts have one of each and equal values | Event/claimed detector-time comparison | Conditional input only after chronology proof |
| Wazuh `agent`, `rule`, `decoder`, `data`; AMiner `AnalysisComponent` | Nested objects; detector/host/rule context, heterogeneous | Descriptive schema and possible later feature review | Unapproved here; may encode detector priors or scripted phase |
| `labels.csv` `scenario,attack,start,end` | Scenario name, attack phase name, numeric Unix-second interval | Ground-truth schedule metadata for retrospective window association only | Ground truth only; never model input |
| Audit `row_ordinal` | One-based line position inside a ZIP member | Reproducible alert record key | Exclude from model input |
| Audit `window_phases` | Derived from timestamp overlap with `labels.csv` | Descriptive association only | Ground truth only; never feature or event label |

There is no source-observation ID, original file offset/line, event-level attack truth, incident ID, collection timestamp, or evidence-availability timestamp in the inspected archive. Observed host/IP fields are not incident labels. The full per-file missing/type report is the machine-readable source of record; fields above are the consequential subset.
