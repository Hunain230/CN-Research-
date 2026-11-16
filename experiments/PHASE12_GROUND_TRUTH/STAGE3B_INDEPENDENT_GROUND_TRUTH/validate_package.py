"""Dependency-free structural and temporal gate for Stage 3B JSON packages.

Passing means internal consistency only, never authorization or truth validity.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HASH = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED = {
    "observations": {"observation_id", "source_system", "native_ref", "event_time", "collected_at", "payload_sha256"},
    "alerts": {"alert_id", "detector", "detector_version", "generated_at", "payload_sha256"},
    "derivations": {"alert_id", "observation_id", "method", "status"},
    "availability_events": {"artifact_type", "artifact_id", "kind", "available_at", "version", "payload_sha256", "sequence"},
    "incidents": {"incident_id", "truth_origin", "truth_status"},
    "memberships": {"alert_id", "incident_id", "judgment", "adjudicator_ref", "decided_at"},
    "actions": {"action_id", "incident_id", "started_at", "ended_at", "observation_ids"},
    "priority_judgments": {"queue_id", "cutoff_at", "incident_id", "rank", "adjudicator_ref", "rationale_ref"},
    "splits": {"incident_id", "scenario_family", "partition"},
}


def parse_time(value, path, errors):
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{path}: expected UTC ISO 8601 ending in Z")
        return None
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
        if result.tzinfo != timezone.utc:
            raise ValueError("not UTC")
        return result
    except ValueError:
        errors.append(f"{path}: malformed timestamp")
        return None


def index(rows, field, section, errors):
    found = {}
    for i, row in enumerate(rows):
        key = row.get(field)
        if not isinstance(key, str) or not key:
            errors.append(f"{section}[{i}].{field}: missing nonempty ID")
        elif key in found:
            errors.append(f"{section}[{i}].{field}: duplicate {key}")
        else:
            found[key] = row
    return found


def validate(package):
    errors, warnings = [], []
    if not isinstance(package, dict):
        return ["package: expected object"], warnings
    if package.get("schema_version") != "phase12-stage3b-v1":
        errors.append("schema_version: expected phase12-stage3b-v1")
    if package.get("track") not in {"soc_export", "controlled_lab"}:
        errors.append("track: expected soc_export or controlled_lab")
    if not isinstance(package.get("run_id"), str) or not package.get("run_id"):
        errors.append("run_id: missing nonempty ID")
    for section, fields in REQUIRED.items():
        rows = package.get(section)
        if not isinstance(rows, list):
            errors.append(f"{section}: expected array")
            package = {**package, section: []}
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"{section}[{i}]: expected object")
                rows[i] = {}
            elif missing := fields - row.keys():
                errors.append(f"{section}[{i}]: missing {sorted(missing)}")
    obs = index(package["observations"], "observation_id", "observations", errors)
    alerts = index(package["alerts"], "alert_id", "alerts", errors)
    incidents = index(package["incidents"], "incident_id", "incidents", errors)
    index(package["actions"], "action_id", "actions", errors)
    for section, id_field, time_fields in (
        ("observations", "observation_id", ("event_time", "collected_at")),
        ("alerts", "alert_id", ("generated_at",)),
        ("availability_events", "artifact_id", ("available_at",)),
        ("memberships", "alert_id", ("decided_at",)),
        ("actions", "action_id", ("started_at", "ended_at")),
        ("priority_judgments", "incident_id", ("cutoff_at",)),
    ):
        for i, row in enumerate(package[section]):
            for field in time_fields:
                parse_time(row.get(field), f"{section}[{i}].{field}", errors)
            if section in {"observations", "alerts", "availability_events"} and not HASH.fullmatch(str(row.get("payload_sha256", ""))):
                errors.append(f"{section}[{i}].payload_sha256: expected lowercase SHA-256")
    for i, row in enumerate(package["observations"]):
        if not row.get("source_system") or not row.get("native_ref"):
            errors.append(f"observations[{i}]: source system and native reference required")
        event = parse_time(row.get("event_time"), f"observations[{i}].event_time", [])
        collected = parse_time(row.get("collected_at"), f"observations[{i}].collected_at", [])
        if event and collected and collected < event:
            errors.append(f"observations[{i}]: collected before event; clock review required")
    linked_alerts = set()
    for i, row in enumerate(package["derivations"]):
        if row.get("alert_id") not in alerts or row.get("observation_id") not in obs:
            errors.append(f"derivations[{i}]: unresolved alert or source observation")
        if row.get("status") not in {"verified", "unverified", "ambiguous"}:
            errors.append(f"derivations[{i}]: invalid status")
        if row.get("status") == "verified":
            linked_alerts.add(row.get("alert_id"))
    if len(linked_alerts) < len(alerts):
        warnings.append(f"verified source-link coverage {len(linked_alerts)}/{len(alerts)} alerts")
    ledger = defaultdict(list)
    seen_sequences = set()
    for i, row in enumerate(package["availability_events"]):
        kind, artifact_type, artifact_id = row.get("kind"), row.get("artifact_type"), row.get("artifact_id")
        source = obs if artifact_type == "observation" else alerts if artifact_type == "alert" else {}
        if artifact_id not in source:
            errors.append(f"availability_events[{i}]: unresolved artifact")
        if kind not in {"available", "corrected", "retracted"}:
            errors.append(f"availability_events[{i}]: invalid kind")
        seq = row.get("sequence")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1 or seq in seen_sequences:
            errors.append(f"availability_events[{i}]: invalid or duplicate sequence")
        seen_sequences.add(seq)
        version = row.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            errors.append(f"availability_events[{i}]: invalid version")
        ledger[(artifact_type, artifact_id)].append(row)
        if kind == "available" and artifact_id in source and row.get("payload_sha256") != source[artifact_id].get("payload_sha256"):
            errors.append(f"availability_events[{i}]: initial payload hash mismatch")
    for artifact_type, records in (("observation", obs), ("alert", alerts)):
        for artifact_id, record in records.items():
            events = ledger[(artifact_type, artifact_id)]
            if not any(e.get("kind") == "available" for e in events):
                errors.append(f"{artifact_type} {artifact_id}: no availability event")
            ordered = sorted(events, key=lambda e: e.get("sequence") if isinstance(e.get("sequence"), int) else -1)
            if ordered and ordered[0].get("kind") != "available":
                errors.append(f"{artifact_type} {artifact_id}: first ledger event must be available")
            versions = [e.get("version") for e in ordered]
            if all(isinstance(v, int) for v in versions) and any(a > b for a, b in zip(versions, versions[1:])):
                errors.append(f"{artifact_type} {artifact_id}: version decreases by sequence")
            times = [parse_time(e.get("available_at"), "ledger time", []) for e in ordered]
            if all(times) and any(a > b for a, b in zip(times, times[1:])):
                errors.append(f"{artifact_type} {artifact_id}: ledger time decreases by sequence")
            first = next((e for e in ordered if e.get("kind") == "available"), None)
            if first:
                available = parse_time(first.get("available_at"), "ledger time", [])
                origin_field = "collected_at" if artifact_type == "observation" else "generated_at"
                origin = parse_time(record.get(origin_field), "origin time", [])
                if available and origin and available < origin:
                    errors.append(f"{artifact_type} {artifact_id}: available before {origin_field}")
    judged = set()
    judgments_by_alert = defaultdict(set)
    positive_incidents_by_alert = defaultdict(set)
    for i, row in enumerate(package["memberships"]):
        aid, iid, judgment = row.get("alert_id"), row.get("incident_id"), row.get("judgment")
        if aid not in alerts:
            errors.append(f"memberships[{i}]: unknown alert")
        if judgment not in {"positive", "negative", "ambiguous"}:
            errors.append(f"memberships[{i}]: invalid judgment")
        if judgment == "positive" and iid not in incidents:
            errors.append(f"memberships[{i}]: positive requires known incident")
        if judgment == "negative" and iid is not None:
            errors.append(f"memberships[{i}]: negative must use null incident_id")
        if iid is not None and iid not in incidents:
            errors.append(f"memberships[{i}]: unknown incident")
        if not row.get("adjudicator_ref"):
            errors.append(f"memberships[{i}]: missing independent adjudicator reference")
        judged.add(aid)
        judgments_by_alert[aid].add(judgment)
        if judgment == "positive":
            positive_incidents_by_alert[aid].add(iid)
    for aid, judgments in judgments_by_alert.items():
        if "positive" in judgments and "negative" in judgments:
            errors.append(f"memberships: contradictory positive and negative judgments for {aid}")
    for aid, linked in positive_incidents_by_alert.items():
        if len(linked) > 1:
            warnings.append(f"memberships: {aid} assigned to multiple incidents; explicit overlap adjudication required")
    if len(judged) < len(alerts):
        warnings.append(f"membership judgment coverage {len(judged)}/{len(alerts)} alerts")
    for i, row in enumerate(package["actions"]):
        if package.get("track") != "controlled_lab":
            errors.append(f"actions[{i}]: lab actions in SOC package")
        if row.get("incident_id") not in incidents or any(x not in obs for x in row.get("observation_ids", [])):
            errors.append(f"actions[{i}]: unresolved incident or observation")
        start = parse_time(row.get("started_at"), "action start", [])
        end = parse_time(row.get("ended_at"), "action end", [])
        if start and end and end < start:
            errors.append(f"actions[{i}]: end before start")
    by_family, by_incident = defaultdict(set), defaultdict(set)
    for i, row in enumerate(package["splits"]):
        if row.get("incident_id") not in incidents:
            errors.append(f"splits[{i}]: unknown incident")
        partition = row.get("partition")
        if partition not in {"development", "validation", "sealed_test"}:
            errors.append(f"splits[{i}]: invalid partition")
        by_family[row.get("scenario_family")].add(partition)
        by_incident[row.get("incident_id")].add(partition)
    if any(len(v) > 1 for v in by_family.values()):
        errors.append("splits: scenario family crosses partitions")
    if any(len(v) != 1 for v in by_incident.values()) or set(by_incident) != set(incidents):
        errors.append("splits: every incident needs exactly one partition")
    ranks = defaultdict(set)
    ranked_incidents = defaultdict(set)
    for i, row in enumerate(package["priority_judgments"]):
        if row.get("incident_id") not in incidents:
            errors.append(f"priority_judgments[{i}]: unknown incident")
        rank = row.get("rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            errors.append(f"priority_judgments[{i}]: invalid rank")
        key = (row.get("queue_id"), row.get("adjudicator_ref"))
        if rank in ranks[key]:
            errors.append(f"priority_judgments[{i}]: duplicate rank for adjudicator/queue")
        if row.get("incident_id") in ranked_incidents[key]:
            errors.append(f"priority_judgments[{i}]: duplicate incident for adjudicator/queue")
        ranks[key].add(rank)
        ranked_incidents[key].add(row.get("incident_id"))
        if not row.get("adjudicator_ref") or not row.get("rationale_ref"):
            errors.append(f"priority_judgments[{i}]: missing reviewer or rationale")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    package = json.loads(args.package.read_text(encoding="utf-8"))
    errors, warnings = validate(package)
    print(json.dumps({"valid": not errors, "errors": errors, "warnings": warnings}, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
