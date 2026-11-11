"""Aggregate-only analysis of positive pairs missed by frozen GUIDE retrieval."""
from __future__ import annotations

import json
import pickle
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import ROOT, PRIVATE, FIELDS, check_raw, key
from .offline_joint_comparison import PREDICTIONS, read_truth
from .phase2 import sha256_file

OUTPUT = ROOT / "outputs/phase_a/missed_positive_pairs_20261111.json"
PREPARED = PRIVATE / "prepared.pkl"
SOURCE_FREEZE = ROOT / "outputs/guide_rerun_v2/correlation_prediction_freeze.json"


def main():
    if OUTPUT.exists():
        raise FileExistsError("miss analysis already exists; preserve it")
    check_raw()
    with PREDICTIONS.open("rb") as stream:
        predicted = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        alerts = pickle.load(stream)["alerts"]
    orgs = set(predicted)
    all_alerts = {a for item in predicted.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, all_alerts)
    expected_hashes = json.loads(SOURCE_FREEZE.read_text())["hashes"]
    totals = defaultdict(int)
    for org, item in sorted(predicted.items()):
        path = PRIVATE / "correlation_predictions" / f"{key(org)}.npz"
        if sha256_file(path) != expected_hashes[key(org)]:
            raise ValueError("frozen correlation candidates changed")
        with np.load(path) as arr:
            keys = arr["keys"].tolist()
            edge_ids = set(int(x) for x in arr["edges"])
        if set(keys) != set(item["input_alert_keys"]):
            raise ValueError("alert set changed")
        index = {a: i for i, a in enumerate(keys)}
        n = len(keys)
        groups = defaultdict(list)
        for a in keys:
            groups[truth[a]].append(a)
        sets = {a: {f: set(alerts[a]["fields"][f]) for f in FIELDS} for a in keys}
        for members in groups.values():
            for left, right in combinations(members, 2):
                i, j = sorted((index[left], index[right]))
                if i * n + j in edge_ids:
                    totals["retrieved_positive_pairs"] += 1
                    continue
                totals["missed_positive_pairs"] += 1
                shared = [f for f in FIELDS if sets[left][f] & sets[right][f]]
                if not shared:
                    totals["missed_with_no_shared_allowed_descriptor"] += 1
                else:
                    totals["missed_with_shared_allowed_descriptor"] += 1
                    for f in shared:
                        totals[f"missed_shared_{f}"] += 1
    missed = totals["missed_positive_pairs"]
    result = {
        "classification": "exploratory_evaluator_only_retrieval_error_analysis",
        "organizations": len(orgs),
        "counts": dict(sorted(totals.items())),
        "missed_fraction_without_any_shared_allowed_descriptor": (
            totals["missed_with_no_shared_allowed_descriptor"] / missed if missed else None),
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                          (PREDICTIONS, PREPARED, SOURCE_FREEZE, Path(__file__))},
        "notes": [
            "This evaluator-only diagnostic reads gold membership after frozen predictions.",
            "It does not create or change model-facing retrieval features.",
            "Only aggregate counts are exported; no identifiers or pair examples.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"organizations": result["organizations"],
                      "missed_positive_pairs": missed,
                      "missed_with_no_shared_allowed_descriptor": totals["missed_with_no_shared_allowed_descriptor"],
                      "fraction": result["missed_fraction_without_any_shared_allowed_descriptor"]},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
