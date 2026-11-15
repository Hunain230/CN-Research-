"""One fixed queue-disjoint hard-negative pair-scorer experiment.

Training reads incident membership only for historical training organizations.
Prediction reads no expert membership, rank, grade, or outcome.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import PARENT, generate, read_docs
from .submission_entity_time_pair_v2 import (SPLIT, shard_map, predict_probability,
    groups_at, edge_features, token_frequencies)
from .submission_group_merge_v10_v2 import load_models, score_groups_v7
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


RUN = "phase9g_pair_boundary_20261115_v1"
CONFIG = ROOT / "configs/phase9g_pair_boundary_v1.json"
CANDIDATE_RUN = "submission_full_entity_time_20261114_v1"
V2_RUN = "submission_entity_time_pair_v2_20261114_v1"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
FROZEN = {
    f"outputs/{CANDIDATE_RUN}/prediction_freeze.json": "eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8",
    f"outputs/{V2_RUN}/prediction_freeze.json": "819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e",
    f"outputs/{V7_RUN}/prediction_freeze.json": "40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743",
    "outputs/submission_fragment_matching_ml_v1_20261115_v2/prediction_freeze.json": "67cb78c4c19f1c2ef54d8ee5a80657c4350e9aeb6673b75d5d97761f2adbf151",
    "outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json": "a734427180521f852364650c78fe9fec6ef27cb7af0bbb6161b33adbfecfe78d",
    "outputs/phase9e_bounded_candidate_20261115_v1/prediction_freeze.json": "7f5d2d0b3372546d0d2028529f107038c04ea77da160d1f9cbf39907e8098f82",
}


def config() -> dict:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (c["run_id"] != RUN or c["pair_threshold"] != .75 or
            c["component_cap"] != 100 or c["max_positive_per_train_queue"] != 80 or
            c["max_negative_per_train_queue"] != 180 or
            c["hard_negative_within_group_quota"] != 80 or
            c["hard_negative_cross_group_quota"] != 80):
        raise ValueError("Predeclared experiment contract changed")
    return c


def verify_freezes() -> None:
    for path, expected in FROZEN.items():
        if sha256_file(ROOT / path) != expected:
            raise ValueError(f"Frozen reference changed: {path}")


def context():
    verify_freezes()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = sorted(org for org in parent if split.get(org) == "train")
    disjoint = sorted(org for org in parent if split.get(org) in ("validation", "holdout"))
    if len(parent) != 499 or len(train) != 334 or len(disjoint) != 135 or set(train) & set(disjoint):
        raise ValueError("Queue split changed")
    paths, shards = shard_map()
    sentinels, _ = detect_modal_sentinels()
    cf = json.loads((ROOT / f"outputs/{CANDIDATE_RUN}/prediction_freeze.json").read_text())
    gf = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    rf = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    return parent, split, train, paths, shards, sentinels, cf, gf, rf


def load_queue(org, parent, paths, shards, sentinels, cf, gf):
    name = key(org)
    cp = ROOT / "data/derived" / CANDIDATE_RUN / f"{name}.pkl"
    gp = ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl"
    shard = paths[org]
    if (sha256_file(cp) != cf["prediction_sha256"][name] or
            sha256_file(gp) != gf["prediction_sha256"][name] or
            sha256_file(shard) != shards["parquet_sha256"][str(shard.relative_to(ROOT))]):
        raise ValueError("Frozen queue input changed")
    with cp.open("rb") as stream: candidate = pickle.load(stream)
    with gp.open("rb") as stream: base = pickle.load(stream)
    keys = parent[org]["input_alert_keys"]
    if keys != candidate["input_alert_keys"] or keys != base["input_alert_keys"]:
        raise ValueError("Queue alert alignment changed")
    docs = read_docs(org, shard, sentinels, set(keys))
    edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
    if not np.array_equal(edges, candidate["candidate_edges"]):
        raise ValueError("Candidate graph changed")
    return keys, docs, edges, flags, base


def choose_training_edges(keys, edges, old_probability, groups, truth, c, seed):
    """Training-label use stops at selecting pair examples and their targets."""
    rng = np.random.default_rng(seed)
    n = len(keys)
    group_of = {alert: gi for gi, group in enumerate(groups) for alert in group}
    positive, within, cross, background = [], [], [], []
    for t, edge in enumerate(edges):
        a, b = divmod(int(edge), n)
        ka, kb = keys[a], keys[b]
        same = truth[ka] == truth[kb]
        different_group = group_of[ka] != group_of[kb]
        if same and different_group:
            positive.append(t)
        elif not same and not different_group and old_probability[t] >= .75:
            within.append(t)
        elif not same and different_group and old_probability[t] >= .5:
            cross.append(t)
        elif not same:
            background.append(t)
    def sample(rows, cap):
        rows = np.asarray(rows, dtype=np.int64)
        if len(rows) <= cap: return rows.tolist()
        return rng.choice(rows, cap, replace=False).tolist()
    selected_positive = sample(positive, c["max_positive_per_train_queue"])
    # Select the most deceptive high-score negatives within each hard category.
    within.sort(key=lambda t: (-float(old_probability[t]), int(edges[t])))
    cross.sort(key=lambda t: (-float(old_probability[t]), int(edges[t])))
    selected_negative = within[:c["hard_negative_within_group_quota"]]
    selected_negative += cross[:c["hard_negative_cross_group_quota"]]
    remaining = c["max_negative_per_train_queue"] - len(selected_negative)
    if remaining > 0:
        extra = within[c["hard_negative_within_group_quota"]:] + cross[c["hard_negative_cross_group_quota"]:] + background
        selected_negative += sample(extra, remaining)
    if len(selected_positive) > 80 or len(selected_negative) > 180 or set(selected_positive) & set(selected_negative):
        raise AssertionError("Training sampling bounds failed")
    return selected_positive, selected_negative, {
        "available_positive_cross_group": len(positive),
        "available_hard_false_inside_group": len(within),
        "available_hard_false_cross_group": len(cross),
        "sampled_positive": len(selected_positive),
        "sampled_negative": len(selected_negative),
        "sampled_hard_inside": min(len(within), c["hard_negative_within_group_quota"]),
        "sampled_hard_cross": min(len(cross), c["hard_negative_cross_group_quota"]),
    }


def features_for_indices(keys, docs, edges, flags, baseline_probability, indices):
    n = len(keys)
    frequency = token_frequencies(docs)
    return np.asarray([edge_features(docs[keys[int(edges[t] // n)]],
                                     docs[keys[int(edges[t] % n)]], frequency,
                                     int(flags[t])) + [float(baseline_probability[t])]
                       for t in indices], dtype=np.float32).reshape(-1, 31)


def score_all(keys, docs, edges, flags, old_model, new_model):
    n = len(keys)
    frequency = token_frequencies(docs)
    old = np.empty(len(edges), dtype=np.float32)
    new = np.empty(len(edges), dtype=np.float32)
    for start in range(0, len(edges), 10000):
        part = edges[start:start+10000]
        x = np.asarray([edge_features(docs[keys[int(e // n)]], docs[keys[int(e % n)]],
                                      frequency, int(flags[start+i]))
                        for i, e in enumerate(part)], dtype=np.float32).reshape(-1, 30)
        base = old_model.predict_proba(x)[:, 1]
        old[start:start+len(part)] = base
        stacked = np.column_stack((x, base)).astype(np.float32)
        new[start:start+len(part)] = new_model.predict_proba(stacked)[:, 1]
    return old, new


def synthetic_test() -> None:
    c = config()
    keys = ["a", "b", "c", "d"]
    edges = np.asarray([1, 2, 3, 6, 7, 11], dtype=np.int64)
    p = np.asarray([.2, .8, .7, .6, .9, .4], dtype=np.float32)
    truth = {"a": "x", "b": "x", "c": "y", "d": "z"}
    pos, neg, counts = choose_training_edges(keys, edges, p, [["a"], ["b", "c"], ["d"]], truth, c, 917)
    assert pos == [0] and 1 in neg and counts["sampled_positive"] == 1
    assert set(pos).isdisjoint(neg) and len(neg) <= 180
    print(json.dumps({"status": "pass", "synthetic_checks": 4, "evaluation_labels_read": False}))


def fit() -> None:
    c = config()
    parent, split, train, paths, shards, sentinels, cf, gf, _ = context()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    if public.exists() or private.exists():
        raise FileExistsError("Use a fresh versioned Phase 9G run")
    truth = read_truth(set(train), {a for org in train for a in parent[org]["input_alert_keys"]})
    old_model, _, _, _ = load_models()
    fit_freeze = json.loads((ROOT / f"outputs/{V2_RUN}/fit_freeze.json").read_text())
    if sha256_file(ROOT / "data/derived" / V2_RUN / "pair_model.pkl") != fit_freeze["model_sha256"]:
        raise ValueError("Old pair model changed")
    x_parts, y_parts, census = [], [], Counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    for number, org in enumerate(train, 1):
        keys, docs, edges, flags, base = load_queue(org, parent, paths, shards, sentinels, cf, gf)
        p = predict_probability(keys, docs, edges, flags, old_model)
        if groups_at(keys, edges, p, .75) != base["groups"]:
            raise ValueError("Frozen v2 score/group mismatch")
        pos, neg, counts = choose_training_edges(keys, edges, p, base["groups"], truth, c,
                                                  c["sampling_seed"] + int(org))
        chosen = pos + neg
        if chosen:
            x_parts.append(features_for_indices(keys, docs, edges, flags, p, chosen))
            y_parts.append(np.asarray([1]*len(pos) + [0]*len(neg), dtype=np.int8))
        census.update({"organizations": 1, "alerts": len(keys), "candidates_seen": len(edges), **counts})
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Phase 9G prepared {number}/334 training queues", flush=True)
    X = np.vstack(x_parts)
    y = np.concatenate(y_parts)
    if len(y) != census["sampled_positive"] + census["sampled_negative"] or len(np.unique(y)) != 2:
        raise ValueError("Training census mismatch")
    model = HistGradientBoostingClassifier(max_iter=c["max_iter"], max_leaf_nodes=c["max_leaf_nodes"],
        max_depth=c["max_depth"], learning_rate=c["learning_rate"],
        l2_regularization=c["l2_regularization"], random_state=c["sampling_seed"])
    model.fit(X, y)
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    model_path = private / "boundary_pair_model.pkl"
    with model_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(public / "fit_freeze.json", {
        "classification": "exploratory_train_only_hard_negative_pair_scorer",
        "run": RUN, "config_sha256": sha256_file(CONFIG),
        "source_sha256": sha256_file(Path(__file__)), "split_sha256": sha256_file(SPLIT),
        "frozen_sha256": FROZEN, "model_sha256": sha256_file(model_path),
        "training_census": dict(census), "training_rows": len(y),
        "training_positive": int(y.sum()), "evaluation_queue_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter()-started,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "model_frozen", "rows": len(y), "positive": int(y.sum()),
                      "organizations": census["organizations"]}))


def predict() -> None:
    c = config()
    parent, split, _, paths, shards, sentinels, cf, gf, rf = context()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    freeze_path = public / "fit_freeze.json"
    fit_freeze = json.loads(freeze_path.read_text())
    model_path = private / "boundary_pair_model.pkl"
    if ((public / "prediction_freeze.json").exists() or
            fit_freeze["config_sha256"] != sha256_file(CONFIG) or
            fit_freeze["source_sha256"] != sha256_file(Path(__file__)) or
            fit_freeze["split_sha256"] != sha256_file(SPLIT) or
            fit_freeze["model_sha256"] != sha256_file(model_path)):
        raise ValueError("Fit freeze changed or prediction exists")
    with model_path.open("rb") as stream:
        new_model = pickle.load(stream)
    old_model, v4, v7, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    census, hashes = Counter(), {}
    for number, org in enumerate(sorted(parent), 1):
        name = key(org)
        keys, docs, edges, flags, base = load_queue(org, parent, paths, shards, sentinels, cf, gf)
        old, new = score_all(keys, docs, edges, flags, old_model, new_model)
        if groups_at(keys, edges, old, .75) != base["groups"]:
            raise ValueError("Frozen v2 comparator did not reproduce")
        groups = groups_at(keys, edges, new, c["pair_threshold"])
        score_path = ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl"
        if sha256_file(score_path) != rf["score_sha256"][name]:
            raise ValueError("Frozen v7 scores changed")
        if groups == base["groups"]:
            with score_path.open("rb") as stream: scores = pickle.load(stream)
        else:
            scores = score_groups_v7(groups, docs, base_ranker, v4, v7, hasher)
        output = private / f"prediction_{name}.pkl"
        with output.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "candidate_pairs": len(edges),
                         "groups": groups, "scores": scores,
                         "links_at_fixed_threshold": int(np.count_nonzero(new >= .75))},
                        stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(output)
        census.update({"organizations": 1, "alerts": len(keys), "candidate_pairs": len(edges),
                       "changed_queues": groups != base["groups"],
                       "linked_edges": int(np.count_nonzero(new >= .75)),
                       "groups": len(groups)})
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Phase 9G predicted {number}/499 queues", flush=True)
    if (census["organizations"], census["alerts"], census["candidate_pairs"]) != (499, 400039, 1942648):
        raise ValueError("Matched prediction scope changed")
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_hard_negative_scorer_predictions_no_evaluator_labels",
        "run": RUN, "fit_freeze_sha256": sha256_file(freeze_path),
        "config_sha256": sha256_file(CONFIG), "source_sha256": sha256_file(Path(__file__)),
        "prediction_sha256": hashes, "census": dict(census),
        "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter()-started,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "fit", "predict"))
    {"self-test": synthetic_test, "fit": fit, "predict": predict}[parser.parse_args().stage]()


if __name__ == "__main__":
    main()
