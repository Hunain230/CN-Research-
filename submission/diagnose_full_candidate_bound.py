"""Evaluator-only candidate-connectivity and group-failure diagnostic."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT


RUN = "submission_full_entity_time_20261114_v1"
FREEZE = ROOT / "outputs" / RUN / "prediction_freeze.json"
PARENT = ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl"
OUT = ROOT / "outputs/submission_full_candidate_bound_20261114_v1.json"
MAX_GROUP = 100


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Diagnostic already frozen")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    all_alerts = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    counts = Counter()
    size_buckets = defaultdict(Counter)
    for org in sorted(orgs):
        path = ROOT / "data/derived" / RUN / f"{key(org)}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][key(org)]:
            raise ValueError("Prediction changed")
        with path.open("rb") as stream:
            item = pickle.load(stream)
        keys = item["input_alert_keys"]
        n = len(keys)
        parent_id = list(range(n))
        size = [1] * n

        def root(i: int) -> int:
            while parent_id[i] != i:
                parent_id[i] = parent_id[parent_id[i]]
                i = parent_id[i]
            return i

        for edge in item["candidate_edges"]:
            i, j = divmod(int(edge), n)
            if truth[keys[i]] != truth[keys[j]]:
                continue
            a, b = root(i), root(j)
            if a != b:
                if size[a] < size[b]:
                    a, b = b, a
                parent_id[b] = a
                size[a] += size[b]
        gold_counts = Counter(truth[a] for a in keys)
        largest = Counter()
        by_gold_root = defaultdict(Counter)
        for i, alert in enumerate(keys):
            by_gold_root[truth[alert]][root(i)] += 1
        for gold, parts in by_gold_root.items():
            largest[gold] = max(parts.values())
        group_overlap = defaultdict(list)
        for group in item["groups"]:
            for gold, overlap in Counter(truth[a] for a in group).items():
                if gold in ranks[org]:
                    group_overlap[gold].append((overlap, len(group)))
        for gold in ranks[org]:
            counts["labels"] += 1
            observed = gold_counts[gold]
            bucket = "absent" if observed == 0 else "1" if observed == 1 else "2-10" if observed <= 10 else "11-100" if observed <= 100 else ">100"
            row = size_buckets[bucket]
            row["labels"] += 1
            if observed == 0:
                counts["absent"] += 1; row["absent"] += 1
                continue
            counts["present"] += 1; row["present"] += 1
            if observed > MAX_GROUP / .8:
                counts["cap_impossible"] += 1; row["cap_impossible"] += 1
            if largest[gold] / observed >= .8:
                counts["candidate_connected_80"] += 1; row["candidate_connected_80"] += 1
            else:
                counts["candidate_disconnected"] += 1; row["candidate_disconnected"] += 1
            viable = any(overlap / observed >= .8 and overlap / group_size >= .8
                         for overlap, group_size in group_overlap[gold])
            if viable:
                counts["group_recoverable"] += 1; row["group_recoverable"] += 1
            elif max((overlap for overlap, _ in group_overlap[gold]), default=0) / observed < .8:
                counts["group_split_below_80"] += 1; row["group_split_below_80"] += 1
            else:
                counts["group_impure"] += 1; row["group_impure"] += 1
    result = {
        "classification": "evaluator_only_oracle_candidate_connectivity_bound_not_model_performance",
        "run": RUN, "counts": dict(counts),
        "size_buckets": {name: dict(row) for name, row in size_buckets.items()},
        "candidate_connected_upper_bound_recall20": counts["candidate_connected_80"] / counts["labels"],
        "observed_group_oracle_order_ceiling": counts["group_recoverable"] / counts["labels"],
        "prediction_freeze_sha256": sha256_file(FREEZE),
        "analysis_code_sha256": sha256_file(Path(__file__)),
        "note": "Candidate bound assumes oracle same-incident link decisions and ignores purity; size cap remains a separate restriction.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": result["counts"],
                      "candidate_bound": result["candidate_connected_upper_bound_recall20"]}))


if __name__ == "__main__":
    main()
