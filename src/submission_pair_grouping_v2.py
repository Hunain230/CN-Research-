"""Apply the development-selected pair-link threshold to 57 frozen queues."""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, load_alerts, score_groups, tie_aware_ranking, write_json
from .submission_pair_group_calibrate import OUT as CALIBRATION, groups_at
from .submission_pair_model_grouping import (CANDIDATE_MANIFEST, PARENT, RANKER,
                                             pair_features, verify_sources)
from .submission_trained_ranker import features as rank_features


PREFIX = "submission_pair_grouping_v2_"
PAIR_RUN = "submission_pair_model_grouping_20261114_v1"


def sources() -> dict:
    base = verify_sources()
    pair_path = ROOT / "data/derived" / PAIR_RUN / "pair_model.pkl"
    fit = ROOT / "outputs" / PAIR_RUN / "fit_freeze.json"
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if sha256_file(pair_path) != json.loads(fit.read_text(encoding="utf-8"))["model_sha256"]:
        raise ValueError("Training model changed")
    calibration_code = Path(__file__).parent / "submission_pair_group_calibrate.py"
    if sha256_file(calibration_code) != calibration["source_sha256"][str(calibration_code.relative_to(ROOT))]:
        raise ValueError("Calibration implementation changed")
    return {**base, str(pair_path.relative_to(ROOT)): sha256_file(pair_path),
            str(fit.relative_to(ROOT)): sha256_file(fit),
            str(CALIBRATION.relative_to(ROOT)): sha256_file(CALIBRATION)}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    source_hashes = sources()
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    threshold = float(calibration["selected_threshold"])
    if calibration["validation_organizations"] != 42 or calibration["holdout_labels_read"]:
        raise ValueError("Calibration boundary changed")
    with (ROOT / "data/derived" / PAIR_RUN / "pair_model.pkl").open("rb") as stream:
        pair_model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if len(parent) != 57:
        raise ValueError("Frozen 57-queue parent changed")
    docs_by_org, census = load_alerts(set(parent))
    candidate_hashes = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))["hashes"]
    predictions = {}
    for org, item in sorted(parent.items()):
        candidate_path = ROOT / "data/derived/guide_rerun_v2/correlation_predictions" / f"{key(org)}.npz"
        if sha256_file(candidate_path) != candidate_hashes[key(org)]:
            raise ValueError("Frozen candidate file changed")
        with np.load(candidate_path) as data:
            keys, pairs = data["keys"].tolist(), data["edges"]
        if set(keys) != set(item["input_alert_keys"]) or set(keys) != set(docs_by_org[org]):
            raise ValueError("Alert universe changed")
        docs = docs_by_org[org]
        x = np.asarray([pair_features(docs[keys[int(a)]], docs[keys[int(b)]])
                        for a, b in zip(pairs // len(keys), pairs % len(keys))], dtype=np.float32)
        probability = pair_model.predict_proba(x)[:, 1] if len(x) else np.array([])
        groups = groups_at(keys, pairs, probability, threshold)
        count_scores, bm25_scores = score_groups(groups, docs)
        scores = ranker.decision_function(rank_features({"count_scores": count_scores,
                                                           "bm25_scores": bm25_scores})).tolist()
        predictions[org] = {"input_alert_keys": keys, "candidate_pair_count": len(pairs),
                            "groups": groups, "scores": scores,
                            "accepted_threshold_edges": int((probability >= threshold).sum())}
    private.mkdir(parents=True)
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_validation_selected_pair_grouping_57_queues",
        "run": run_id, "organizations": len(predictions),
        "alerts": sum(len(x["input_alert_keys"]) for x in predictions.values()),
        "candidate_pairs": sum(x["candidate_pair_count"] for x in predictions.values()),
        "accepted_threshold_edges": sum(x["accepted_threshold_edges"] for x in predictions.values()),
        "threshold": threshold, "raw_scan_rows": census["raw_rows_scanned"],
        "prediction_sha256": sha256_file(prediction_path),
        "source_sha256": source_hashes, "code_sha256": sha256_file(Path(__file__)),
        "evaluation_labels_read_in_prediction_stage": False,
        "unchanged_candidate_pairs": True,
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id,
                      "organizations": len(predictions), "threshold": threshold}))


