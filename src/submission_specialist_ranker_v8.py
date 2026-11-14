"""Exploratory singleton/multi-alert specialists on frozen v2 groups."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import vstack
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import LogisticRegression

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_group_ranker_v4 import bootstrap
from .submission_trained_ranker import training_targets
from .submission_descriptor_ranker_v7 import (GROUP_FREEZE, GROUP_RUN, V4_FREEZE,
                                               featurize, load_org, old_scores)
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_specialist_ranker_v8_"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
V7_FREEZE = ROOT / "outputs" / V7_RUN / "prediction_freeze.json"
BLENDS = (0.0, .25, .5, .75, 1.0)


def sources() -> dict:
    paths = (Path(__file__), ROOT / "src/submission_descriptor_ranker_v7.py",
             ROOT / "src/submission_group_ranker_v4.py", GROUP_FREEZE,
             V4_FREEZE, V7_FREEZE, SPLIT,
             ROOT / "outputs/submission_entity_time_shards_20261114_v1.json")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def v7_scores(org: str, freeze: dict) -> list[float]:
    path = ROOT / "data/derived" / V7_RUN / f"scores_{key(org)}.pkl"
    if sha256_file(path) != freeze["score_sha256"][key(org)]:
        raise ValueError("V7 scores changed")
    with path.open("rb") as stream:
        return pickle.load(stream)


def specialist_scores(groups: list[list[str]], x, models: dict) -> np.ndarray:
    is_single = np.array([len(group) == 1 for group in groups])
    scores = np.zeros(len(groups), dtype=float)
    for name, mask in (("single", is_single), ("multi", ~is_single)):
        if mask.any():
            scores[mask] = models[name].predict_proba(x[mask])[:, 1]
    return scores


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v8 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    train = [org for org in orgs if split.get(org) == "train"]
    dev = [org for org in orgs if split.get(org) == "validation"]
    if (len(orgs), len(train), len(dev)) != (499, 334, 67):
        raise ValueError("Historical organization split changed")
    train_truth = read_truth(set(train), {alert for org in train for alert in baseline[org]["input_alert_keys"]})
    train_ranks = labels(set(train))
    dev_truth = read_truth(set(dev), {alert for org in dev for alert in baseline[org]["input_alert_keys"]})
    dev_ranks = labels(set(dev))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    features, targets, sizes = [], [], []
    started = time.perf_counter()
    for index, org in enumerate(train, 1):
        item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
        features.append(featurize(item["groups"], docs, item["scores"], hasher))
        targets.extend(training_targets(item, train_truth, train_ranks[org]))
        sizes.extend(len(group) == 1 for group in item["groups"])
        if index % 50 == 0:
            print(f"Prepared training queues {index}/334", flush=True)
    x = vstack(features, format="csr")
    y = np.asarray(targets, dtype=np.uint8)
    single = np.asarray(sizes, dtype=bool)
    if len(y) != 157072 or int(y.sum()) != 4624:
        raise ValueError("Training labels changed")
    models = {}
    for name, mask in (("single", single), ("multi", ~single)):
        model = LogisticRegression(C=.25, solver="liblinear", max_iter=250, random_state=81)
        model.fit(x[mask], y[mask], sample_weight=np.where(y[mask], 10.0, 1.0))
        models[name] = model
    del x, features, targets, sizes
    dev_rows = {blend: [] for blend in BLENDS}
    for org in dev:
        item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
        old = np.asarray(v7_scores(org, v7_freeze))
        new = specialist_scores(item["groups"], featurize(item["groups"], docs, item["scores"], hasher), models)
        for blend in BLENDS:
            metric = tie_aware_ranking(item["groups"], ((1-blend)*old + blend*new).tolist(), dev_truth, dev_ranks[org])
            dev_rows[blend].append((metric["recall_at_20"], metric["precision_at_10"], metric["ndcg_at_20_rank1_highest"]))
    table = {str(blend): {"recall20": float(np.mean(rows, axis=0)[0]),
                          "p10": float(np.mean(rows, axis=0)[1]),
                          "ndcg20": float(np.mean(rows, axis=0)[2])}
             for blend, rows in dev_rows.items()}
    eligible = [b for b in BLENDS if table[str(b)]["p10"] >= table["0.0"]["p10"]
                and table[str(b)]["ndcg20"] >= table["0.0"]["ndcg20"]]
    chosen = max(eligible, key=lambda b: (table[str(b)]["recall20"], table[str(b)]["p10"], -b))
    if table[str(chosen)]["recall20"] <= table["0.0"]["recall20"]:
        chosen = 0.0
    private.mkdir(parents=True)
    model_hashes = {}
    for name, model in models.items():
        path = private / f"model_{name}.pkl"
        with path.open("wb") as stream:
            pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
        model_hashes[name] = sha256_file(path)
    score_hashes = {}
    for index, org in enumerate(orgs, 1):
        old = np.asarray(v7_scores(org, v7_freeze))
        if chosen:
            item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
            new = specialist_scores(item["groups"], featurize(item["groups"], docs, item["scores"], hasher), models)
            scores = ((1-chosen)*old + chosen*new).tolist()
        else:
            scores = old.tolist()
        path = private / f"scores_{key(org)}.pkl"
        with path.open("wb") as stream:
            pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
        score_hashes[key(org)] = sha256_file(path)
        if index % 50 == 0:
            print(f"Frozen scores {index}/499", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_singleton_multi_specialist_dev_selection",
        "run": run_id, "training_organizations": 334, "development_organizations": 67,
        "training_groups": len(y), "positive_groups": int(y.sum()),
        "single_groups": int(single.sum()), "single_positive_groups": int(y[single].sum()),
        "selected_blend": chosen, "development_table": table,
        "selection_rule": "maximize_development_recall20_with_p10_and_ndcg20_at_least_v7",
        "historical_holdout_labels_read_during_prediction": False,
        "source_sha256": sources(), "model_sha256": model_hashes,
        "score_sha256": score_hashes, "wall_seconds": time.perf_counter()-started,
    })
    print(json.dumps({"status": "predictions_frozen", "selected_blend": chosen, "development": table}))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources():
        raise ValueError("Method source changed")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    truth = read_truth(set(orgs), {alert for item in baseline.values() for alert in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    for org in orgs:
        name = key(org)
        group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        score_path = private / f"scores_{name}.pkl"
        if sha256_file(group_path) != group_freeze["prediction_sha256"][name] or sha256_file(score_path) != freeze["score_sha256"][name]:
            raise ValueError("Frozen prediction changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        with score_path.open("rb") as stream:
            new = pickle.load(stream)
        for method, scores in (("v8_selected", new), ("v7_reference", v7_scores(org, v7_freeze))):
            metric = tie_aware_ranking(item["groups"], scores, truth, ranks[org])
            rows[method][org] = {"recall20": metric["recall_at_20"],
                                 "p10": metric["precision_at_10"],
                                 "ndcg20": metric["ndcg_at_20_rank1_highest"]}
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [org for org in orgs if split.get(org) in ("validation", "holdout")],
               "holdout_68_previously_exposed": [org for org in orgs if split.get(org) == "holdout"]}
    result = {}
    for name, selected in cohorts.items():
        result[name] = {"organizations": len(selected), "expert_top20_denominator": 20*len(selected),
                        "methods": {method: {metric: bootstrap([rows[method][org][metric] for org in selected])
                                             for metric in ("recall20", "p10", "ndcg20")}
                                    for method in rows},
                        "paired_v8_minus_v7": {metric: bootstrap([rows["v8_selected"][org][metric]-rows["v7_reference"][org][metric]
                                                             for org in selected])
                                               for metric in ("recall20", "p10", "ndcg20")}}
    write_json(public / "metrics.json", {"classification": "exploratory_post_exposure_specialist_ranker_not_confirmatory",
                                         "run": run_id, "selected_blend": freeze["selected_blend"],
                                         "groups_and_candidates": "identical_to_v2", "cohorts": result,
                                         "prediction_freeze_sha256": sha256_file(freeze_path)})
    write_json(public / "run_manifest.json", {"sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                                                           for path in (Path(__file__), freeze_path,
                                                                        public / "metrics.json", private / "model_single.pkl",
                                                                        private / "model_multi.pkl")},
                                              "private_score_sha256": freeze["score_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete", "selected_blend": freeze["selected_blend"],
                      "all_499_recall20": result["all_499_descriptive"]["methods"]["v8_selected"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_specialist_ranker_v8_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
