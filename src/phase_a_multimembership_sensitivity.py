"""Evaluator-only aggregate sensitivity for conflicting alert memberships.

This does not relabel the primary task. A multi-membership graph is kept only as
an optimistic sensitivity bound until the dataset owner confirms its semantics.
"""
from __future__ import annotations

import csv
import json
import pickle
from collections import Counter, defaultdict

from .guide_rerun_v2 import ROOT, check_raw, key, labels
from .phase2 import sha256_file

PRED = ROOT / "data/derived/offline_joint_v2/predictions.pkl"
LEDGER = ROOT / "data/derived/preprocessing/evaluator/incident_membership.csv"
OUT = ROOT / "outputs/phase_a/multimembership_sensitivity_v1.json"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    check_raw()
    with PRED.open("rb") as stream:
        predicted = pickle.load(stream)
    cohort = set(predicted)
    truth = labels(cohort)
    groups = defaultdict(set)
    statuses = {}
    with LEDGER.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            org = row["OrgId"]
            if org not in cohort:
                continue
            alert = key(org, row["AlertId"])
            groups[(org, alert)].add(key(org, row["IncidentId"]))
            statuses[(org, alert)] = row["mapping_status"]
    primary = Counter()
    optimistic = Counter()
    degrees = Counter()
    dual_top20 = 0
    for org in sorted(cohort):
        top = set(truth[org])
        primary_incidents = set()
        all_incidents = set()
        for (o, alert), incident_set in groups.items():
            if o != org:
                continue
            matches = incident_set & top
            all_incidents.update(matches)
            if statuses[(o, alert)] == "unambiguous":
                primary_incidents.update(matches)
            else:
                degrees[len(incident_set)] += 1
                dual_top20 += len(matches) >= 2
        primary["represented"] += len(primary_incidents)
        optimistic["represented"] += len(all_incidents)
    denominator = len(cohort) * 20
    report = {
        "classification": "exploratory_evaluator_only_optimistic_sensitivity_not_ground_truth",
        "organizations": len(cohort), "expert_label_denominator": denominator,
        "current_primary_represented": primary["represented"],
        "all_assignment_edges_optimistic_represented": optimistic["represented"],
        "additional_potentially_represented": optimistic["represented"] - primary["represented"],
        "minimum_additional_for_95_percent": max(0, (95 * denominator + 99) // 100 - primary["represented"]),
        "ambiguous_alert_incident_degree_counts": dict(sorted(degrees.items())),
        "ambiguous_alerts_linked_to_multiple_top20_incidents": dual_top20,
        "multi_membership_semantics_confirmed": False,
        "primary_denominator_changed": False,
        "interpretation": "All reported incident memberships are considered only for an optimistic coverage bound. No ambiguous alert is assigned to one incident, passed to the model, or scored in the primary metric.",
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in (PRED, LEDGER, __import__("pathlib").Path(__file__))},
    }
    if report["current_primary_represented"] != 1066 or denominator != 1140:
        raise ValueError("primary cohort/coverage drift")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("expert_label_denominator", "current_primary_represented", "all_assignment_edges_optimistic_represented", "additional_potentially_represented", "minimum_additional_for_95_percent")}, indent=2))


if __name__ == "__main__":
    main()
