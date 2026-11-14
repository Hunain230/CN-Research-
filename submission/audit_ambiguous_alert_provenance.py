"""Aggregate evaluator-only provenance audit of ambiguous alert keys."""

from __future__ import annotations

import csv
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json


RAW = ROOT / "data/raw/GUIDE_Test.csv"
AMBIGUOUS = ROOT / "data/derived/preprocessing/review/ambiguous_alert_memberships.csv"
OUT = ROOT / "outputs/submission_ambiguous_provenance_audit_20261114_v1.json"


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Ambiguity audit already frozen")
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute("CREATE TEMP TABLE ambiguous AS SELECT OrgId,AlertId FROM read_csv(?, header=true, all_varchar=true)", [str(AMBIGUOUS)])
    cursor = con.execute("""
        SELECT COUNT(*) AS evidence_rows,
               COUNT(DISTINCT IncidentId) AS incident_assignments,
               COUNT(DISTINCT Id) AS source_incident_ids,
               COUNT(DISTINCT Timestamp) AS timestamps,
               COUNT(DISTINCT DetectorId) AS detectors,
               COUNT(DISTINCT AlertTitle) AS titles,
               COUNT(DISTINCT Category) AS categories,
               COUNT(DISTINCT MitreTechniques) AS techniques
        FROM read_csv(?, header=true, all_varchar=true) AS raw
        JOIN ambiguous USING (OrgId, AlertId)
        GROUP BY raw.OrgId, raw.AlertId
    """, [str(RAW)])
    counts = Counter()
    for row in cursor.fetchall():
        evidence_rows, assignments, source_ids, timestamps, detectors, titles, categories, techniques = row
        counts["ambiguous_keys"] += 1
        counts["evidence_rows"] += evidence_rows
        counts["multiple_incident_assignments"] += assignments > 1
        counts["single_timestamp"] += timestamps == 1
        counts["multiple_timestamps"] += timestamps > 1
        counts["single_detector"] += detectors == 1
        counts["multiple_detectors"] += detectors > 1
        counts["single_title"] += titles == 1
        counts["multiple_titles"] += titles > 1
        counts["multiple_categories"] += categories > 1
        counts["multiple_techniques"] += techniques > 1
        counts["source_id_distinguishes_assignments"] += source_ids >= assignments
    con.close()
    if counts["ambiguous_keys"] != 70702 or counts["multiple_incident_assignments"] != 70702:
        raise ValueError("Ambiguous key census changed")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    truth = read_truth(orgs, {a for item in parent.values() for a in item["input_alert_keys"]})
    top20 = labels(orgs)
    present = defaultdict(set)
    for org, item in parent.items():
        present[org].update(truth[a] for a in item["input_alert_keys"])
    ambiguous_incidents = defaultdict(set)
    with AMBIGUOUS.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["OrgId"] in orgs:
                ambiguous_incidents[row["OrgId"]].update(json.loads(row["IncidentAssignments"]))
    absent = Counter()
    for org in orgs:
        for gold in top20[org]:
            if gold in present[org]:
                continue
            absent["all_absent_from_unambiguous_scope"] += 1
            absent["has_ambiguous_source_rows"] += gold in ambiguous_incidents[org]
            absent["no_ambiguous_source_rows"] += gold not in ambiguous_incidents[org]
    if absent["all_absent_from_unambiguous_scope"] != 855:
        raise ValueError("Absent top-20 census changed")
    result = {
        "classification": "aggregate_evaluator_only_ambiguous_alert_provenance_no_label_based_resolution",
        "ambiguous_key_counts": dict(counts), "absent_top20_label_counts": dict(absent),
        "resolution_decision": "retain_exclusion_until_alert_identity_or_assignment_is_authoritatively_disambiguated_without_using_evaluation_labels",
        "source_ordinals_note": "Source row ordinals identify evidence rows, but do not provide a unique prediction-time alert-to-incident assignment.",
        "analysis_code_sha256": sha256_file(Path(__file__)),
        "raw_sha256": sha256_file(RAW), "ambiguous_review_sha256": sha256_file(AMBIGUOUS),
    }
    write_json(OUT, result)
    print(json.dumps({"ambiguous_keys": counts["ambiguous_keys"],
                      "absent_top20": dict(absent)}, sort_keys=True))


if __name__ == "__main__":
    main()
