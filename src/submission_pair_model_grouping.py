"""Exploratory trained pair-link grouping on 57 complete GUIDE queues.

Fit opens only historical training membership. Predict reads permitted local
descriptors and frozen label-blind candidates. Evaluate opens the 57 labels
after the grouping and ranking predictions are frozen.
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .guide_rerun_v2 import FIELDS, key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, DSU, load_alerts, score_groups, tie_aware_ranking, write_json
from .submission_trained_ranker import features as rank_features


PREFIX = "submission_pair_model_grouping_"
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
SPLIT = ROOT / "data/derived/guide_rerun_v2/split.json"
PARENT = ROOT / "data/derived/offline_joint_v2/predictions.pkl"
PARENT_MANIFEST = ROOT / "outputs/offline_joint_v2/run_manifest.json"
CANDIDATE_MANIFEST = ROOT / "outputs/guide_rerun_v2/correlation_prediction_freeze.json"
RANKER = ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl"
RANKER_FREEZE = ROOT / "outputs/submission_trained_ranker_20261114_v1/prediction_freeze.json"
LINK_THRESHOLD = 0.5


def pair_features(left: dict, right: dict) -> list[float]:
    values = []
    for field in FIELDS:
        a, b = set(left[field]), set(right[field])
        both = len(a & b)
        values.extend((both / len(a | b) if a | b else 0.0,
                       float(both > 0), float(bool(a) and a == b)))
    return values


def verify_sources() -> dict:
    parent_manifest = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(PARENT) != parent_manifest["sha256"][str(PARENT.relative_to(ROOT))]:
        raise ValueError("Parent group prediction changed")
    rank_freeze = json.loads(RANKER_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(RANKER) != rank_freeze["model_sha256"]:
        raise ValueError("Frozen ranker changed")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in
            (PREPARED, SPLIT, PARENT, PARENT_MANIFEST, CANDIDATE_MANIFEST, RANKER, RANKER_FREEZE)}


def sample_training() -> tuple[np.ndarray, np.ndarray, dict]:
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = {org for org, name in split.items() if name == "train"}
    if len(train) != 334:
        raise ValueError("Historical training split changed")
    by_org: dict[str, dict] = defaultdict(dict)
    for alert, item in data["alerts"].items():
        if item["org"] in train:
            by_org[item["org"]][alert] = item["fields"]
    selected = {org: sorted(docs)[:500] for org, docs in by_org.items()}
    training_keys = {a for keys in selected.values() for a in keys}
    truth = read_truth(train, training_keys)
    rng = np.random.default_rng(29)
    x, y = [], []
    positive_count = hard_negative_count = 0
    for org in sorted(train):
        docs = by_org[org]
        keys = selected[org]
        groups: dict[str, list[str]] = defaultdict(list)
        buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
        for alert in keys:
            groups[truth[alert]].append(alert)
            for field in ("DetectorId", "Category", "MitreTechniques"):
                for value in docs[alert][field]:
                    buckets[(field, value)].append(alert)
        positives: set[tuple[str, str]] = set()
        for members in groups.values():
            if len(members) < 2:
                continue
            for _ in range(min(2 * len(members), 24)):
                i, j = rng.choice(len(members), 2, replace=False)
                positives.add(tuple(sorted((members[int(i)], members[int(j)]))))
        positives = set(sorted(positives)[:200])
        negatives: set[tuple[str, str]] = set()
        for alert in keys:
            if len(negatives) >= len(positives):
                break
            for field in ("DetectorId", "Category", "MitreTechniques"):
                if len(negatives) >= len(positives):
                    break
                for value in docs[alert][field]:
                    pool = buckets[(field, value)]
                    if len(pool) < 2:
                        continue
                    other = pool[int(rng.integers(len(pool)))]
                    if other != alert and truth[other] != truth[alert]:
                        negatives.add(tuple(sorted((alert, other))))
                        break
        hard_negative_count += len(negatives)
        attempts = 0
        while len(keys) >= 2 and len(negatives) < len(positives) and attempts < 20 * len(positives):
            attempts += 1
            i, j = rng.choice(len(keys), 2, replace=False)
            a, b = keys[int(i)], keys[int(j)]
            if truth[a] != truth[b]:
                negatives.add(tuple(sorted((a, b))))
        for a, b in sorted(positives):
            x.append(pair_features(docs[a], docs[b])); y.append(1)
        for a, b in sorted(negatives):
            x.append(pair_features(docs[a], docs[b])); y.append(0)
        positive_count += len(positives)
    if positive_count < 100 or len(set(y)) != 2:
        raise ValueError("Insufficient training pairs")
    return np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.int8), {
        "train_organizations": len(train), "positive_sample_pairs": positive_count,
        "negative_sample_pairs": len(y) - positive_count,
        "hard_negative_sample_pairs": hard_negative_count,
    }


def fit(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    sources = verify_sources()
    x, y, census = sample_training()
    model = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15,
                                           max_depth=4, learning_rate=0.08,
                                           l2_regularization=1.0, random_state=29)
    model.fit(x, y)
    private.mkdir(parents=True)
    path = private / "pair_model.pkl"
    with path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "fit_freeze.json", {
        "classification": "exploratory_training_only_pair_model",
        "run": run_id, "training": census, "training_labels_read": True,
        "evaluation_labels_read": False, "model_sha256": sha256_file(path),
        "source_hashes": sources, "source_code_sha256": sha256_file(Path(__file__)),
        "model": "hist_gradient_boosting_120_leaf15_depth4_lr0.08_seed29",
        "sampling": "at_most_500_alerts_per_training_org; up_to_200_positive_pairs_and_equal_hard_or_random_negatives",
        "threshold": LINK_THRESHOLD,
    })
    print(json.dumps({"status": "model_frozen", "run": run_id, **census}))


def grouped(keys: list[str], edges: np.ndarray, probability: np.ndarray) -> list[list[str]]:
    n = len(keys)
    dsu = DSU(n)
    strong = np.flatnonzero(probability >= LINK_THRESHOLD)
    order = strong[np.lexsort((edges[strong], -probability[strong]))]
    for t in order:
        a, b = divmod(int(edges[t]), n)
        dsu.union(a, b)
    groups: dict[int, list[str]] = defaultdict(list)
    for i, alert in enumerate(keys):
        groups[dsu.root(i)].append(alert)
    return sorted((sorted(v) for v in groups.values()), key=lambda v: v[0])


def predict(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "prediction_freeze.json").exists():
        raise FileExistsError("Predictions already frozen")
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    if fit_freeze["source_hashes"] != verify_sources() or fit_freeze["source_code_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Fit source lineage changed")
    pair_path = private / "pair_model.pkl"
    if sha256_file(pair_path) != fit_freeze["model_sha256"]:
        raise ValueError("Pair model changed")
    with pair_path.open("rb") as stream:
        pair_model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if len(parent) != 57:
        raise ValueError("Small-queue cohort changed")
    docs_by_org, census = load_alerts(set(parent))
    frozen = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))["hashes"]
    predictions = {}
    for org, item in sorted(parent.items()):
        path = ROOT / "data/derived/guide_rerun_v2/correlation_predictions" / f"{key(org)}.npz"
        if sha256_file(path) != frozen[key(org)]:
            raise ValueError("Candidate prediction changed")
        with np.load(path) as data:
            keys, edges = data["keys"].tolist(), data["edges"]
        if set(keys) != set(item["input_alert_keys"]) or set(keys) != set(docs_by_org[org]):
            raise ValueError("Alert scope differs from frozen parent")
        docs = docs_by_org[org]
        x = np.asarray([pair_features(docs[keys[int(i)]], docs[keys[int(j)]])
                        for i, j in zip(edges // len(keys), edges % len(keys))], dtype=np.float32)
        probability = pair_model.predict_proba(x)[:, 1] if len(x) else np.array([])
        groups = grouped(keys, edges, probability)
        counts, bm25 = score_groups(groups, docs)
        scores = ranker.decision_function(rank_features({"count_scores": counts,
                                                           "bm25_scores": bm25})).tolist()
        predictions[org] = {"input_alert_keys": keys, "candidate_pair_count": len(edges),
                            "groups": groups, "scores": scores,
                            "strong_edges": int((probability >= LINK_THRESHOLD).sum())}
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_pair_model_grouping_on_frozen_57_candidates",
        "run": run_id, "organizations": len(predictions),
        "alerts": sum(len(item["input_alert_keys"]) for item in predictions.values()),
        "candidate_pairs": sum(item["candidate_pair_count"] for item in predictions.values()),
        "strong_edges": sum(item["strong_edges"] for item in predictions.values()),
        "raw_scan_rows": census["raw_rows_scanned"],
        "prediction_sha256": sha256_file(prediction_path),
        "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
        "evaluation_labels_read_in_prediction_stage": False,
        "unchanged_candidate_pairs": True,
        "threshold": LINK_THRESHOLD,
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id,
                      "organizations": len(predictions)}))


def bootstrap(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(29)
    draws = arr[rng.integers(0, len(arr), size=(10000, len(arr)))].mean(axis=1)
    return {"mean": float(arr.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
            "organizations": len(arr), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    prediction_path = private / "predictions.pkl"
    if sha256_file(prediction_path) != freeze["prediction_sha256"]:
        raise ValueError("Frozen prediction changed")
    if sha256_file(public / "fit_freeze.json") != freeze["fit_freeze_sha256"]:
        raise ValueError("Fitted method changed")
    with prediction_path.open("rb") as stream:
        predicted = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(predicted)
    if len(orgs) != 57 or orgs != set(parent):
        raise ValueError("Evaluation cohort changed")
    alerts = {a for item in predicted.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alerts)
    ranks = labels(orgs)
    rows = defaultdict(list)
    confusion = defaultdict(Counter)
    ceiling = Counter()
    for org in sorted(orgs):
        item = predicted[org]
        original = parent[org]["methods"]["B1_rule_bm25"]
        for method, groups, scores in (("new_pair_grouping", item["groups"], item["scores"]),
                                       ("frozen_rule_bm25", original["groups"], original["scores"])):
            raw = score_org(groups, scores, truth, ranks[org], item["input_alert_keys"],
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[method].append({"recall20": tied["recall_at_20"],
                                 "p10": tied["precision_at_10"],
                                 "ndcg20": tied["ndcg_at_20_rank1_highest"]})
            confusion[method].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"],
                                      "fn": raw["pair_fn"]})
            counts = Counter(truth[a] for a in item["input_alert_keys"])
            found = set()
            for group in groups:
                overlap = Counter(truth[a] for a in group)
                gold, n = max(overlap.items(), key=lambda v: (v[1], v[0]))
                if gold in ranks[org] and n / counts[gold] >= 0.8 and n / len(group) >= 0.8:
                    found.add(gold)
            ceiling[method] += len(found)
    methods = {}
    for name, series in rows.items():
        tp, fp, fn = (confusion[name][k] for k in ("tp", "fp", "fn"))
        methods[name] = {
            "end_to_end_recall_at_20_macro": bootstrap([r["recall20"] for r in series]),
            "precision_at_10_macro": bootstrap([r["p10"] for r in series]),
            "ndcg_at_20_macro": bootstrap([r["ndcg20"] for r in series]),
            "pair_confusion_micro": {"tp": tp, "fp": fp, "fn": fn,
                                     "precision": tp / (tp + fp) if tp + fp else 0.0,
                                     "recall": tp / (tp + fn) if tp + fn else 0.0,
                                     "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0},
            "oracle_order_recoverable_labels": ceiling[name],
            "oracle_order_recall20_ceiling": ceiling[name] / (20 * len(orgs)),
        }
    metrics = {"classification": "exploratory_previously_exposed_57_queue_pair_model_grouping_not_confirmatory",
               "run": run_id, "organizations": len(orgs), "alerts": len(alerts),
               "expert_top20_denominator": 20 * len(orgs),
               "candidate_pairs": sum(v["candidate_pair_count"] for v in predicted.values()),
               "methods": methods,
               "limits": ["Previously exposed 57 complete small queues",
                          "Fitted pair model uses 334 historical training organizations only",
                          "Frozen candidates are unchanged and cover 80.52% of possible pairs",
                          "Five descriptor fields are local-only assumptions, not officially approved model inputs",
                          "Transferred ranker is fitted on different frozen groups",
                          "No Qwen inference or live SOC evaluation"],
               "prediction_freeze_sha256": sha256_file(freeze_path)}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_fit": f"python -m src.submission_pair_model_grouping fit --run-id {run_id}",
        "command_predict": f"python -m src.submission_pair_model_grouping predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_pair_model_grouping evaluate --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in
                   (Path(__file__), private / "pair_model.pkl", prediction_path,
                    public / "fit_freeze.json", freeze_path, public / "metrics.json")},
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "new_recall20": methods["new_pair_grouping"]["end_to_end_recall_at_20_macro"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_pair_model_grouping_20261114_v1")
    args = parser.parse_args()
    {"fit": fit, "predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
