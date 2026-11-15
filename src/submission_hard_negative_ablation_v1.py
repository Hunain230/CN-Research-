"""Matched full-versus-hard-negative LightGBM ranking ablation on frozen groups."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import lightgbm as lgb
import numpy as np
import psutil
import scipy.sparse as sp

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_entity_time_pair_v2 import SPLIT
from .submission_trained_ranker import training_targets


CONFIG = ROOT / "configs/hard_negative_ablation_v1.json"
PREFIX = "submission_hard_negative_ablation_v1_"
FEATURE_RUN = "submission_ranking_ltr_v1_20261115_v1"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
FEATURE_FREEZE = ROOT / "outputs" / FEATURE_RUN / "prediction_freeze.json"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
PRIVATE_FEATURES = ROOT / "data/derived" / FEATURE_RUN
METHODS = ("full_40", "hard_40", "full_60", "hard_60")


def configuration() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (value["run_prefix"] != PREFIX or value["frozen_feature_run"] != FEATURE_RUN
            or value["group_run"] != GROUP_RUN or value["reference_rank_run"] != V7_RUN
            or value["matched_min_child_samples"] != [40, 60]):
        raise ValueError("Matched ablation configuration changed")
    return value


def source_hashes() -> dict[str, str]:
    paths = (Path(__file__), CONFIG, FEATURE_FREEZE, GROUP_FREEZE, SPLIT,
             ROOT / "src/submission_ranking_ltr_v1.py",
             ROOT / "src/submission_trained_ranker.py")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def sample_indices(y: np.ndarray, old_scores: list[float], rng: np.random.Generator,
                   hard_count: int, random_count: int):
    if len(y) != len(old_scores):
        raise ValueError("Group scores and relevance labels are misaligned")
    positive = np.flatnonzero(y)
    negative = np.flatnonzero(1 - y)
    ranked = negative[np.argsort(-np.asarray(old_scores)[negative], kind="stable")]
    hard = ranked[:hard_count]
    rest = ranked[hard_count:]
    random = rng.choice(rest, size=min(random_count, len(rest)), replace=False)
    chosen = np.sort(np.concatenate((positive, hard, random)))
    if len(np.unique(chosen)) != len(chosen) or int(y[chosen].sum()) != len(positive):
        raise ValueError("Sampling dropped a positive or duplicated a group")
    return chosen, {"full_groups": len(y), "positive_groups": len(positive),
                    "full_negative_groups": len(negative),
                    "selected_hard_negatives": len(hard),
                    "selected_random_negatives": len(random),
                    "sampled_groups": len(chosen),
                    "sampled_positive_groups": int(y[chosen].sum())}


def make_model(min_child_samples: int, rule: dict):
    return lgb.LGBMRanker(
        objective=rule["objective"], n_estimators=rule["n_estimators"],
        num_leaves=rule["num_leaves"], learning_rate=rule["learning_rate"],
        min_child_samples=min_child_samples,
        lambdarank_truncation_level=rule["lambdarank_truncation_level"],
        random_state=rule["random_seed"], n_jobs=rule["n_jobs"], verbosity=-1)


def self_test() -> None:
    rule = configuration()
    rng = np.random.default_rng(rule["random_seed"])
    y = np.asarray([0, 1, 0, 0, 1, 0], dtype=np.uint8)
    chosen, detail = sample_indices(y, [0.9, 0.1, 0.8, 0.7, 0.2, 0.6],
                                    rng, 2, 1)
    assert detail["sampled_positive_groups"] == 2
    assert detail["selected_hard_negatives"] == 2
    assert len(chosen) == 5 and all(i in chosen for i in (1, 4))
    model40, model60 = make_model(40, rule), make_model(60, rule)
    assert model40.get_params()["min_child_samples"] == 40
    assert model60.get_params()["min_child_samples"] == 60
    print(json.dumps({"status": "pass", "synthetic_assertions": 5,
                      "guide_label_reads": 0}))


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Use a versioned hard-negative ablation run ID")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("A run path already exists")
    rule = configuration()
    lineage = source_hashes()
    feature_freeze = json.loads(FEATURE_FREEZE.read_text(encoding="utf-8"))
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    train = [org for org in orgs if split.get(org) == "train"]
    if len(orgs) != 499 or len(train) != rule["training_organizations"]:
        raise ValueError("Organization cohort changed")
    # The only label reads are the designated historical training queues.
    train_items = {}
    train_keys = set()
    for org in train:
        name = key(org)
        path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        if sha256_file(path) != group_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen training groups changed")
        with path.open("rb") as stream:
            item = pickle.load(stream)
        train_items[org] = item
        train_keys.update(item["input_alert_keys"])
    truth = read_truth(set(train), train_keys)
    ranks = labels(set(train))
    process = psutil.Process()
    started = time.perf_counter()
    peak = process.memory_info().rss
    rng = np.random.default_rng(rule["random_seed"])
    full_matrices, full_targets, full_groups = [], [], []
    hard_matrices, hard_targets, hard_groups = [], [], []
    detail = {}
    for number, org in enumerate(train, 1):
        name = key(org)
        feature_path = PRIVATE_FEATURES / f"features_{name}.npz"
        if sha256_file(feature_path) != feature_freeze["feature_sha256"][name]:
            raise ValueError("Frozen feature file changed")
        x = sp.load_npz(feature_path)
        if x.shape[1] != rule["feature_columns"]:
            raise ValueError("Feature column count changed")
        item = train_items[org]
        y = np.asarray(training_targets(item, truth, ranks[org]), dtype=np.uint8)
        if len(y) != x.shape[0]:
            raise ValueError("Training target length changed")
        selected, counts = sample_indices(
            y, item["scores"], rng,
            rule["sampling"]["hard"]["highest_old_v2_score_negatives_per_organization"],
            rule["sampling"]["hard"]["seeded_random_negatives_per_organization"])
        full_matrices.append(x)
        full_targets.append(y)
        full_groups.append(len(y))
        hard_matrices.append(x[selected])
        hard_targets.append(y[selected])
        hard_groups.append(len(selected))
        detail[name] = counts
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Prepared matched ranking queries {number}/334", flush=True)
    x_full = sp.vstack(full_matrices, format="csr")
    y_full = np.concatenate(full_targets)
    x_hard = sp.vstack(hard_matrices, format="csr")
    y_hard = np.concatenate(hard_targets)
    if (len(y_full), int(y_full.sum()), len(y_hard), int(y_hard.sum())) != (157072, 4624, 29478, 4624):
        raise ValueError("Training denominators differ from the frozen reference")
    del full_matrices, hard_matrices, full_targets, hard_targets, train_items
    models = {method: make_model(int(method.split("_")[1]), rule) for method in METHODS}
    private.mkdir(parents=True)
    fit_seconds = {}
    for method, model in models.items():
        tic = time.perf_counter()
        if method.startswith("full"):
            model.fit(x_full, y_full, group=full_groups)
        else:
            model.fit(x_hard, y_hard, group=hard_groups)
        fit_seconds[method] = time.perf_counter() - tic
        with (private / f"{method}_model.pkl").open("wb") as stream:
            pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
        peak = max(peak, process.memory_info().rss)
        print(f"Fitted {method} in {fit_seconds[method]:.2f} seconds", flush=True)
    del x_full, y_full, x_hard, y_hard
    score_hashes = {}
    score_started = time.perf_counter()
    for number, org in enumerate(orgs, 1):
        name = key(org)
        feature_path = PRIVATE_FEATURES / f"features_{name}.npz"
        if sha256_file(feature_path) != feature_freeze["feature_sha256"][name]:
            raise ValueError("Frozen prediction features changed")
        x = sp.load_npz(feature_path)
        result = {method: model.predict(x).astype(float).tolist()
                  for method, model in models.items()}
        score_path = private / f"scores_{name}.pkl"
        with score_path.open("wb") as stream:
            pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
        score_hashes[name] = sha256_file(score_path)
        peak = max(peak, process.memory_info().rss)
        if number % 100 == 0:
            print(f"Frozen ablation scores {number}/499", flush=True)
    original = ROOT / "data/derived" / FEATURE_RUN
    original_scores = feature_freeze["score_sha256"]
    match = {"full_60_vs_phase4_full": 0.0, "hard_40_vs_phase4_hard": 0.0}
    for org in orgs:
        name = key(org)
        with (private / f"scores_{name}.pkl").open("rb") as stream:
            newer = pickle.load(stream)
        if sha256_file(original / f"scores_{name}.pkl") != original_scores[name]:
            raise ValueError("Phase 4 score file changed")
        with (original / f"scores_{name}.pkl").open("rb") as stream:
            earlier = pickle.load(stream)
        match["full_60_vs_phase4_full"] = max(
            match["full_60_vs_phase4_full"],
            float(np.max(np.abs(np.asarray(newer["full_60"]) - earlier["lightgbm_full"]))))
        match["hard_40_vs_phase4_hard"] = max(
            match["hard_40_vs_phase4_hard"],
            float(np.max(np.abs(np.asarray(newer["hard_40"]) - earlier["lightgbm_hardneg"]))))
    if any(value > 1e-10 for value in match.values()):
        raise ValueError("Matched existing LightGBM settings did not reproduce Phase 4 scores")
    public.mkdir()
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_post_exposure_matched_negative_sampling_ablation",
        "run": run_id, "methods": list(METHODS),
        "frozen_v2_groups": True, "frozen_phase4_features": True,
        "training_organizations": 334, "evaluation_organizations": 499,
        "full_training_groups": 157072, "hard_training_groups": 29478,
        "positive_training_groups_each_strategy": 4624,
        "per_training_organization_pseudonymous": detail,
        "selection_on_499_performed": False,
        "validation_or_holdout_labels_read_in_prediction": False,
        "source_sha256": lineage,
        "model_sha256": {method: sha256_file(private / f"{method}_model.pkl") for method in METHODS},
        "score_sha256": score_hashes,
        "reproduced_phase4_score_max_absolute_difference": match,
        "versions": {"lightgbm": lgb.__version__, "numpy": np.__version__},
        "resource": {
            "fit_seconds": fit_seconds, "score_seconds": time.perf_counter() - score_started,
            "wall_seconds": time.perf_counter() - started,
            "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "predictions_frozen",
                      "phase4_replication_max_error": match,
                      "full_groups": 157072, "hard_groups": 29478},
                     sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict"))
    parser.add_argument("--run-id", default="submission_hard_negative_ablation_v1_20261115_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": lambda: predict(args.run_id)}[args.stage]()


if __name__ == "__main__":
    main()
