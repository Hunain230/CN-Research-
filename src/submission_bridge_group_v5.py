"""Frozen development-selected corroborated link bridges on all GUIDE queues."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from .submission_full_entity_time import PARENT, RANKER, read_docs, generate
from .submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability
from .submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels
from submission.calibrate_component_cap_v3 import groups_at
from submission.development_bridge_links import bridge_mask


PREFIX = "submission_bridge_group_v5_"
V2 = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1"
V2_FREEZE = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json"
PAIR = V2 / "pair_model.pkl"
CALIBRATION = ROOT / "outputs/submission_development_bridge_links_20261114_v1.json"


def source_hashes() -> dict:
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration["selected_config"] != "rare_descriptor_065":
        raise ValueError("Development choice changed")
    if sha256_file(PAIR) != calibration["pair_model_sha256"]:
        raise ValueError("Pair model changed")
    bridge_code = ROOT / "submission/development_bridge_links.py"
    if sha256_file(bridge_code) != calibration["analysis_code_sha256"]:
        raise ValueError("Bridge experiment changed")
    paths = (Path(__file__), bridge_code, CALIBRATION, PAIR, V2_FREEZE, SPLIT)
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v5 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    source = source_hashes()
    with PAIR.open("rb") as stream:
        model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    private.mkdir(parents=True)
    hashes, census = {}, Counter()
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        mask = bridge_mask(keys, docs, edges, probability, .65, "rare_and_descriptor")
        groups = groups_at(keys, edges, np.where(mask, probability, 0), .65, 100)
        count, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in keys})
        scores = ranker.decision_function(rank_features({"count_scores": count,
                                                          "bm25_scores": bm25})).tolist()
        output_path = private / f"v5_{key(org)}.pkl"
        with output_path.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "groups": groups, "scores": scores,
                         "candidate_pairs": len(edges)}, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[key(org)] = sha256_file(output_path)
        census.update({"organizations": 1, "alerts": len(keys),
                       "candidate_pairs": len(edges), "predicted_groups": len(groups)})
        if index % 50 == 0:
            print(f"Bridge predicted {index}/499 organizations", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_development_selected_bridge_group_v5",
        "run": run_id, "config": "rare_descriptor_065_cap100",
        "census": dict(census), "prediction_sha256": hashes,
        "source_sha256": source,
        "evaluation_labels_read_in_prediction_stage": False,
        "wall_seconds": time.perf_counter() - started,
    })
    print(json.dumps({"status": "predictions_frozen", "organizations": 499}))


def bootstrap(values: list[float]) -> dict:
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(53)
    draws = x[rng.integers(0, len(x), size=(5000, len(x)))].mean(axis=1)
    return {"mean": float(x.mean()), "ci95": np.quantile(draws, [.025, .975]).tolist(),
            "organizations": len(x), "resamples": 5000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != source_hashes():
        raise ValueError("Frozen source changed")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for o in orgs for a in parent[o]["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows, pair, ceiling = defaultdict(dict), defaultdict(Counter), Counter()
    for org in orgs:
        name = key(org)
        newer_path = private / f"v5_{name}.pkl"
        older_path = V2 / f"v2_{name}.pkl"
        if sha256_file(newer_path) != freeze["prediction_sha256"][name] or sha256_file(older_path) != v2_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen prediction changed")
        with newer_path.open("rb") as stream:
            newer = pickle.load(stream)
        with older_path.open("rb") as stream:
            older = pickle.load(stream)
        if newer["input_alert_keys"] != older["input_alert_keys"] or newer["candidate_pairs"] != older["candidate_pairs"]:
            raise ValueError("Candidate scope changed")
        keys = newer["input_alert_keys"]
        gold_sizes = Counter(truth[a] for a in keys)
        for method, item in (("v5_bridge_group", newer), ("v2_base_group", older)):
            groups, scores = item["groups"], item["scores"]
            metric = tie_aware_ranking(groups, scores, truth, ranks[org])
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": .8, "top20_recovery_min_purity": .8})
            rows[method][org] = {"recall20": metric["recall_at_20"],
                                 "p10": metric["precision_at_10"],
                                 "ndcg20": metric["ndcg_at_20_rank1_highest"]}
            pair[method].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"]})
            for gold in ranks[org]:
                if any((overlap := sum(truth[a] == gold for a in group)) / gold_sizes[gold] >= .8
                       and overlap / len(group) >= .8 for group in groups if gold_sizes[gold]):
                    ceiling[method] += 1
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [o for o in orgs if split.get(o) in ("validation", "holdout")],
               "holdout_68_previously_exposed": [o for o in orgs if split.get(o) == "holdout"]}
    result = {}
    for name, chosen in cohorts.items():
        result[name] = {"organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
                        "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                             for metric in ("recall20", "p10", "ndcg20")}
                                    for method in rows},
                        "paired_v5_minus_v2": {metric: bootstrap([rows["v5_bridge_group"][o][metric] - rows["v2_base_group"][o][metric]
                                                                 for o in chosen])
                                               for metric in ("recall20", "p10", "ndcg20")}}
    pair_results = {}
    for method, c in pair.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        pair_results[method] = {"tp": tp, "fp": fp, "fn": fn,
                                "precision": tp / (tp + fp), "recall": tp / (tp + fn),
                                "f1": 2 * tp / (2 * tp + fp + fn),
                                "recoverable_top20_oracle_order": ceiling[method],
                                "oracle_order_recall20_ceiling": ceiling[method] / (20 * len(orgs))}
    metrics = {"classification": "exploratory_post_exposure_bridge_group_not_confirmatory",
               "run": run_id, "cohorts": result, "pair_and_group": pair_results,
               "prediction_freeze_sha256": sha256_file(freeze_path),
               "limits": ["GUIDE_Test labels previously accessed", "No untouched cohort",
                          "Entity/time availability and operational approval unresolved"]}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {"classification": metrics["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, public / "metrics.json")},
        "private_prediction_sha256": freeze["prediction_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete",
                      "all_499_recall20": result["all_499_descriptive"]["methods"]["v5_bridge_group"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_bridge_group_v5_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
