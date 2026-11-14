"""Apply development-selected component cap to frozen entity/time pair model."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from .submission_full_entity_time import PARENT, RANKER, read_docs, generate
from .submission_entity_time_pair_v2 import (shard_map, predict_probability,
                                             source_hashes, SPLIT)
from .submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels
from submission.calibrate_component_cap_v3 import groups_at


PREFIX = "submission_entity_time_cap_v3_"
MODEL = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl"
MODEL_FIT = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json"
CALIBRATION = ROOT / "outputs/submission_component_cap_calibration_20261114_v1.json"
V2 = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1"
V2_FREEZE = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json"


def sources() -> dict:
    fit = json.loads(MODEL_FIT.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if fit["source_sha256"] != source_hashes() or sha256_file(MODEL) != fit["model_sha256"]:
        raise ValueError("Pair model changed")
    code = ROOT / "submission/calibrate_component_cap_v3.py"
    if sha256_file(code) != calibration["analysis_code_sha256"]:
        raise ValueError("Component-cap calibration changed")
    paths = (MODEL, MODEL_FIT, CALIBRATION, code, V2_FREEZE, Path(__file__))
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    hashes = sources()
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    threshold, cap = calibration["selected_config"].split(":")
    threshold, cap = float(threshold), int(cap)
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    private.mkdir(parents=True)
    prediction_hashes = {}
    census = Counter()
    times = []
    peak = 0
    process = psutil.Process()
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        tic = time.perf_counter()
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        groups = groups_at(keys, edges, probability, threshold, cap)
        count, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in keys})
        scores = ranker.decision_function(rank_features({"count_scores": count,
                                                          "bm25_scores": bm25})).tolist()
        output_path = private / f"v3_{key(org)}.pkl"
        with output_path.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "groups": groups, "scores": scores,
                         "candidate_pairs": len(edges)}, stream, protocol=pickle.HIGHEST_PROTOCOL)
        prediction_hashes[key(org)] = sha256_file(output_path)
        census.update({"organizations": 1, "alerts": len(keys),
                       "candidate_pairs": len(edges), "predicted_groups": len(groups)})
        times.append(time.perf_counter() - tic)
        peak = max(peak, process.memory_info().rss)
        del docs, edges, flags, probability, groups
        if index % 25 == 0:
            print(f"Predicted {index}/499 organizations", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_full_entity_time_component_cap_v3",
        "run": run_id, "organizations": 499, "threshold": threshold,
        "component_cap": cap, "census": dict(census),
        "prediction_sha256": prediction_hashes, "source_sha256": hashes,
        "evaluation_labels_read_in_prediction_stage": False,
        "candidate_route_identical_to_v2": True,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "organization_seconds_p50": float(np.quantile(times, .5)),
                     "organization_seconds_p95": float(np.quantile(times, .95)),
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id,
                      "organizations": 499, "config": calibration["selected_config"]}))


def bootstrap(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(37)
    draws = array[rng.integers(0, len(array), size=(10000, len(array)))].mean(axis=1)
    return {"mean": float(array.mean()), "ci95": np.quantile(draws, [.025, .975]).tolist(),
            "organizations": len(array), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources():
        raise ValueError("Frozen method changed")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    truth = read_truth(orgs, {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(orgs)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    confusion = defaultdict(Counter)
    ceilings = Counter()
    for org in sorted(orgs):
        v3_path = private / f"v3_{key(org)}.pkl"
        v2_path = V2 / f"v2_{key(org)}.pkl"
        if sha256_file(v3_path) != freeze["prediction_sha256"][key(org)] or sha256_file(v2_path) != v2_freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen prediction changed")
        with v3_path.open("rb") as stream:
            newer = pickle.load(stream)
        with v2_path.open("rb") as stream:
            older = pickle.load(stream)
        keys = newer["input_alert_keys"]
        if keys != older["input_alert_keys"] or newer["candidate_pairs"] != older["candidate_pairs"]:
            raise ValueError("Candidate cohort changed")
        gold_counts = Counter(truth[a] for a in keys)
        for name, item in (("v3_cap_selected", newer), ("v2_model", older)):
            groups, scores = item["groups"], item["scores"]
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": .8,
                             "top20_recovery_min_purity": .8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name][org] = {"recall20": tied["recall_at_20"],
                               "p10": tied["precision_at_10"],
                               "ndcg20": tied["ndcg_at_20_rank1_highest"]}
            confusion[name].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"],
                                    "fn": raw["pair_fn"]})
            found = set()
            for group in groups:
                membership = Counter(truth[a] for a in group)
                gold, n = max(membership.items(), key=lambda z: (z[1], z[0]))
                if gold in ranks[org] and n / gold_counts[gold] >= .8 and n / len(group) >= .8:
                    found.add(gold)
            ceilings[name] += len(found)
    cohort = {"all_499_descriptive": sorted(orgs),
              "training_disjoint_135": sorted(o for o in orgs if split.get(o) in ("validation", "holdout")),
              "holdout_68_previously_exposed": sorted(o for o in orgs if split.get(o) == "holdout")}
    results = {}
    for name, chosen in cohort.items():
        methods = {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                            for metric in ("recall20", "p10", "ndcg20")}
                   for method in rows}
        paired = {metric: bootstrap([rows["v3_cap_selected"][o][metric]
                                     - rows["v2_model"][o][metric] for o in chosen])
                  for metric in ("recall20", "p10", "ndcg20")}
        results[name] = {"organizations": len(chosen),
                         "expert_top20_denominator": len(chosen) * 20,
                         "methods": methods, "paired_v3_minus_v2": paired}
    pair_result = {}
    for name, c in confusion.items():
        tp, fp, fn = (c[k] for k in ("tp", "fp", "fn"))
        pair_result[name] = {"tp": tp, "fp": fp, "fn": fn,
                             "precision": tp / (tp + fp) if tp + fp else 0,
                             "recall": tp / (tp + fn) if tp + fn else 0,
                             "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                             "recoverable_top20_oracle_order": ceilings[name],
                             "oracle_order_recall20_ceiling": ceilings[name] / (20 * len(orgs))}
    metrics = {"classification": "exploratory_full_guide_post_exposure_component_cap_v3_not_confirmatory",
               "run": run_id, "organizations": len(orgs),
               "cohorts": results, "pair_and_group": pair_result,
               "candidate": "identical_to_submission_full_entity_time_20261114_v1",
               "prediction_resource": freeze["resource"],
               "limits": ["All GUIDE_Test labels previously accessed",
                          "Threshold and component cap selected on 42 development queues",
                          "Entity evidence availability at alert creation and operational field approval unresolved",
                          "No independent cohort or live SOC evaluation"],
               "prediction_freeze_sha256": sha256_file(freeze_path)}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_entity_time_cap_v3 predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_entity_time_cap_v3 evaluate --run-id {run_id}",
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, public / "metrics.json")},
        "private_prediction_sha256": freeze["prediction_sha256"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "v3_recall20_all": results["all_499_descriptive"]["methods"]["v3_cap_selected"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_entity_time_cap_v3_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
