"""One prespecified candidate-route ablation; inference never imports evaluator labels."""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import (PARENT, generate, read_docs,
    MAX_TOKEN_FREQUENCY, MAX_NEAREST_PER_SIDE, TIME_ENTITY_SECONDS,
    TIME_TECHNIQUE_SECONDS, RARE_TOKEN_FREQUENCY)
from .submission_entity_time_pair_v2 import (shard_map, predict_probability, groups_at)
from .submission_group_merge_v10_v2 import load_models, score_groups_v7
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


CONFIG = ROOT / "configs/phase9e_bounded_candidate_v1.json"
RUN = "phase9e_bounded_candidate_20261115_v1"
CANDIDATE_RUN = "submission_full_entity_time_20261114_v1"
V2_RUN = "submission_entity_time_pair_v2_20261114_v1"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
FROZEN = {
    f"outputs/{CANDIDATE_RUN}/prediction_freeze.json": "eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8",
    f"outputs/{V2_RUN}/prediction_freeze.json": "819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e",
    f"outputs/{V7_RUN}/prediction_freeze.json": "40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743",
    "outputs/submission_fragment_matching_ml_v1_20261115_v2/prediction_freeze.json": "67cb78c4c19f1c2ef54d8ee5a80657c4350e9aeb6673b75d5d97761f2adbf151",
    "outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json": "a734427180521f852364650c78fe9fec6ef27cb7af0bbb6161b33adbfecfe78d",
    "outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json": "794a02d115d78f6a8a944e0e3c5090ffd962daeabc0b23909d40628d9b279c19",
}


def config() -> dict:
    p = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (p["run_id"] != RUN or p["neighbor_before"] != MAX_NEAREST_PER_SIDE or
            p["neighbor_after"] != MAX_NEAREST_PER_SIDE + 1 or
            p["posting_cap"] != MAX_TOKEN_FREQUENCY or
            p["entity_window_seconds"] != TIME_ENTITY_SECONDS or
            p["technique_window_seconds"] != TIME_TECHNIQUE_SECONDS or
            p["pair_threshold"] != .75 or p["component_cap"] != 100):
        raise ValueError("Prespecified frozen comparison changed")
    for field in ("max_new_edges_per_alert", "max_new_edges_per_queue"):
        if not isinstance(p[field], int) or p[field] <= 0:
            raise ValueError(f"Invalid candidate budget: {field}")
    if not 0 < p["max_new_edges_fraction_of_original_queue"] <= .1:
        raise ValueError("Candidate fraction budget exceeds prespecification")
    return p


def verify_frozen() -> dict:
    for relative, expected in FROZEN.items():
        if sha256_file(ROOT / relative) != expected:
            raise ValueError(f"Frozen artifact changed: {relative}")
    return FROZEN


