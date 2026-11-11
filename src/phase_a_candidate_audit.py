"""Aggregate-only full-small-queue candidate recall audit for Phase A."""
from __future__ import annotations

import json
import math
import pickle
from collections import Counter
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import ROOT, PRIVATE, bootstrap, check_raw, key
from .offline_joint_comparison import PREDICTIONS, read_truth
from .phase2 import sha256_file

OUTPUT = ROOT / "outputs/phase_a/candidate_20261111.json"
SOURCE_FREEZE = ROOT / "outputs/guide_rerun_v2/correlation_prediction_freeze.json"


def main():
    if OUTPUT.exists():
        raise FileExistsError("candidate audit exists; preserve it and choose a new version")
    check_raw()
    with PREDICTIONS.open("rb") as stream:
        predicted = pickle.load(stream)
    orgs = set(predicted)
    all_alerts = {a for result in predicted.values() for a in result["input_alert_keys"]}
    truth = read_truth(orgs, all_alerts)
    source_hashes = json.loads(SOURCE_FREEZE.read_text())["hashes"]
    rows = []
    for org, result in sorted(predicted.items()):
        path = PRIVATE / "correlation_predictions" / f"{key(org)}.npz"
        if sha256_file(path) != source_hashes[key(org)]:
            raise ValueError("frozen candidate hash mismatch")
        with np.load(path) as arr:
            keys = arr["keys"].tolist()
            edges = arr["edges"]
        if set(keys) != set(result["input_alert_keys"]):
            raise ValueError("candidate alert population differs from joint comparison")
        n = len(keys)
        group_sizes = Counter(truth[a] for a in keys)
        positive = sum(v * (v - 1) // 2 for v in group_sizes.values())
        candidate_positive = sum(truth[keys[int(e // n)]] == truth[keys[int(e % n)]] for e in edges)
        possible = n * (n - 1) // 2
        rows.append({"positive": positive, "candidate_positive": candidate_positive,
                     "candidates": len(edges), "possible_pairs": possible,
                     "candidate_recall": candidate_positive / positive if positive else None,
                     "candidate_coverage": len(edges) / possible if possible else None})
    totals = {k: sum(r[k] for r in rows) for k in
              ("positive", "candidate_positive", "candidates", "possible_pairs")}
    result = {
        "classification": "exploratory_full_small_queue_candidate_audit",
        "organizations": len(rows),
        "organizations_with_positive_pairs": sum(r["positive"] > 0 for r in rows),
        "alerts": len(all_alerts),
        "source_neighbor_cap_per_route": 200,
        "totals": totals,
        "micro_candidate_recall": (totals["candidate_positive"] / totals["positive"]
                                   if totals["positive"] else None),
        "macro_candidate_recall": bootstrap([r["candidate_recall"] for r in rows
                                              if r["candidate_recall"] is not None]),
        "candidate_pair_coverage": totals["candidates"] / totals["possible_pairs"],
        "target_positive_pair_candidate_recall": 0.99,
        "target_met": (totals["candidate_positive"] / totals["positive"] >= 0.99
                       if totals["positive"] else False),
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                          (PREDICTIONS, SOURCE_FREEZE, Path(__file__))},
        "notes": [
            "Same 57 complete small ambiguity-excluded queues as offline_joint_v2.",
            "The frozen candidate set was previously evaluated and this is exploratory.",
            "Candidate recall is not pair-classification recall or end-to-end Recall@20.",
            "No organization, alert, or incident identifiers are exported.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("organizations", "alerts", "micro_candidate_recall",
                                           "macro_candidate_recall", "candidate_pair_coverage",
                                           "target_met")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
