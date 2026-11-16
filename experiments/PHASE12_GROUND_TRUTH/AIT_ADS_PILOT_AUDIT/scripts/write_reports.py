"""Render forensic audit reports from inspected, immutable summary artifacts."""
from __future__ import annotations

import csv
import json
import platform
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "AIT_ADS_INSPECTION_SUMMARY.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "AIT_ADS_DOWNLOAD_MANIFEST.json").read_text(encoding="utf-8"))
with (ROOT / "data/raw/labels.csv").open(newline="", encoding="utf-8") as stream:
    windows = list(csv.DictReader(stream))
n = summary["global_counts"]["alerts"]


def pct(value: int) -> str:
    return f"{value:,}/{n:,} ({100 * value / n:.4f}%)"


def table(rows):
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)


def write(name, body):
    target = ROOT / name
    if target.exists():
        raise FileExistsError(f"No silent overwrite: {target}")
    target.write_text(body.strip() + "\n", encoding="utf-8")


member_rows = [["Member", "Rows", "Uncompressed bytes", "Missing alert ID", "Missing flow ID", "Malformed", "Duplicate alert IDs"]]
member_rows.append(["---", "---:", "---:", "---:", "---:", "---:", "---:"])
for name, m in summary["members"].items():
    member_rows.append([name, f"{m['rows']:,}", f"{m['uncompressed_bytes']:,}",
                        f"{m['missing'].get('alert_id', 0):,}", f"{m['missing'].get('flow_id', 0):,}",
                        m["malformed_rows"], m["duplicate_alert_ids"]])

schema_rows = [["Member", "Nested path", "Presence", "Missing", "Observed JSON types"]]
schema_rows.append(["---", "---", "---:", "---:", "---"])
for name, m in summary["members"].items():
    for path, count in sorted(m["nested_path_presence"].items()):
        kinds = ", ".join(f"{kind}:{amount}" for kind, amount in m["nested_path_types"][path].items())
        schema_rows.append([name, f"`{path}`", f"{count:,}", f"{m['rows']-count:,}", kinds])

phase_rows = [["Attack window phase", "Window associated alerts", "Share of all alerts"] , ["---", "---:", "---:"]]
for phase, count in sorted(summary["by_window_phase"].items()):
    phase_rows.append([phase, f"{count:,}", f"{100*count/n:.4f}%"])

source = "[Zenodo v1](https://zenodo.org/records/8263181) and [author workflow at ce927dd](https://github.com/ait-aecid/alert-data-set/tree/ce927ddaeaa674f6909e1de676fa7dc293e393bd)"
write("AIT_ADS_DATASET_AUDIT.md", f"""
# AIT-ADS dataset forensic audit

## Provenance and scope

AIT Alert Data Set, Zenodo record 8263181, version 1, CC BY 4.0; cite Landauer, Skopik, and Wurzenberger, DOI 10.5281/zenodo.8263181. Metadata, exact download sizes, published MD5, and independently computed SHA-256 are in `AIT_ADS_DOWNLOAD_MANIFEST.json`. The author workflow was inspected read-only at commit `ce927ddaeaa674f6909e1de676fa7dc293e393bd`. Sources: {source}. Only the 96,202,946-byte alert ZIP and 3,703-byte attack-window CSV were downloaded. The approximately 130.6 GB packed AIT-LDSv2 original logs and AIT-NDS netflow data were not downloaded. The ZIP was read as JSON lines without extracting or executing its contents.

## Measured inventory

The ZIP contains 16 newline-delimited JSON members, eight scenario names, two files per scenario. Sum of uncompressed member sizes: {sum(m['uncompressed_bytes'] for m in summary['members'].values()):,} bytes. All {n:,} JSON objects parsed; zero malformed rows. The scenario file names identify run provenance, not incident membership. The separate `labels.csv` has {len(windows)} rows with `scenario,attack,start,end`: 10 phases per scenario except Wheeler with nine. Its 79 intervals have zero pairwise temporal overlaps, including across scenario names. That property does not prove original source-event labels.

{table(member_rows)}

Detailed per-member nested field names, observed JSON types, presence, and missing counts are preserved in `AIT_ADS_INSPECTION_SUMMARY.json` and `AIT_ADS_SCHEMA_INVENTORY.csv`. The latter is the exhaustive column inventory; JSON members have variable nested keys, so one fixed global schema would misstate missingness.

## Reference and suitability findings

- Wazuh-native `id` is present in {pct(summary['global_counts']['stable_alert_ids'])}; the other {n-summary['global_counts']['stable_alert_ids']:,} AMiner alerts have no per-alert native ID. No repeated Wazuh alert ID was observed within scenario and detector; the archive member plus row ordinal is the audit record key, not an invented source-observation ID.
- `location` or `LogData.LogResources` gives a source path in {pct(summary['global_counts']['source_path_present'])}. A path alone is not a unique record reference. Source line/offset is absent in every alert. Embedded raw log text appears in {pct(summary['global_counts']['embedded_raw'])}; embedded text is evidence for a detector input, but not independent verification against the original source.
- `data.flow_id` plus path occurs in {pct(summary['global_counts']['structural_source_reference'])}; this is a structural reference, not a resolved flow. {summary['global_counts']['duplicate_structural_source_references']:,} of these rows reuse a prior scenario/path/flow key, so one-to-one resolution is not established. This count is not a count of unique ambiguous alerts or false alerts.
- Resolvable original observations: {pct(0)}. Unresolved external-source references: {pct(n)}. Verified source-level provenance and verified event-level labels: {pct(0)} each. This means **unverified within the audit scope**, not that the corresponding source events do not exist.
- Detector distribution: {', '.join(f'{k} {v:,}' for k,v in summary['by_detector'].items())}. Suricata alerts are counted as a subset of Wazuh JSON records, not a third archive member family.

**Suitability:** the small archive supports descriptive alert and attack-window statistics. It does not independently support event-level attack-phase association, incident membership, point-in-time C evaluation, or P/V benchmark comparison. The author workflow's event-labeling branch is disabled by default and joins Wazuh/AMiner raw log text against AIT-LDSv2 and Suricata flow tuples against AIT-NDS; this is external dependence, not evidence contained in the small archive. See the source-code logic in [analyze.py](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py).
""")

