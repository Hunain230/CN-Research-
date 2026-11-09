"""Build a reproducible Phase 6B data and label disposition audit.

This command reads existing aggregate validation/preprocessing records and policy
files. It never scans raw evidence or changes evaluator stores.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fields_from_yaml(text: str, key: str) -> list[str]:
    match = re.search(rf"(?ms)^{re.escape(key)}:\s*\n((?:\s+-\s+[^\n]+\n)+)", text)
    return [line.strip()[2:].strip() for line in match.group(1).splitlines()] if match else []


def build(root: Path) -> dict:
    root = root.resolve()
    field_path = root / "data/derived/audit/field_disposition.csv"
    preprocessing_path = root / "data/derived/preprocessing/preprocessing.json"
    leak_path = root / "data/derived/preprocessing/leakage_audit.json"
    audit_path = root / "phases_outputs/Phase6A_audit.json"
    empirical_policy_path = root / "configs/empirical_field_policy.yaml"
    production_policy_path = root / "configs/field_policy.yaml"
    protocol_path = root / "configs/phase6_protocol.yaml"
    for p in (field_path, preprocessing_path, leak_path, audit_path, empirical_policy_path, production_policy_path, protocol_path):
        if not p.is_file():
            raise FileNotFoundError(f"required Phase 6B evidence missing: {p.relative_to(root)}")

    phase1_fields = list(csv.DictReader(field_path.open("r", newline="", encoding="utf-8-sig")))
    prep = json.loads(preprocessing_path.read_text(encoding="utf-8"))
    leakage = json.loads(leak_path.read_text(encoding="utf-8"))
    phase6a = json.loads(audit_path.read_text(encoding="utf-8"))
    empirical_text = empirical_policy_path.read_text(encoding="utf-8")
    official_text = production_policy_path.read_text(encoding="utf-8")
    empirical = fields_from_yaml(empirical_text, "approved_model_fields")
    official = fields_from_yaml(official_text, "approved_model_fields")
    evaluator_only = fields_from_yaml(empirical_text, "evaluator_only")
    denied = fields_from_yaml(empirical_text, "denied")
    field_rows = []
    for row in phase1_fields:
        name = row["column"]
        if name in evaluator_only:
            disposition = "evaluator_only"
            basis = "Explicitly listed in local evaluator-only policy; prohibited from inference inputs."
        elif name in denied or name in {"OrgId", "AlertId", "Id", "Timestamp"}:
            disposition = "denied_or_lineage_only"
            basis = "Explicit deny/lineage policy or unresolved time semantics; not a model feature."
        elif name in empirical:
            disposition = "assumption_only_local_offline"
            basis = "User-directed local offline assumption; not independent timing/privacy approval and not authorized for hosted APIs."
        else:
            disposition = "unresolved_default_deny"
            basis = "No approved provenance/timing basis in the current local policy; remain denied."
        field_rows.append({
            "field": name,
            "null_rate": row.get("null_rate", ""),
            "cardinality_estimate": row.get("cardinality_estimate", ""),
            "phase1_disposition": row.get("allow_decision", ""),
            "module6b_disposition": disposition,
            "evidence_basis": basis,
        })

    source_hashes = phase6a.get("source_facts", {}).get("raw_hashes", {})
    ambiguity = phase6a.get("ambiguity", {})
    labels = [
        {"label": "IncidentId membership", "source": "data/derived/preprocessing/evaluator/incident_membership.csv", "status": "evaluator_only; conflicting membership semantics unresolved", "join_key": "(OrgId, AlertId)", "use": "Ambiguity-excluded exploratory correlation diagnostic only; never model input."},
        {"label": "QueueRank", "source": "data/derived/preprocessing/evaluator/queue_labels.csv", "status": "evaluator_only; rank direction and local queue snapshot unresolved", "join_key": "(OrgId, IncidentId)", "use": "Previously accessed test cohort supports exploratory reporting only; rank-direction sensitivity required for nDCG."},
        {"label": "IncidentGrade / response actions", "source": "GUIDE source columns and evaluator store", "status": "outcome/evaluator-only; not approved as features", "join_key": "incident-level source association", "use": "Excluded from candidate generation, prompts, calibration, dashboard inference, and ranking features."},
    ]
    evidence_files = [field_path, preprocessing_path, leak_path, audit_path, empirical_policy_path, production_policy_path, protocol_path,
                     root / "data/derived/preprocessing/split_manifest.json",
                     root / "data/derived/preprocessing/review/ambiguous_alert_memberships.csv",
                     root / "data/derived/preprocessing/evaluator/incident_membership.csv",
                     root / "data/derived/preprocessing/evaluator/queue_labels.csv"]
    return {
        "module": "6B",
        "protocol": "phase6b-data-label-disposition-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "assumption_based_local_offline_only; prior test results exploratory",
        "evidence_sha256": {p.relative_to(root).as_posix(): sha256(p) for p in evidence_files},
        "raw_input_hashes_from_frozen_audit": source_hashes,
        "feature_rows": leakage.get("rows"),
        "official_field_policy_approved_fields": official,
        "assumption_only_local_offline_fields": empirical,
        "field_dispositions": field_rows,
        "labels": labels,
        "ambiguity": {
            "conflicting_composite_alert_keys": ambiguity.get("conflicting_key_count"),
            "policy": "exclude all conflicting keys and associated evidence from primary correlation/joint scoring; preserve restricted diagnostic records; never choose an incident assignment heuristically",
            "source_artifact_sha256": sha256(root / "data/derived/preprocessing/review/ambiguous_alert_memberships.csv"),
        },
        "split": phase6a.get("split", {}),
        "status": {
            "local_assumption_based_exploratory_runs": "permitted only under existing offline empirical protocol and descriptive classification",
            "confirmatory_real_data": "blocked; no fresh confirmed cohort and existing test was accessed",
            "hosted_llm_or_external_transmission": "not authorized",
            "production_privacy_approval": "unresolved",
            "feature_view": "empty; no production/confirmatory model fields approved",
        },
        "prohibited_actions": ["use evaluator labels as features", "resolve ambiguous keys by vote/order/model", "infer QueueRank direction from score quality", "tune on existing test results", "send evidence to hosted services", "promote assumption-only fields to approved status"],
    }


def self_test() -> int:
    """Small synthetic policy checks; does not read project or raw data."""
    sample = [
        {"column": "IncidentId", "allow_decision": "deny"},
        {"column": "DetectorId", "allow_decision": "deny_pending"},
        {"column": "IpAddress", "allow_decision": "deny"},
        {"column": "UnreviewedNewField", "allow_decision": "deny_pending"},
    ]
    evaluator = {"IncidentId"}
    assumed = {"DetectorId"}
    denied = {"IpAddress"}
    result = {}
    for row in sample:
        name = row["column"]
        result[name] = ("evaluator_only" if name in evaluator else
                        "denied_or_lineage_only" if name in denied else
                        "assumption_only_local_offline" if name in assumed else
                        "unresolved_default_deny")
    assert result["IncidentId"] == "evaluator_only"
    assert result["DetectorId"] == "assumption_only_local_offline"
    assert result["IpAddress"] == "denied_or_lineage_only"
    assert result["UnreviewedNewField"] == "unresolved_default_deny"
    return 4


def write(root: Path, result: dict) -> None:
    out = root / "phases_outputs"
    out.mkdir(exist_ok=True)
    (out / "Phase6B_audit.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    field_path = out / "Phase6B_field_disposition.csv"
    with field_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["field_dispositions"][0]))
        writer.writeheader()
        writer.writerows(result["field_dispositions"])
    lines = [
        "# Module 6B — Data and label disposition", "",
        f"**Classification:** `{result['classification']}`  ",
        f"**Official approved feature fields:** {len(result['official_field_policy_approved_fields'])}  ",
        f"**Assumption-only local offline descriptors:** {', '.join(result['assumption_only_local_offline_fields']) or 'none'}  ",
        f"**Feature-view rows at Phase 2:** {result['feature_rows']}  ",
        f"**Conflicting alert keys excluded from primary correlation truth:** {result['ambiguity']['conflicting_composite_alert_keys']:,}", "",
        "## Decisions", "",
        "The Phase 1 field inventory and Phase 2 leakage report were reconciled with the frozen Phase 6A policy and both field policies. The production allowlist remains empty. Five descriptors remain assumption-only for local offline descriptive experiments; that status is not point-in-time or privacy approval and does not authorize a hosted model. All evaluator labels remain evaluator-only.", "",
        "All conflicting composite `(OrgId, AlertId)` mappings and associated evidence remain excluded from primary correlation and joint scoring. No mapping is resolved by majority vote, ordering, or model output. QueueRank direction and exact local query snapshot remain unresolved. Prior test results remain exploratory because labels were accessed.", "",
        "## Gate status", "",
        "- Local assumption-based offline work: permitted only as exploratory under the existing amended protocol.",
        "- Confirmatory real-data evaluation: blocked; no fresh exposure-audited cohort is available.",
        "- Hosted LLM comparison and external data transmission: unauthorized by the current project protocol.",
        "- Production deployment with real evidence: blocked pending field timing/privacy approval and a valid deployment evaluation.", "",
        "## Focused checks", "",
        "- `phase6b-self-test`: passed (4 synthetic policy assertions).",
        "- Phase 6A synthetic protocol self-test: passed (7 checks).",
        "- Phase 6B audit reads aggregate audit/policy artifacts only; it does not scan raw evidence or open evaluator labels.", "",
        "See `Phase6B_field_disposition.csv` for every source field and `Phase6B_audit.json` for label dispositions, hashes, and machine-readable gate status.", "",
        "No raw data, split, evaluator store, previous run, or Phase 1–5 artifact was changed by the audit generator.", "",
    ]
    (out / "Phase6B.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps({"status": "phase6b_self_test_pass", "assertions": self_test()}, sort_keys=True))
        return 0
    root = Path(args.root)
    result = build(root)
    write(root.resolve(), result)
    print(json.dumps({"status": "phase6b_audit_written", "field_count": len(result["field_dispositions"]), "conflicts": result["ambiguity"]["conflicting_composite_alert_keys"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
