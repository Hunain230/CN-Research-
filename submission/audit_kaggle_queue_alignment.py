"""Freeze the publisher ranking-file match and aggregate raw incident alignment."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from src.guide_rerun_v2 import key, labels
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json


OUT = ROOT / "outputs/submission_kaggle_queue_alignment_20261114_v1.json"
LOCAL = ROOT / "data/raw/GUIDE_Test_Queue_Rankings.csv"
DOWNLOADED = ROOT / "data/derived/publisher_queue_audit_20261114/GUIDE_Test_Queue_Rankings.csv"
RAW = ROOT / "data/raw/GUIDE_Test.csv"


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Publisher alignment audit already frozen")
    if sha256_file(LOCAL) != sha256_file(DOWNLOADED):
        raise ValueError("Local and freshly downloaded Kaggle ranking files differ")
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    raw_incidents = defaultdict(set)
    cursor = con.execute("SELECT DISTINCT OrgId, IncidentId FROM read_csv(?, header=true, all_varchar=true)", [str(RAW)])
    while batch := cursor.fetchmany(10000):
        for org, incident in batch:
            raw_incidents[org].add(key(org, incident))
    con.close()
    with LOCAL.open(encoding="utf-8", newline="") as stream:
        ranked_orgs = {row["OrgId"] for row in csv.DictReader(stream)}
    ranks = labels(ranked_orgs)
    counts = Counter()
    absent_by_rank = Counter()
    for org, ranking in ranks.items():
        for incident, rank in ranking.items():
            counts["expert_labels"] += 1
            if incident not in raw_incidents[org]:
                counts["absent_raw_incident_pairs"] += 1
                absent_by_rank[str(rank)] += 1
                counts["absent_rank_1_to_10"] += int(int(rank) <= 10)
                counts["absent_rank_11_to_20"] += int(int(rank) > 10)
    if counts["expert_labels"] != 9980:
        raise ValueError("Benchmark source alignment changed")
    result = {
        "classification": "publisher_file_identity_and_aggregate_rank_scope_audit_not_metric_revision",
        "publisher_url": "https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction/data",
        "download_command": "python -m kaggle datasets download Microsoft/microsoft-security-incident-prediction -f GUIDE_Test_Queue_Rankings.csv --unzip",
        "ranking_file_byte_identical": True,
        "local_ranking_sha256": sha256_file(LOCAL),
        "downloaded_ranking_sha256": sha256_file(DOWNLOADED),
        "raw_local_sha256": sha256_file(RAW),
        "raw_local_bytes": RAW.stat().st_size,
        "counts": dict(counts),
        "absent_by_rank": {str(k): absent_by_rank[str(k)] for k in range(1, 21)},
        "rank_direction_note": "Rank-position counts are descriptive; numeric direction remains a local assumption until confirmed.",
        "denominator_policy": "retain_all_9980_expert_labels",
        "analysis_code_sha256": sha256_file(Path(__file__)),
    }
    write_json(OUT, result)
    print(json.dumps({"ranking_file_byte_identical": True, "counts": dict(counts)}, sort_keys=True))


if __name__ == "__main__":
    main()
