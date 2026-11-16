"""Freeze queue-normalized score fusions before opening evaluator labels."""

from __future__ import annotations

import json
import pickle
import time
from collections import Counter
from pathlib import Path

import psutil
from scipy.stats import rankdata

from .guide_rerun_v2 import key
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json


RUN = "sprint_rank_fusion_v1_20261116"
CONFIG = ROOT / "experiments/24H_PERFORMANCE_SPRINT/rank_fusion_v1.json"
V2 = "submission_entity_time_pair_v2_20261114_v1"
V7 = "submission_descriptor_ranker_v7_20261114_v1"
HARD = "submission_hard_negative_ablation_v1_20261115_v1"


def percentile(scores):
    n = len(scores)
    if n <= 1:
        return [0.5] * n
    return ((rankdata(scores, method="average") - 1) / (n - 1)).tolist()


def predict():
    config = json.loads(CONFIG.read_text())
    if config["weights_hard40"] != [0.25, 0.5, 0.75]:
        raise ValueError("Fusion contract changed")
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    if public.exists() or private.exists():
        raise FileExistsError("Fusion run already exists")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    v2f = json.loads((ROOT / "outputs" / V2 / "prediction_freeze.json").read_text())
    v7f = json.loads((ROOT / "outputs" / V7 / "prediction_freeze.json").read_text())
    hf = json.loads((ROOT / "outputs" / HARD / "prediction_freeze.json").read_text())
    if len(parent) != 499:
        raise ValueError("Queue scope changed")
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    hashes = {}
    count = Counter()
    for number, org in enumerate(sorted(parent), 1):
        name = key(org)
        paths = ((ROOT / "data/derived" / V2 / f"v2_{name}.pkl", v2f["prediction_sha256"][name]),
                 (ROOT / "data/derived" / V7 / f"scores_{name}.pkl", v7f["score_sha256"][name]),
                 (ROOT / "data/derived" / HARD / f"scores_{name}.pkl", hf["score_sha256"][name]))
        if any(sha256_file(path) != digest for path, digest in paths):
            raise ValueError("Frozen input changed")
        with paths[0][0].open("rb") as stream: groups = pickle.load(stream)
        with paths[1][0].open("rb") as stream: v7 = pickle.load(stream)
        with paths[2][0].open("rb") as stream: hard = pickle.load(stream)["hard_40"]
        if len(groups["groups"]) != len(v7) or len(v7) != len(hard):
            raise ValueError("Group/score alignment changed")
        a, b = percentile(v7), percentile(hard)
        scores = {str(w): [(1-w)*x + w*y for x,y in zip(a,b)]
                  for w in config["weights_hard40"]}
        output = private / f"scores_{name}.pkl"
        with output.open("wb") as stream: pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(output)
        count.update({"queues": 1, "groups": len(v7)})
        peak = max(peak, process.memory_info().rss)
        if number % 100 == 0:
            print(f"Rank fusion predicted {number}/499", flush=True)
    write_json(public / "prediction_freeze.json", {
        "run": RUN, "classification": "exploratory_prediction_no_evaluator_labels",
        "source_sha256": sha256_file(Path(__file__)), "config_sha256": sha256_file(CONFIG),
        "v2_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / V2 / "prediction_freeze.json"),
        "v7_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / V7 / "prediction_freeze.json"),
        "hard_prediction_freeze_sha256": sha256_file(ROOT / "outputs" / HARD / "prediction_freeze.json"),
        "score_sha256": hashes, "census": dict(count), "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter()-started,
                     "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "frozen", "census": dict(count)}))


if __name__ == "__main__":
    predict()
