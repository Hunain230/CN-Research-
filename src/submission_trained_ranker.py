"""Exploratory organization-split logistic ranker on frozen GUIDE groups.

Training reads only the historical 334 training organizations. Predictions on
the 67 validation and 68 holdout organizations are frozen before their truth
is read by the separate evaluate command. All labels were previously exposed
in this project, so this is not a new confirmatory holdout.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .guide_rerun_v2 import labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking
from .submission_rank_fusion import average_ranks, bootstrap, parent_paths, write_json, PARENT


PREFIX = "submission_trained_ranker_"
SPLIT = ROOT / "data/derived/guide_rerun_v2/split.json"
TRAIN_NAME = "train"
EVAL_NAMES = {"validation", "holdout"}


def partition(parent: dict) -> tuple[list[str], list[str]]:
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = sorted(org for org in parent if split.get(org) == TRAIN_NAME)
    evaluated = sorted(org for org in parent if split.get(org) in EVAL_NAMES)
    if len(train) != 334 or len(evaluated) != 135 or set(train) & set(evaluated):
        raise ValueError("Historical organization split changed")
    return train, evaluated


def features(item: dict) -> np.ndarray:
    """Use frozen label-free group scores and within-queue positions only."""
    count = item["count_scores"]
    bm25 = item["bm25_scores"]
    n = len(count)
    if n != len(bm25) or not n:
        raise ValueError("Missing aligned group scores")
    count_rank = average_ranks(count)
    bm25_rank = average_ranks(bm25)
    return np.asarray([
        [math.log1p(count[i]), math.log1p(max(0.0, bm25[i])),
         1 - count_rank[i] / (n + 1), 1 - bm25_rank[i] / (n + 1),
         math.log1p(n)]
        for i in range(n)
    ], dtype=float)


def training_targets(item: dict, truth: dict[str, str], ranks: dict[str, int]) -> list[int]:
    counts = Counter(truth[a] for a in item["input_alert_keys"])
    result = []
    for group in item["groups"]:
        memberships = Counter(truth[a] for a in group)
        gold, overlap = max(memberships.items(), key=lambda pair: (pair[1], pair[0]))
        result.append(int(gold in ranks and overlap / counts[gold] >= 0.8 and overlap / len(group) >= 0.8))
    return result


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("New versioned run ID required")
    _, parent_prediction, parent_freeze = parent_paths()
    with parent_prediction.open("rb") as stream:
        parent = pickle.load(stream)
    train, evaluated = partition(parent)
    train_keys = {a for org in train for a in parent[org]["input_alert_keys"]}
    train_truth = read_truth(set(train), train_keys)
    train_ranks = labels(set(train))
    matrices = []
    targets = []
    for org in train:
        matrices.append(features(parent[org]))
        targets.extend(training_targets(parent[org], train_truth, train_ranks[org]))
    positives = sum(targets)
    if positives < 20 or positives == len(targets):
        raise ValueError("Training target lacks classes")
    model = make_pipeline(StandardScaler(), LogisticRegression(
        C=1.0, class_weight="balanced", solver="liblinear", max_iter=500, random_state=0,
    ))
    model.fit(np.vstack(matrices), np.asarray(targets))
    scores = {org: model.decision_function(features(parent[org])).tolist() for org in evaluated}
    private.mkdir(parents=True)
    model_path = private / "model.pkl"
    scores_path = private / "scores.pkl"
    with model_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    with scores_path.open("wb") as stream:
        pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_organization_disjoint_trained_ranker_post_exposure",
        "run": run_id,
        "parent_run": PARENT,
        "parent_prediction_sha256": sha256_file(parent_prediction),
        "parent_freeze_sha256": sha256_file(parent_freeze),
        "split_sha256": sha256_file(SPLIT),
        "source_sha256": sha256_file(Path(__file__)),
        "training_organizations": len(train),
        "evaluation_organizations": len(evaluated),
        "training_groups": len(targets),
        "positive_training_groups": positives,
        "training_labels_read": True,
        "evaluation_labels_read_in_prediction_stage": False,
        "features": ["log_alert_count", "log_bm25_like", "count_rank_percentile", "bm25_rank_percentile", "log_queue_groups"],
        "model": "standard_scaler_plus_balanced_logistic_C1_liblinear_seed0",
        "model_sha256": sha256_file(model_path),
        "prediction_sha256": sha256_file(scores_path),
        "candidate_pairs_and_groups": "identical to parent run",
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, "training_orgs": len(train), "evaluation_orgs": len(evaluated), "training_positive_groups": positives}, sort_keys=True))


def evaluate(run_id: str) -> None:
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze = json.loads((public / "prediction_freeze.json").read_text(encoding="utf-8"))
    if sha256_file(private / "scores.pkl") != freeze["prediction_sha256"] or sha256_file(private / "model.pkl") != freeze["model_sha256"]:
        raise ValueError("Frozen model or prediction changed")
    if sha256_file(Path(__file__)) != freeze["source_sha256"] or sha256_file(SPLIT) != freeze["split_sha256"]:
        raise ValueError("Frozen method or split changed")
    _, parent_prediction, parent_freeze = parent_paths()
    if sha256_file(parent_prediction) != freeze["parent_prediction_sha256"] or sha256_file(parent_freeze) != freeze["parent_freeze_sha256"]:
        raise ValueError("Parent changed")
    with (private / "scores.pkl").open("rb") as stream:
        predictions = pickle.load(stream)
    with parent_prediction.open("rb") as stream:
        parent = pickle.load(stream)
    train, evaluated = partition(parent)
    if set(predictions) != set(evaluated) or set(predictions) & set(train):
        raise ValueError("Prediction cohort changed")
    eval_keys = {a for org in evaluated for a in parent[org]["input_alert_keys"]}
    truth = read_truth(set(evaluated), eval_keys)
    ranks = labels(set(evaluated))
    rows: dict[str, list[dict]] = defaultdict(list)
    pair_totals = Counter()
    candidate_pairs = possible_pairs = candidate_positive = positive_pairs = 0
    for org in evaluated:
        item = parent[org]
        keys = item["input_alert_keys"]
        groups = item["groups"]
        candidate_pairs += len(item["candidate_edges"])
        possible_pairs += len(keys) * (len(keys) - 1) // 2
        counts = Counter(truth[a] for a in keys)
        positive_pairs += sum(n * (n - 1) // 2 for n in counts.values())
        candidate_positive += sum(truth[a] == truth[b] for a, b in item["candidate_edges"])
        for name, scores in (("count", item["count_scores"]), ("bm25_like", item["bm25_scores"]), ("trained_logistic", predictions[org])):
            raw = score_org(groups, scores, truth, ranks[org], keys, {"top20_recovery_min_completeness": 0.8, "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name].append({"p10": tied["precision_at_10"], "recall20": tied["recall_at_20"], "ndcg1": tied["ndcg_at_20_rank1_highest"], "ndcg20": tied["ndcg_at_20_rank20_highest_sensitivity"], "pair_f1": raw["pair_f1"]})
            if name == "trained_logistic":
                pair_totals.update({"tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"]})
    metrics = {
        "classification": "exploratory_organization_disjoint_trained_ranker_post_exposure_not_confirmatory",
        "run": run_id,
        "parent_run": PARENT,
        "training_organizations": len(train),
        "evaluation_organizations": len(evaluated),
        "evaluation_alerts": len(eval_keys),
        "expert_top20_denominator": 20 * len(evaluated),
        "candidate_pairs": candidate_pairs,
        "possible_pairs": possible_pairs,
        "positive_pairs": positive_pairs,
        "candidate_positive_pairs": candidate_positive,
        "candidate_recall_micro": candidate_positive / positive_pairs,
        "candidate_coverage_micro": candidate_pairs / possible_pairs,
        "shared_pair_confusion": {"tp": pair_totals["tp"], "fp": pair_totals["fp"], "fn": pair_totals["fn"], "f1_micro": 2 * pair_totals["tp"] / (2 * pair_totals["tp"] + pair_totals["fp"] + pair_totals["fn"])},
        "methods": {name: {
            "precision_at_10_macro": bootstrap([row["p10"] for row in series]),
            "end_to_end_recall_at_20_macro": bootstrap([row["recall20"] for row in series]),
            "ndcg_at_20_rank1_high_macro": bootstrap([row["ndcg1"] for row in series]),
            "ndcg_at_20_rank20_high_macro": bootstrap([row["ndcg20"] for row in series]),
            "pair_f1_macro": bootstrap([row["pair_f1"] for row in series]),
        } for name, series in rows.items()},
        "paired_trained_minus_bm25": {key: bootstrap([a[key] - b[key] for a, b in zip(rows["trained_logistic"], rows["bm25_like"])]) for key in ("p10", "recall20", "ndcg1")},
        "limits": ["all GUIDE_Test labels previously exposed elsewhere in project", "334/135 organization disjointness is respected in this run but does not restore an untouched test", "same weak parent candidates/groups for all three rankers", "training target is 80/80 recoverable expert top20 component, not incident severity", "official field approval and queue/rank semantics unresolved"],
        "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
    }
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_trained_ranker predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_trained_ranker evaluate --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), SPLIT, private / "model.pkl", private / "scores.pkl", public / "prediction_freeze.json", public / "metrics.json")},
        "parent_prediction_sha256": freeze["parent_prediction_sha256"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id, "trained_recall20_macro": metrics["methods"]["trained_logistic"]["end_to_end_recall_at_20_macro"]["mean"]}, sort_keys=True))


def self_test() -> None:
    item = {"count_scores": [2.0, 1.0], "bm25_scores": [3.0, 2.0]}
    matrix = features(item)
    assert matrix.shape == (2, 5) and np.isfinite(matrix).all()
    assert matrix[0, 2] > matrix[1, 2]
    print("trained ranker self-test: 2 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_trained_ranker_20261114_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": predict, "evaluate": evaluate}[args.stage](**({} if args.stage == "self-test" else {"run_id": args.run_id}))


if __name__ == "__main__":
    main()
