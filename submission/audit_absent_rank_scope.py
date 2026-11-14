"""Check whether expert-ranked incidents missing from model scope exist anywhere in raw GUIDE_Test."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json


OUT = ROOT / "outputs/submission_absent_rank_scope_audit_20261114_v1.json"
RAW = ROOT / "data/raw/GUIDE_Test.csv"


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Rank-scope audit already frozen")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    truth = read_truth(orgs, {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(orgs)
    in_scope = defaultdict(set)
    for org, item in parent.items():
        in_scope[org].update(truth[a] for a in item["input_alert_keys"])
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    raw_incidents = defaultdict(set)
    cursor = con.execute("SELECT DISTINCT OrgId, IncidentId FROM read_csv(?, header=true, all_varchar=true)", [str(RAW)])
    while batch := cursor.fetchmany(10000):
        for org, incident in batch:
            if org in orgs:
                raw_incidents[org].add(incident)
    con.close()
    c = Counter()
    for org in orgs:
        for gold in ranks[org]:
            c["expert_top20_labels"] += 1
            if gold in in_scope[org]:
                c["present_unambiguous"] += 1
            elif gold in raw_incidents[org]:
                c["absent_unambiguous_but_present_raw"] += 1
            else:
                c["absent_from_raw_test_incidents"] += 1
    if c["expert_top20_labels"] != 9980 or c["present_unambiguous"] != 9125:
        raise ValueError("Rank scope changed")
    result = {"classification": "evaluator_only_aggregate_rank_scope_audit_not_metric_redefinition",
              "counts": dict(c),
              "denominator_policy": "retain_all_9980_expert_labels_in_recall20",
              "resolution": "obtain_publisher_queue_snapshot_or_matching_alert_export_before_any_new_cohort_evaluation",
              "analysis_code_sha256": sha256_file(Path(__file__)), "raw_sha256": sha256_file(RAW)}
    write_json(OUT, result)
    print(json.dumps(c, sort_keys=True))


if __name__ == "__main__":
    main()
