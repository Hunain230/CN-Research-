"""Train-only group priority model on frozen v2 groups; exploratory evaluation."""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from .submission_full_entity_time import read_docs
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_trained_ranker import training_targets
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_group_ranker_v4_"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
PRIVATE_GROUPS = ROOT / "data/derived" / GROUP_RUN
FIELDS = ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")


def group_features(groups: list[list[str]], docs: dict, old_scores: list[float]) -> np.ndarray:
    counts, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in docs})
    n = len(groups)
    ranks_old = np.argsort(np.argsort(np.asarray(old_scores), kind="stable"), kind="stable")
    ranks_bm = np.argsort(np.argsort(np.asarray(bm25), kind="stable"), kind="stable")
    rows = []
    for i, group in enumerate(groups):
        timestamps = [docs[a]["stamp"] for a in group]
        field_sizes = [len(set().union(*(docs[a]["fields"][field] for a in group))) for field in FIELDS]
        entity_sizes = [len(set().union(*(docs[a]["entities"] for a in group)))]
        rows.append([math.log1p(counts[i]), math.log1p(max(bm25[i], 0)),
                     float(old_scores[i]), float(ranks_old[i] / n), float(ranks_bm[i] / n),
                     math.log1p(n), math.log1p((max(timestamps) - min(timestamps)) / 3600),
                     *[math.log1p(x) for x in field_sizes + entity_sizes]])
    return np.asarray(rows, dtype=np.float32)


def bootstrap(values: list[float]) -> dict:
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(51)
    draws = x[rng.integers(0, len(x), size=(5000, len(x)))].mean(axis=1)
    return {"mean": float(x.mean()), "ci95": np.quantile(draws, [.025, .975]).tolist(),
            "organizations": len(x), "resamples": 5000}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v4 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    train = [o for o in orgs if split.get(o) == "train"]
    if len(orgs) != 499 or len(train) != 334:
        raise ValueError("Historical cohort changed")
    truth = read_truth(set(train), {a for o in train for a in baseline[o]["input_alert_keys"]})
    ranks = labels(set(train))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    matrices, targets = [], []
    private.mkdir(parents=True)
    scores_hash = {}
    cached_features = {}
    started = time.perf_counter()
    for index, org in enumerate(orgs, 1):
        group_path = PRIVATE_GROUPS / f"v2_{key(org)}.pkl"
        if sha256_file(group_path) != freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen v2 group changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        path = paths[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Field projection changed")
        docs = read_docs(org, path, sentinels, set(item["input_alert_keys"]))
        x = group_features(item["groups"], docs, item["scores"])
        if org in train:
            matrices.append(x)
            targets.extend(training_targets(item, truth, ranks[org]))
        else:
            cached_features[org] = x
        if index % 50 == 0:
            print(f"Prepared {index}/499 organizations", flush=True)
    x_train = np.vstack(matrices)
    y_train = np.asarray(targets, dtype=np.uint8)
    if y_train.sum() < 100 or y_train.sum() >= len(y_train):
        raise ValueError("Priority target invalid")
    # Fixed before inspecting validation/holdout results; modest weighting preserves rank utility.
    model = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15,
                                           min_samples_leaf=50, learning_rate=.05,
                                           l2_regularization=2, random_state=51)
    weights = np.where(y_train == 1, 10.0, 1.0)
    model.fit(x_train, y_train, sample_weight=weights)
    model_path = private / "rank_model.pkl"
    with model_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    # Reconstruct training features from their frozen groups only; no further label reads.
    for org in orgs:
        if org in cached_features:
            x = cached_features[org]
        else:
            group_path = PRIVATE_GROUPS / f"v2_{key(org)}.pkl"
            with group_path.open("rb") as stream:
                item = pickle.load(stream)
            docs = read_docs(org, paths[org], sentinels, set(item["input_alert_keys"]))
            x = group_features(item["groups"], docs, item["scores"])
        score_path = private / f"scores_{key(org)}.pkl"
        with score_path.open("wb") as stream:
            pickle.dump(model.predict_proba(x)[:, 1].tolist(), stream, protocol=pickle.HIGHEST_PROTOCOL)
        scores_hash[key(org)] = sha256_file(score_path)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_train_only_priority_model_on_frozen_v2_groups",
        "run": run_id, "organizations": 499, "train_organizations": 334,
        "train_groups": len(y_train), "positive_train_groups": int(y_train.sum()),
        "validation_or_holdout_labels_read_in_prediction_stage": False,
        "model_sha256": sha256_file(model_path), "score_sha256": scores_hash,
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                          (Path(__file__), GROUP_FREEZE, SPLIT)},
        "wall_seconds": time.perf_counter() - started,
        "features": "old_rank_score_count_bm25_queue_rank_percentiles_group_field_diversity_entity_diversity_time_span",
    })
    print(json.dumps({"status": "predictions_frozen", "train_groups": len(y_train),
                      "positive_groups": int(y_train.sum())}))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for relative, expected in freeze["source_sha256"].items():
        if sha256_file(ROOT / relative) != expected:
            raise ValueError("Source changed")
    if sha256_file(private / "rank_model.pkl") != freeze["model_sha256"]:
        raise ValueError("Model changed")
    v2_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    truth = read_truth(set(orgs), {a for x in baseline.values() for a in x["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    for org in orgs:
        name = key(org)
        score_path = private / f"scores_{name}.pkl"
        v2_path = PRIVATE_GROUPS / f"v2_{name}.pkl"
        if sha256_file(score_path) != freeze["score_sha256"][name] or sha256_file(v2_path) != v2_freeze["prediction_sha256"][name]:
            raise ValueError("Prediction changed")
        with score_path.open("rb") as stream:
            scores = pickle.load(stream)
        with v2_path.open("rb") as stream:
            item = pickle.load(stream)
        for method, values in (("v4_group_ranker", scores), ("v2_ranker", item["scores"])):
            metric = tie_aware_ranking(item["groups"], values, truth, ranks[org])
            rows[method][org] = {"recall20": metric["recall_at_20"],
                                 "p10": metric["precision_at_10"],
                                 "ndcg20": metric["ndcg_at_20_rank1_highest"]}
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [o for o in orgs if split.get(o) in ("validation", "holdout")],
               "validation_67_previously_exposed": [o for o in orgs if split.get(o) == "validation"],
               "holdout_68_previously_exposed": [o for o in orgs if split.get(o) == "holdout"]}
    result = {}
    for name, chosen in cohorts.items():
        result[name] = {"organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
                        "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                             for metric in ("recall20", "p10", "ndcg20")}
                                    for method in rows},
                        "paired_v4_minus_v2": {metric: bootstrap([rows["v4_group_ranker"][o][metric] - rows["v2_ranker"][o][metric]
                                                                 for o in chosen])
                                               for metric in ("recall20", "p10", "ndcg20")}}
    metrics = {"classification": "exploratory_post_exposure_priority_model_not_confirmatory",
               "run": run_id, "groups_and_candidates": "identical_to_frozen_v2",
               "cohorts": result, "prediction_freeze_sha256": sha256_file(freeze_path),
               "limits": ["GUIDE_Test labels previously accessed", "No untouched cohort",
                          "Entity/time availability and operational approval unresolved"]}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {"classification": metrics["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, public / "metrics.json", private / "rank_model.pkl")},
        "private_score_sha256": freeze["score_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete",
                      "all_499_recall20": result["all_499_descriptive"]["methods"]["v4_group_ranker"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_group_ranker_v4_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
