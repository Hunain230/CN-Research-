"""Label-blind Phase 10 fragment reconstruction. Run from repository root."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
from sklearn.feature_extraction import FeatureHasher

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key
from src.phase2 import sha256_file
from src.submission_full_entity_time import PARENT
from src.submission_entity_time_pair_v2 import shard_map
from src.submission_group_merge_v10_v2 import load_models, load_queue, score_groups_v7
from src.submission_ranking_ltr_v1 import featurize as hard_featurize
from src.submission_group_ranker_v4 import group_features
from src.submission_full_guide import score_groups as lexical_scores
from src.submission_trained_ranker import features as rank_features
from src.sprint_rank_fusion_v1 import percentile
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "PHASE10_EXPERIMENT_CONFIG.json"
FROZEN = {
    "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json": "eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8",
    "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json": "819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e",
    "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json": "40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743",
    "outputs/submission_hard_negative_ablation_v1_20261115_v1/prediction_freeze.json": "98af72e2080bf5ab3c4c39d84fe07321d3cab43e7517f056885e5a9e2ae4a285",
    "outputs/sprint_rank_fusion_v1_20261116/prediction_freeze.json": "6068fabdc254bbde151be57b8a6dde31207aa4ad5a824c642dbad6c27085862b",
}


def digest_alert(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def verify_parents():
    for path, expected in FROZEN.items():
        if sha256_file(ROOT / path) != expected:
            raise ValueError(f"Frozen parent changed: {path}")


def fragments(keys, groups, docs):
    membership = {}
    summaries = []
    for index, group in enumerate(groups):
        if not group:
            raise ValueError("Empty frozen fragment")
        for alert in group:
            if alert in membership:
                raise ValueError("Duplicate alert in fragments")
            membership[alert] = index
        summaries.append({
            "size": len(group),
            "entities": set().union(*(docs[a]["entities"] for a in group)),
            "categories": set().union(*(docs[a]["fields"]["Category"] for a in group)),
            "techniques": set().union(*(docs[a]["fields"]["MitreTechniques"] for a in group)),
            "start": min(docs[a]["stamp"] for a in group),
            "end": max(docs[a]["stamp"] for a in group),
        })
    if set(membership) != set(keys):
        raise ValueError("Frozen fragments do not partition alert scope")
    return np.asarray([membership[a] for a in keys], dtype=np.int32), summaries


def boundaries(keys, groups, docs, edges, probabilities, cap_records, min_max_pair=.55):
    if len(edges) != len(probabilities):
        raise ValueError("Candidate scores misaligned")
    membership, summaries = fragments(keys, groups, docs)
    n = len(keys)
    viable = set()
    for code, score in zip(edges, probabilities):
        if score < min_max_pair:
            continue
        left, right = divmod(int(code), n)
        ga, gb = int(membership[left]), int(membership[right])
        if ga != gb:
            viable.add((min(ga, gb), max(ga, gb)))
    if len(viable) > cap_records:
        raise ValueError("Viable boundary record budget exceeded; do not silently truncate")
    cross = {}
    for code, score in zip(edges, probabilities):
        left, right = divmod(int(code), n)
        ga, gb = int(membership[left]), int(membership[right])
        if ga == gb:
            continue
        if ga > gb:
            ga, gb, left, right = gb, ga, right, left
        pair = (ga, gb)
        if pair not in viable:
            continue
        row = cross.get(pair)
        if row is None:
            row = cross[pair] = {"max": 0.0, "sum": 0.0, "count": 0, "left": set(), "right": set()}
        row["max"] = max(row["max"], float(score))
        row["sum"] += float(score)
        row["count"] += 1
        row["left"].add(left)
        row["right"].add(right)
    result = {}
    for (a, b), row in cross.items():
        x, y = summaries[a], summaries[b]
        shared_entity = x["entities"] & y["entities"]
        shared_descriptor = bool(x["categories"] & y["categories"] or x["techniques"] & y["techniques"])
        joint_conflict = bool(x["categories"] and y["categories"] and not x["categories"] & y["categories"] and x["techniques"] and y["techniques"] and not x["techniques"] & y["techniques"])
        gap = max(0.0, x["start"] - y["end"], y["start"] - x["end"]) / 3600
        result[(a, b)] = {
            "max_pair": row["max"], "mean_pair": row["sum"] / row["count"],
            "edges": row["count"], "left_touched": len(row["left"]), "right_touched": len(row["right"]),
            "coverage_left": len(row["left"]) / x["size"], "coverage_right": len(row["right"]) / y["size"],
            "shared_entity": bool(shared_entity), "descriptor_agreement": shared_descriptor,
            "joint_conflict": joint_conflict, "gap_hours": gap,
        }
    return summaries, result


def score_boundary(row, weights):
    coverage = min(row["coverage_left"], row["coverage_right"])
    time_support = math.exp(-row["gap_hours"] / 24)
    return (weights["max_pair"] * row["max_pair"] + weights["mean_pair"] * row["mean_pair"]
            + weights["coverage"] * coverage + weights["shared_entity"] * int(row["shared_entity"])
            + weights["descriptor"] * int(row["descriptor_agreement"]) + weights["time"] * time_support
            - weights["joint_conflict_penalty"] * int(row["joint_conflict"]))


def verify_boundary(row, verification):
    if row["joint_conflict"] and verification["reject_joint_descriptor_conflict"]:
        return "verification_descriptor_contradiction"
    if row["gap_hours"] > verification["maximum_time_gap_hours"]:
        return "verification_temporal_uncertainty"
    if min(row["left_touched"], row["right_touched"]) < verification["minimum_distinct_endpoints_each"]:
        return "verification_insufficient_endpoints"
    if min(row["coverage_left"], row["coverage_right"]) < verification["minimum_coverage_each"]:
        return "verification_weak_reciprocal_coverage"
    return None


def reconstruct(keys, groups, summaries, boundary, policy, cfg):
    """Atomic fragments, deterministic mutual choice, bounded hierarchy, auditable vetoes."""
    parent = list(range(len(groups)))
    members = {i: {i} for i in range(len(groups))}
    decisions = []
    candidates = []
    for (a, b), row in boundary.items():
        value = score_boundary(row, cfg["scoring"])
        reason = None
        if summaries[a]["size"] + summaries[b]["size"] > cfg["cap"]:
            reason = "component_cap"
        elif row["edges"] < policy["min_edges"]:
            reason = "insufficient_cross_edges"
        elif row["max_pair"] < policy["min_max_pair"]:
            reason = "weak_max_pair"
        elif min(row["coverage_left"], row["coverage_right"]) < policy["min_coverage_each"]:
            reason = "weak_reciprocal_coverage"
        elif not row["shared_entity"]:
            reason = "no_shared_entity"
        elif row["joint_conflict"]:
            reason = "joint_descriptor_contradiction"
        elif value < policy["min_score"]:
            reason = "low_fragment_score"
        record = {"fragments": [a, b], "score": round(value, 8), "evidence": row, "decision": "rejected" if reason else "candidate", "reason": reason}
        decisions.append(record)
        if reason is None:
            candidates.append(record)
    best = {}
    for record in candidates:
        a, b = record["fragments"]
        for src, dst in ((a, b), (b, a)):
            if src not in best or (record["score"], -dst) > (best[src][0], -best[src][1]):
                best[src] = (record["score"], dst)
    candidates.sort(key=lambda x: (-x["score"], x["fragments"]))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for record in candidates:
        a, b = record["fragments"]
        ra, rb = root(a), root(b)
        reason = None
        if ra == rb:
            reason = "already_connected"
        elif policy["require_mutual_best"] and (best[a][1] != b or best[b][1] != a):
            reason = "nonmutual_best"
        elif not policy["hierarchical"] and (len(members[ra]) > 1 or len(members[rb]) > 1):
            reason = "noncascading_policy"
        elif len(members[ra]) + len(members[rb]) > cfg["maximum_fragments_per_reconstruction"]:
            reason = "fragment_growth_cap"
        elif sum(summaries[i]["size"] for i in members[ra] | members[rb]) > cfg["cap"]:
            reason = "component_cap"
        elif policy["hierarchical"] and any(
            (min(i, j), max(i, j)) not in boundary or
            score_boundary(boundary[(min(i, j), max(i, j))], cfg["scoring"]) < policy["min_score"]
            for i in members[ra] for j in members[rb]
        ):
            reason = "missing_union_cross_support"
        elif policy["verify"]:
            reason = verify_boundary(record["evidence"], cfg["verification"])
            if reason is None:
                for i in members[ra]:
                    for j in members[rb]:
                        reason = verify_boundary(boundary[(min(i, j), max(i, j))], cfg["verification"])
                        if reason:
                            break
                    if reason:
                        break
        if reason:
            record.update(decision="rejected", reason=reason)
            continue
        if ra > rb:
            ra, rb = rb, ra
        parent[rb] = ra
        members[ra] |= members.pop(rb)
        record.update(decision="accepted", reason="evidence_supported_merge")
    merged = defaultdict(list)
    for i, group in enumerate(groups):
        merged[root(i)].extend(group)
    output = sorted((sorted(group) for group in merged.values()), key=lambda x: x[0])
    if sum(map(len, output)) != len(keys) or max(map(len, output)) > cfg["cap"]:
        raise AssertionError("Scope or cap violation")
    return output, decisions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["sample", "predict"])
    parser.add_argument("--sample-queues", type=int, default=3)
    args = parser.parse_args()
    cfg = json.loads(CONFIG.read_text())
    verify_parents()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if args.stage == "sample":
        orgs = orgs[:args.sample_queues]
    elif len(orgs) != 499:
        raise ValueError("Evaluation queue scope changed")
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    models = load_models()
    hasher_v7 = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    hasher_hard = FeatureHasher(n_features=4096, input_type="dict", alternate_sign=False)
    with (ROOT / "data/derived/submission_hard_negative_ablation_v1_20261115_v1/hard_40_model.pkl").open("rb") as stream:
        hard_model = pickle.load(stream)
    base_freeze = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json").read_text())
    candidate_freeze = json.loads((ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json").read_text())
    output = HERE / ("sample_predictions" if args.stage == "sample" else "predictions")
    if output.exists():
        raise FileExistsError(f"Refusing overwrite: {output}")
    output.mkdir()
    started = time.perf_counter()
    process = psutil.Process()
    peak = 0
    hashes = {}
    totals = Counter()
    for index, org in enumerate(orgs, 1):
        name = key(org)
        item, docs, edges, probabilities = load_queue(org, parent, base_freeze, paths, shard_manifest, sentinels, models[0])
        candidate_path = ROOT / "data/derived/submission_full_entity_time_20261114_v1" / f"{name}.pkl"
        if sha256_file(candidate_path) != candidate_freeze["prediction_sha256"][name]:
            raise ValueError("Candidate graph hash mismatch")
        with candidate_path.open("rb") as stream:
            candidate = pickle.load(stream)
        if not np.array_equal(edges, candidate["candidate_edges"]):
            raise ValueError("Candidate edge mismatch")
        print(f"Queue {index}: alerts={len(item['input_alert_keys'])}, edges={len(edges)}, cap={cfg['maximum_boundary_records_per_queue']}", flush=True)
        summaries, boundary = boundaries(item["input_alert_keys"], item["groups"], docs, edges, probabilities, cfg["maximum_boundary_records_per_queue"])
        result = {"input_alert_keys": item["input_alert_keys"], "candidate_pairs": len(edges), "methods": {}}
        for method, policy in cfg["policies"].items():
            groups, decisions = reconstruct(item["input_alert_keys"], item["groups"], summaries, boundary, policy, cfg)
            if groups == item["groups"]:
                score_path = ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1" / f"scores_{name}.pkl"
                with score_path.open("rb") as stream:
                    v7_scores = pickle.load(stream)
                hard_path = ROOT / "data/derived/submission_hard_negative_ablation_v1_20261115_v1" / f"scores_{name}.pkl"
                with hard_path.open("rb") as stream:
                    hard_scores = pickle.load(stream)["hard_40"]
            else:
                v7_scores = score_groups_v7(groups, docs, models[3], models[1], models[2], hasher_v7)
                # The child40 model consumes the same queue-relative group features as its frozen fit.
                count, bm25 = lexical_scores(groups, {a: d["fields"] for a, d in docs.items()})
                old_scores = models[3].decision_function(rank_features({"count_scores": count, "bm25_scores": bm25})).tolist()
                x = hard_featurize(groups, docs, old_scores, hasher_hard)
                hard_scores = hard_model.predict(x).astype(float).tolist()
            blend = [0.25*a + 0.75*b for a, b in zip(percentile(v7_scores), percentile(hard_scores))]
            result["methods"][method] = {"groups": groups, "v7_scores": v7_scores, "blend_scores": blend,
                "decisions": decisions, "accepted": sum(d["decision"] == "accepted" for d in decisions)}
            totals[f"{method}_accepted"] += result["methods"][method]["accepted"]
            totals[f"{method}_rejected"] += sum(d["decision"] == "rejected" for d in decisions)
        file = output / f"{name}.pkl"
        with file.open("wb") as stream:
            pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(file)
        totals.update(queues=1, alerts=len(item["input_alert_keys"]), candidate_pairs=len(edges))
        peak = max(peak, process.memory_info().rss)
        if index % 25 == 0:
            print(f"Phase10 predicted {index}/{len(orgs)}", flush=True)
    freeze = {"classification": "retrospective_exploratory_label_blind_predictions", "stage": args.stage,
        "config_sha256": sha256_file(CONFIG), "code_sha256": sha256_file(Path(__file__)),
        "frozen_parent_sha256": FROZEN, "prediction_sha256": hashes, "census": dict(totals),
        "evaluator_labels_read": False, "resource": {"wall_seconds": time.perf_counter()-started,
        "peak_process_rss_bytes": peak}}
    (output / "prediction_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"status": "frozen", "stage": args.stage, "census": dict(totals), "resource": freeze["resource"]}))


if __name__ == "__main__":
    main()
