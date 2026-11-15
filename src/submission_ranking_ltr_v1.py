"""Versioned exploratory queue-aware rankers on frozen v2 incident groups.

Only historical train and validation labels are opened during prediction.
Holdout labels are reserved for the separate evaluator; all GUIDE results
remain post-exposure exploratory.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import lightgbm as lgb
import numpy as np
import psutil
import scipy.sparse as sp
import xgboost as xgb
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_full_entity_time import read_docs
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_group_ranker_v4 import group_features
from .submission_trained_ranker import training_targets
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


CONFIG = ROOT / "configs/ranking_ltr_v1.json"
PREFIX = "submission_ranking_ltr_v1_"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
V7_RUN = "submission_descriptor_ranker_v7_20261114_v1"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
V7_FREEZE = ROOT / "outputs" / V7_RUN / "prediction_freeze.json"
SHARD_MANIFEST = ROOT / "outputs/submission_entity_time_shards_20261114_v1.json"
FIELDS = ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")
NUMERIC_NAMES = ("log_group_size", "log_bm25", "old_group_score", "old_score_position",
                 "bm25_position", "log_queue_groups", "log_time_span_hours",
                 "log_detector_diversity", "log_category_diversity",
                 "log_technique_diversity", "log_entity_type_diversity",
                 "log_evidence_role_diversity", "log_entity_diversity")


def cfg() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (value["run_prefix"] != PREFIX or value["group_run"] != GROUP_RUN
            or value["reference_rank_run"] != V7_RUN or len(NUMERIC_NAMES) != 13):
        raise ValueError("Ranking configuration differs from reference")
    return value


def sources() -> dict[str, str]:
    paths = (Path(__file__), CONFIG, GROUP_FREEZE, V7_FREEZE, SPLIT, SHARD_MANIFEST,
             ROOT / "src/submission_group_ranker_v4.py",
             ROOT / "src/submission_trained_ranker.py",
             ROOT / "src/submission_descriptor_ranker_v7.py",
             ROOT / "src/submission_full_guide.py")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def featurize(groups: list[list[str]], docs: dict, old_scores: list[float],
              hasher: FeatureHasher) -> sp.csr_matrix:
    numeric = group_features(groups, docs, old_scores)
    if numeric.shape != (len(groups), len(NUMERIC_NAMES)):
        raise ValueError("Numeric group feature schema changed")
    records = []
    for group in groups:
        row = {}
        for field in FIELDS:
            values = set().union(*(docs[alert]["fields"][field] for alert in group))
            for value in values:
                row[f"{field}={value}"] = 1.0
        records.append(row)
    identity = hasher.transform(records)
    return sp.hstack((sp.csr_matrix(numeric), identity), format="csr", dtype=np.float32)


def hard_negative_training(x_by_org: dict, y_by_org: dict, old_scores: dict,
                           seed: int, hard_count: int, random_count: int):
    rng = np.random.default_rng(seed)
    matrices, targets, groups = [], [], []
    for org in sorted(y_by_org):
        y = y_by_org[org]
        positive = np.flatnonzero(y)
        negative = np.flatnonzero(1 - y)
        ranked = negative[np.argsort(-np.asarray(old_scores[org])[negative], kind="stable")]
        hard = ranked[:hard_count]
        rest = ranked[hard_count:]
        random = rng.choice(rest, size=min(random_count, len(rest)), replace=False)
        chosen = np.sort(np.concatenate((positive, hard, random)))
        matrices.append(x_by_org[org][chosen])
        targets.append(y[chosen])
        groups.append(len(chosen))
    return sp.vstack(matrices, format="csr"), np.concatenate(targets), groups


def build_models(settings: dict, seed: int):
    a = settings["lightgbm_full"]
    b = settings["xgboost_full"]
    c = settings["lightgbm_hardneg"]
    return {
        "lightgbm_full": lgb.LGBMRanker(objective=a["objective"], n_estimators=a["n_estimators"],
            num_leaves=a["num_leaves"], learning_rate=a["learning_rate"],
            min_child_samples=a["min_child_samples"],
            lambdarank_truncation_level=a["lambdarank_truncation_level"],
            random_state=seed, n_jobs=4, verbosity=-1),
        "xgboost_full": xgb.XGBRanker(objective=b["objective"], n_estimators=b["n_estimators"],
            max_depth=b["max_depth"], learning_rate=b["learning_rate"],
            min_child_weight=b["min_child_weight"],
            lambdarank_num_pair_per_sample=b["lambdarank_num_pair_per_sample"],
            tree_method=b["tree_method"], random_state=seed, n_jobs=4),
        "lightgbm_hardneg": lgb.LGBMRanker(objective=c["objective"], n_estimators=c["n_estimators"],
            num_leaves=c["num_leaves"], learning_rate=c["learning_rate"],
            min_child_samples=c["min_child_samples"],
            lambdarank_truncation_level=c["lambdarank_truncation_level"],
            random_state=seed, n_jobs=4, verbosity=-1)}


def self_test() -> None:
    hasher = FeatureHasher(n_features=cfg()["descriptor_hash_bins"],
                           input_type="dict", alternate_sign=False)
    docs = {
        "a": {"fields": {field: {"x"} for field in FIELDS}, "entities": set(), "stamp": 0},
        "b": {"fields": {field: {"y"} for field in FIELDS}, "entities": set(), "stamp": 0}}
    x = featurize([["a"], ["b"]], docs, [0.2, 0.1], hasher)
    assert x.shape == (2, 13 + cfg()["descriptor_hash_bins"])
    y = {"q": np.asarray([1, 0], dtype=np.uint8)}
    h, target, group = hard_negative_training({"q": x}, y, {"q": [0.2, 0.1]},
                                              181, 1, 1)
    assert h.shape[0] == 2 and target.tolist() == [1, 0] and group == [2]
    print(json.dumps({"status": "pass", "synthetic_checks": 2, "guide_label_reads": 0}))


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Use a versioned learning-to-rank run ID")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Run path already exists")
    settings = cfg()
    source_hashes = sources()
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    train = [org for org in orgs if split.get(org) == "train"]
    dev = [org for org in orgs if split.get(org) == "validation"]
    holdout = [org for org in orgs if split.get(org) == "holdout"]
    if (len(orgs), len(train), len(dev), len(holdout)) != (499, 334, 67, 68):
        raise ValueError("Historical organization split changed")
    # Only designated historical train and development labels are opened.
    train_keys, dev_keys = set(), set()
    for org in train + dev:
        with (ROOT / "data/derived" / GROUP_RUN / f"v2_{key(org)}.pkl").open("rb") as stream:
            item = pickle.load(stream)
        (train_keys if org in train else dev_keys).update(item["input_alert_keys"])
    train_truth, train_rank = read_truth(set(train), train_keys), labels(set(train))
    dev_truth, dev_rank = read_truth(set(dev), dev_keys), labels(set(dev))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=settings["descriptor_hash_bins"],
                           input_type="dict", alternate_sign=False)
    process = psutil.Process()
    started = time.perf_counter()
    peak = process.memory_info().rss
    private.mkdir(parents=True)
    feature_hashes = {}
    y_by_org, old_by_org, train_x, dev_items = {}, {}, {}, {}
    sizes = Counter()
    for index, org in enumerate(orgs, 1):
        name = key(org)
        group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        if sha256_file(group_path) != group_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen v2 groups changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        shard = paths[org]
        if sha256_file(shard) != shard_manifest["parquet_sha256"][str(shard.relative_to(ROOT))]:
            raise ValueError("Evidence projection changed")
        docs = read_docs(org, shard, sentinels, set(item["input_alert_keys"]))
        x = featurize(item["groups"], docs, item["scores"], hasher)
        feature_path = private / f"features_{name}.npz"
        sp.save_npz(feature_path, x)
        feature_hashes[name] = sha256_file(feature_path)
        sizes["organizations"] += 1
        sizes["groups"] += len(item["groups"])
        sizes["alerts"] += len(item["input_alert_keys"])
        if org in train:
            y_by_org[org] = np.asarray(training_targets(item, train_truth, train_rank[org]), dtype=np.uint8)
            old_by_org[org] = item["scores"]
            train_x[org] = x
        elif org in dev:
            dev_items[org] = item
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Prepared ranking features {index}/499", flush=True)
    feature_seconds = time.perf_counter() - started
    if sizes["groups"] != 370850 or sizes["alerts"] != 400039:
        raise ValueError("Frozen group or alert population changed")
    x_train = sp.vstack([train_x[o] for o in train], format="csr")
    y_train = np.concatenate([y_by_org[o] for o in train])
    train_groups = [len(y_by_org[o]) for o in train]
    if len(y_train) != 157072 or int(y_train.sum()) != 4624:
        raise ValueError("Historical training target changed")
    hard = settings["methods"]["lightgbm_hardneg"]
    x_hard, y_hard, hard_groups = hard_negative_training(
        train_x, y_by_org, old_by_org, settings["seed"],
        hard["hard_negatives_per_queue"], hard["random_negatives_per_queue"])
    del train_x, y_by_org, old_by_org
    models = build_models(settings["methods"], settings["seed"])
    fit_seconds = {}
    for method, model in models.items():
        tic = time.perf_counter()
        if method == "lightgbm_hardneg":
            model.fit(x_hard, y_hard, group=hard_groups)
        elif method == "xgboost_full":
            model.fit(x_train, y_train, group=train_groups, verbose=False)
        else:
            model.fit(x_train, y_train, group=train_groups)
        fit_seconds[method] = time.perf_counter() - tic
        with (private / f"{method}_model.pkl").open("wb") as stream:
            pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
        peak = max(peak, process.memory_info().rss)
        print(f"Fitted {method} in {fit_seconds[method]:.1f} seconds", flush=True)
    del x_train, y_train, x_hard, y_hard
    score_hashes = {}
    dev_rows = defaultdict(dict)
    score_started = time.perf_counter()
    for index, org in enumerate(orgs, 1):
        name = key(org)
        x = sp.load_npz(private / f"features_{name}.npz")
        result = {method: model.predict(x).astype(float).tolist()
                  for method, model in models.items()}
        score_path = private / f"scores_{name}.pkl"
        with score_path.open("wb") as stream:
            pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
        score_hashes[name] = sha256_file(score_path)
        if org in dev:
            item = dev_items[org]
            v7_path = ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl"
            if sha256_file(v7_path) != v7_freeze["score_sha256"][name]:
                raise ValueError("Frozen v7 scores changed")
            with v7_path.open("rb") as stream:
                baseline_scores = pickle.load(stream)
            for method, scores in [("frozen_v7", baseline_scores), *result.items()]:
                metric = tie_aware_ranking(item["groups"], scores, dev_truth, dev_rank[org])
                dev_rows[method][org] = {
                    "recall20": metric["recall_at_20"],
                    "p10": metric["precision_at_10"],
                    "ndcg20": metric["ndcg_at_20_rank1_highest"]}
        peak = max(peak, process.memory_info().rss)
        if index % 100 == 0:
            print(f"Frozen ranker scores {index}/499", flush=True)
    dev_table = {method: {field: float(np.mean([row[field] for row in dev_rows[method].values()]))
                          for field in ("recall20", "p10", "ndcg20")}
                 for method in dev_rows}
    base = dev_table["frozen_v7"]
    rule = settings["development_selection"]
    eligible = [method for method in models if
                dev_table[method]["recall20"] >= base["recall20"] + rule["minimum_recall20_absolute_gain"]
                and dev_table[method]["p10"] >= base["p10"] - rule["maximum_p10_absolute_loss"]
                and dev_table[method]["ndcg20"] >= base["ndcg20"] - rule["maximum_ndcg20_absolute_loss"]]
    selected = (max(eligible, key=lambda method: (dev_table[method]["recall20"],
                                                 dev_table[method]["p10"],
                                                 dev_table[method]["ndcg20"], method))
                if eligible else "frozen_v7")
    model_hashes = {method: sha256_file(private / f"{method}_model.pkl") for method in models}
    importance = {}
    for method, model in models.items():
        if method.startswith("lightgbm"):
            values = model.feature_importances_
        else:
            values = model.feature_importances_
        importance[method] = {NUMERIC_NAMES[i]: float(values[i]) for i in range(len(NUMERIC_NAMES))}
    public.mkdir()
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_post_exposure_queue_aware_ranker_predictions",
        "run": run_id, "candidate_graph_and_groups": "identical_to_frozen_v2",
        "organization_split": {"train": 334, "validation": 67, "historical_holdout": 68,
                               "unassigned_prediction_only": 30},
        "training_groups": 157072, "training_positive_groups": 4624,
        "hard_negative_training_groups": sum(hard_groups),
        "development_selection_table": dev_table, "selected_method": selected,
        "selection_uses_only_historical_validation_labels": True,
        "historical_holdout_labels_read_in_prediction": False,
        "source_sha256": source_hashes, "feature_sha256": feature_hashes,
        "model_sha256": model_hashes, "score_sha256": score_hashes,
        "numeric_feature_importance": importance,
        "versions": {"lightgbm": lgb.__version__, "xgboost": xgb.__version__,
                     "numpy": np.__version__},
        "resource": {"feature_seconds": feature_seconds, "fit_seconds": fit_seconds,
                     "score_seconds": time.perf_counter() - score_started,
                     "wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "predictions_frozen", "selected_method": selected,
                      "development_table": dev_table}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict"))
    parser.add_argument("--run-id", default="submission_ranking_ltr_v1_20261115_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": lambda: predict(args.run_id)}[args.stage]()


if __name__ == "__main__":
    main()
