"""Aggregate-only audit of top-20 labels missing from the offline joint cohort."""
from __future__ import annotations

import csv
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from .guide_rerun_v2 import ROOT, check_raw, key, labels
from .phase2 import sha256_file

PREDICTIONS = ROOT / "data/derived/offline_joint_v2/predictions.pkl"
MEMBERSHIP = ROOT / "data/derived/preprocessing/evaluator/incident_membership.csv"
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
OUTPUT = ROOT / "outputs/phase_a/coverage_20261111.json"


def main():
    if OUTPUT.exists():
        raise FileExistsError("coverage audit exists; preserve it and choose a new version")
    check_raw()
    freeze = json.loads((ROOT / "outputs/offline_joint_v2/prediction_freeze.json").read_text())
    if sha256_file(PREDICTIONS) != freeze["sha256"][str(PREDICTIONS.relative_to(ROOT))]:
        raise ValueError("offline joint prediction hash mismatch")
    with PREDICTIONS.open("rb") as stream:
        predicted = pickle.load(stream)
    orgs = set(predicted)
    if len(orgs) != 57:
        raise ValueError("unexpected organization cohort")
    rank_by_org = labels(orgs)
    in_scope = {a for result in predicted.values() for a in result["input_alert_keys"]}
    seen = defaultdict(lambda: defaultdict(set))
    with MEMBERSHIP.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            org = row["OrgId"]
            if org not in orgs:
                continue
            incident = key(org, row["IncidentId"])
            if incident not in rank_by_org[org]:
                continue
            alert = key(org, row["AlertId"])
            status = row["mapping_status"]
            seen[(org, incident)][status].add(alert)
            if status == "unambiguous" and alert not in in_scope:
                seen[(org, incident)]["unambiguous_missing_from_prepared"].add(alert)
    categories = Counter()
    status_counts = Counter()
    for org in orgs:
        for incident in rank_by_org[org]:
            statuses = seen[(org, incident)]
            for status, alerts in statuses.items():
                status_counts[status] += len(alerts)
            if statuses.get("unambiguous") and not statuses.get("unambiguous_missing_from_prepared"):
                categories["represented_by_unambiguous_alert"] += 1
            elif statuses.get("ambiguous"):
                categories["ambiguous_only_or_unusable"] += 1
            elif statuses.get("unambiguous_missing_from_prepared"):
                categories["unambiguous_missing_from_prepared"] += 1
            else:
                categories["no_membership_ledger_alert"] += 1
    total = sum(categories.values())
    if total != 20 * len(orgs):
        raise ValueError("top-20 label accounting mismatch")
    result = {
        "classification": "exploratory_restricted_label_coverage_audit",
        "organizations": len(orgs),
        "top20_labels": total,
        "categories": dict(sorted(categories.items())),
        "membership_status_alert_assignment_counts": dict(sorted(status_counts.items())),
        "maximum_possible_end_to_end_recall_at_20_under_current_policy": categories["represented_by_unambiguous_alert"] / total,
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (PREDICTIONS, MEMBERSHIP, PREPARED,
                         ROOT / "outputs/offline_joint_v2/prediction_freeze.json", Path(__file__))
        },
        "notes": [
            "No raw organization, incident, alert, or evidence identifiers are exported.",
            "The audit describes the already-accessed 57-organization exploratory cohort.",
            "It cannot establish source semantics or an untouched confirmatory cohort.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("organizations", "top20_labels", "categories",
                                           "maximum_possible_end_to_end_recall_at_20_under_current_policy")},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
