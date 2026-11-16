"""Label-blind one-pass evidence-weighted fragment matching on frozen graph."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key
from src.phase2 import sha256_file
from src.submission_entity_time_pair_v2 import shard_map
from src.submission_full_entity_time import read_docs
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels
from reconstruct import boundaries


def score(row, diverse, weights):
    return (weights["max_pair"] * row["max_pair"] + weights["mean_pair"] * row["mean_pair"]
            + weights["min_reciprocal_coverage"] * min(row["coverage_left"], row["coverage_right"])
            + weights["shared_entity"] * int(row["shared_entity"])
            + weights["descriptor_agreement"] * int(row["descriptor_agreement"])
            + weights["route_diversity"] * int(diverse)
            + weights["time_support"] * math.exp(-row["gap_hours"] / 24)
            - weights["joint_conflict_penalty"] * int(row["joint_conflict"]))


def match_fragments(keys, groups, boundary, routes, policy, weights):
    proposals = []
    decisions = []
    for (a, b), row in sorted(boundary.items()):
        diverse = routes.get((a, b), 0).bit_count() >= 2
        value = score(row, diverse, weights)
        reason = None
        if len(groups[a]) + len(groups[b]) > 100:
            reason = "cap"
        elif row["joint_conflict"]:
            reason = "descriptor_contradiction"
        elif row["max_pair"] < policy["min_max_pair"]:
            reason = "weak_max_pair"
        elif row["edges"] < policy["min_edges"]:
            reason = "insufficient_edges"
        elif min(row["coverage_left"], row["coverage_right"]) < policy["min_coverage_each"]:
            reason = "weak_reciprocal_coverage"
        elif min(row["left_touched"], row["right_touched"]) < policy["min_distinct_endpoints_each"]:
            reason = "insufficient_distinct_endpoints"
        elif policy["require_route_diversity"] and not diverse:
            reason = "single_route"
        elif value < policy["min_score"]:
            reason = "weak_aggregate_score"
        item = {"fragments": [a, b], "score": round(value, 8),
                "max_pair": row["max_pair"], "mean_pair": row["mean_pair"],
                "edges": row["edges"], "coverage_left": row["coverage_left"],
                "coverage_right": row["coverage_right"], "left_touched": row["left_touched"],
                "right_touched": row["right_touched"], "shared_entity": row["shared_entity"],
                "descriptor_agreement": row["descriptor_agreement"],
                "joint_conflict": row["joint_conflict"], "gap_hours": row["gap_hours"],
                "route_diversity": diverse, "reason": reason}
        decisions.append(item)
        if reason is None:
            proposals.append((a, b, value))
    best = {}
    for a, b, value in proposals:
        for left, right in ((a, b), (b, a)):
            if left not in best or (value, -right) > (best[left][1], -best[left][0]):
                best[left] = (right, value)
    eligible = [(a, b, value) for a, b, value in proposals
                if best[a][0] == b and best[b][0] == a]
    eligible.sort(key=lambda item: (-item[2], item[0], item[1]))
    used, selected = set(), set()
    for a, b, _ in eligible:
        if a not in used and b not in used:
            used.update((a, b))
            selected.add((a, b))
    partner = {a: b for a, b in selected} | {b: a for a, b in selected}
    output = []
    for i, group in enumerate(groups):
        if i not in partner:
            output.append(group)
        elif i < partner[i]:
            output.append(sorted(group + groups[partner[i]]))
    output.sort(key=lambda g: g[0])
    for item in decisions:
        a, b = item["fragments"]
        if item["reason"] is None:
            item["reason"] = "accepted" if (a, b) in selected else "not_mutual_best"
    if sorted(x for group in output for x in group) != sorted(keys):
        raise AssertionError("Fragment matching changed alert scope")
    return output, decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-queues", type=int, default=0)
    args = parser.parse_args()
    cfg_path = HERE / "EVIDENCE_GRAPH_CONFIG.json"
    cfg = json.loads(cfg_path.read_text())
    source = ROOT / "experiments/PHASE13_RECOVERY/c_predictions"
    source_freeze = json.loads((source / "prediction_freeze.json").read_text())
    output = HERE / ("evidence_graph_sample" if args.sample_queues else "evidence_graph_predictions")
    if output.exists():
        raise FileExistsError(f"Refusing overwrite: {output}")
    names = list(source_freeze["prediction_sha256"])
    if args.sample_queues:
        names = names[:args.sample_queues]
    paths, _ = shard_map()
    sentinels, _ = detect_modal_sentinels()
    # Org-to-opaque-name mapping is read from the frozen parent, never evaluator labels.
    from src.submission_full_entity_time import PARENT
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    org_by_name = {key(org): org for org in parent}
    output.mkdir()
    start, process = time.perf_counter(), psutil.Process()
    hashes, count, peak = {}, Counter(), 0
    with gzip.open(output / "merge_provenance.jsonl.gz", "xt", encoding="utf-8") as trace:
        for number, name in enumerate(names, 1):
            source_file = source / f"{name}.pkl"
            if sha256_file(source_file) != source_freeze["prediction_sha256"][name]:
                raise ValueError("Frozen C prediction hash mismatch")
            with source_file.open("rb") as stream:
                row = pickle.load(stream)
            org = org_by_name[name]
            docs = read_docs(org, paths[org], sentinels, set(row["keys"]))
            groups = row["groups"]["0.75"]
            _, boundary = boundaries(row["keys"], groups, docs, row["edges"], row["probabilities"],
                                     cfg["boundary_max_records_per_queue"], cfg["minimum_viable_max_pair"])
            group_of = {alert: i for i, group in enumerate(groups) for alert in group}
            routes = defaultdict(int)
            n = len(row["keys"])
            for code, flag, p in zip(row["edges"], row["flags"], row["probabilities"]):
                if p < cfg["minimum_viable_max_pair"]:
                    continue
                a, b = divmod(int(code), n)
                ga, gb = group_of[row["keys"][a]], group_of[row["keys"][b]]
                if ga != gb:
                    routes[(min(ga, gb), max(ga, gb))] |= (1 if flag & 1 else 0) | (2 if flag & 6 else 0) | (4 if flag & 8 else 0)
            result = {"keys": row["keys"], "methods": {}}
            for method, policy in cfg["policies"].items():
                new_groups, decisions = match_fragments(row["keys"], groups, boundary, routes, policy, cfg["score"])
                result["methods"][method] = {"groups": new_groups,
                                              "accepted": sum(d["reason"] == "accepted" for d in decisions)}
                for decision in decisions:
                    trace.write(json.dumps({"queue_key": name, "method": method, **decision}, separators=(",", ":")) + "\n")
                    count[f"{method}_{decision['reason']}"] += 1
            path = output / f"{name}.pkl"
            with path.open("wb") as stream:
                pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
            hashes[name] = sha256_file(path)
            count.update(queues=1, alerts=len(row["keys"]), candidate_edges=len(row["edges"]))
            peak = max(peak, process.memory_info().rss)
            if number % 25 == 0 or args.sample_queues:
                print(f"Evidence graph predicted {number}/{len(names)}", flush=True)
    freeze = {"classification": "label_blind_retrospective_predictions", "sample": bool(args.sample_queues),
              "code_sha256": sha256_file(Path(__file__)), "config_sha256": sha256_file(cfg_path),
              "source_freeze_sha256": sha256_file(source / "prediction_freeze.json"),
              "prediction_sha256": hashes, "provenance_sha256": sha256_file(output / "merge_provenance.jsonl.gz"),
              "counts": dict(count), "resource": {"wall_seconds": time.perf_counter()-start,
                                                   "peak_process_rss_bytes": peak},
              "evaluator_labels_read": False}
    (output / "prediction_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"status": "frozen", "counts": dict(count), "resource": freeze["resource"]}))


if __name__ == "__main__":
    main()
