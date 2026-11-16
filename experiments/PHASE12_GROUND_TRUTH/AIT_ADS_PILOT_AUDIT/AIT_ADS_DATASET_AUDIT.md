# AIT-ADS dataset forensic audit

## Provenance and scope

AIT Alert Data Set, Zenodo record 8263181, version 1, CC BY 4.0; cite Landauer, Skopik, and Wurzenberger, DOI 10.5281/zenodo.8263181. Metadata, exact download sizes, published MD5, and independently computed SHA-256 are in `AIT_ADS_DOWNLOAD_MANIFEST.json`. The author workflow was inspected read-only at commit `ce927ddaeaa674f6909e1de676fa7dc293e393bd`. Sources: [Zenodo v1](https://zenodo.org/records/8263181) and [author workflow at ce927dd](https://github.com/ait-aecid/alert-data-set/tree/ce927ddaeaa674f6909e1de676fa7dc293e393bd). Only the 96,202,946-byte alert ZIP and 3,703-byte attack-window CSV were downloaded. The approximately 130.6 GB packed AIT-LDSv2 original logs and AIT-NDS netflow data were not downloaded. The ZIP was read as JSON lines without extracting or executing its contents.

## Measured inventory

The ZIP contains 16 newline-delimited JSON members, eight scenario names, two files per scenario. Sum of uncompressed member sizes: 2,857,702,804 bytes. All 2,655,821 JSON objects parsed; zero malformed rows. The scenario file names identify run provenance, not incident membership. The separate `labels.csv` has 79 rows with `scenario,attack,start,end`: 10 phases per scenario except Wheeler with nine. Its 79 intervals have zero pairwise temporal overlaps, including across scenario names. That property does not prove original source-event labels.

| Member | Rows | Uncompressed bytes | Missing alert ID | Missing flow ID | Malformed | Duplicate alert IDs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fox_aminer.json | 10,581 | 8,879,125 | 10,581 | 10,581 | 0 | 0 |
| fox_wazuh.json | 462,523 | 491,410,473 | 0 | 451,439 | 0 | 0 |
| harrison_aminer.json | 10,194 | 8,693,273 | 10,194 | 10,194 | 0 | 0 |
| harrison_wazuh.json | 583,754 | 632,912,134 | 0 | 516,370 | 0 | 0 |
| russellmitchell_aminer.json | 4,056 | 3,411,024 | 4,056 | 4,056 | 0 | 0 |
| russellmitchell_wazuh.json | 41,488 | 45,282,051 | 0 | 32,302 | 0 | 0 |
| santos_aminer.json | 4,266 | 3,634,879 | 4,266 | 4,266 | 0 | 0 |
| santos_wazuh.json | 126,513 | 145,438,925 | 0 | 82,401 | 0 | 0 |
| shaw_aminer.json | 2,243 | 1,944,470 | 2,243 | 2,243 | 0 | 0 |
| shaw_wazuh.json | 68,539 | 74,755,213 | 0 | 51,847 | 0 | 0 |
| wardbeck_aminer.json | 3,053 | 2,583,498 | 3,053 | 3,053 | 0 | 0 |
| wardbeck_wazuh.json | 88,204 | 96,564,119 | 0 | 63,694 | 0 | 0 |
| wheeler_aminer.json | 12,222 | 10,220,678 | 12,222 | 12,222 | 0 | 0 |
| wheeler_wazuh.json | 603,939 | 650,679,741 | 0 | 535,310 | 0 | 0 |
| wilson_aminer.json | 8,943 | 7,570,675 | 8,943 | 8,943 | 0 | 0 |
| wilson_wazuh.json | 625,303 | 673,722,526 | 0 | 560,265 | 0 | 0 |

Detailed per-member nested field names, observed JSON types, presence, and missing counts are preserved in `AIT_ADS_INSPECTION_SUMMARY.json` and `AIT_ADS_SCHEMA_INVENTORY.csv`. The latter is the exhaustive column inventory; JSON members have variable nested keys, so one fixed global schema would misstate missingness.

## Reference and suitability findings

- Wazuh-native `id` is present in 2,600,263/2,655,821 (97.9081%); the other 55,558 AMiner alerts have no per-alert native ID. No repeated Wazuh alert ID was observed within scenario and detector; the archive member plus row ordinal is the audit record key, not an invented source-observation ID.
- `location` or `LogData.LogResources` gives a source path in 2,655,821/2,655,821 (100.0000%). A path alone is not a unique record reference. Source line/offset is absent in every alert. Embedded raw log text appears in 2,349,186/2,655,821 (88.4542%); embedded text is evidence for a detector input, but not independent verification against the original source.
- `data.flow_id` plus path occurs in 306,635/2,655,821 (11.5458%); this is a structural reference, not a resolved flow. 173,230 of these rows reuse a prior scenario/path/flow key, so one-to-one resolution is not established. This count is not a count of unique ambiguous alerts or false alerts.
- Resolvable original observations: 0/2,655,821 (0.0000%). Unresolved external-source references: 2,655,821/2,655,821 (100.0000%). Verified source-level provenance and verified event-level labels: 0/2,655,821 (0.0000%) each. This means **unverified within the audit scope**, not that the corresponding source events do not exist.
- Detector distribution: AMiner 55,558, Wazuh 2,293,628, Suricata via Wazuh 306,635. Suricata alerts are counted as a subset of Wazuh JSON records, not a third archive member family.

**Suitability:** the small archive supports descriptive alert and attack-window statistics. It does not independently support event-level attack-phase association, incident membership, point-in-time C evaluation, or P/V benchmark comparison. The author workflow's event-labeling branch is disabled by default and joins Wazuh/AMiner raw log text against AIT-LDSv2 and Suricata flow tuples against AIT-NDS; this is external dependence, not evidence contained in the small archive. See the source-code logic in [analyze.py](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py).
