"""Train-only group-pair merge model with development-only selection."""

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
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_full_entity_time import PARENT, RANKER, read_docs, generate
from .submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability
from .submission_group_ranker_v4 import bootstrap
from .submission_descriptor_ranker_v7 import GROUP_FREEZE, GROUP_RUN, V4_FREEZE
from .submission_specialist_ranker_v8 import V7_FREEZE, V7_RUN, v7_scores
from .submission_group_ranker_v4 import group_features
from .submission_trained_ranker import features as rank_features
from .submission_full_guide import score_groups
from .submission_descriptor_ranker_v7 import featurize
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_group_merge_v10_"
PAIR_MODEL = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl"
V4_MODEL = ROOT / "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl"
V7_MODEL = ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1/descriptor_rank_model.pkl"
FLOOR = .4
CONFIGS = ((.5, 4), (.6, 4), (.7, 4), (.5, 8), (.6, 8), (.7, 8))


def source_hashes() -> dict:
    paths = (Path(__file__), PAIR_MODEL, V4_MODEL, V7_MODEL, GROUP_FREEZE,
             V4_FREEZE, V7_FREEZE, SPLIT,
             ROOT / "outputs/submission_entity_time_shards_20261114_v1.json")
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def load_models():
    with PAIR_MODEL.open("rb") as stream:
        pair = pickle.load(stream)
    with V4_MODEL.open("rb") as stream:
        v4 = pickle.load(stream)
    with V7_MODEL.open("rb") as stream:
        v7 = pickle.load(stream)
    with RANKER.open("rb") as stream:
        base_ranker = pickle.load(stream)
    return pair, v4, v7, base_ranker


def load_queue(org: str, parent: dict, group_freeze: dict, paths: dict,
               shard_manifest: dict, sentinels: dict, pair_model):
    path = paths[org]
    if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
        raise ValueError("Entity projection changed")
    group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{key(org)}.pkl"
    if sha256_file(group_path) != group_freeze["prediction_sha256"][key(org)]:
        raise ValueError("V2 groups changed")
    with group_path.open("rb") as stream:
        item = pickle.load(stream)
    keys = parent[org]["input_alert_keys"]
    if keys != item["input_alert_keys"]:
        raise ValueError("Alert order changed")
    docs = read_docs(org, path, sentinels, set(keys))
    edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
    probability = predict_probability(keys, docs, edges, flags, pair_model)
    return item, docs, edges, probability


