"""Development-selected hard-negative and singleton-aware ranking on fixed v2 groups."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_full_entity_time import read_docs
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_group_ranker_v4 import group_features, bootstrap
from .submission_trained_ranker import training_targets
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_priority_focus_v6_"
V2 = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1"
V2_FREEZE = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json"
V4 = ROOT / "data/derived/submission_group_ranker_v4_20261114_v1"
V4_FREEZE = ROOT / "outputs/submission_group_ranker_v4_20261114_v1/prediction_freeze.json"
VARIANTS = ("hardneg", "singleton", "focus")


def source_hashes() -> dict:
    paths = (Path(__file__), ROOT / "src/submission_group_ranker_v4.py", V2_FREEZE, V4_FREEZE, SPLIT)
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def weights_for(variant: str, y: np.ndarray, sizes: np.ndarray, top40: np.ndarray) -> np.ndarray:
    if variant == "hardneg":
        return np.where(y, 10.0, np.where(top40, 3.0, 1.0))
    if variant == "singleton":
        return np.where(y, np.where(sizes == 1, 20.0, 10.0), np.where(top40, 2.0, 1.0))
    if variant == "focus":
        return np.where(y, np.where(sizes == 1, 30.0, 15.0), np.where(top40, 4.0, 1.0))
    raise ValueError(variant)


def build_model() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15,
                                          min_samples_leaf=50, learning_rate=.05,
                                          l2_regularization=2, random_state=61)


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v6 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    v4_freeze = json.loads(V4_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    train = [o for o in orgs if split.get(o) == "train"]
    development = [o for o in orgs if split.get(o) == "validation"]
    if len(orgs) != 499 or len(train) != 334 or len(development) != 67:
        raise ValueError("Historical split changed")
    train_truth = read_truth(set(train), {a for o in train for a in baseline[o]["input_alert_keys"]})
    train_ranks = labels(set(train))
    dev_truth = read_truth(set(development), {a for o in development for a in baseline[o]["input_alert_keys"]})
    dev_ranks = labels(set(development))
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    features, train_x, train_y, train_sizes, train_top40 = {}, [], [], [], []
    development_groups = {}
    started = time.perf_counter()
    for index, org in enumerate(orgs, 1):
        v2_path = V2 / f"v2_{key(org)}.pkl"
        if sha256_file(v2_path) != v2_freeze["prediction_sha256"][key(org)]:
            raise ValueError("V2 groups changed")
        with v2_path.open("rb") as stream:
            item = pickle.load(stream)
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        docs = read_docs(org, path, sentinels, set(item["input_alert_keys"]))
        x = group_features(item["groups"], docs, item["scores"])
        features[org] = x
        if org in train:
            y = np.asarray(training_targets(item, train_truth, train_ranks[org]), dtype=np.uint8)
            old_scores = np.asarray(item["scores"])
            top = np.zeros(len(y), dtype=bool)
            top[np.argsort(-old_scores, kind="stable")[:40]] = True
            train_x.append(x)
            train_y.append(y)
            train_sizes.append(np.asarray([len(g) for g in item["groups"]]))
            train_top40.append(top)
        elif org in development:
            development_groups[org] = item["groups"]
        if index % 50 == 0:
            print(f"Prepared {index}/499 groups for priority study", flush=True)
    x_train, y_train = np.vstack(train_x), np.concatenate(train_y)
    sizes, top40 = np.concatenate(train_sizes), np.concatenate(train_top40)
    if len(y_train) != 157072 or int(y_train.sum()) != 4624:
        raise ValueError("Training target changed")
    models, dev_results = {}, {}
    for variant in VARIANTS:
        model = build_model()
        model.fit(x_train, y_train, sample_weight=weights_for(variant, y_train, sizes, top40))
        scores = {org: model.predict_proba(features[org])[:, 1].tolist() for org in development}
        recall = [tie_aware_ranking(development_groups[org], scores[org], dev_truth, dev_ranks[org])["recall_at_20"]
                  for org in development]
        p10 = [tie_aware_ranking(development_groups[org], scores[org], dev_truth, dev_ranks[org])["precision_at_10"]
               for org in development]
        dev_results[variant] = {"recall20_macro": float(np.mean(recall)), "p10_macro": float(np.mean(p10))}
        models[variant] = model
    old_recall, old_p10 = [], []
    for org in development:
        path = V4 / f"scores_{key(org)}.pkl"
        if sha256_file(path) != v4_freeze["score_sha256"][key(org)]:
            raise ValueError("V4 score changed")
        with path.open("rb") as stream:
            old_scores = pickle.load(stream)
        metric = tie_aware_ranking(development_groups[org], old_scores, dev_truth, dev_ranks[org])
        old_recall.append(metric["recall_at_20"])
        old_p10.append(metric["precision_at_10"])
    dev_results["v4_baseline"] = {"recall20_macro": float(np.mean(old_recall)), "p10_macro": float(np.mean(old_p10))}
    eligible = [v for v in VARIANTS if dev_results[v]["p10_macro"] >= dev_results["v4_baseline"]["p10_macro"]]
    selected = max(eligible, key=lambda v: (dev_results[v]["recall20_macro"], dev_results[v]["p10_macro"])) if eligible else "v4_baseline"
    if selected != "v4_baseline" and dev_results[selected]["recall20_macro"] <= dev_results["v4_baseline"]["recall20_macro"]:
        selected = "v4_baseline"
    private.mkdir(parents=True)
    model_hash = None
    if selected != "v4_baseline":
        model_path = private / "rank_model.pkl"
        with model_path.open("wb") as stream:
            pickle.dump(models[selected], stream, protocol=pickle.HIGHEST_PROTOCOL)
        model_hash = sha256_file(model_path)
    score_hashes = {}
    for org in orgs:
        if selected == "v4_baseline":
            source_path = V4 / f"scores_{key(org)}.pkl"
            with source_path.open("rb") as stream:
                scores = pickle.load(stream)
        else:
            scores = models[selected].predict_proba(features[org])[:, 1].tolist()
        path = private / f"scores_{key(org)}.pkl"
        with path.open("wb") as stream:
            pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
        score_hashes[key(org)] = sha256_file(path)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_development_selected_priority_model_on_frozen_v2_groups",
        "run": run_id, "training_organizations": len(train), "development_organizations": len(development),
        "model_selection_read_validation_labels": True,
        "holdout_labels_read_in_prediction_stage": False,
        "selected": selected, "development_table": dev_results,
        "selection_rule": "maximum_development_recall20_with_p10_at_least_v4_and_strict_recall_gain",
        "model_sha256": model_hash, "score_sha256": score_hashes,
        "source_sha256": source_hashes(), "wall_seconds": time.perf_counter() - started,
    })
    print(json.dumps({"status": "predictions_frozen", "selected": selected,
                      "development": dev_results}, sort_keys=True))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != source_hashes():
        raise ValueError("Source changed")
    if freeze["model_sha256"] is not None and sha256_file(private / "rank_model.pkl") != freeze["model_sha256"]:
        raise ValueError("Model changed")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    v4_freeze = json.loads(V4_FREEZE.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    truth = read_truth(set(orgs), {a for x in baseline.values() for a in x["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    for org in orgs:
        name = key(org)
        v2_path = V2 / f"v2_{name}.pkl"
        v4_path = V4 / f"scores_{name}.pkl"
        v6_path = private / f"scores_{name}.pkl"
        if (sha256_file(v2_path) != v2_freeze["prediction_sha256"][name]
            or sha256_file(v4_path) != v4_freeze["score_sha256"][name]
            or sha256_file(v6_path) != freeze["score_sha256"][name]):
            raise ValueError("Frozen prediction changed")
        with v2_path.open("rb") as stream:
            item = pickle.load(stream)
        for method, path in (("v4_baseline", v4_path), ("v6_selected", v6_path)):
            with path.open("rb") as stream:
                scores = pickle.load(stream)
            m = tie_aware_ranking(item["groups"], scores, truth, ranks[org])
            rows[method][org] = {"recall20": m["recall_at_20"], "p10": m["precision_at_10"],
                                 "ndcg20": m["ndcg_at_20_rank1_highest"]}
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [o for o in orgs if split.get(o) in ("validation", "holdout")],
               "holdout_68_previously_exposed": [o for o in orgs if split.get(o) == "holdout"]}
    results = {}
    for name, chosen in cohorts.items():
        results[name] = {"organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
            "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                 for metric in ("recall20", "p10", "ndcg20")} for method in rows},
            "paired_v6_minus_v4": {metric: bootstrap([rows["v6_selected"][o][metric] - rows["v4_baseline"][o][metric]
                                                   for o in chosen]) for metric in ("recall20", "p10", "ndcg20")}}
    metrics = {"classification": "exploratory_post_exposure_priority_focus_not_confirmatory",
               "run": run_id, "selected": freeze["selected"], "groups_and_candidates": "identical_to_v2",
               "cohorts": results, "prediction_freeze_sha256": sha256_file(freeze_path),
               "limits": ["All GUIDE_Test labels previously accessed", "No untouched cohort",
                          "Entity/time availability and operational approval unresolved"]}
    write_json(public / "metrics.json", metrics)
    manifest_paths = [Path(__file__), freeze_path, public / "metrics.json"]
    if freeze["model_sha256"] is not None:
        manifest_paths.append(private / "rank_model.pkl")
    write_json(public / "run_manifest.json", {"classification": metrics["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in manifest_paths},
        "private_score_sha256": freeze["score_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete", "selected": freeze["selected"],
                      "holdout_recall20": results["holdout_68_previously_exposed"]["methods"]["v6_selected"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_priority_focus_v6_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
