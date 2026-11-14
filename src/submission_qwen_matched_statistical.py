"""Frozen five-descriptor statistical control on the 20-queue Qwen pair budget."""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import labels
from .offline_joint_comparison import bootstrap, read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, score_groups, write_json
from .submission_local_qwen import groups_from_links
from .submission_local_qwen_v2 import rank_metrics
from .submission_pair_model_grouping import pair_features


PREFIX = "submission_qwen_matched_statistical_"
QWEN_RUN = "submission_qwen_v2_paper_20261113_v1"
QWEN_FREEZE = ROOT / "outputs" / QWEN_RUN / "prediction_freeze.json"
QWEN_METRICS = ROOT / "outputs" / QWEN_RUN / "metrics.json"
QWEN_PREDICTIONS = ROOT / "data/derived" / QWEN_RUN / "predictions.pkl"
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
MODEL = ROOT / "data/derived/submission_pair_model_grouping_20261114_v1/pair_model.pkl"
CALIBRATION = ROOT / "outputs/submission_pair_group_calibration_20261114_v1.json"


def sources() -> dict:
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration["selected_threshold"] != .995:
        raise ValueError("Development threshold changed")
    fit = json.loads((ROOT / "outputs/submission_pair_model_grouping_20261114_v1/fit_freeze.json").read_text(encoding="utf-8"))
    if sha256_file(MODEL) != fit["model_sha256"]:
        raise ValueError("Pair model changed")
    qwen = json.loads(QWEN_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(QWEN_PREDICTIONS) != qwen["prediction_sha256"]:
        raise ValueError("Qwen pair sample changed")
    paths = (Path(__file__), ROOT / "src/submission_pair_model_grouping.py", QWEN_FREEZE,
             QWEN_PREDICTIONS, PREPARED, MODEL, CALIBRATION)
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned statistical-control run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    source = sources()
    threshold = json.loads(CALIBRATION.read_text(encoding="utf-8"))["selected_threshold"]
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    with QWEN_PREDICTIONS.open("rb") as stream:
        qwen = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    predictions = {}
    census = Counter()
    for org, item in sorted(qwen.items()):
        pairs = item["pairs"]
        if len(pairs) != 12:
            raise ValueError("Qwen pair budget changed")
        docs = {a: data["alerts"][a]["fields"] for a in item["alerts"]}
        x = np.asarray([pair_features(docs[p["left"]], docs[p["right"]]) for p in pairs], dtype=np.float32)
        probability = model.predict_proba(x)[:, 1]
        decisions = {p["id"]: {"decision": "LINK" if probability[i] >= threshold else "NO_LINK"}
                     for i, p in enumerate(pairs)}
        groups = groups_from_links(item["alerts"], pairs, decisions)
        count, bm25 = score_groups(groups, docs)
        predictions[org] = {"alerts": item["alerts"], "pairs": pairs,
                            "groups": groups, "count_scores": count, "bm25_scores": bm25,
                            "accepted_edges": sum(d["decision"] == "LINK" for d in decisions.values())}
        census.update({"organizations": 1, "selected_pairs": len(pairs),
                       "selected_alerts": len(item["alerts"]),
                       "accepted_edges": predictions[org]["accepted_edges"]})
    private.mkdir(parents=True)
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_five_descriptor_statistical_control_on_frozen_qwen_pair_sample",
        "run": run_id, "census": dict(census), "threshold": threshold,
        "prediction_sha256": sha256_file(prediction_path), "source_sha256": source,
        "evaluation_labels_read_in_prediction_stage": False,
        "model_calls": 0,
    })
    print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources():
        raise ValueError("Source changed")
    path = private / "predictions.pkl"
    if sha256_file(path) != freeze["prediction_sha256"]:
        raise ValueError("Prediction changed")
    with path.open("rb") as stream:
        predictions = pickle.load(stream)
    with QWEN_PREDICTIONS.open("rb") as stream:
        qwen = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    orgs = set(predictions)
    all_alerts = {a for a, doc in data["alerts"].items() if doc["org"] in orgs}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    by_org = defaultdict(list)
    for a in all_alerts:
        by_org[data["alerts"][a]["org"]].append(a)
    rows = defaultdict(list)
    for org in sorted(orgs):
        item = predictions[org]
        original = qwen[org]
        if item["alerts"] != original["alerts"] or item["pairs"] != original["pairs"]:
            raise ValueError("Selected alert/pair scope changed")
        full_counts = Counter(truth[a] for a in by_org[org])
        choices = (("statistical_count", item["groups"], item["count_scores"]),
                   ("statistical_bm25", item["groups"], item["bm25_scores"]),
                   ("qwen_c_p", original["groups"], original["scores"]))
        for name, groups, scores in choices:
            metric, recovered = rank_metrics(groups, scores, truth, ranks[org], full_counts)
            rows[name].append({"recall20": metric["recall_at_20"],
                               "p10": metric["precision_at_10"],
                               "ndcg20": metric["ndcg_at_20_rank1_highest"],
                               "recovered": recovered})
    old = json.loads(QWEN_METRICS.read_text(encoding="utf-8"))
    if abs(sum(r["recall20"] for r in rows["qwen_c_p"]) / 20
           - old["cpv"]["end_to_end_recall_at_20_macro"]["mean"]) > 1e-12:
        raise ValueError("Original Qwen evaluation reproduction failed")
    methods = {name: {metric: bootstrap([r[metric] for r in series])
                      for metric in ("recall20", "p10", "ndcg20")}
               for name, series in rows.items()}
    paired = {name: {metric: bootstrap([a[metric] - b[metric] for a, b in zip(rows[name], rows["qwen_c_p"])])
                     for metric in ("recall20", "p10", "ndcg20")}
              for name in ("statistical_count", "statistical_bm25")}
    result = {"classification": "exploratory_20_queue_matched_statistical_control_not_CPV_superiority",
              "run": run_id, "scope": freeze["census"], "expert_top20_denominator": 400,
              "methods": methods, "paired_statistical_minus_qwen": paired,
              "prediction_freeze_sha256": sha256_file(freeze_path),
              "limits": ["Previously accessed 20 queues", "Same 240 selected exact-match candidate pairs and five descriptors",
                         "B2/B3 group-priority outputs unavailable", "V did not revise Qwen C/P predictions"]}
    write_json(public / "metrics.json", result)
    write_json(public / "run_manifest.json", {"classification": result["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, path, public / "metrics.json")}})
    print(json.dumps({name: round(v["recall20"]["mean"], 4) for name, v in methods.items()}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_qwen_matched_statistical_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
