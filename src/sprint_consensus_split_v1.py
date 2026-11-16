"""Prediction-only small-component split from two already frozen partitions."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import psutil
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import PARENT, read_docs
from .submission_entity_time_pair_v2 import shard_map
from .submission_group_merge_v10_v2 import load_models, score_groups_v7
from .phase9g_pair_boundary_v1 import verify_freezes
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


RUN = "sprint_consensus_split_v1_20261116"
CONFIG = ROOT / "experiments/24H_PERFORMANCE_SPRINT/consensus_split_v1.json"
V2 = "submission_entity_time_pair_v2_20261114_v1"
V7 = "submission_descriptor_ranker_v7_20261114_v1"
G = "phase9g_pair_boundary_20261115_v1"


def split_groups(base_groups, alternate_groups, maximum_size):
    alternate_of = {alert: index for index, group in enumerate(alternate_groups)
                    for alert in group}
    result = []
    changed = 0
    for group in base_groups:
        if len(group) > maximum_size:
            result.append(group)
            continue
        pieces = defaultdict(list)
        for alert in group:
            pieces[alternate_of[alert]].append(alert)
        if len(pieces) > 1:
            changed += 1
        result.extend(pieces.values())
    return sorted((sorted(group) for group in result), key=lambda group: group[0]), changed


def self_test():
    before = [["a", "b", "c"], ["d", "e"], ["f"]]
    alternate = [["a", "b", "d"], ["c", "e"], ["f"]]
    assert split_groups(before, alternate, 4) == ([['a', 'b'], ['c'], ['d'], ['e'], ['f']], 2)
    assert split_groups(before, alternate, 2) == ([['a', 'b', 'c'], ['d'], ['e'], ['f']], 1)
    print(json.dumps({"status": "pass", "synthetic_checks": 2}))


def predict():
    verify_freezes()
    config = json.loads(CONFIG.read_text())
    if config["experiment_id"] != "consensus_split_v1":
        raise ValueError("Experiment config changed")
    public = ROOT / "outputs" / RUN
    private = ROOT / "data/derived" / RUN
    if public.exists() or private.exists():
        raise FileExistsError("Sprint prediction already exists")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    _, v4, v7, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    base_freeze = json.loads((ROOT / "outputs" / V2 / "prediction_freeze.json").read_text())
    rank_freeze = json.loads((ROOT / "outputs" / V7 / "prediction_freeze.json").read_text())
    second_freeze = json.loads((ROOT / "outputs" / G / "prediction_freeze.json").read_text())
    if len(parent) != 499 or len(second_freeze["prediction_sha256"]) != 499:
        raise ValueError("Scope changed")
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    hashes = {}
    census = Counter()
    for number, org in enumerate(sorted(parent), 1):
        name = key(org)
        base_path = ROOT / "data/derived" / V2 / f"v2_{name}.pkl"
        second_path = ROOT / "data/derived" / G / f"prediction_{name}.pkl"
        rank_path = ROOT / "data/derived" / V7 / f"scores_{name}.pkl"
        for path, expected in ((base_path, base_freeze["prediction_sha256"][name]),
                               (second_path, second_freeze["prediction_sha256"][name]),
                               (rank_path, rank_freeze["score_sha256"][name])):
            if sha256_file(path) != expected:
                raise ValueError(f"Frozen input changed: {path}")
        with base_path.open("rb") as stream: base = pickle.load(stream)
        with second_path.open("rb") as stream: second = pickle.load(stream)
        keys = base["input_alert_keys"]
        if keys != second["input_alert_keys"]:
            raise ValueError("Alert scope changed")
        groups, changed = split_groups(base["groups"], second["groups"],
                                        config["maximum_v2_group_size_to_split"])
        if changed:
            shard = paths[org]
            if sha256_file(shard) != shard_manifest["parquet_sha256"][str(shard.relative_to(ROOT))]:
                raise ValueError("Projection changed")
            docs = read_docs(org, shard, sentinels, set(keys))
            scores = score_groups_v7(groups, docs, base_ranker, v4, v7, hasher)
        else:
            with rank_path.open("rb") as stream: scores = pickle.load(stream)
        output = private / f"prediction_{name}.pkl"
        with output.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "candidate_pairs": base["candidate_pairs"],
                         "groups": groups, "scores": scores}, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(output)
        census.update({"organizations": 1, "alerts": len(keys),
                       "changed_queues": int(changed > 0), "split_groups": changed,
                       "predicted_groups": len(groups)})
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Consensus split predicted {number}/499", flush=True)
    write_json(public / "prediction_freeze.json", {
        "run": RUN, "classification": "exploratory_prediction_no_evaluator_labels",
        "source_sha256": sha256_file(Path(__file__)),
        "config_sha256": sha256_file(CONFIG),
        "v2_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / V2 / "prediction_freeze.json"),
        "v7_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / V7 / "prediction_freeze.json"),
        "phase9g_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / G / "prediction_freeze.json"),
        "prediction_sha256": hashes, "census": dict(census),
        "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "frozen", "census": dict(census)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("self-test", "predict"))
    {"self-test": self_test, "predict": predict}[parser.parse_args().stage]()


if __name__ == "__main__":
    main()