def bootstrap(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    rng = np.random.default_rng(29)
    draws = a[rng.integers(0, len(a), size=(10000, len(a)))].mean(axis=1)
    return {"mean": float(a.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
            "organizations": len(a), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    prediction_path = private / "predictions.pkl"
    if freeze["source_sha256"] != sources() or freeze["code_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Method lineage changed")
    if sha256_file(prediction_path) != freeze["prediction_sha256"]:
        raise ValueError("Frozen predictions changed")
    with prediction_path.open("rb") as stream:
        predicted = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with (ROOT / "data/derived/submission_transfer_ranker_20261114_v1/scores.pkl").open("rb") as stream:
        parent_ranked = pickle.load(stream)
    orgs = set(predicted)
    if len(orgs) != 57 or orgs != set(parent) or orgs != set(parent_ranked):
        raise ValueError("Cohort mismatch")
    alerts = {a for item in predicted.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alerts)
    ranks = labels(orgs)
    rows = defaultdict(list)
    pair = defaultdict(Counter)
    ceilings = Counter()
    for org in sorted(orgs):
        item = predicted[org]
        rule = parent[org]["methods"]["B1_rule_bm25"]["groups"]
        compare = (("new_pair_grouping", item["groups"], item["scores"]),
                   ("frozen_rule_transferred_ranker", rule, parent_ranked[org]["rule"]))
        for method, groups, scores in compare:
            raw = score_org(groups, scores, truth, ranks[org], item["input_alert_keys"],
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[method].append({"recall20": tied["recall_at_20"],
                                 "p10": tied["precision_at_10"],
                                 "ndcg20": tied["ndcg_at_20_rank1_highest"]})
            pair[method].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"],
                                 "fn": raw["pair_fn"]})
            counts = Counter(truth[a] for a in item["input_alert_keys"])
            found = set()
            for group in groups:
                overlaps = Counter(truth[a] for a in group)
                gold, n = max(overlaps.items(), key=lambda v: (v[1], v[0]))
                if gold in ranks[org] and n / counts[gold] >= 0.8 and n / len(group) >= 0.8:
                    found.add(gold)
            ceilings[method] += len(found)
    methods = {}
    for method, series in rows.items():
        tp, fp, fn = (pair[method][k] for k in ("tp", "fp", "fn"))
        methods[method] = {
            "end_to_end_recall_at_20_macro": bootstrap([x["recall20"] for x in series]),
            "precision_at_10_macro": bootstrap([x["p10"] for x in series]),
            "ndcg_at_20_macro": bootstrap([x["ndcg20"] for x in series]),
            "pair_confusion_micro": {"tp": tp, "fp": fp, "fn": fn,
                                     "precision": tp / (tp + fp) if tp + fp else 0,
                                     "recall": tp / (tp + fn) if tp + fn else 0,
                                     "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0},
            "oracle_order_recoverable_labels": ceilings[method],
            "oracle_order_recall20_ceiling": ceilings[method] / (20 * len(orgs)),
        }
    paired = {metric: bootstrap([a[metric] - b[metric] for a, b in zip(
        rows["new_pair_grouping"], rows["frozen_rule_transferred_ranker"])])
        for metric in ("recall20", "p10", "ndcg20")}
    metrics = {"classification": "exploratory_previously_exposed_57_queue_validation_selected_grouping_not_confirmatory",
               "run": run_id, "organizations": len(orgs), "alerts": len(alerts),
               "expert_top20_denominator": 20 * len(orgs),
               "candidate_pairs": sum(x["candidate_pair_count"] for x in predicted.values()),
               "methods": methods, "paired_new_minus_frozen_rule": paired,
               "limits": ["All 57 labels were previously exposed during this project",
                          "0.995 threshold selected on 42 separate complete small development organizations",
                          "Frozen candidate retrieval unchanged; only link decisions and grouping differ",
                          "Five local descriptor fields are assumptions, not approved operational model inputs",
                          "No Qwen calls or live SOC evaluation"],
               "prediction_freeze_sha256": sha256_file(freeze_path)}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_pair_grouping_v2 predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_pair_grouping_v2 evaluate --run-id {run_id}",
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), prediction_path, freeze_path, public / "metrics.json")},
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "new_recall20": methods["new_pair_grouping"]["end_to_end_recall_at_20_macro"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_pair_grouping_v2_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
