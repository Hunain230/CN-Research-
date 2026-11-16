"""Evaluator-only retrospective Phase 14 audit. Never import into prediction code."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "experiments/PHASE13_RECOVERY/PHASE13_ERROR_ANALYSIS.csv"
BASE = HERE / "PHASE10_EVALUATION.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"Refusing empty deliverable: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    with SOURCE.open(newline="", encoding="utf-8") as stream:
        source = list(csv.DictReader(stream))
    baseline = json.loads(BASE.read_text(encoding="utf-8"))["methods"]["E1"]
    assert len(source) == baseline["expert_top20_denominator"] == 9980
    assert len({(r["queue_key"], r["incident_key"]) for r in source}) == 9980
    assert len({r["queue_key"] for r in source}) == 499
    assert baseline["group_recoverability_count"] == 6969
    assert baseline["incident_recall20_count"] == 5066
    expected = {"outside_scope": 855, "candidate_disconnected": 487,
                "incomplete": 1451, "impure": 218, "recoverable": 6969}
    assert Counter(r["recoverability_status"] for r in source) == expected
    # Phase 13's rank positions are deterministic diagnostics, while its reported
    # recall is a tie-aware expectation. They cannot assign 5,066 binary wins.
    rows, bound = [], []
    for r in source:
        state = r["recoverability_status"]
        size = int(r["expert_alerts_in_scope"])
        cap_feasible = size > 0 and math.ceil(.8 * size - 1e-12) <= 100
        true_connected = bool(int(r["candidate_connected"]))
        score = r["strongest_genuine_cross_fragment_score"]
        if state == "outside_scope":
            category, secondary = "A_outside_scope", ""
        elif not cap_feasible:
            category = "E_component_cap"
            secondary = "B_candidate_disconnected" if not true_connected else "C_candidate_connected_fragmented"
        elif state == "candidate_disconnected":
            category, secondary = "B_candidate_disconnected", "mixed_incident_bridge_unassessed"
        elif state == "incomplete":
            category, secondary = "C_candidate_connected_fragmented", ""
        elif state == "impure":
            category, secondary = "D_impure_predicted_group", ""
        else:
            category = "G_ranking_only_or_success"
            secondary = "exact_binary_rank_outcome_unavailable_tie_aware_metric"
        rows.append({**r, "primary_category": category, "secondary_cause": secondary,
                     "cap_feasible": int(cap_feasible),
                     "reported_recoverable": int(state == "recoverable"),
                     "rank_outcome_note": "tie_aware_aggregate_only" if state == "recoverable" else "not_applicable"})
        bound.append({"queue_key": r["queue_key"], "incident_key": r["incident_key"],
                      "expert_alerts_in_scope": size,
                      "candidate_true_connected_80pct": int(true_connected),
                      "cap_feasible_80pct": int(cap_feasible),
                      "phase13_bound_included": int(true_connected and cap_feasible),
                      "corrected_cap_scope_bound_included": int(cap_feasible),
                      "reported_recoverable": int(state == "recoverable"),
                      "exclusion_reason": "outside_scope" if not size else "cap" if not cap_feasible else "none"})
    write_csv(HERE / "PHASE14_ERROR_CLASSIFICATION.csv", rows)
    write_csv(HERE / "PHASE14_UPPER_BOUND_AUDIT.csv", bound)
    counts = Counter(r["primary_category"] for r in rows)
    assert sum(counts.values()) == 9980
    assert sum(int(r["phase13_bound_included"]) for r in bound) == 8596
    assert sum(int(r["corrected_cap_scope_bound_included"]) for r in bound) == 9063
    assert sum(int(r["reported_recoverable"]) for r in bound) == 6969
    missing = [r for r in rows if not r["reported_recoverable"]]
    opportunities = []
    for r in missing:
        cat = r["primary_category"]
        if cat in ("A_outside_scope", "E_component_cap"):
            decision = "impossible_under_current_constraints"
        elif cat == "D_impure_predicted_group":
            decision = "unsafe_due_to_false_merge_risk"
        else:
            decision = "undetermined_pending_source_provenance"
        opportunities.append({"queue_key": r["queue_key"], "incident_key": r["incident_key"],
                              "primary_category": cat, "classification": decision,
                              "expert_alerts_in_scope": r["expert_alerts_in_scope"],
                              "predicted_fragments": r["predicted_fragments"],
                              "candidate_edges_present_count": r["genuine_cross_fragment_edges"],
                              "max_true_edge_score_evaluator_only": r["strongest_genuine_cross_fragment_score"],
                              "max_false_edge_score_evaluator_only": r["strongest_false_cross_fragment_score"],
                              "source_evidence_available_at_decision": "unverified",
                              "specific_edge_provenance": "not_in_phase13_row_audit",
                              "safe_merge_established": "no",
                              "priority": "source_provenance_audit" if cat in ("B_candidate_disconnected", "C_candidate_connected_fragmented") else "constraint_or_safety_review"})
    write_csv(HERE / "PHASE14_RECOVERY_OPPORTUNITIES.csv", opportunities)
    write_csv(HERE / "PHASE14_CANDIDATE_EDGE_AUDIT.csv", [
        {"queue_key": r["queue_key"], "incident_key": r["incident_key"],
         "candidate_connected_true_only": r["candidate_connected"],
         "cross_fragment_true_edge_count_evaluator_only": r["genuine_cross_fragment_edges"],
         "max_true_score_evaluator_only": r["strongest_genuine_cross_fragment_score"],
         "max_false_score_evaluator_only": r["strongest_false_cross_fragment_score"],
         "edge_ids_or_source_observation_ids": "unavailable_in_diagnostic_table",
         "decision_time_provenance_verified": "no"} for r in missing])
    write_csv(HERE / "PHASE14_FEATURE_AVAILABILITY_AUDIT.csv", [
        {"clock": name, "guide_field_or_source": field, "point_in_time_provenance": "unverified",
         "operational_allowlist": "no", "research_use": use}
        for name, field, use in [
            ("event_time", "Timestamp (noised alert creation)", "retrospective_only"),
            ("collection_time", "not established", "none"),
            ("detector_time", "DetectorId is an identifier, no detector clock", "none"),
            ("evidence_availability_time", "not established", "none"),
            ("processing_time", "not established", "none"),
            ("analyst_decision_time", "not established", "none")]])
    write_csv(HERE / "PHASE14_METRICS_COMPARISON.csv", [{"experiment": "E1_reproduced", **{
        k: baseline[k] for k in ("queues", "expert_top20_denominator", "incident_recall20_count",
        "incident_recall20", "group_recoverability_count", "group_recoverability", "p10", "ndcg20",
        "grouped_pair_precision", "false_grouped_pairs", "mixed_predicted_groups")},
        "phase14_candidate": "none_evidence_gate_no_go", "difference": "not_measured"}])
    summary = {"rows": len(rows), "queues": 499, "categories": dict(counts),
               "original_bound": 8596, "corrected_cap_scope_upper_bound": 9063,
               "source_sha256": digest(SOURCE), "baseline_sha256": digest(BASE)}
    (HERE / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
