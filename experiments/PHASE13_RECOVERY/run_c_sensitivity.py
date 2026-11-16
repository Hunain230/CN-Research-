"""Label-blind Phase 13 route ablations and v2 threshold sensitivity.

The first three queues can be smoke-tested, then the full 499 predictions frozen.
No evaluator labels are imported here.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key
from src.phase2 import sha256_file
from src.submission_full_entity_time import PARENT
from src.submission_entity_time_pair_v2 import groups_at, shard_map
from src.submission_group_merge_v10_v2 import load_models, load_queue
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-queues", type=int, default=0)
    args = parser.parse_args()
    cfg_path = HERE / "PHASE13_EXPERIMENT_CONFIG.json"
    cfg = json.loads(cfg_path.read_text())
    output = HERE / ("c_sample" if args.sample_queues else "c_predictions")
    if output.exists():
        raise FileExistsError(f"Refusing overwrite: {output}")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != cfg["population"]["queues"]:
        raise ValueError("Queue scope changed")
    if args.sample_queues:
        orgs = orgs[:args.sample_queues]
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model = load_models()[0]
    group_freeze = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json").read_text())
    candidate_freeze = json.loads((ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json").read_text())
    output.mkdir()
    start, process = time.perf_counter(), psutil.Process()
    peak, hashes, census = 0, {}, Counter()
    for number, org in enumerate(orgs, 1):
        name = key(org)
        item, docs, edges, probabilities = load_queue(org, parent, group_freeze, paths,
                                                       shard_manifest, sentinels, pair_model)
        candidate_path = ROOT / "data/derived/submission_full_entity_time_20261114_v1" / f"{name}.pkl"
        if sha256_file(candidate_path) != candidate_freeze["prediction_sha256"][name]:
            raise ValueError("Candidate input hash changed")
        with candidate_path.open("rb") as stream:
            candidate = pickle.load(stream)
        if not np.array_equal(edges, candidate["candidate_edges"]):
            raise ValueError("Candidate edge order changed")
        # Reconstruct route flags from the same frozen docs; this generator is deterministic.
        from src.submission_full_entity_time import generate
        reproduced_edges, flags, _ = generate(item["input_alert_keys"], docs, parent[org]["candidate_edges"])
        if not np.array_equal(edges, reproduced_edges):
            raise ValueError("Route flag alignment changed")
        policies = {}
        for threshold in cfg["group_thresholds"]:
            groups = groups_at(item["input_alert_keys"], edges, probabilities, threshold)
            if threshold == 0.75 and groups != item["groups"]:
                raise ValueError("Frozen 0.75 groups failed to reproduce")
            policies[str(threshold)] = groups
        row = {"keys": item["input_alert_keys"], "edges": edges, "flags": flags,
               "probabilities": probabilities, "groups": policies}
        path = output / f"{name}.pkl"
        with path.open("wb") as stream:
            pickle.dump(row, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(path)
        census.update(queues=1, alerts=len(row["keys"]), edges=len(edges))
        peak = max(peak, process.memory_info().rss)
        if number % 25 == 0 or args.sample_queues:
            print(f"Phase13 C predicted {number}/{len(orgs)}", flush=True)
    freeze = {"classification": "label_blind_retrospective_predictions", "sample": bool(args.sample_queues),
              "code_sha256": sha256_file(Path(__file__)), "config_sha256": sha256_file(cfg_path),
              "parent_freeze_sha256": {"candidate": sha256_file(ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json"),
                                       "group": sha256_file(ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json")},
              "prediction_sha256": hashes, "census": dict(census),
              "resource": {"wall_seconds": time.perf_counter()-start, "peak_process_rss_bytes": peak},
              "evaluator_labels_read": False}
    (output / "prediction_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"status": "frozen", "census": dict(census), "resource": freeze["resource"]}))


if __name__ == "__main__":
    main()
