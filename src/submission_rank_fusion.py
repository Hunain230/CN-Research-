"""Exploratory, label-free rank fusion on frozen full-GUIDE predicted groups.

Uses standard equal-weight reciprocal rank fusion with fixed k=60. The
predict stage reads only the prior frozen predictions, never evaluator truth.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking


PARENT = "submission_full_guide_paper_20261113_v1"
PREFIX = "submission_rank_fusion_"
K = 60


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def average_ranks(scores: list[float]) -> list[float]:
    """Descending, one-based average positions for tied raw scores."""
    if any(not math.isfinite(float(value)) for value in scores):
        raise ValueError("Non-finite upstream score")
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and scores[order[stop]] == scores[order[start]]:
            stop += 1
        mean_position = (start + 1 + stop) / 2
        for index in order[start:stop]:
            ranks[index] = mean_position
        start = stop
    return ranks


def fused_scores(count_scores: list[float], bm25_scores: list[float]) -> list[float]:
    if len(count_scores) != len(bm25_scores):
        raise ValueError("Ranker group counts differ")
    count_ranks = average_ranks(count_scores)
    bm25_ranks = average_ranks(bm25_scores)
    return [1 / (K + a) + 1 / (K + b) for a, b in zip(count_ranks, bm25_ranks)]


def parent_paths() -> tuple[Path, Path, Path]:
    public = ROOT / "outputs" / PARENT
    private = ROOT / "data/derived" / PARENT / "predictions.pkl"
    freeze = public / "prediction_freeze.json"
    manifest = json.loads((public / "run_manifest.json").read_text(encoding="utf-8"))
    if sha256_file(private) != manifest["sha256"][str(private.relative_to(ROOT))]:
        raise ValueError("Parent predictions differ from immutable manifest")
    if sha256_file(freeze) != manifest["sha256"][str(freeze.relative_to(ROOT))]:
        raise ValueError("Parent freeze differs from immutable manifest")
    if not json.loads(freeze.read_text(encoding="utf-8"))["labels_read_in_prediction_stage"] is False:
        raise ValueError("Parent predictions were not label-blind")
    return public, private, freeze


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
    if len(parent) != 499:
        raise ValueError("Parent organization count changed")
    scores = {}
    for org, item in parent.items():
        if len(item["groups"]) != len(item["count_scores"]) or len(item["groups"]) != len(item["bm25_scores"]):
            raise ValueError("Parent group/score mismatch")
        scores[org] = fused_scores(item["count_scores"], item["bm25_scores"])
    private.mkdir(parents=True)
    prediction = private / "scores.pkl"
    with prediction.open("wb") as stream:
        pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_frozen_group_label_free_rank_fusion",
        "run": run_id,
        "parent_run": PARENT,
        "parent_prediction_sha256": sha256_file(parent_prediction),
        "parent_freeze_sha256": sha256_file(parent_freeze),
        "prediction_sha256": sha256_file(prediction),
        "source_sha256": sha256_file(Path(__file__)),
        "labels_read_in_prediction_stage": False,
        "method": "equal_weight_rrf_of_count_and_local_bm25_like",
        "rrf_k": K,
        "raw_score_ties": "average one-based rank positions",
        "grouping_and_candidate_pairs": "identical to parent run",
        "organizations": len(scores),
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, "organizations": len(scores)}, sort_keys=True))


def bootstrap(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(0)
    means = array[rng.integers(0, len(array), (10_000, len(array)))].mean(axis=1)
    return {"mean": float(array.mean()), "ci95": np.quantile(means, [0.025, 0.975]).tolist(), "organizations": len(array), "resamples": 10_000}


def evaluate(run_id: str) -> None:
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id / "scores.pkl"
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation exists")
    freeze = json.loads((public / "prediction_freeze.json").read_text(encoding="utf-8"))
    if sha256_file(private) != freeze["prediction_sha256"]:
        raise ValueError("Fused predictions differ from freeze")
    if sha256_file(Path(__file__)) != freeze["source_sha256"]:
        raise ValueError("Method code differs from freeze")
    _, parent_prediction, parent_freeze = parent_paths()
    if sha256_file(parent_prediction) != freeze["parent_prediction_sha256"] or sha256_file(parent_freeze) != freeze["parent_freeze_sha256"]:
        raise ValueError("Parent source changed")
    with private.open("rb") as stream:
        fused = pickle.load(stream)
    with parent_prediction.open("rb") as stream:
        parent = pickle.load(stream)
    if set(fused) != set(parent):
        raise ValueError("Organization mismatch")
    orgs = set(parent)
    alert_keys = {alert for item in parent.values() for alert in item["input_alert_keys"]}
    truth = read_truth(orgs, alert_keys)
    ranks = labels(orgs)
    rows: dict[str, list[dict]] = defaultdict(list)
    for org, item in sorted(parent.items()):
        groups = item["groups"]
        keys = item["input_alert_keys"]
        for name, scores in (
            ("count", item["count_scores"]),
            ("bm25_like", item["bm25_scores"]),
            ("rrf_count_bm25", fused[org]),
        ):
            raw = score_org(groups, scores, truth, ranks[org], keys, {"top20_recovery_min_completeness": 0.8, "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name].append({
                "pair_f1": raw["pair_f1"],
                "p10": tied["precision_at_10"],
                "recall20": tied["recall_at_20"],
                "ndcg1": tied["ndcg_at_20_rank1_highest"],
                "ndcg20": tied["ndcg_at_20_rank20_highest_sensitivity"],
            })
    parent_metrics = json.loads((ROOT / "outputs" / PARENT / "metrics.json").read_text(encoding="utf-8"))
    for name, prior in (("count", "full_rule_count"), ("bm25_like", "full_rule_local_bm25")):
        for key, previous in (("p10", "precision_at_10_macro"), ("recall20", "end_to_end_recall_at_20_macro"), ("ndcg1", "ndcg_at_20_rank1_high_macro")):
            observed = sum(row[key] for row in rows[name]) / len(rows[name])
            if abs(observed - parent_metrics["methods"][prior][previous]["mean"]) > 1e-12:
                raise ValueError(f"Parent metric mismatch: {name}/{key}")
    metrics = {
        "classification": "exploratory_post_exposure_new_baseline_not_confirmatory",
        "run": run_id,
        "parent_run": PARENT,
        "organizations": len(orgs),
        "alerts": len(alert_keys),
        "expert_top20_denominator": parent_metrics["expert_top20_denominator"],
        "candidate_pairs": parent_metrics["candidate_pairs"],
        "possible_pairs": parent_metrics["possible_pairs"],
        "positive_pairs": parent_metrics["positive_pairs"],
        "candidate_positive_pairs": parent_metrics["candidate_positive_pairs"],
        "candidate_recall_micro": parent_metrics["candidate_recall_micro"],
        "candidate_coverage_micro": parent_metrics["candidate_coverage_micro"],
        "methods": {name: {
            "pair_f1_macro": bootstrap([row["pair_f1"] for row in series]),
            "precision_at_10_macro": bootstrap([row["p10"] for row in series]),
            "end_to_end_recall_at_20_macro": bootstrap([row["recall20"] for row in series]),
            "ndcg_at_20_rank1_high_macro": bootstrap([row["ndcg1"] for row in series]),
            "ndcg_at_20_rank20_high_macro": bootstrap([row["ndcg20"] for row in series]),
        } for name, series in rows.items()},
        "paired_rrf_minus_bm25": {
            key: bootstrap([a[key] - b[key] for a, b in zip(rows["rrf_count_bm25"], rows["bm25_like"])])
            for key in ("p10", "recall20", "ndcg1")
        },
        "limits": ["same previously accessed GUIDE_Test cohort as parent", "method is a new post-exposure descriptive baseline, no confirmatory claim", "no change to candidate pairs or grouping", "official field allowlist empty; five local descriptors only", "ambiguous keys excluded but all expert labels retained", "rank direction and queue scope unresolved"],
        "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
    }
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_rank_fusion predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_rank_fusion evaluate --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), private, public / "prediction_freeze.json", public / "metrics.json")},
        "parent_prediction_sha256": freeze["parent_prediction_sha256"],
        "method": freeze["method"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id, "rrf_recall20_macro": metrics["methods"]["rrf_count_bm25"]["end_to_end_recall_at_20_macro"]["mean"]}, sort_keys=True))


def self_test() -> None:
    assert average_ranks([5, 5, 1]) == [1.5, 1.5, 3.0]
    assert fused_scores([2, 1], [1, 2]) == fused_scores([1, 2], [2, 1])
    assert fused_scores([2, 1], [2, 1])[0] > fused_scores([2, 1], [2, 1])[1]
    print("rank fusion self-test: 3 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_rank_fusion_20261114_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": predict, "evaluate": evaluate}[args.stage](**({} if args.stage == "self-test" else {"run_id": args.run_id}))


if __name__ == "__main__":
    main()
