"""Aggregate-only GUIDE entity/time availability audit; writes no raw values."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from itertools import islice
from pathlib import Path

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/GUIDE_Test.csv"
OUT = ROOT / "outputs/entity_time_field_audit_20261114_v3.json"
FIELDS = ("Timestamp", "DeviceId", "Sha256", "IpAddress", "Url", "AccountSid",
          "AccountUpn", "AccountObjectId", "AccountName", "DeviceName",
          "NetworkMessageId", "EmailClusterId", "ApplicationId", "OAuthApplicationId")
ENTITY_FIELDS = FIELDS[1:]
PLACEHOLDERS = {"", "0", "-1", "nan", "none", "null", "unknown", "n/a"}


def detect_modal_sentinels() -> tuple[dict[str, str], dict[str, dict]]:
    sample = {field: Counter() for field in ENTITY_FIELDS}
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        for row in islice(csv.DictReader(stream), 100_000):
            for field in ENTITY_FIELDS:
                sample[field][row[field].strip()] += 1
    sentinels, evidence = {}, {}
    for field, counts in sample.items():
        modal, n = counts.most_common(1)[0]
        numeric = [int(value) for value in counts if value.isdigit()]
        is_numeric_max = modal.isdigit() and int(modal) == max(numeric)
        if n >= 50_000 and is_numeric_max:
            sentinels[field] = modal
        evidence[field] = {
            "sample_modal_fraction": n / 100_000,
            "sample_modal_is_numeric_max": is_numeric_max,
            "excluded_as_probable_sentinel": field in sentinels,
            "modal_value_sha256": hashlib.sha256(modal.encode()).hexdigest(),
        }
    return sentinels, evidence


def present(value: str, field: str, sentinels: dict[str, str]) -> bool:
    value = value.strip()
    return value.lower() not in PLACEHOLDERS and value != sentinels.get(field)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Use a new versioned audit output")
    sentinels, sentinel_evidence = detect_modal_sentinels()
    nonempty = Counter()
    placeholders = Counter()
    parseable = 0
    rows = 0
    alert_mask: dict[tuple[str, str], int] = {}
    first_timestamp: dict[tuple[str, str], str] = {}
    timestamp_conflict: set[tuple[str, str]] = set()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rows += 1
            alert = (row["OrgId"], row["AlertId"])
            mask = alert_mask.get(alert, 0)
            for i, field in enumerate(FIELDS):
                if present(row[field], field, sentinels):
                    nonempty[field] += 1
                    mask |= 1 << i
                else:
                    placeholders[field] += 1
            alert_mask[alert] = mask
            stamp = row["Timestamp"].strip()
            if stamp:
                try:
                    datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    parseable += 1
                except ValueError:
                    pass
                before = first_timestamp.setdefault(alert, stamp)
                if before != stamp:
                    timestamp_conflict.add(alert)
            if rows % 1_000_000 == 0:
                print(f"Audited {rows:,} rows", flush=True)
    alerts = len(alert_mask)
    result = {
        "classification": "aggregate_only_local_field_inventory_not_point_in_time_approval",
        "source_sha256": sha256_file(SOURCE),
        "analysis_code_sha256": sha256_file(Path(__file__)),
        "evidence_rows": rows, "composite_alert_keys": alerts,
        "timestamp_parseable_rows": parseable,
        "alerts_with_inconsistent_timestamp_across_evidence_rows": len(timestamp_conflict),
        "field_row_nonempty": {field: nonempty[field] for field in FIELDS},
        "field_row_placeholder_or_missing": {field: placeholders[field] for field in FIELDS},
        "modal_sentinel_sample_evidence": sentinel_evidence,
        "field_alert_nonempty": {field: sum(bool(mask & (1 << i)) for mask in alert_mask.values())
                                 for i, field in enumerate(FIELDS)},
        "alerts_with_any_entity_field": sum(bool(mask & ~1) for mask in alert_mask.values()),
        "notes": ["Counts include ambiguous alert keys and all source organizations",
                  "Publisher describes Timestamp as alert creation time but says noise was added",
                  "Local CSV cannot prove when each evidence field became available to an analyst",
                  "Literal 0 and other declared placeholders are treated as missing",
                  "Dominant numeric-maximum values are conservatively excluded as probable per-field missing sentinels; this is an inference, not publisher confirmation",
                  "No field is approved for operational model input by this inventory"],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "audited", "rows": rows, "alerts": alerts,
                      "timestamp_conflicts": len(timestamp_conflict)}, sort_keys=True))


if __name__ == "__main__":
    main()
