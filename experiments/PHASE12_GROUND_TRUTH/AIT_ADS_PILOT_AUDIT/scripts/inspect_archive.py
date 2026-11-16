"""Stream all AIT-ADS JSONL members; never execute archive contents or use labels as truth."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RAW = HERE / "data/raw"
ZIP = RAW / "ait_ads.zip"
WINDOWS = RAW / "labels.csv"
OUT = HERE / "AIT_ADS_SOURCE_REFERENCE_AUDIT.csv"
SUMMARY = HERE / "AIT_ADS_INSPECTION_SUMMARY.json"


def iso_seconds(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value) if math.isfinite(float(value)) else None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def load_windows():
    result = defaultdict(list)
    with WINDOWS.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            start, end = float(row["start"]), float(row["end"])
            if not start < end:
                raise ValueError("Invalid attack window")
            result[row["scenario"]].append((start, end, row["attack"]))
    return result


def nested_paths(value, prefix="", depth=0):
    if not isinstance(value, dict) or depth > 3:
        return
    for name, child in value.items():
        path = prefix + str(name)
        yield path, type(child).__name__
        if isinstance(child, dict):
            yield from nested_paths(child, path + ".", depth + 1)


def main():
    if OUT.exists() or SUMMARY.exists():
        raise FileExistsError("Audit output exists; no silent overwrite")
    windows = load_windows()
    start = time.perf_counter()
    summary = {"source_zip_sha256": hashlib.sha256(ZIP.read_bytes()).hexdigest(),
        "attack_windows_sha256": hashlib.sha256(WINDOWS.read_bytes()).hexdigest(),
        "window_counts_by_scenario": {s: len(v) for s, v in windows.items()},
        "members": {}, "global_counts": Counter(), "by_detector": Counter(),
        "by_scenario": Counter(), "by_window_phase": Counter(), "by_window_status": Counter(),
        "by_reference_status": Counter(), "by_resolution_status": Counter(),
        "timestamps": defaultdict(Counter)}
    seen_ids = set()
    seen_source_refs = set()
    fields = ["scenario", "archive_member", "row_ordinal", "detector", "alert_id", "alert_id_status",
        "source_path", "source_line", "flow_id", "source_reference_status", "resolution_status",
        "embedded_raw_present", "event_time", "detector_time", "collection_time", "evidence_available_time",
        "window_phases", "window_status", "event_level_label_status"]
    with zipfile.ZipFile(ZIP) as archive, OUT.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(".json") or "/" in info.filename or ".." in info.filename:
                raise ValueError(f"Unexpected ZIP member: {info.filename}")
            match = re.fullmatch(r"([a-z]+)_(aminer|wazuh)\.json", info.filename)
            if not match or match.group(1) not in windows:
                raise ValueError(f"Unexpected scenario or detector: {info.filename}")
            scenario, family = match.groups()
            member = {"compressed_bytes": info.compress_size, "uncompressed_bytes": info.file_size,
                "rows": 0, "malformed_rows": 0, "top_level_presence": Counter(), "nested_path_presence": Counter(),
                "nested_path_types": defaultdict(Counter), "missing": Counter(), "duplicate_alert_ids": 0,
                "timestamp_min": {}, "timestamp_max": {}}
            with archive.open(info) as stream:
                for ordinal, raw in enumerate(stream, 1):
                    try:
                        item = json.loads(raw)
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        member["malformed_rows"] += 1
                        raise ValueError(f"Malformed JSON: {info.filename}:{ordinal}") from exc
                    if not isinstance(item, dict):
                        raise ValueError(f"Non-object alert: {info.filename}:{ordinal}")
                    member["rows"] += 1
                    member["top_level_presence"].update(item.keys())
                    for path, kind in nested_paths(item):
                        member["nested_path_presence"][path] += 1
                        member["nested_path_types"][path][kind] += 1
                    if family == "aminer":
                        detector = "AMiner"
                        log = item.get("LogData") or {}
                        alert_id = ""
                        paths = log.get("LogResources") or []
                        source_path = "|".join(map(str, paths))
                        source_line = ""
                        flow_id = ""
                        raw_present = bool(log.get("RawLogData"))
                        times = log.get("Timestamps") or []
                        event_time = iso_seconds(times[0]) if times else None
                        detector_time = iso_seconds((log.get("DetectionTimestamp") or [None])[0]) if isinstance(log.get("DetectionTimestamp"), list) else iso_seconds(log.get("DetectionTimestamp"))
                        collection_time = None
                    else:
                        groups = (item.get("rule") or {}).get("groups") or []
                        data = item.get("data") or {}
                        detector = "Suricata via Wazuh" if "suricata" in groups or str(item.get("location", "")).endswith("/suricata/eve.json") else "Wazuh"
                        alert_id = str(item.get("id") or "")
                        source_path = str(item.get("location") or "")
                        source_line = ""
                        flow_id = str(data.get("flow_id") or "")
                        raw_present = bool(item.get("full_log"))
                        event_time = iso_seconds(data.get("timestamp") or item.get("@timestamp"))
                        detector_time = None  # @timestamp may be parsed source time, not generation time.
                        collection_time = None  # id resembles replay time but is not a documented ingest clock.
                    for label, value in (("alert_id", alert_id), ("source_path", source_path),
                                         ("source_line", source_line), ("flow_id", flow_id),
                                         ("event_time", event_time), ("detector_time", detector_time),
                                         ("collection_time", collection_time)):
                        if value is None or value == "":
                            member["missing"][label] += 1
                    alert_key = (scenario, detector, alert_id) if alert_id else None
                    duplicate_id = bool(alert_key and alert_key in seen_ids)
                    if alert_key:
                        seen_ids.add(alert_key)
                    if duplicate_id:
                        member["duplicate_alert_ids"] += 1
                    if flow_id and source_path:
                        reference_status = "path_and_flow_id"
                    elif source_path and source_line:
                        reference_status = "path_and_line"
                    elif source_path:
                        reference_status = "path_only"
                    elif raw_present:
                        reference_status = "embedded_raw_only"
                    else:
                        reference_status = "none"
                    resolution_status = "unresolved_external_source" if source_path else "no_external_source_reference"
                    if reference_status in ("path_and_flow_id", "path_and_line"):
                        ref_key = (scenario, source_path, source_line, flow_id)
                        if ref_key in seen_source_refs:
                            summary["global_counts"]["duplicate_structural_source_references"] += 1
                        seen_source_refs.add(ref_key)
                    phases = [name for lo, hi, name in windows[scenario] if event_time is not None and lo <= event_time < hi]
                    window_status = "no_event_time" if event_time is None else "outside_window" if not phases else "ambiguous_overlap" if len(phases) > 1 else "in_one_window"
                    row = {"scenario": scenario, "archive_member": info.filename, "row_ordinal": ordinal,
                        "detector": detector, "alert_id": alert_id, "alert_id_status": "duplicate" if duplicate_id else "present" if alert_id else "missing",
                        "source_path": source_path, "source_line": source_line, "flow_id": flow_id,
                        "source_reference_status": reference_status, "resolution_status": resolution_status,
                        "embedded_raw_present": int(raw_present), "event_time": event_time or "",
                        "detector_time": detector_time or "", "collection_time": "", "evidence_available_time": "",
                        "window_phases": "|".join(phases), "window_status": window_status,
                        "event_level_label_status": "unverified_source_dataset_absent"}
                    writer.writerow(row)
                    summary["global_counts"]["alerts"] += 1
                    summary["global_counts"]["stable_alert_ids"] += bool(alert_id)
                    summary["global_counts"]["duplicate_alert_ids"] += duplicate_id
                    summary["global_counts"]["embedded_raw"] += raw_present
                    summary["global_counts"]["source_path_present"] += bool(source_path)
                    summary["global_counts"]["structural_source_reference"] += reference_status in ("path_and_flow_id", "path_and_line")
                    summary["global_counts"]["verified_source_observation"] += 0
                    summary["global_counts"]["verified_event_level_label"] += 0
                    summary["by_detector"][detector] += 1
                    summary["by_scenario"][scenario] += 1
                    summary["by_reference_status"][reference_status] += 1
                    summary["by_resolution_status"][resolution_status] += 1
                    summary["by_window_status"][window_status] += 1
                    for phase in phases:
                        summary["by_window_phase"][phase] += 1
                    for field, value in (("event_time", event_time), ("detector_time", detector_time)):
                        if value is not None:
                            current_min = member["timestamp_min"].get(field)
                            current_max = member["timestamp_max"].get(field)
                            member["timestamp_min"][field] = min(current_min, value) if current_min is not None else value
                            member["timestamp_max"][field] = max(current_max, value) if current_max is not None else value
                    if ordinal % 100000 == 0:
                        print(f"{info.filename}: {ordinal}", flush=True)
            summary["members"][info.filename] = member
            print(f"Completed {info.filename}: {member['rows']}", flush=True)
    summary["audit_seconds"] = time.perf_counter() - start
    summary["source_reference_csv_bytes"] = OUT.stat().st_size
    summary["source_reference_csv_sha256"] = hashlib.sha256(OUT.read_bytes()).hexdigest()
    def clean(x):
        if isinstance(x, Counter):
            return dict(x)
        if isinstance(x, defaultdict):
            return {k: clean(v) for k, v in x.items()}
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        return x
    SUMMARY.write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "alerts": summary["global_counts"]["alerts"],
        "csv_bytes": OUT.stat().st_size, "seconds": summary["audit_seconds"]}))


if __name__ == "__main__":
    main()
