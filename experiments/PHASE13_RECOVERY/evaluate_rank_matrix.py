"""Exact tie-aware evaluation of previously frozen rank vectors on frozen v2 groups."""
from __future__ import annotations

import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_entity_time import PARENT
from src.submission_full_guide import tie_aware_ranking


def main():
    target = HERE / "PHASE13_RANK_EVALUATION.json"
    if target.exists():
        raise FileExistsError("Refusing overwrite")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499:
        raise ValueError("Queue denominator changed")
    truth = read_truth(set(orgs), {a for row in parent.values() for a in row["input_alert_keys"]})
    ranks = labels(set(orgs))
    base_freeze = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json").read_text())
    blend_freeze = json.loads((ROOT / "outputs/sprint_rank_fusion_v1_20261116/prediction_freeze.json").read_text())
    v7_freeze = json.loads((ROOT / "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json").read_text())
    hard_freeze = json.loads((ROOT / "outputs/submission_hard_negative_ablation_v1_20261115_v1/prediction_freeze.json").read_text())
    totals = {k: Counter() for k in ("v7", "blend_0.25", "blend_0.5", "blend_0.75", "child40")}
    start, process = time.perf_counter(), psutil.Process()
    peak = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        paths = [
            (ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1" / f"v2_{name}.pkl", base_freeze["prediction_sha256"][name]),
            (ROOT / "data/derived/sprint_rank_fusion_v1_20261116" / f"scores_{name}.pkl", blend_freeze["score_sha256"][name]),
            (ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1" / f"scores_{name}.pkl", v7_freeze["score_sha256"][name]),
            (ROOT / "data/derived/submission_hard_negative_ablation_v1_20261115_v1" / f"scores_{name}.pkl", hard_freeze["score_sha256"][name]),
        ]
        if any(sha256_file(path) != digest for path, digest in paths):
            raise ValueError("Frozen score/group hash changed")
        with paths[0][0].open("rb") as stream: base = pickle.load(stream)
        with paths[1][0].open("rb") as stream: blend = pickle.load(stream)
        with paths[2][0].open("rb") as stream: v7 = pickle.load(stream)
        with paths[3][0].open("rb") as stream: hard = pickle.load(stream)["hard_40"]
        groups = base["groups"]
        vectors = {"v7": v7, "blend_0.25": blend["0.25"], "blend_0.5": blend["0.5"],
                   "blend_0.75": blend["0.75"], "child40": hard}
        if any(len(v) != len(groups) for v in vectors.values()):
            raise ValueError("Rank vector alignment changed")
        for method, vector in vectors.items():
            row = tie_aware_ranking(groups, vector, truth, ranks[org])
            totals[method].update(recall20=row["recall_at_20"], p10=row["precision_at_10"],
                                  ndcg20=row["ndcg_at_20_rank1_highest"])
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Phase13 rank evaluated {number}/499", flush=True)
    results = {k: {"queues": 499, "expert_top20_denominator": 9980,
                   "incident_recall20_count": round(v["recall20"] * 20),
                   "incident_recall20": v["recall20"] / 499,
                   "p10": v["p10"] / 499, "ndcg20": v["ndcg20"] / 499} for k,v in totals.items()}
    e1 = json.loads((HERE / "PHASE10_EVALUATION.json").read_text())["methods"]["E1"]
    if any(results["blend_0.75"][k] != e1[k] for k in ("incident_recall20_count", "incident_recall20", "p10", "ndcg20")):
        raise ValueError("Selected frozen blend failed exact reproduction")
    target.write_text(json.dumps({"classification": "retrospective_exploratory_frozen_ranking_comparison",
                                  "methods": results, "resource": {"wall_seconds": time.perf_counter()-start,
                                                                 "peak_process_rss_bytes": peak}}, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
