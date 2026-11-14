"""Exploratory entity/time pair model with train/development/full-run separation."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
from sklearn.ensemble import HistGradientBoostingClassifier

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, DSU, score_groups, tie_aware_ranking, write_json
from .submission_full_entity_time import (PARENT, RANKER, SHARD_MANIFEST,
                                          ENTITY_FIELDS, read_docs, generate,
                                          sources as parent_sources)
from .submission_pair_model_grouping import pair_features
from .submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_entity_time_pair_v2_"
SPLIT = ROOT / "data/derived/guide_rerun_v2/split.json"
PRIOR = ROOT / "data/derived/submission_full_entity_time_20261114_v1"
PRIOR_FREEZE = ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json"
THRESHOLDS = (0.5, 0.75, 0.9, 0.95, 0.98, 0.995)
TRAIN_POS_CAP = 200
TRAIN_NEG_CAP = 400


def source_hashes() -> dict:
    paths = (Path(__file__), ROOT / "src/submission_full_entity_time.py",
             ROOT / "src/submission_pair_model_grouping.py", SPLIT, PRIOR_FREEZE)
    base = parent_sources()
    return {**base, **{str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}


def shard_map() -> tuple[dict[str, Path], dict]:
    manifest = json.loads(SHARD_MANIFEST.read_text(encoding="utf-8"))
    paths = {p.parent.name.split("=", 1)[1]: p for p in
             (ROOT / "data/derived/submission_entity_time_shards_20261114_v1/parts").rglob("*.parquet")}
    if len(paths) != 499:
        raise ValueError("Ranked projection changed")
    return paths, manifest


def edge_features(a: dict, b: dict, token_frequency: Counter, flag: int) -> list[float]:
    shared = a["entities"] & b["entities"]
    by_field = Counter(field for field, _ in shared)
    seconds = abs(a["stamp"] - b["stamp"])
    rarest = min((token_frequency[token] for token in shared), default=0)
    return (pair_features(a["fields"], b["fields"])
            + [float(bool(by_field[field])) for field in ENTITY_FIELDS]
            + [float(min(len(shared), 10)),
               1.0 / np.log1p(rarest) if rarest > 1 else 0.0,
               float(np.log1p(seconds / 3600)),
               float(seconds <= 3600), float(seconds <= 48 * 3600),
               float(bool(flag & 1)), float(bool(flag & 2)),
               float(bool(flag & 4)), float(bool(flag & 8))])


def token_frequencies(docs: dict[str, dict]) -> Counter:
    return Counter(token for doc in docs.values() for token in doc["entities"])


def groups_at(keys: list[str], edges: np.ndarray, probability: np.ndarray,
              threshold: float) -> list[list[str]]:
    n = len(keys)
    dsu = DSU(n)
    selected = np.flatnonzero(probability >= threshold)
    order = selected[np.lexsort((edges[selected], -probability[selected]))]
    for t in order:
        a, b = divmod(int(edges[t]), n)
        dsu.union(a, b)
    groups: dict[int, list[str]] = defaultdict(list)
    for i, alert in enumerate(keys):
        groups[dsu.root(i)].append(alert)
    return sorted((sorted(group) for group in groups.values()), key=lambda g: g[0])


def predict_probability(keys: list[str], docs: dict[str, dict], edges: np.ndarray,
                        flags: np.ndarray, model) -> np.ndarray:
    n = len(keys)
    frequency = token_frequencies(docs)
    result = np.empty(len(edges), dtype=np.float32)
    for start in range(0, len(edges), 10000):
        part = edges[start:start + 10000]
        x = np.asarray([edge_features(docs[keys[int(e // n)]],
                                      docs[keys[int(e % n)]], frequency,
                                      int(flags[start + i]))
                        for i, e in enumerate(part)], dtype=np.float32)
        result[start:start + len(part)] = model.predict_proba(x)[:, 1] if len(x) else []
    return result


def fit(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    sources = source_hashes()
    paths, shard_manifest = shard_map()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = sorted(o for o in parent if split.get(o) == "train")
    if len(train) != 334:
        raise ValueError("Training organization split changed")
    truth = read_truth(set(train), {a for o in train for a in parent[o]["input_alert_keys"]})
    sentinels, _ = detect_modal_sentinels()
    rng = np.random.default_rng(37)
    matrices, targets = [], []
    census = Counter()
    started = time.perf_counter()
    for index, org in enumerate(train, 1):
        path = paths[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection hash changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        n = len(keys)
        positive = np.fromiter((i for i, e in enumerate(edges)
                                if truth[keys[int(e // n)]] == truth[keys[int(e % n)]]),
                               dtype=np.int64)
        negative = np.fromiter((i for i, e in enumerate(edges)
                                if truth[keys[int(e // n)]] != truth[keys[int(e % n)]]),
                               dtype=np.int64)
        if len(positive) > TRAIN_POS_CAP:
            positive = rng.choice(positive, TRAIN_POS_CAP, replace=False)
        if len(negative) > TRAIN_NEG_CAP:
            negative = rng.choice(negative, TRAIN_NEG_CAP, replace=False)
        chosen = np.concatenate((positive, negative))
        frequency = token_frequencies(docs)
        x = np.asarray([edge_features(docs[keys[int(edges[i] // n)]],
                                      docs[keys[int(edges[i] % n)]], frequency,
                                      int(flags[i])) for i in chosen], dtype=np.float32)
        if len(x):
            matrices.append(x)
            targets.extend([1] * len(positive) + [0] * len(negative))
        census.update({"organizations": 1, "alerts": n, "candidates_seen": len(edges),
                       "positive_train_pairs": len(positive),
                       "negative_train_pairs": len(negative)})
        if index % 50 == 0:
            print(f"Fitted sample from {index}/334 training organizations", flush=True)
    model = HistGradientBoostingClassifier(max_iter=180, max_leaf_nodes=31,
                                           max_depth=6, learning_rate=0.05,
                                           l2_regularization=1.0, random_state=37)
    model.fit(np.vstack(matrices), np.asarray(targets, dtype=np.int8))
    private.mkdir(parents=True)
    model_path = private / "pair_model.pkl"
    with model_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "fit_freeze.json", {
        "classification": "exploratory_train_only_entity_time_pair_model",
        "run": run_id, "training_census": dict(census),
        "model_sha256": sha256_file(model_path),
        "source_sha256": sources, "training_labels_read": True,
        "validation_or_holdout_labels_read": False,
        "model": "hist_gradient_boosting_180_leaf31_depth6_lr0.05_seed37",
        "features": "15_descriptor_overlap_plus_entity_type_overlap_rarity_time_gap_and_candidate_route",
        "sampling": "up_to_200_positive_and_400_negative_candidate_pairs_per_training_organization",
        "wall_seconds": time.perf_counter() - started,
    })
    print(json.dumps({"status": "model_frozen", "run": run_id, **dict(census)}))


def calibrate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "calibration.json").exists():
        raise FileExistsError("Calibration already frozen")
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    if fit_freeze["source_sha256"] != source_hashes():
        raise ValueError("Fit lineage changed")
    model_path = private / "pair_model.pkl"
    if sha256_file(model_path) != fit_freeze["model_sha256"]:
        raise ValueError("Model changed")
    with model_path.open("rb") as stream:
        model = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    paths, shard_manifest = shard_map()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    development = sorted(o for o, item in parent.items()
                         if split.get(o) == "validation" and len(item["input_alert_keys"]) <= 500)
    if len(development) != 42:
        raise ValueError("Small development cohort changed")
    truth = read_truth(set(development), {a for o in development for a in parent[o]["input_alert_keys"]})
    ranks = labels(set(development))
    sentinels, _ = detect_modal_sentinels()
    scores = {str(t): [] for t in THRESHOLDS}
    for index, org in enumerate(development, 1):
        path = paths[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        field_docs = {a: docs[a]["fields"] for a in keys}
        for threshold in THRESHOLDS:
            groups = groups_at(keys, edges, probability, threshold)
            count, bm25 = score_groups(groups, field_docs)
            ranked = ranker.decision_function(rank_features({"count_scores": count,
                                                               "bm25_scores": bm25})).tolist()
            metric = tie_aware_ranking(groups, ranked, truth, ranks[org])
            raw = score_org(groups, ranked, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            scores[str(threshold)].append({"recall20": metric["recall_at_20"],
                                           "p10": metric["precision_at_10"],
                                           "tp": raw["pair_tp"], "fp": raw["pair_fp"],
                                           "fn": raw["pair_fn"]})
        if index % 10 == 0:
            print(f"Calibrated {index}/42 development organizations", flush=True)
    table = {}
    for threshold in THRESHOLDS:
        rows = scores[str(threshold)]
        tp, fp, fn = (sum(row[field] for row in rows) for field in ("tp", "fp", "fn"))
        table[str(threshold)] = {
            "recall20_macro": sum(row["recall20"] for row in rows) / len(rows),
            "p10_macro": sum(row["p10"] for row in rows) / len(rows),
            "pair_f1_micro": 2 * tp / (2 * tp + fp + fn),
            "pair_precision_micro": tp / (tp + fp) if tp + fp else 0,
        }
    selected = max(THRESHOLDS, key=lambda t: (table[str(t)]["recall20_macro"],
                                             table[str(t)]["pair_f1_micro"], t))
    write_json(public / "calibration.json", {
        "classification": "exploratory_development_only_entity_time_threshold_selection",
        "run": run_id, "validation_organizations": len(development),
        "validation_labels_read": True, "holdout_labels_read": False,
        "selected_threshold": selected, "threshold_table": table,
        "selection_rule": "maximize_macro_recall20_then_pair_f1_then_higher_threshold",
        "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
        "source_code_sha256": sha256_file(Path(__file__)),
    })
    print(json.dumps({"status": "threshold_frozen", "threshold": selected, "table": table}))


def predict(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "prediction_freeze.json").exists():
        raise FileExistsError("Predictions already frozen")
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    calibration_path = public / "calibration.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if (fit_freeze["source_sha256"] != source_hashes() or
        calibration["fit_freeze_sha256"] != sha256_file(public / "fit_freeze.json") or
        calibration["source_code_sha256"] != sha256_file(Path(__file__))):
        raise ValueError("Frozen method changed")
    model_path = private / "pair_model.pkl"
    if sha256_file(model_path) != fit_freeze["model_sha256"]:
        raise ValueError("Model changed")
    with model_path.open("rb") as stream:
        model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    threshold = float(calibration["selected_threshold"])
    hashes, times = {}, []
    census = Counter()
    peak = 0
    process = psutil.Process()
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        tic = time.perf_counter()
        path = paths[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        groups = groups_at(keys, edges, probability, threshold)
        count, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in keys})
        ranked = ranker.decision_function(rank_features({"count_scores": count,
                                                           "bm25_scores": bm25})).tolist()
        result_path = private / f"v2_{key(org)}.pkl"
        with result_path.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "groups": groups,
                         "scores": ranked, "candidate_pairs": len(edges),
                         "linked_edges": int((probability >= threshold).sum())},
                        stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[key(org)] = sha256_file(result_path)
        census.update({"organizations": 1, "alerts": len(keys),
                       "candidate_pairs": len(edges),
                       "linked_edges": int((probability >= threshold).sum()),
                       "predicted_groups": len(groups)})
        times.append(time.perf_counter() - tic)
        peak = max(peak, process.memory_info().rss)
        del docs, edges, flags, probability, groups
        if index % 25 == 0:
            print(f"Predicted {index}/499 organizations", flush=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_full_entity_time_pair_model_v2",
        "run": run_id, "organizations": 499, "threshold": threshold,
        "census": dict(census), "prediction_sha256": hashes,
        "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
        "calibration_sha256": sha256_file(calibration_path),
        "source_code_sha256": sha256_file(Path(__file__)),
        "evaluation_labels_read_in_prediction_stage": False,
        "candidate_route_identical_to_parent_entity_time_run": True,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "organization_seconds_p50": float(np.quantile(times, 0.5)),
                     "organization_seconds_p95": float(np.quantile(times, 0.95)),
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, **dict(census)}))


def bootstrap(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    rng = np.random.default_rng(37)
    draws = a[rng.integers(0, len(a), size=(10000, len(a)))].mean(axis=1)
    return {"mean": float(a.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
            "organizations": len(a), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (freeze["source_code_sha256"] != sha256_file(Path(__file__)) or
        freeze["fit_freeze_sha256"] != sha256_file(public / "fit_freeze.json") or
        freeze["calibration_sha256"] != sha256_file(public / "calibration.json")):
        raise ValueError("Prediction lineage changed")
    prior_freeze = json.loads(PRIOR_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    truth = read_truth(orgs, {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(orgs)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    pair = defaultdict(Counter)
    ceiling = Counter()
    for org in sorted(orgs):
        v2_path = private / f"v2_{key(org)}.pkl"
        prior_path = PRIOR / f"{key(org)}.pkl"
        if sha256_file(v2_path) != freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen v2 prediction changed")
        if sha256_file(prior_path) != prior_freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen earlier prediction changed")
        with v2_path.open("rb") as stream:
            new = pickle.load(stream)
        with prior_path.open("rb") as stream:
            old = pickle.load(stream)
        keys = new["input_alert_keys"]
        if keys != old["input_alert_keys"] or new["candidate_pairs"] != len(old["candidate_edges"]):
            raise ValueError("Matched candidate population changed")
        gold_counts = Counter(truth[a] for a in keys)
        for name, item in (("v2_entity_time_pair", new), ("v1_entity_time_rule", old)):
            groups, scores = item["groups"], item["scores"]
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name][org] = {"recall20": tied["recall_at_20"],
                               "p10": tied["precision_at_10"],
                               "ndcg20": tied["ndcg_at_20_rank1_highest"]}
            pair[name].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"],
                               "fn": raw["pair_fn"]})
            recoverable = set()
            for group in groups:
                membership = Counter(truth[a] for a in group)
                gold, overlap = max(membership.items(), key=lambda z: (z[1], z[0]))
                if gold in ranks[org] and overlap / gold_counts[gold] >= .8 and overlap / len(group) >= .8:
                    recoverable.add(gold)
            ceiling[name] += len(recoverable)
    cohorts = {"all_499_descriptive": sorted(orgs),
               "training_disjoint_135": sorted(o for o in orgs if split.get(o) in ("validation", "holdout")),
               "holdout_68_previously_exposed": sorted(o for o in orgs if split.get(o) == "holdout")}
    result = {}
    for cohort, chosen in cohorts.items():
        methods = {name: {field: bootstrap([rows[name][o][field] for o in chosen])
                          for field in ("recall20", "p10", "ndcg20")} for name in rows}
        difference = {field: bootstrap([rows["v2_entity_time_pair"][o][field]
                                        - rows["v1_entity_time_rule"][o][field] for o in chosen])
                      for field in ("recall20", "p10", "ndcg20")}
        result[cohort] = {"organizations": len(chosen),
                          "expert_top20_denominator": 20 * len(chosen),
                          "methods": methods, "paired_v2_minus_v1": difference}
    confusion = {}
    for name, c in pair.items():
        tp, fp, fn = (c[k] for k in ("tp", "fp", "fn"))
        confusion[name] = {"tp": tp, "fp": fp, "fn": fn,
                           "precision": tp / (tp + fp) if tp + fp else 0,
                           "recall": tp / (tp + fn) if tp + fn else 0,
                           "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                           "oracle_order_recoverable_top20": ceiling[name],
                           "oracle_order_recall20_ceiling": ceiling[name] / (20 * len(orgs))}
    metrics = {"classification": "exploratory_full_guide_post_exposure_entity_time_pair_v2_not_confirmatory",
               "run": run_id, "organizations": len(orgs),
               "cohorts": result, "pair_and_group": confusion,
               "candidate": "identical_to_submission_full_entity_time_20261114_v1",
               "prediction_resource": freeze["resource"],
               "limits": ["All GUIDE_Test top-20 labels were previously accessed in this project",
                          "Development threshold selected on 42 previously accessed validation organizations",
                          "Entity availability at alert creation and operational field approval unresolved",
                          "No independent new cohort or live SOC evaluation"],
               "prediction_freeze_sha256": sha256_file(freeze_path)}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_fit": f"python -m src.submission_entity_time_pair_v2 fit --run-id {run_id}",
        "command_calibrate": f"python -m src.submission_entity_time_pair_v2 calibrate --run-id {run_id}",
        "command_predict": f"python -m src.submission_entity_time_pair_v2 predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_entity_time_pair_v2 evaluate --run-id {run_id}",
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), private / "pair_model.pkl", public / "fit_freeze.json",
                    public / "calibration.json", freeze_path, public / "metrics.json")},
        "private_prediction_sha256": freeze["prediction_sha256"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "v2_recall20_all": result["all_499_descriptive"]["methods"]["v2_entity_time_pair"]["recall20"]["mean"]}))


def self_test() -> None:
    empty = {"fields": {f: set() for f in ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")},
             "entities": set(), "stamp": 0.0}
    rich = {"fields": empty["fields"], "entities": {("DeviceId", "x")}, "stamp": 10.0}
    values = edge_features(rich, rich, Counter({("DeviceId", "x"): 2}), 4)
    assert len(values) == 30 and values[15] == 1 and values[-2] == 1
    groups = groups_at(["a", "b", "c"], np.asarray([1, 2], dtype=np.int64),
                       np.asarray([.9, .1]), .5)
    assert groups == [["a", "b"], ["c"]]
    print("entity/time pair v2 self-test: 3 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "fit", "calibrate", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_entity_time_pair_v2_20261114_v1")
    args = parser.parse_args()
    if args.stage == "self-test":
        self_test()
    else:
        {"fit": fit, "calibrate": calibrate, "predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