def proposals(keys: list[str], groups: list[list[str]], docs: dict,
              edges: np.ndarray, probability: np.ndarray):
    n = len(keys)
    group_of = {}
    summaries = []
    for i, group in enumerate(groups):
        for alert in group:
            group_of[alert] = i
        fields = {field: set().union(*(docs[a]["fields"][field] for a in group))
                  for field in ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")}
        summaries.append({"fields": fields,
                          "entities": set().union(*(docs[a]["entities"] for a in group)),
                          "min_time": min(docs[a]["stamp"] for a in group),
                          "max_time": max(docs[a]["stamp"] for a in group)})
    group_index = np.asarray([group_of[a] for a in keys], dtype=np.int32)
    aggregation = {}
    for t in np.flatnonzero(probability >= FLOOR):
        a, b = divmod(int(edges[t]), n)
        ga, gb = int(group_index[a]), int(group_index[b])
        if ga == gb:
            continue
        if ga > gb:
            ga, gb, a, b = gb, ga, b, a
        record = aggregation.setdefault((ga, gb), [0.0, 0.0, 0, set(), set(), 0])
        score = float(probability[t])
        record[0] = max(record[0], score)
        record[1] += score
        record[2] += 1
        record[3].add(a)
        record[4].add(b)
        record[5] += int(score >= .6)
    pairs = sorted(aggregation)
    frequency = Counter(entity for summary in summaries for entity in summary["entities"])
    rows = []
    for ga, gb in pairs:
        value = aggregation[ga, gb]
        left, right = summaries[ga], summaries[gb]
        shared = left["entities"] & right["entities"]
        rarest = min((frequency[entity] for entity in shared), default=0)
        field_shared = [len(left["fields"][field] & right["fields"][field])
                        for field in ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")]
        a, b = len(groups[ga]), len(groups[gb])
        gap = max(0.0, left["min_time"] - right["max_time"],
                  right["min_time"] - left["max_time"])
        rows.append([value[0], value[1]/value[2], np.log1p(value[2]),
                     np.log1p(len(value[3])), np.log1p(len(value[4])),
                     np.log1p(value[5]), np.log1p(min(a, b)), np.log1p(max(a, b)),
                     np.log1p(len(shared)), 1/np.log1p(rarest) if rarest > 1 else 0.0,
                     np.log1p(gap/3600),
                     *[np.log1p(count) for count in field_shared]])
    return pairs, np.asarray(rows, dtype=np.float32).reshape(-1, 16)


def merge(groups: list[list[str]], pairs: list[tuple[int, int]], x: np.ndarray,
          model, threshold: float, cap: int) -> list[list[str]]:
    if not pairs:
        return groups
    probability = model.predict_proba(x)[:, 1]
    parent = list(range(len(groups)))
    sizes = [len(group) for group in groups]

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    selected = np.flatnonzero(probability >= threshold)
    order = selected[np.argsort(-probability[selected], kind="stable")]
    for t in order:
        a, b = pairs[t]
        ra, rb = root(a), root(b)
        if ra == rb or sizes[ra] + sizes[rb] > cap:
            continue
        if sizes[ra] < sizes[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        sizes[ra] += sizes[rb]
    result = defaultdict(list)
    for i, group in enumerate(groups):
        result[root(i)].extend(group)
    return sorted((sorted(group) for group in result.values()), key=lambda group: group[0])


def score_groups_v7(groups: list[list[str]], docs: dict, base_ranker, v4, v7,
                    hasher: FeatureHasher) -> list[float]:
    count, bm25 = score_groups(groups, {alert: doc["fields"] for alert, doc in docs.items()})
    original = base_ranker.decision_function(rank_features({"count_scores": count,
                                                             "bm25_scores": bm25})).tolist()
    tree = v4.predict_proba(group_features(groups, docs, original))[:, 1]
    linear = v7.predict_proba(featurize(groups, docs, original, hasher))[:, 1]
    return (.25*tree + .75*linear).tolist()


def pair_group_metrics(groups: list[list[str]], scores: list[float], keys: list[str],
                       truth: dict, ranks: dict) -> dict:
    ranking = tie_aware_ranking(groups, scores, truth, ranks)
    raw = score_org(groups, scores, truth, ranks, keys,
                    {"top20_recovery_min_completeness": .8,
                     "top20_recovery_min_purity": .8})
    gold_sizes = Counter(truth[alert] for alert in keys)
    recoverable = set()
    for group in groups:
        membership = Counter(truth[alert] for alert in group)
        gold, overlap = max(membership.items(), key=lambda item: (item[1], item[0]))
        if gold in ranks and overlap/gold_sizes[gold] >= .8 and overlap/len(group) >= .8:
            recoverable.add(gold)
    return {"recall20": ranking["recall_at_20"],
            "p10": ranking["precision_at_10"],
            "ndcg20": ranking["ndcg_at_20_rank1_highest"],
            "tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"],
            "recoverable": len(recoverable), "groups": len(groups)}


def fit(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v10 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = sorted(org for org in parent if split.get(org) == "train")
    if len(train) != 334:
        raise ValueError("Training cohort changed")
    truth = read_truth(set(train), {alert for org in train for alert in parent[org]["input_alert_keys"]})
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model, _, _, _ = load_models()
    rng = np.random.default_rng(101)
    features, targets = [], []
    census = Counter()
    started = time.perf_counter()
    for index, org in enumerate(train, 1):
        item, docs, edges, probability = load_queue(org, parent, group_freeze, paths,
                                                      shard_manifest, sentinels, pair_model)
        pairs, x = proposals(item["input_alert_keys"], item["groups"], docs, edges, probability)
        majority = []
        for group in item["groups"]:
            counts = Counter(truth[a] for a in group)
            incident, hits = max(counts.items(), key=lambda row: (row[1], row[0]))
            majority.append(incident if hits/len(group) >= .8 else None)
        y = np.asarray([int(majority[a] is not None and majority[a] == majority[b])
                        for a, b in pairs], dtype=np.uint8)
        positives = np.flatnonzero(y)
        negatives = np.flatnonzero(~y.astype(bool))
        if len(positives) > 200:
            positives = rng.choice(positives, 200, replace=False)
        if len(negatives) > 400:
            # Hard negatives: likely links by the frozen pair scorer, plus a random sample.
            high = negatives[np.argsort(-x[negatives, 0], kind="stable")[:200]]
            remaining = np.setdiff1d(negatives, high, assume_unique=True)
            random = rng.choice(remaining, min(200, len(remaining)), replace=False)
            negatives = np.concatenate((high, random))
        chosen = np.concatenate((positives, negatives))
        if len(chosen):
            features.append(x[chosen])
            targets.extend(y[chosen].tolist())
        census.update({"organizations": 1, "candidate_group_pairs": len(pairs),
                       "sample_positive": len(positives), "sample_negative": len(negatives)})
        if index % 50 == 0:
            print(f"Prepared group-pair training queues {index}/334", flush=True)
    x_train = np.vstack(features)
    y_train = np.asarray(targets, dtype=np.uint8)
    if len(y_train) < 1000 or y_train.sum() < 100:
        raise ValueError("Insufficient group-pair training sample")
    model = HistGradientBoostingClassifier(max_iter=160, max_leaf_nodes=15,
                                           max_depth=5, min_samples_leaf=30,
                                           learning_rate=.05, l2_regularization=2,
                                           random_state=101)
    model.fit(x_train, y_train)
    private.mkdir(parents=True)
    with (private / "merge_model.pkl").open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "fit_freeze.json", {"classification": "exploratory_train_only_group_merge_model",
                                              "run": run_id, "training_organizations": 334,
                                              "training_census": dict(census),
                                              "train_rows": len(y_train), "positive_train_rows": int(y_train.sum()),
                                              "proposal_probability_floor": FLOOR,
                                              "model_sha256": sha256_file(private / "merge_model.pkl"),
                                              "source_sha256": source_hashes(),
                                              "development_or_holdout_labels_read": False,
                                              "wall_seconds": time.perf_counter()-started})
    print(json.dumps({"status": "merge_model_frozen", "train_rows": len(y_train),
                      "positive_rows": int(y_train.sum()), "census": dict(census)}))


def calibrate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "calibration.json").exists():
        raise FileExistsError("Calibration already frozen")
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    if fit_freeze["source_sha256"] != source_hashes():
        raise ValueError("Method changed")
    model_path = private / "merge_model.pkl"
    if sha256_file(model_path) != fit_freeze["model_sha256"]:
        raise ValueError("Merge model changed")
    with model_path.open("rb") as stream:
        merge_model = pickle.load(stream)
    pair_model, v4, v7, base_ranker = load_models()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev = sorted(org for org in parent if split.get(org) == "validation"
                 and len(parent[org]["input_alert_keys"]) <= 500)
    if len(dev) != 42:
        raise ValueError("Development cohort changed")
    truth = read_truth(set(dev), {alert for org in dev for alert in parent[org]["input_alert_keys"]})
    ranks = labels(set(dev))
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    configs = ["base"] + [f"{threshold}:{cap}" for threshold, cap in CONFIGS]
    rows = {config: [] for config in configs}
    for index, org in enumerate(dev, 1):
        item, docs, edges, probability = load_queue(org, parent, group_freeze, paths,
                                                      shard_manifest, sentinels, pair_model)
        pairs, x = proposals(item["input_alert_keys"], item["groups"], docs, edges, probability)
        for config in configs:
            if config == "base":
                groups = item["groups"]
                scores = v7_scores(org, v7_freeze)
            else:
                threshold, cap = config.split(":")
                groups = merge(item["groups"], pairs, x, merge_model, float(threshold), int(cap))
                scores = (v7_scores(org, v7_freeze) if groups == item["groups"] else
                          score_groups_v7(groups, docs, base_ranker, v4, v7, hasher))
            rows[config].append(pair_group_metrics(groups, scores, item["input_alert_keys"], truth, ranks[org]))
        if index % 10 == 0:
            print(f"Calibrated group merges {index}/42", flush=True)
    table = {}
    for config, series in rows.items():
        tp, fp, fn = (sum(row[field] for row in series) for field in ("tp", "fp", "fn"))
        table[config] = {"recall20": float(np.mean([row["recall20"] for row in series])),
                         "p10": float(np.mean([row["p10"] for row in series])),
                         "ndcg20": float(np.mean([row["ndcg20"] for row in series])),
                         "pair_precision": tp/(tp+fp) if tp+fp else 0,
                         "pair_recall": tp/(tp+fn),
                         "pair_f1": 2*tp/(2*tp+fp+fn),
                         "pair_false_positives": fp,
                         "recoverable_labels": sum(row["recoverable"] for row in series),
                         "predicted_groups": sum(row["groups"] for row in series)}
    base = table["base"]
    eligible = [config for config in configs if table[config]["pair_precision"] >= base["pair_precision"]
                and table[config]["pair_false_positives"] <= base["pair_false_positives"]
                and table[config]["p10"] >= base["p10"]
                and table[config]["recoverable_labels"] > base["recoverable_labels"]
                and table[config]["recall20"] > base["recall20"]]
    selected = (max(eligible, key=lambda config: (table[config]["recall20"],
                                                   table[config]["recoverable_labels"],
                                                   table[config]["pair_precision"]))
                if eligible else "base")
    write_json(public / "calibration.json", {"classification": "exploratory_development_group_merge_selection",
                                                "run": run_id, "development_organizations": 42,
                                                "selected_config": selected, "table": table,
                                                "selection_rule": "strict_recall_and_recoverability_gain_with_no_worse_pair_precision_false_merges_or_p10",
                                                "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
                                                "source_sha256": source_hashes(),
                                                "holdout_labels_read": False})
    print(json.dumps({"status": "merge_rule_frozen", "selected": selected, "table": table}))


def predict(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "prediction_freeze.json").exists():
        raise FileExistsError("Predictions already frozen")
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    calibration = json.loads((public / "calibration.json").read_text(encoding="utf-8"))
    if fit_freeze["source_sha256"] != source_hashes() or calibration["source_sha256"] != source_hashes():
        raise ValueError("Method source changed")
    if calibration["fit_freeze_sha256"] != sha256_file(public / "fit_freeze.json"):
        raise ValueError("Calibration parent changed")
    model_path = private / "merge_model.pkl"
    if sha256_file(model_path) != fit_freeze["model_sha256"]:
        raise ValueError("Merge model changed")
    with model_path.open("rb") as stream:
        merge_model = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    pair_model, v4, v7, base_ranker = load_models()
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    selected = calibration["selected_config"]
    hashes = {}
    census = Counter()
    started = time.perf_counter()
    process = psutil.Process()
    peak = 0
    for index, org in enumerate(sorted(parent), 1):
        item, docs, edges, probability = load_queue(org, parent, group_freeze, paths,
                                                      shard_manifest, sentinels, pair_model)
        pairs, x = proposals(item["input_alert_keys"], item["groups"], docs, edges, probability)
        if selected == "base":
            groups, scores = item["groups"], v7_scores(org, v7_freeze)
        else:
            threshold, cap = selected.split(":")
            groups = merge(item["groups"], pairs, x, merge_model, float(threshold), int(cap))
            scores = (v7_scores(org, v7_freeze) if groups == item["groups"] else
                      score_groups_v7(groups, docs, base_ranker, v4, v7, hasher))
        path = private / f"v10_{key(org)}.pkl"
        with path.open("wb") as stream:
            pickle.dump({"input_alert_keys": item["input_alert_keys"], "groups": groups,
                         "scores": scores, "candidate_pairs": item["candidate_pairs"]},
                        stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[key(org)] = sha256_file(path)
        census.update({"organizations": 1, "alerts": len(item["input_alert_keys"]),
                       "candidate_pairs": item["candidate_pairs"],
                       "candidate_group_pairs": len(pairs), "predicted_groups": len(groups)})
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Frozen group predictions {index}/499", flush=True)
    write_json(public / "prediction_freeze.json", {"classification": "exploratory_development_selected_group_merge",
                                                    "run": run_id, "selected_config": selected,
                                                    "census": dict(census),
                                                    "prediction_sha256": hashes,
                                                    "source_sha256": source_hashes(),
                                                    "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
                                                    "calibration_sha256": sha256_file(public / "calibration.json"),
                                                    "evaluation_labels_read": False,
                                                    "resource": {"wall_seconds": time.perf_counter()-started,
                                                                 "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "predictions_frozen", "selected": selected, "census": dict(census)}))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != source_hashes():
        raise ValueError("Method changed")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {alert for item in parent.values() for alert in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    totals = defaultdict(Counter)
    for org in orgs:
        name = key(org)
        path = private / f"v10_{name}.pkl"
        base_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][name] or sha256_file(base_path) != group_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen group prediction changed")
        with path.open("rb") as stream:
            newer = pickle.load(stream)
        with base_path.open("rb") as stream:
            older = pickle.load(stream)
        if newer["input_alert_keys"] != older["input_alert_keys"] or newer["candidate_pairs"] != older["candidate_pairs"]:
            raise ValueError("Candidate population changed")
        for method, item, scores in (("v10_selected", newer, newer["scores"]),
                                     ("v2_groups_v7_ranker", older, v7_scores(org, v7_freeze))):
            metric = pair_group_metrics(item["groups"], scores, item["input_alert_keys"], truth, ranks[org])
            rows[method][org] = {field: metric[field] for field in ("recall20", "p10", "ndcg20")}
            totals[method].update({field: metric[field] for field in ("tp", "fp", "fn", "recoverable")})
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [org for org in orgs if split.get(org) in ("validation", "holdout")],
               "holdout_68_previously_exposed": [org for org in orgs if split.get(org) == "holdout"]}
    comparisons = {}
    for cohort, selected in cohorts.items():
        comparisons[cohort] = {"organizations": len(selected), "expert_top20_denominator": 20*len(selected),
                               "methods": {method: {metric: bootstrap([rows[method][org][metric] for org in selected])
                                                    for metric in ("recall20", "p10", "ndcg20")}
                                           for method in rows},
                               "paired_v10_minus_v7": {metric: bootstrap([rows["v10_selected"][org][metric]-
                                                                           rows["v2_groups_v7_ranker"][org][metric]
                                                                           for org in selected])
                                                       for metric in ("recall20", "p10", "ndcg20")}}
    pair = {}
    for method, c in totals.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        pair[method] = {"tp": tp, "fp": fp, "fn": fn,
                        "precision": tp/(tp+fp) if tp+fp else 0,
                        "recall": tp/(tp+fn), "f1": 2*tp/(2*tp+fp+fn),
                        "recoverable_top20_oracle_order": c["recoverable"],
                        "oracle_order_recall20_ceiling": c["recoverable"]/(20*len(orgs))}
    write_json(public / "metrics.json", {"classification": "exploratory_post_exposure_group_merge_not_confirmatory",
                                         "run": run_id, "selected_config": freeze["selected_config"],
                                         "cohorts": comparisons, "pair_and_group": pair,
                                         "resource": freeze["resource"],
                                         "prediction_freeze_sha256": sha256_file(freeze_path),
                                         "limits": ["GUIDE_Test labels previously accessed", "No untouched cohort",
                                                    "Point-in-time entity availability unresolved"]})
    write_json(public / "run_manifest.json", {"sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                                                           for path in (Path(__file__), private/"merge_model.pkl",
                                                                        public/"fit_freeze.json", public/"calibration.json",
                                                                        freeze_path, public/"metrics.json")},
                                              "private_prediction_sha256": freeze["prediction_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete", "selected": freeze["selected_config"],
                      "all_499_recall20": comparisons["all_499_descriptive"]["methods"]["v10_selected"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "calibrate", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_group_merge_v10_20261114_v1")
    args = parser.parse_args()
    {"fit": fit, "calibrate": calibrate, "predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
