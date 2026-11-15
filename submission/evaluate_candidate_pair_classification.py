"""Evaluate frozen pair-model scores on the frozen candidate-pair population."""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_full_entity_time import PARENT, read_docs, generate
from src.submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


OUT = ROOT / "outputs/submission_candidate_pair_classification_20261115_v1.json"
RUN = "submission_entity_time_pair_v2_20261114_v1"
MODEL = ROOT / "data/derived" / RUN / "pair_model.pkl"
FIT = ROOT / "outputs" / RUN / "fit_freeze.json"
CALIBRATION = ROOT / "outputs" / RUN / "calibration.json"


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Candidate-pair evaluation already frozen")
    fit = json.loads(FIT.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if sha256_file(MODEL) != fit["model_sha256"]:
        raise ValueError("Frozen pair model changed")
    threshold = float(calibration["selected_threshold"])
    if threshold != .75:
        raise ValueError("Selected pair threshold changed")
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    truth = read_truth(set(orgs), {alert for item in parent.values() for alert in item["input_alert_keys"]})
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    scores, targets, cohort = [], [], []
    started = time.perf_counter()
    for index, org in enumerate(orgs, 1):
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        n = len(keys)
        y = np.fromiter((truth[keys[int(edge // n)]] == truth[keys[int(edge % n)]]
                         for edge in edges), dtype=np.uint8, count=len(edges))
        scores.append(probability)
        targets.append(y)
        cohort.append((split.get(org), len(edges)))
        if index % 50 == 0:
            print(f"Scored candidate pairs {index}/499 queues", flush=True)
    p = np.concatenate(scores)
    y = np.concatenate(targets)
    if len(p) != 1942648 or int(y.sum()) != 699790:
        raise ValueError("Candidate-pair population changed")
    slices = {}
    offset = 0
    for group, length in cohort:
        slices.setdefault(group, []).append((offset, offset + length))
        offset += length

    def evaluate(mask: np.ndarray) -> dict:
        selected_scores, selected_truth = p[mask], y[mask]
        predicted = selected_scores >= threshold
        tp = int(np.count_nonzero(predicted & (selected_truth == 1)))
        fp = int(np.count_nonzero(predicted & (selected_truth == 0)))
        fn = int(np.count_nonzero(~predicted & (selected_truth == 1)))
        tn = int(np.count_nonzero(~predicted & (selected_truth == 0)))
        return {"candidate_pairs": len(selected_truth), "positive_pairs": int(selected_truth.sum()),
                "positive_prevalence": float(selected_truth.mean()),
                "threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "recall": tp/(tp+fn), "precision": tp/(tp+fp) if tp+fp else 0,
                "f1": 2*tp/(2*tp+fp+fn), "fpr": fp/(fp+tn),
                "roc_auc": float(roc_auc_score(selected_truth, selected_scores)),
                "pr_auc_average_precision": float(average_precision_score(selected_truth, selected_scores))}

    def cohort_mask(names: set[str]) -> np.ndarray:
        mask = np.zeros(len(p), dtype=bool)
        for name in names:
            for start, end in slices.get(name, []):
                mask[start:end] = True
        return mask

    result = {"classification": "exploratory_frozen_pair_model_conditional_on_candidate_retrieval",
              "dataset": "GUIDE_Test", "organizations": 499,
              "all_499_descriptive": evaluate(np.ones(len(p), dtype=bool)),
              "outside_training_135": evaluate(cohort_mask({"validation", "holdout"})),
              "historical_holdout_68_previously_exposed": evaluate(cohort_mask({"holdout"})),
              "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                                for path in (Path(__file__), MODEL, FIT, CALIBRATION, SPLIT,
                                             ROOT / "outputs/submission_entity_time_shards_20261114_v1.json")},
              "wall_seconds": time.perf_counter()-started,
              "limits": ["Conditional on the frozen 1,942,648 candidate pairs; misses outside retrieval are excluded",
                         "All GUIDE_Test labels were previously accessed elsewhere in the project",
                         "Candidate pair classification is not group co-membership or end-to-end Recall@20",
                         "Entity/time availability at alert creation remains unconfirmed"]}
    write_json(OUT, result)
    print(json.dumps({"status": "candidate_pair_classification_complete",
                      "all_499": result["all_499_descriptive"],
                      "outside_training_135": result["outside_training_135"]}, sort_keys=True))


if __name__ == "__main__":
    main()
