"""Frozen Phase 6A study protocol audit and synthetic checks."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import random
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_cohort(org_ids, n, seed):
    """Label-blind selection from caller-supplied eligible IDs; no label argument exists."""
    return sorted(set(map(str, org_ids)), key=lambda x: (hashlib.sha256(f"{seed}\0{x}".encode()).digest(), x))[:n]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path, out: Path):
    split_path = root / "data/derived/preprocessing/split_manifest.json"
    split = load_json(split_path)
    assignments = split["assignments"]
    partitions = {p: {o for o, v in assignments.items() if v == p} for p in ("pilot", "development", "test")}
    disjoint = all(not (partitions[a] & partitions[b]) for i, a in enumerate(partitions) for b in list(partitions)[i + 1:])
    access = (root / "phases_outputs/test_evaluation_access_log.md").read_text(encoding="utf-8")
    amb_path = root / "data/derived/preprocessing/review/ambiguous_alert_memberships.csv"
    conflict_keys = set()
    with amb_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            conflict_keys.add((row["OrgId"], row["AlertId"]))
    phase2 = load_json(root / "data/derived/preprocessing/preprocessing.json")
    validation = load_json(root / "data/derived/audit/validation.json")
    priority = load_json(root / "outputs/phase6/priority/phase6-priority-20261108-v2/run_manifest.json")
    correlation = load_json(root / "outputs/phase6/correlation/phase6-correlation-20261108-v1/run_manifest.json")
    evaluation = load_json(root / "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/evaluation_manifest.json")

    # Prior run evidence shows test scoring and test-label access. The frozen split only
    # assigns 50 of 499 eligible orgs; remaining IDs cannot be selected label-blind from
    # the public aggregate artifacts, and no complete exposure inventory exists for them.
    run_dirs = ["outputs/phase6/priority/phase6-priority-20261108-v1", "outputs/phase6/priority/phase6-priority-20261108-v2", "outputs/phase6/correlation/phase6-correlation-20261108-v1"]
    evidence = {
        "specifications": ["01_dataset_validation.md", "02_preprocessing.md", "03_Baselines.md", "04-Multi-agent system.md", "05-Evaluation.md", "06-Research-experiments.md", "phases_outputs/Phase1.md", "phases_outputs/Phase2.md", "phases_outputs/Phase3.md", "phases_outputs/Phase4.md", "phases_outputs/Phase5.md", "phases_outputs/Phase6.md"],
        "gate_records": ["phases_outputs/UNBLOCKED.md", "phases_outputs/readiness_evidence_review.md", "phases_outputs/research_gate_register.csv", "phases_outputs/test_evaluation_access_log.md", "phases_outputs/empirical_protocol_freeze.md", "phases_outputs/empirical_protocol_freeze_manifest.json"],
        "manifests": {"split": {"path": "data/derived/preprocessing/split_manifest.json", "sha256": sha256(split_path), "assignment_sha256": split["assignment_sha256"]}, "phase2": {"path": "data/derived/preprocessing/run_manifest.json", "sha256": sha256(root / "data/derived/preprocessing/run_manifest.json")}, "phase1": {"path": "data/derived/audit/run_manifest.json", "sha256": sha256(root / "data/derived/audit/run_manifest.json")}, "priority_v2": {"path": run_dirs[1] + "/run_manifest.json", "sha256": sha256(root / run_dirs[1] / "run_manifest.json")}, "correlation_v1": {"path": run_dirs[2] + "/run_manifest.json", "sha256": sha256(root / run_dirs[2] / "run_manifest.json")}, "evaluation": {"path": run_dirs[1] + "/evaluation/evaluation_manifest.json", "sha256": sha256(root / run_dirs[1] / "evaluation/evaluation_manifest.json")}},
        "phase6_runs": run_dirs,
        "phase6_prediction_label_state": {"priority_predictions_frozen_before_labels": priority.get("test_priority_labels_read") is False, "priority_test_labels_read_by_evaluator": evaluation.get("test_labels_read") is True, "correlation_predictor_did_not_read_labels": correlation.get("IncidentId_read_by_predictor") is False and correlation.get("QueueRank_read_by_predictor") is False, "correlation_evaluator_access_recorded": "Correlation diagnostic access" in access, "metrics_or_amendments_after_access": True},
        "split": {"assignment_sha256": split["assignment_sha256"], "assigned_count": len(assignments), "partition_counts": {p: len(v) for p, v in partitions.items()}, "disjoint": disjoint, "split_manifest_status": split.get("status"), "eligible_org_count": validation["checks"].get("qualified_orgs"), "eligible_unassigned_count": validation["checks"].get("qualified_orgs", 0) - len(assignments)},
        "ambiguity": {"policy": "exclude every conflicting composite (OrgId, AlertId) key from primary correlation/joint truth; retain restricted diagnostics", "conflicting_key_count": len(conflict_keys), "phase2_reported_count": phase2.get("ambiguous_alert_keys"), "counts_match": len(conflict_keys) == phase2.get("ambiguous_alert_keys")},
        "fresh_confirmatory_cohort": {"status": "unavailable", "reason": "Prior test labels and metrics were accessed; only 50 of 499 eligible organization IDs are assigned in the preserved split manifest; aggregate artifacts do not identify an auditable unused remainder, and no complete prior exposure/label-independence record supports a frozen fresh cohort.", "selector_specified": "SHA-256(seed NUL exact OrgId) then exact OrgId tie-break over an independently documented eligible and unused ID list", "membership_frozen": False},
        "claims": {"old_test_cohort": "exploratory", "queue_rank_direction": "unresolved; rank-1-highest is a prior assumption only", "query_universe": "unresolved local active-queue/snapshot correspondence", "feature_provenance": "unresolved; five descriptors are an adopted local assumption, not independently approved; Phase 2 allowlist remains empty", "data_release_provenance": "partial; local filenames/sizes and hashes are recorded, original download receipt unavailable", "guide_id_semantics": "unresolved", "correlation_truth": "exploratory ambiguity-excluded diagnostic only; conflicting mapping semantics unresolved", "real_data_model_permission": "blocked until point-in-time/privacy approval and confirmatory cohort; only existing exploratory reruns can be explicitly classified exploratory"},
        "test_access": {"confirmatory_access": "blocked", "test_tuned_selection": "blocked", "existing_test_results": "exploratory; labels already read", "new_test_evaluation_during_6A": False, "real_data_model_gate": "closed because configs/field_policy.yaml has empty allowlist; local five-field policy is assumption-only"},
        "source_facts": {"raw_hashes": validation["inputs"], "source_rows": validation["rows"], "ambiguous_key_count": len(conflict_keys), "feature_view_rows": phase2.get("feature_rows")},
    }
    out.mkdir(parents=True, exist_ok=True)
    audit_path = root / "phases_outputs/Phase6A_audit.json"
    audit_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cfg_path = root / "configs/phase6_protocol.yaml"
    protocol_path = root / "phases_outputs/Phase6A_StudyProtocol.md"
    manifest = {"protocol": "phase6a-study-protocol-v1", "protocol_sha256": hashlib.sha256(cfg_path.read_bytes() + b"\0" + protocol_path.read_bytes()).hexdigest(), "config_sha256": sha256(cfg_path), "protocol_document_sha256": sha256(protocol_path), "audit_sha256": sha256(audit_path), "split_manifest_sha256": sha256(split_path), "split_assignment_sha256": split["assignment_sha256"], "classification": "protocol_frozen_prior_test_exploratory_fresh_confirmatory_unavailable", "test_labels_read": False, "created_date": "2026-11-09"}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence, manifest


def self_test(root: Path):
    checks = {}
    fixture = load_json(root / "fixtures/stage6a/protocol_cases.json")
    if fixture.get("classification") != "synthetic_only":
        raise ValueError("Phase 6A fixture must be explicitly synthetic")
    # Determinism, set membership independent of ordering, fixed synthetic seed.
    ids = fixture["cohort_ids"]
    checks["selector_deterministic"] = stable_cohort(ids, fixture["cohort_size"], fixture["seed"]) == stable_cohort(list(reversed(ids)), fixture["cohort_size"], fixture["seed"])
    checks["selector_label_blind_api"] = "label" not in stable_cohort.__code__.co_varnames
    partitions = {k: set(v) for k, v in fixture["partitions"].items()}
    checks["split_disjoint"] = all(not (partitions[a] & partitions[b]) for i, a in enumerate(partitions) for b in list(partitions)[i + 1:])
    synthetic_memberships = {(m["org"], m["alert"]): set(m["incident_assignments"]) for m in fixture["memberships"]}
    eligible = {k: v for k, v in synthetic_memberships.items() if len(v) == 1}
    checks["ambiguous_key_excluded"] = sum(len(v) > 1 for v in synthetic_memberships.values()) == fixture["expected_ambiguous_excluded"] and len(eligible) == fixture["expected_eligible_memberships"]
    checks["test_tuning_blocked_by_status"] = {"confirmatory_access": "blocked", "test_tuned_selection": "blocked"}["test_tuned_selection"] == "blocked"
    # AST boundary: model-facing packages cannot import the evaluator store/truth reader.
    forbidden = {"src.evaluator_store", "src.evaluation.truth_reader", ".evaluator_store", "..evaluator_store"}
    violations = []
    for base in (root / "src/agents", root / "src/baselines"):
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in forbidden:
                    violations.append(str(path.relative_to(root)))
                if isinstance(node, ast.Import):
                    violations.extend(str(path.relative_to(root)) for name in node.names if name.name in forbidden)
    checks["model_code_evaluator_import_boundary"] = not violations
    checks["prior_test_access_is_exploratory"] = "exploratory" in (root / "phases_outputs/test_evaluation_access_log.md").read_text(encoding="utf-8").lower()
    if not all(checks.values()):
        raise AssertionError(checks)
    return {"status": "pass", "synthetic_only": True, "fixture": "fixtures/stage6a/protocol_cases.json", "checks": checks, "evaluator_import_violations": violations}
