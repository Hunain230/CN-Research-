"""Exploratory full-GUIDE transfer of the previously frozen priority ranker.

The prediction stage reads only frozen label-free groups and ranker weights.
The evaluator opens incident membership and queue ranks after scores are frozen.
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_trained_ranker import features


PARENT = ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl"
PARENT_FREEZE = ROOT / "outputs/submission_full_guide_paper_20261113_v1/prediction_freeze.json"
MODEL = ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl"
MODEL_FREEZE = ROOT / "outputs/submission_trained_ranker_20261114_v1/prediction_freeze.json"
SPLIT = ROOT / "data/derived/guide_rerun_v2/split.json"
PREFIX = "submission_full_ranker_transfer_"


def upstream() -> dict:
    parent_freeze = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    model_freeze = json.loads(MODEL_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(PARENT) != parent_freeze["prediction_sha256"]:
        raise ValueError("Parent prediction hash changed")
    if sha256_file(MODEL) != model_freeze["model_sha256"]:
        raise ValueError("Trained model hash changed")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in
            (PARENT, PARENT_FREEZE, MODEL, MODEL_FREEZE, SPLIT)}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    sources = upstream()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    if len(parent) != 499 or len({org for org in parent if split.get(org) == "train"}) != 334:
        raise ValueError("Parent cohort or ranker training split changed")
    scores = {}
    for org, item in sorted(parent.items()):
        values = model.decision_function(features(item)).tolist()
        if len(values) != len(item["groups"]):
            raise ValueError("Group and score length mismatch")
        scores[org] = values
    private.mkdir(parents=True)
    path = private / "scores.pkl"
    with path.open("wb") as stream:
        pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_full_guide_frozen_group_ranker_transfer",
        "run": run_id,
        "organizations": len(scores),
        "source_hashes": sources,
        "code_sha256": sha256_file(Path(__file__)),
        "prediction_sha256": sha256_file(path),
        "evaluation_labels_read_in_prediction_stage": False,
        "unchanged_candidate_pairs_and_groups": True,
        "training_organizations": 334,
        "disjoint_evaluation_organizations": 135,
        "all_499_includes_training_organizations": True,
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, "organizations": len(scores)}))


def bootstrap(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(42)
    draws = arr[rng.integers(0, len(arr), size=(10000, len(arr)))].mean(axis=1)
    return {"mean": float(arr.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
            "organizations": len(arr), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze = json.loads((public / "prediction_freeze.json").read_text(encoding="utf-8"))
    if freeze["source_hashes"] != upstream() or freeze["code_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Frozen source or method changed")
    path = private / "scores.pkl"
    if freeze["prediction_sha256"] != sha256_file(path):
        raise ValueError("Frozen scores changed")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with path.open("rb") as stream:
        scores = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    if set(parent) != set(scores) or len(scores) != 499:
        raise ValueError("Prediction cohort changed")
    orgs = set(parent)
    alert_keys = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alert_keys)
    ranks = labels(orgs)
    rows = defaultdict(list)
    for org, item in sorted(parent.items()):
        for name, values in (("count", item["count_scores"]),
                             ("bm25_like", item["bm25_scores"]),
                             ("transferred_ranker", scores[org])):
            tied = tie_aware_ranking(item["groups"], values, truth, ranks[org])
            rows[(split.get(org, "historical"), name)].append({
                "org": org, "precision_at_10": tied["precision_at_10"],
                "recall_at_20": tied["recall_at_20"],
                "ndcg_at_20": tied["ndcg_at_20_rank1_highest"],
            })
    cohorts = {"disjoint_135": [o for o in sorted(orgs) if split.get(o) in ("validation", "holdout")],
               "all_499_descriptive": sorted(orgs)}
    by_method = {name: {row["org"]: row for (partition, method), series in rows.items() if method == name
                        for row in series} for name in ("count", "bm25_like", "transferred_ranker")}
    metrics = {"classification": "exploratory_post_exposure_full_guide_ranker_transfer_not_confirmatory",
               "run": run_id, "alerts": len(alert_keys), "unchanged_candidate_pairs_and_groups": True,
               "cohorts": {}}
    for cohort, selected in cohorts.items():
        methods = {}
        for name, lookup in by_method.items():
            methods[name] = {field: bootstrap([lookup[o][field] for o in selected])
                             for field in ("precision_at_10", "recall_at_20", "ndcg_at_20")}
        differences = {base: {field: bootstrap([by_method["transferred_ranker"][o][field]
                                                 - by_method[base][o][field] for o in selected])
                              for field in ("precision_at_10", "recall_at_20", "ndcg_at_20")}
                       for base in ("count", "bm25_like")}
        metrics["cohorts"][cohort] = {"organizations": len(selected),
                                      "expert_top20_denominator": 20 * len(selected),
                                      "methods": methods, "paired_ranker_minus": differences}
    metrics["limits"] = ["All GUIDE_Test labels were previously accessed during project development",
                         "The model was trained on 334 organizations from a different frozen grouping run",
                         "The 135 comparison organizations are disjoint from model training, but method selection followed earlier label exposure",
                         "All-499 aggregate includes training organizations and is descriptive only",
                         "Candidate and group predictions are unchanged; this experiment tests ordering only",
                         "No local Qwen calls; field and active-queue assumptions remain unresolved"]
    metrics["prediction_freeze_sha256"] = sha256_file(public / "prediction_freeze.json")
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_full_ranker_transfer predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_full_ranker_transfer evaluate --run-id {run_id}",
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), path, public / "prediction_freeze.json", public / "metrics.json")},
        "upstream_sha256": freeze["source_hashes"],
    })
    result = metrics["cohorts"]["disjoint_135"]["methods"]["transferred_ranker"]["recall_at_20"]["mean"]
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "disjoint_135_recall_at_20": result}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_full_ranker_transfer_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