def sixth_neighbor_candidates(keys: list[str], docs: dict, original: np.ndarray,
                              policy: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Only sixth forward-neighbor proposals; all original flags remain untouched."""
    n = len(keys)
    old = set(map(int, original))
    proposals: dict[int, int] = {}
    stamps = [docs[k]["stamp"] for k in keys]
    entity, technique = defaultdict(list), defaultdict(list)
    for i, alert in enumerate(keys):
        for token in docs[alert]["entities"]:
            entity[token].append(i)
        for token in docs[alert]["fields"]["MitreTechniques"]:
            technique[token].append(i)
    def add(posting: list[int], seconds: int, flag: int) -> None:
        if len(posting) < 7 or len(posting) > policy["posting_cap"]:
            return
        ordered = sorted(posting, key=lambda i: (stamps[i], i))
        for pos in range(len(ordered) - 6):
            a, b = ordered[pos], ordered[pos + 6]
            if stamps[b] - stamps[a] > seconds:
                continue
            lo, hi = (a, b) if a < b else (b, a)
            encoded = lo * n + hi
            if encoded not in old:
                proposals[encoded] = proposals.get(encoded, 0) | flag
    for posting in entity.values():
        add(posting, policy["entity_window_seconds"],
            4 if len(posting) <= RARE_TOKEN_FREQUENCY else 2)
    for posting in technique.values():
        add(posting, policy["technique_window_seconds"], 8)
    limit = min(policy["max_new_edges_per_queue"],
                math.floor(len(original) * policy["max_new_edges_fraction_of_original_queue"]))
    degree = Counter()
    selected = []
    rejected_degree = 0
    for edge in sorted(proposals):
        if len(selected) >= limit:
            break
        a, b = divmod(edge, n)
        if degree[a] >= policy["max_new_edges_per_alert"] or degree[b] >= policy["max_new_edges_per_alert"]:
            rejected_degree += 1
            continue
        selected.append(edge)
        degree[a] += 1
        degree[b] += 1
    edges = np.asarray(selected, dtype=np.int64)
    flags = np.asarray([proposals[e] for e in selected], dtype=np.uint8)
    return edges, flags, {"raw_sixth_neighbor_pairs": len(proposals),
                          "added_pairs": len(edges),
                          "budget_excluded": len(proposals) - len(edges),
                          "degree_excluded_before_queue_cap": rejected_degree,
                          "queue_limit": limit,
                          "route_entity": int(np.count_nonzero(flags & 6)),
                          "route_technique": int(np.count_nonzero(flags & 8))}


def merged_edges(original: np.ndarray, original_flags: np.ndarray,
                 added: np.ndarray, added_flags: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(original) != len(original_flags) or len(added) != len(added_flags):
        raise ValueError("Candidate edge and flag alignment changed")
    if len(added) and np.intersect1d(original, added).size:
        raise ValueError("Variant overlaps frozen candidates")
    edges = np.concatenate((original, added))
    flags = np.concatenate((original_flags, added_flags))
    order = np.argsort(edges)
    return edges[order], flags[order]


def synthetic_test() -> None:
    policy = config()
    keys = [str(i) for i in range(8)]
    docs = {k: {"stamp": float(i), "entities": {("DeviceId", "x")},
                "fields": {"MitreTechniques": set()}} for i, k in enumerate(keys)}
    original = np.asarray([a * 8 + b for a in range(8) for b in range(a + 1, min(8, a + 6))], dtype=np.int64)
    added, flags, count = sixth_neighbor_candidates(keys, docs, original, policy)
    assert added.tolist() == [6, 15] and flags.tolist() == [4, 4]
    assert count["added_pairs"] == 2 and count["raw_sixth_neighbor_pairs"] == 2
    docs[keys[-1]]["stamp"] = float(200000)
    assert sixth_neighbor_candidates(keys, docs, original, policy)[0].tolist() == [6]
    all_edges, all_flags = merged_edges(original, np.zeros(len(original), dtype=np.uint8), added, flags)
    assert len(all_edges) == len(original) + 2 and np.all(np.diff(all_edges) > 0)
    print(json.dumps({"status": "pass", "synthetic_assertions": 5, "labels_read": 0}))


def load_context():
    verify_frozen()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    paths, shards = shard_map()
    if len(parent) != 499 or set(parent) != set(paths):
        raise ValueError("499-queue scope changed")
    sentinels, _ = detect_modal_sentinels()
    cf = json.loads((ROOT / f"outputs/{CANDIDATE_RUN}/prediction_freeze.json").read_text())
    gf = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    rf = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    return parent, paths, shards, sentinels, cf, gf, rf


def generate_candidates() -> None:
    policy = config()
    parent, paths, shards, sentinels, cf, _, _ = load_context()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    if public.exists() or private.exists():
        raise FileExistsError("Choose a fresh Phase 9E run version")
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    hashes, census = {}, Counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        name = key(org)
        shard = paths[org]
        frozen_path = ROOT / "data/derived" / CANDIDATE_RUN / f"{name}.pkl"
        if (sha256_file(shard) != shards["parquet_sha256"][str(shard.relative_to(ROOT))] or
                sha256_file(frozen_path) != cf["prediction_sha256"][name]):
            raise ValueError("Frozen candidate or evidence shard changed")
        with frozen_path.open("rb") as stream:
            frozen = pickle.load(stream)
        keys = parent[org]["input_alert_keys"]
        if keys != frozen["input_alert_keys"]:
            raise ValueError("Alert scope changed")
        docs = read_docs(org, shard, sentinels, set(keys))
        old, _, _ = generate(keys, docs, parent[org]["candidate_edges"])
        if not np.array_equal(old, frozen["candidate_edges"]):
            raise ValueError("Frozen candidate graph did not regenerate")
        added, flags, counts = sixth_neighbor_candidates(keys, docs, old, policy)
        path = private / f"candidates_{name}.pkl"
        with path.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "added_edges": added,
                         "added_flags": flags, "counts": counts}, stream,
                        protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(path)
        census.update({"organizations": 1, "alerts": len(keys), "original_pairs": len(old),
                       **{k: counts[k] for k in ("raw_sixth_neighbor_pairs", "added_pairs",
                                                   "budget_excluded", "degree_excluded_before_queue_cap",
                                                   "route_entity", "route_technique")}})
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Phase 9E candidates {index}/499", flush=True)
    if (census["organizations"], census["alerts"], census["original_pairs"]) != (499, 400039, 1942648):
        raise ValueError("Matched baseline scope changed")
    write_json(public / "candidate_freeze.json", {
        "classification": "prespecified_exploratory_candidate_only",
        "run": RUN, "config_sha256": sha256_file(CONFIG),
        "source_sha256": sha256_file(Path(__file__)), "frozen_sha256": FROZEN,
        "candidate_sha256": hashes, "census": dict(census),
        "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "candidates_frozen", "census": dict(census)}))


def predict() -> None:
    policy = config()
    parent, paths, shards, sentinels, cf, gf, rf = load_context()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    freeze_path = public / "candidate_freeze.json"
    if (public / "prediction_freeze.json").exists():
        raise FileExistsError("Predictions already frozen")
    freeze = json.loads(freeze_path.read_text())
    if (freeze["config_sha256"] != sha256_file(CONFIG) or
            freeze["source_sha256"] != sha256_file(Path(__file__)) or
            freeze["frozen_sha256"] != FROZEN or freeze["evaluation_labels_read"]):
        raise ValueError("Candidate freeze changed")
    pair, v4, v7, base_ranker = load_models()
    fit = json.loads((ROOT / f"outputs/{V2_RUN}/fit_freeze.json").read_text())
    if sha256_file(ROOT / "data/derived" / V2_RUN / "pair_model.pkl") != fit["model_sha256"]:
        raise ValueError("Frozen v2 pair model changed")
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    census, hashes = Counter(), {}
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        name = key(org)
        cp = private / f"candidates_{name}.pkl"
        gp = ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl"
        sp = ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl"
        fp = ROOT / "data/derived" / CANDIDATE_RUN / f"{name}.pkl"
        shard = paths[org]
        if (sha256_file(cp) != freeze["candidate_sha256"][name] or
                sha256_file(gp) != gf["prediction_sha256"][name] or
                sha256_file(sp) != rf["score_sha256"][name] or
                sha256_file(fp) != cf["prediction_sha256"][name] or
                sha256_file(shard) != shards["parquet_sha256"][str(shard.relative_to(ROOT))]):
            raise ValueError("Frozen per-queue input changed")
        with cp.open("rb") as stream: added = pickle.load(stream)
        with gp.open("rb") as stream: base = pickle.load(stream)
        with sp.open("rb") as stream: base_scores = pickle.load(stream)
        with fp.open("rb") as stream: frozen = pickle.load(stream)
        keys = base["input_alert_keys"]
        if keys != added["input_alert_keys"] or keys != frozen["input_alert_keys"]:
            raise ValueError("Prediction alert alignment changed")
        docs = read_docs(org, shard, sentinels, set(keys))
        old, old_flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        if not np.array_equal(old, frozen["candidate_edges"]):
            raise ValueError("Frozen graph changed")
        edges, flags = merged_edges(old, old_flags, added["added_edges"], added["added_flags"])
        probability = predict_probability(keys, docs, edges, flags, pair)
        groups = groups_at(keys, edges, probability, policy["pair_threshold"])
        if groups == base["groups"]:
            scores = base_scores
        else:
            scores = score_groups_v7(groups, docs, base_ranker, v4, v7, hasher)
        added_prob = probability[np.searchsorted(edges, added["added_edges"])]
        result = {"input_alert_keys": keys, "groups": groups, "scores": scores,
                  "candidate_pairs": len(edges), "original_pairs": len(old),
                  "added_edges": added["added_edges"],
                  "added_edge_scores": added_prob,
                  "linked_edges": int(np.count_nonzero(probability >= policy["pair_threshold"]))}
        out = private / f"prediction_{name}.pkl"
        with out.open("wb") as stream:
            pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(out)
        census.update({"organizations": 1, "alerts": len(keys), "candidate_pairs": len(edges),
                       "added_pairs": len(added["added_edges"]), "changed_queues": groups != base["groups"],
                       "linked_added_edges": int(np.count_nonzero(added_prob >= policy["pair_threshold"]))})
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Phase 9E predicted {index}/499", flush=True)
    if census["organizations"] != 499 or census["alerts"] != 400039:
        raise ValueError("Prediction scope changed")
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_candidate_expansion_fixed_pair_group_rank_models",
        "run": RUN, "candidate_freeze_sha256": sha256_file(freeze_path),
        "config_sha256": sha256_file(CONFIG), "source_sha256": sha256_file(Path(__file__)),
        "prediction_sha256": hashes, "census": dict(census),
        "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "candidates", "predict"))
    args = parser.parse_args()
    {"self-test": synthetic_test, "candidates": generate_candidates, "predict": predict}[args.stage]()


if __name__ == "__main__":
    main()
