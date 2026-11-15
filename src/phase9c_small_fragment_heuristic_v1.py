"""One fixed retrospective fragment-merge experiment; no evaluator imports.

Phase 7's frozen proposals are used as the bounded candidate boundary set.
Multiple candidate edges are heuristic corroboration only: GUIDE has no source
observation lineage or evidence-availability timestamps.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import psutil
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import read_docs
from .submission_entity_time_pair_v2 import shard_map
from .submission_group_merge_v10_v2 import load_models, score_groups_v7
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


CONFIG = ROOT / "configs/phase9c_small_fragment_heuristic_v1.json"
RUN = "phase9c_small_fragment_heuristic_20261115_v1"
V2_RUN = "submission_entity_time_pair_v2_20261114_v1"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
P7_RUN = "submission_fragment_matching_ml_v1_20261115_v2"
CANDIDATE_RUN = "submission_full_entity_time_20261114_v1"
FROZEN = {
    f"outputs/{V2_RUN}/prediction_freeze.json": "819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e",
    f"outputs/{V7_RUN}/prediction_freeze.json": "40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743",
    f"outputs/{P7_RUN}/prediction_freeze.json": "67cb78c4c19f1c2ef54d8ee5a80657c4350e9aeb6673b75d5d97761f2adbf151",
    f"outputs/{CANDIDATE_RUN}/prediction_freeze.json": "eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8",
}


def config() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if value["run_id"] != RUN or [value[k] for k in
            ("candidate_run", "group_run", "rank_run", "proposal_run")] != [
            CANDIDATE_RUN, V2_RUN, V7_RUN, P7_RUN]:
        raise ValueError("Run or frozen parent changed")
    policy = value["policy"]
    if (policy["hard_component_cap"] != 100 or
            not policy["one_merge_per_original_group"] or
            not policy["non_cascading_single_pass"] or
            policy["single_edge_action"] != "review_only"):
        raise ValueError("Safety contract changed")
    return value


def verify_freezes() -> dict:
    for relative, expected in FROZEN.items():
        if sha256_file(ROOT / relative) != expected:
            raise ValueError(f"Frozen artifact changed: {relative}")
    return FROZEN


def feature(record: dict, name: str) -> float:
    return float(record["evidence"][name])


def structural_reason(record: dict, groups: list[list[str]], p: dict) -> str | None:
    left, right = record["base_group_left"], record["base_group_right"]
    if not 0 <= left < right < len(groups):
        raise ValueError("Proposal group indices not aligned to v2")
    if len(groups[left]) + len(groups[right]) > p["hard_component_cap"]:
        return "component_cap"
    if feature(record, "combined_group_size") > p["maximum_combined_group_size"]:
        return "not_small_fragment"
    if feature(record, "log_cross_edges") + 1e-6 < math.log1p(p["minimum_cross_candidate_edges"]):
        return "single_edge_review"
    if (feature(record, "log_touched_left") + 1e-6 < math.log1p(p["minimum_touched_alerts_each_side"]) or
            feature(record, "log_touched_right") + 1e-6 < math.log1p(p["minimum_touched_alerts_each_side"])):
        return "reused_endpoint_review"
    frequency = feature(record, "entity_group_frequency_min")
    if not 0 < frequency <= p["maximum_shared_entity_group_frequency"]:
        return "no_rare_entity"
    if (p["require_shared_category_or_technique"] and
            not (feature(record, "log_shared_category") > 0 or
                 feature(record, "log_shared_technique") > 0)):
        return "no_descriptor_agreement"
    if (p["reject_joint_category_and_technique_conflict"] and
            feature(record, "category_conflict") > 0 and
            feature(record, "technique_conflict") > 0):
        return "descriptor_conflict"
    if math.expm1(feature(record, "log_intergroup_hours")) > p["maximum_intergroup_gap_hours"]:
        return "time_gap"
    if float(record["model_probability"]) < p["minimum_phase7_boundary_probability"]:
        return "low_boundary_score"
    return None


def choose_merges(groups: list[list[str]], decisions: list[dict], p: dict) -> tuple[list[list[str]], list[tuple[int, int]], dict]:
    """Label-blind, bounded, mutual-best matching on original v2 group IDs."""
    if any(not g or len(g) > 100 for g in groups):
        raise ValueError("Invalid frozen group")
    if len({a for g in groups for a in g}) != sum(map(len, groups)):
        raise ValueError("Overlapping frozen groups")
    best: dict[int, list[tuple[float, int]]] = defaultdict(list)
    eligible = []
    reasons = Counter()
    seen = set()
    for row in decisions:
        pair = (int(row["base_group_left"]), int(row["base_group_right"]))
        if pair in seen:
            raise ValueError("Repeated fragment proposal")
        seen.add(pair)
        score = float(row["model_probability"])
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid frozen proposal score")
        reason = structural_reason(row, groups, p)
        reasons[reason or "structurally_eligible"] += 1
        best[pair[0]].append((score, pair[1]))
        best[pair[1]].append((score, pair[0]))
        if reason is None:
            eligible.append((score, pair))
    for rows in best.values():
        rows.sort(key=lambda x: (-x[0], x[1]))
    eligible.sort(key=lambda x: (-x[0], x[1]))
    excluded_budget = max(0, len(eligible) - p["maximum_structural_proposals_per_queue"])
    eligible = eligible[:p["maximum_structural_proposals_per_queue"]]
    used = set()
    selected = []
    for score, (left, right) in eligible:
        a, b = best[left], best[right]
        if a[0][1] != right or b[0][1] != left:
            reasons["nonmutual_review"] += 1
            continue
        margin_left = a[0][0] - a[1][0] if len(a) > 1 else 1.0
        margin_right = b[0][0] - b[1][0] if len(b) > 1 else 1.0
        if min(margin_left, margin_right) < p["minimum_mutual_best_margin"]:
            reasons["competing_neighbor_review"] += 1
            continue
        if left in used or right in used:
            reasons["already_used"] += 1
            continue
        selected.append((left, right))
        used.update((left, right))
    partner = {a: b for a, b in selected}
    partner.update({b: a for a, b in selected})
    result = []
    for i, group in enumerate(groups):
        if i not in partner:
            result.append(list(group))
        elif i < partner[i]:
            result.append(sorted(list(group) + list(groups[partner[i]])))
    result.sort(key=lambda g: g[0])
    if sum(map(len, result)) != sum(map(len, groups)) or any(len(g) > 100 for g in result):
        raise AssertionError("Merge changed scope or exceeded cap")
    return result, selected, {"proposal_reasons": dict(reasons), "budget_excluded": excluded_budget,
                              "accepted": len(selected), "reviewed_single_edges": reasons["single_edge_review"]}


def self_test() -> None:
    p = config()["policy"]
    groups = [["a", "b"], ["c", "d"], ["e", "f"]]
    def row(left, right, score, edges=2, touched=2):
        return {"base_group_left": left, "base_group_right": right,
                "model_probability": score,
                "evidence": {"combined_group_size": 4, "log_cross_edges": math.log1p(edges),
                             "log_touched_left": math.log1p(touched),
                             "log_touched_right": math.log1p(touched),
                             "entity_group_frequency_min": 2,
                             "log_shared_category": math.log1p(1),
                             "log_shared_technique": 0,
                             "category_conflict": 0, "technique_conflict": 0,
                             "log_intergroup_hours": 0}}
    merged, selected, count = choose_merges(groups, [row(0, 1, .9)], p)
    assert selected == [(0, 1)] and merged == [["a", "b", "c", "d"], ["e", "f"]]
    assert choose_merges(groups, [row(0, 1, .9, edges=1)], p)[1] == []
    assert choose_merges(groups, [row(0, 1, .9), row(1, 2, .89)], p)[1] == []
    assert choose_merges(groups, [row(0, 1, .9), row(1, 2, .2)], p)[1] == [(0, 1)]
    assert max(map(len, merged)) <= 100 and count["accepted"] == 1
    print(json.dumps({"status": "pass", "synthetic_assertions": 5, "labels_read": 0}))


def predict() -> None:
    cfg = config()
    frozen = verify_freezes()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    if public.exists() or private.exists():
        raise FileExistsError("Versioned Phase 9C run already exists")
    v2_freeze = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    v7_freeze = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    p7_freeze = json.loads((ROOT / f"outputs/{P7_RUN}/prediction_freeze.json").read_text())
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    _, v4, v7, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    process = psutil.Process()
    peak = process.memory_info().rss
    start = time.perf_counter()
    census = Counter()
    hashes = {}
    for index, org in enumerate(sorted(paths), 1):
        name = key(org)
        base_path = ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl"
        score_path = ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl"
        proposal_path = ROOT / "data/derived" / P7_RUN / f"decisions_{name}.pkl"
        for path, expected in ((base_path, v2_freeze["prediction_sha256"][name]),
                               (score_path, v7_freeze["score_sha256"][name]),
                               (proposal_path, p7_freeze["decision_sha256"][name])):
            if sha256_file(path) != expected:
                raise ValueError("Frozen per-organization artifact changed")
        with base_path.open("rb") as stream:
            base = pickle.load(stream)
        with score_path.open("rb") as stream:
            base_scores = pickle.load(stream)
        with proposal_path.open("rb") as stream:
            decisions = pickle.load(stream)
        if len(base["groups"]) != len(base_scores):
            raise ValueError("Frozen score alignment changed")
        groups, selected, counts = choose_merges(base["groups"], decisions, cfg["policy"])
        if selected:
            shard = paths[org]
            if sha256_file(shard) != shard_manifest["parquet_sha256"][str(shard.relative_to(ROOT))]:
                raise ValueError("Evidence shard changed")
            docs = read_docs(org, shard, sentinels, set(base["input_alert_keys"]))
            scores = score_groups_v7(groups, docs, base_ranker, v4, v7, hasher)
        else:
            scores = base_scores
        output = private / f"groups_{name}.pkl"
        with output.open("wb") as stream:
            pickle.dump({"input_alert_keys": base["input_alert_keys"], "groups": groups,
                         "scores": scores, "selected_original_group_pairs": selected,
                         "decision_counts": counts,
                         "candidate_pairs": base["candidate_pairs"]}, stream,
                        protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(output)
        census.update({"organizations": 1, "alerts": len(base["input_alert_keys"]),
                       "candidate_pairs": base["candidate_pairs"],
                       "selected_merges": len(selected),
                       "proposals": len(decisions),
                       "single_edge_review": counts["reviewed_single_edges"],
                       "budget_excluded": counts["budget_excluded"]})
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Phase 9C predicted {index}/499", flush=True)
    if (census["organizations"], census["alerts"], census["candidate_pairs"]) != (499, 400039, 1942648):
        raise ValueError("Frozen matched scope changed")
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_heuristic_prediction_not_provenance_verified",
        "run": RUN, "config_sha256": sha256_file(CONFIG),
        "code_sha256": sha256_file(Path(__file__)), "frozen_parent_sha256": frozen,
        "prediction_sha256": hashes, "census": dict(census),
        "evaluator_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - start,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict"))
    stage = parser.parse_args().stage
    {"self-test": self_test, "predict": predict}[stage]()


if __name__ == "__main__":
    main()