with (ROOT / "AIT_ADS_SCHEMA_INVENTORY.csv").open("x", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerows([["archive_member", "nested_path", "present_count", "missing_count", "observed_json_types"]] +
                     [[row[0], row[1].strip('`'), row[2].replace(',', ''), row[3].replace(',', ''), row[4]] for row in schema_rows[2:]])

write("AIT_ADS_DATA_DICTIONARY.md", f"""
# AIT-ADS data dictionary

Observed types and presence for every nested path in every member are in `AIT_ADS_SCHEMA_INVENTORY.csv`. The entries below distinguish observed structure from verified meaning. Source: {source}, especially `analyze.py`. "Input" means a possible future inference feature only after time-of-availability and feature-policy review; this audit trains no model.

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
""")

write("AIT_ADS_TIME_SEMANTICS.md", f"""
# Time semantics and point-in-time audit

| Concept | Available finding | Status |
| --- | --- | --- |
| `event_time` | Wazuh `data.timestamp` where present, otherwise `@timestamp`; AMiner first `LogData.Timestamps` value. These are parsed or carried source-event candidates, not a verified source clock. | Present and parseable in {pct(n)} for the audit extraction; timezone semantics of all numeric source clocks are not independently documented here. ISO `Z` is UTC. |
| `detector_time` | AMiner `DetectionTimestamp` is present in all 55,558 AMiner rows, with one value per row and exactly equal to its `Timestamps` value in all 55,558; this equality cannot establish an independent detection latency. Wazuh generation time is not documented by an unambiguous field. | Partly present; semantics unverified. |
| `collection_time` | No validated ingest/collection clock. Wazuh `id` resembles a later epoch but is an alert ID and must not be repurposed as collection time. | Unavailable. |
| `evidence_available_time` | No observation of when original evidence or detector alert became accessible to the correlator. | Unavailable. |

The author analysis chooses Wazuh `data.timestamp`, then parsed `predecoder.timestamp`, then extracted full-log time; AMiner uses `DetectionTimestamp[-1]` to compare with attack windows. This audit uses Wazuh `data.timestamp`/`@timestamp` and AMiner first detection timestamp for descriptive window counts. All inspected AMiner detection lists contain one element, so the first/last difference is zero here. Wazuh `@timestamp` is not asserted to match every author time-selection branch; the window counts are a mechanical audit calculation, not the author's published event labels. See [pinned author workflow](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py).

All {n:,} extracted candidate event timestamps parsed; zero were missing or malformed under the audit parser. All 55,558 extracted AMiner detection timestamps parsed and equaled the extracted event timestamp, so no negative AMiner detection-minus-event differences were observed. Wazuh detector-minus-event and collection/evidence ordering cannot be checked because a trusted independent timestamp is absent. These findings do not prove correct original timezone or chronological availability. The JSON records reflect a retrospective workflow; original detector operation versus replay generation is unresolved for individual fields. **Point-in-time evidence availability is not established.**
""")

write("AIT_ADS_LABEL_AUDIT.md", f"""
# Attack-phase label audit

The downloaded `labels.csv` contains {len(windows)} scripted attack intervals across eight named scenarios; phase counts: {', '.join(f'{k} {v}' for k,v in sorted(Counter(r['attack'] for r in windows).items()))}. No intervals overlap within or across scenario names in this file. File organization and author description support eight scenario runs, but do not establish multiple independent incidents per run or identify every original source observation. No per-alert ground-truth label appears in `labels.csv`.

| Association level | Evidence in small archive | Verdict |
| --- | --- | --- |
| A. Attack-window association | Compare an extracted alert time with a same-scenario scripted interval. | Descriptive only; measured below. |
| B. Event-level attack-phase association | Requires matching detector-carried raw text to original AIT-LDSv2 labeled log event, or Suricata flow to original AIT-NDS netflow, using the author workflow. | Zero independently verified within downloaded files. |
| C. Alert-to-incident membership | No complete incident ID or multi-incident mapping. | Unavailable. |

Mechanical half-open `[start,end)` window association, using the audit timestamp selection: {pct(summary['by_window_status'].get('in_one_window',0))} in exactly one phase; {pct(summary['by_window_status'].get('outside_window',0))} outside all phases; {pct(summary['by_window_status'].get('ambiguous_overlap',0))} in multiple phases; {pct(summary['by_window_status'].get('no_event_time',0))} missing timestamp. Outside-window alerts are **not** proven benign; inside-window alerts are **not** proven true positives. Thus the small archive provides no validated positive/negative event-label counts and no known false-positive rate.

{table(phase_rows)}

Detector counts: {', '.join(f'{k} {v:,}' for k,v in summary['by_detector'].items())}. Scenario counts: {', '.join(f'{k} {v:,}' for k,v in summary['by_scenario'].items())}. Each uses denominator {n:,} alerts and mutually exclusive bins, except phase counts reflect window matching. The author source code has `do_event_labeling = False` by default and requires external AIT-LDSv2 and AIT-NDS data when enabled. Its Wazuh/AMiner raw-line and Suricata flow matching is a *potential* event-level construction workflow, not a verified result of this audit. [Pinned `analyze.py`](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py).
""")

write("AIT_ADS_LEAKAGE_POLICY.md", """
# Leakage and validity policy

This is an audit policy; no model was trained. A future C-only experiment must first prove source resolution and point-in-time feature availability.

| Field/source | Risk | Allowed use now |
| --- | --- | --- |
| Scenario name, ZIP member, run-specific source paths, host/IP, row order, Wazuh generated ID | Run fingerprint and attack schedule proxy | Audit and scenario-disjoint split only; no predictive input |
| `labels.csv` attack phase and interval endpoints, derived `window_phases`, precomputed event labels | Direct target leakage | Evaluation-only layer; never merge, threshold, or feature input |
| Detector name, Wazuh rule/category, AMiner component | Detector priors may reflect known attack steps | Audit-only until provenance and time-of-availability review |
| Raw log content and flow tuple | May be a valid observed input, but may include scripted strings and retrospective enrichment | Matching audit only until external original event and availability proof |
| Author `analyze.py` output | Event labels can be derived using external source labels and known schedule | Ground-truth construction only, isolated from inference |

If a later authorized pilot becomes feasible, split by complete scenario run, never randomly by alerts or time slices from the same run. With eight named runs, any held-out evaluation would be small and should report each run separately. Keep source matching and label construction in a separate evaluation-only process; freeze field allowlists and matching rules before evaluating held-out runs. Audit duplicate flow references and ambiguous matches explicitly. No GUIDE comparison, incident-level metric, or independent priority result follows from this dataset.
""")

write("AIT_ADS_C_ONLY_EVALUATION_PROTOCOL.md", f"""
# C-only endpoint: blocked protocol

**Current endpoint supported:** descriptive same-scenario attack-window overlap of an alert's extracted timestamp with a scripted interval. This is level A only. It is not a valid event-level C accuracy endpoint because {pct(0)} original source observations and {pct(0)} event-level labels were verified within the authorized small archive. It is not full incident reconstruction or any P ranking metric.

**Proposed endpoint if external source access is later authorized:** event-level attack-phase association for an alert whose exact original labeled log line or netflow is resolved. Unit: one detector alert, keyed by archive member and row ordinal (retaining native Wazuh ID where present). Truth: source event labels from separately versioned AIT-LDSv2/AIT-NDS plus pinned matching code, with one-to-one or explicitly adjudicated many-to-one links. Positive: resolved source observation independently labeled as a scripted attack phase. Negative: resolved source observation explicitly labeled nonattack; absence from an attack window is insufficient. Ambiguous, missing, or conflicting matches remain abstentions and stay in the coverage denominator. Multiple detector alerts for one event are distinct alerts but must be grouped for leakage-safe split/dedup reporting. Train/test separation: scenario-disjoint runs, frozen transformations and thresholds, no label-derived input. Point-in-time use additionally requires evidence-availability records; without them this would remain retrospective.

**Proposed, unmeasured metrics:** reference coverage = uniquely resolved alert-to-source links / all eligible alerts; label coverage = alerts with verified unambiguous event truth / all eligible alerts; conditional precision = correctly predicted attack associations / predicted attack associations among verified truth; conditional recall = correctly predicted attack associations / verified positive alerts; abstention = unresolved or ambiguous alerts / all eligible alerts. Also report false-association count and performance by held-out scenario/detector. Report exact numerators/denominators. None of these are estimated here.

The present verdict is **NO-GO** for the event-level C-only pilot using only the small archive. A future read-only remote query or authorized local source subset would need to validate exact source IDs/line/flow joins and label semantics before revisiting the decision. The full 130.6 GB packed AIT-LDSv2 data and AIT-NDS were not downloaded.
""")

write("AIT_ADS_FINAL_DECISION.md", f"""
# Final decision: NO-GO

The authorized AIT-ADS files contain {n:,} parsed alerts and {len(windows)} attack windows. Resolvable original source references: {pct(0)}. Verified source-level provenance: {pct(0)}. Verified event-level attack-phase labels: {pct(0)}. All {n:,} alerts point to source paths outside the small archive. A source path or timestamp does not identify and verify an original observation; a Suricata flow ID is a structural clue but the original flow data are absent. The author event-labeling workflow depends on external AIT-LDSv2 and AIT-NDS. Evidence-availability time is absent. **Point-in-time evidence availability is not established.**

The archive is sufficient for descriptive alert and scripted-window overlap counts only. The exact supported C-only output is a retrospective window-association *audit*, not an event-level association accuracy evaluation. Neither the GUIDE benchmark nor Phase 10 E1 is comparable here. No model was trained; no GUIDE, Phase 10, or frozen baseline artifact was modified. Reconsider only after authorized access to original source observations, verifiable matching, independently justified positive/negative event labels, and a point-in-time evidence record. The principal leakage risks are scenario/run identity, schedule windows, generated IDs, run-specific paths, and detector features correlated with scripted phases.
""")

write("AIT_ADS_REPRODUCIBILITY.md", f"""
# Reproducibility and integrity

Run from `experiments/PHASE12_GROUND_TRUTH/AIT_ADS_PILOT_AUDIT/` with Python 3.11+ and the requests package for download; inspection and reporting use only the standard library. Audit host: {platform.platform()}; Python {platform.python_version()}. The official sources are [Zenodo record 8263181](https://zenodo.org/records/8263181), [AIT-LDSv2 source record](https://zenodo.org/records/5789064), and [author repository pinned to ce927dd](https://github.com/ait-aecid/alert-data-set/tree/ce927ddaeaa674f6909e1de676fa7dc293e393bd). No external code from the ZIP was executed.

1. `python scripts/download_verified.py` verifies Zenodo metadata, license and exact file names/sizes before downloading only `ait_ads.zip` and `labels.csv` into `data/raw/`. It verifies published MD5 and records SHA-256 and UTC download time in `AIT_ADS_DOWNLOAD_MANIFEST.json`.
2. `python scripts/inspect_archive.py` streams every JSONL member without extraction. It writes all {n:,} alert audit rows to `AIT_ADS_SOURCE_REFERENCE_AUDIT.csv` and aggregate field/type/missingness counts to `AIT_ADS_INSPECTION_SUMMARY.json`. It refuses to overwrite existing outputs. Measured scan time: {summary['audit_seconds']:.2f} seconds on this host. No peak-memory measure was captured; the script holds alert IDs and structural reference keys in memory and writes a {summary['source_reference_csv_bytes']:,}-byte CSV.
3. `python scripts/write_reports.py` renders the prose reports and exhaustive `AIT_ADS_SCHEMA_INVENTORY.csv` from the measured summary. It also refuses silent overwrite. To reproduce in a separate clean directory, copy scripts into an empty audit directory and execute in that order; preserve the original downloaded bytes.

Integrity anchors: ZIP SHA-256 `{summary['source_zip_sha256']}`; window CSV SHA-256 `{summary['attack_windows_sha256']}`; per-alert audit CSV SHA-256 `{summary['source_reference_csv_sha256']}`. Published MD5, exact sizes, license, source URLs, and timestamps are in the manifest. The inspection summary is the machine-readable source of all table counts. Window comparisons use half-open `[start,end)` and the timestamp extraction documented in `AIT_ADS_TIME_SEMANTICS.md`. All percentages in reports use denominator {n:,} unless explicitly identified as a different subset. Empty `detector_time` for Wazuh is deliberate: no verified generation clock. No source logs or models are required to reproduce this *negative* suitability finding.
""")

print("Rendered reports and schema inventory")
