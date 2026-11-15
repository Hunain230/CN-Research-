"""Exploratory train-only LightGBM fragment matching on frozen v2 groups.

Fit reads incident membership for the 334 historical training organizations only.
Predict reads no expert labels. Evaluate opens labels after predictions are frozen.
No feature or decision uses IncidentId, expert rank, grade, or outcome.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import lightgbm as lgb
import numpy as np
import psutil
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import PARENT
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_group_merge_v10_v2 import (
    load_models, load_queue, proposals as prior_proposals, score_groups_v7,
    pair_group_metrics,
)
from .submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from .submission_group_ranker_v4 import bootstrap
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


CONFIG = ROOT / "configs/fragment_matching_ml_v1.json"
PREFIX = "submission_fragment_matching_ml_v1_"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
RANK_RUN = "submission_descriptor_ranker_v7_20261114_v1"
CANDIDATE_RUN = "submission_full_entity_time_20261114_v1"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
RANK_FREEZE = ROOT / "outputs" / RANK_RUN / "prediction_freeze.json"
CANDIDATE_FREEZE = ROOT / "outputs" / CANDIDATE_RUN / "prediction_freeze.json"
CANDIDATES = ROOT / "data/derived" / CANDIDATE_RUN
BASE_FEATURES = (
    "max_pair_score", "mean_pair_score", "log_cross_edges", "log_touched_left",
    "log_touched_right", "log_edges_score_ge_0_6", "log_small_group",
    "log_large_group", "log_shared_entities", "rarest_entity_inverse_log",
    "log_intergroup_hours", "log_shared_detector", "log_shared_category",
    "log_shared_technique", "log_shared_entity_type", "log_shared_evidence_role",
)
EXTRA_FEATURES = (
    "entity_group_frequency_min", "entity_group_frequency_max",
    "shared_technique_frequency_min", "shared_detector_any", "category_conflict",
    "technique_conflict", "evidence_role_shared", "left_category_consistency",
    "right_category_consistency", "left_technique_consistency",
    "right_technique_consistency", "category_jaccard", "technique_jaccard",
    "combined_group_size", "single_bridge_edge", "common_entity_only",
)
FEATURES = BASE_FEATURES + EXTRA_FEATURES


def settings() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (value["candidate_run"], value["group_run"], value["rank_run"]) != (
            CANDIDATE_RUN, GROUP_RUN, RANK_RUN):
        raise ValueError("Frozen reference run IDs changed")
    if (not value["no_guide_test_parameter_selection"] or
            value["operational_feature_approval"] or
            value["decision"]["maximum_combined_alerts"] != 100 or
            not value["decision"]["single_non_cascading_pass"]):
        raise ValueError("Phase 7 fixed research policy changed")
    return value


def lineage() -> dict[str, str]:
    paths = (
        Path(__file__), CONFIG, GROUP_FREEZE, RANK_FREEZE, CANDIDATE_FREEZE,
        SPLIT, ROOT / "src/submission_full_guide.py",
        ROOT / "src/submission_full_entity_time.py",
        ROOT / "src/submission_entity_time_pair_v2.py",
        ROOT / "src/submission_group_merge_v10_v2.py",
        ROOT / "src/submission_fragment_aware_v1.py",
        ROOT / "src/submission_descriptor_ranker_v7.py",
        ROOT / "data/derived" / GROUP_RUN / "pair_model.pkl",
        ROOT / "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl",
        ROOT / "data/derived" / RANK_RUN / "descriptor_rank_model.pkl",
        ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl",
    )
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def _consistency(group: list[str], docs: dict, field: str) -> float:
    count = Counter(token for alert in group for token in docs[alert]["fields"][field])
    return max(count.values(), default=0) / len(group)


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def fragment_features(keys: list[str], groups: list[list[str]], docs: dict,
                      edges: np.ndarray, probability: np.ndarray):
    """Return unchanged v10 proposals plus independently defined boundary signals."""
    pairs, base = prior_proposals(keys, groups, docs, edges, probability)
    if not pairs:
        return [], np.empty((0, len(FEATURES)), dtype=np.float32)
    field_names = ("DetectorId", "Category", "MitreTechniques", "EvidenceRole")
    summaries = []
    entity_frequency = Counter()
    technique_frequency = Counter()
    for group in groups:
        fields = {field: set().union(*(docs[a]["fields"][field] for a in group))
                  for field in field_names}
        entities = set().union(*(docs[a]["entities"] for a in group))
        entity_frequency.update(entities)
        technique_frequency.update(fields["MitreTechniques"])
        summaries.append({"fields": fields, "entities": entities,
                          "category_consistency": _consistency(group, docs, "Category"),
                          "technique_consistency": _consistency(group, docs, "MitreTechniques")})
    extra = np.empty((len(pairs), len(EXTRA_FEATURES)), dtype=np.float32)
    for i, (ga, gb) in enumerate(pairs):
        left, right = summaries[ga], summaries[gb]
        a, b = left["fields"], right["fields"]
        shared_entity = left["entities"] & right["entities"]
        entity_freq = [entity_frequency[token] for token in shared_entity]
        shared_technique = a["MitreTechniques"] & b["MitreTechniques"]
        technique_freq = [technique_frequency[token] for token in shared_technique]
        category_conflict = bool(a["Category"] and b["Category"] and
                                 not a["Category"] & b["Category"])
        technique_conflict = bool(a["MitreTechniques"] and b["MitreTechniques"] and
                                  not shared_technique)
        extra[i] = (
            min(entity_freq, default=0), max(entity_freq, default=0),
            min(technique_freq, default=0), bool(a["DetectorId"] & b["DetectorId"]),
            category_conflict, technique_conflict,
            bool(a["EvidenceRole"] & b["EvidenceRole"]),
            left["category_consistency"], right["category_consistency"],
            left["technique_consistency"], right["technique_consistency"],
            _jaccard(a["Category"], b["Category"]),
            _jaccard(a["MitreTechniques"], b["MitreTechniques"]),
            len(groups[ga]) + len(groups[gb]), base[i, 2] < np.log1p(2),
            bool(shared_entity) and min(entity_freq) > 10,
        )
    return pairs, np.hstack((base, extra))


def _majority(group: list[str], truth: dict[str, str]) -> str | None:
    count = Counter(truth[a] for a in group)
    incident, hits = max(count.items(), key=lambda row: (row[1], row[0]))
    return incident if hits / len(group) >= .8 else None


def _queue(org: str, parent: dict, group_freeze: dict, candidate_freeze: dict,
           paths: dict, manifest: dict, sentinels: dict, pair_model):
    item, docs, edges, probability = load_queue(
        org, parent, group_freeze, paths, manifest, sentinels, pair_model)
    candidate_path = CANDIDATES / f"{key(org)}.pkl"
    if sha256_file(candidate_path) != candidate_freeze["prediction_sha256"][key(org)]:
        raise ValueError("Frozen candidate output changed")
    with candidate_path.open("rb") as stream:
        candidate = pickle.load(stream)
    if (item["input_alert_keys"] != candidate["input_alert_keys"] or
            not np.array_equal(edges, candidate["candidate_edges"])):
        raise ValueError("Candidate edges or alert scope changed")
    return item, docs, edges, probability


def fit(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Use a Phase 7 versioned run ID")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Run already exists")
    cfg = settings()
    source = lineage()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = sorted(org for org in parent if split.get(org) == "train")
    if len(parent) != 499 or len(train) != cfg["training_organizations_expected"]:
        raise ValueError("Historical organization split changed")
    truth = read_truth(set(train), {a for org in train for a in parent[org]["input_alert_keys"]})
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    candidate_freeze = json.loads(CANDIDATE_FREEZE.read_text(encoding="utf-8"))
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model, _, _, _ = load_models()
    rng = np.random.default_rng(cfg["seed"])
    matrices, targets = [], []
    by_org = {}
    total = Counter()
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    for number, org in enumerate(train, 1):
        item, docs, edges, probability = _queue(
            org, parent, group_freeze, candidate_freeze, paths, manifest, sentinels,
            pair_model)
        pairs, x = fragment_features(item["input_alert_keys"], item["groups"],
                                     docs, edges, probability)
        majority = [_majority(group, truth) for group in item["groups"]]
        valid = np.asarray([majority[a] is not None and majority[b] is not None
                            for a, b in pairs], dtype=bool)
        y = np.asarray([int(majority[a] is not None and majority[a] == majority[b])
                        for a, b in pairs], dtype=np.uint8)
        positives = np.flatnonzero(valid & (y == 1))
        negatives = np.flatnonzero(valid & (y == 0))
        max_pos = cfg["training_max_positive_per_organization"]
        if len(positives) > max_pos:
            positives = np.sort(rng.choice(positives, max_pos, replace=False))
        max_hard = cfg["training_max_hard_negative_per_organization"]
        hard = negatives[np.argsort(-x[negatives, 0], kind="stable")[:max_hard]]
        remaining = np.setdiff1d(negatives, hard, assume_unique=True)
        max_random = cfg["training_max_random_negative_per_organization"]
        random = np.sort(rng.choice(remaining, min(max_random, len(remaining)),
                                    replace=False))
        chosen = np.concatenate((positives, hard, random))
        if len(chosen):
            matrices.append(x[chosen])
            targets.append(y[chosen])
        counts = {"proposed_pairs": len(pairs), "eligible_label_pairs": int(valid.sum()),
                  "available_positive": int((valid & (y == 1)).sum()),
                  "available_negative": len(negatives), "sample_positive": len(positives),
                  "sample_hard_negative": len(hard), "sample_random_negative": len(random),
                  "ambiguous_group_pairs_excluded": len(pairs) - int(valid.sum())}
        by_org[key(org)] = counts
        total.update(counts)
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Prepared {number}/334 training queues", flush=True)
    x_train = np.vstack(matrices)
    y_train = np.concatenate(targets)
    if x_train.shape[1] != len(FEATURES) or y_train.sum() < 100 or (y_train == 0).sum() < 100:
        raise ValueError("Insufficient training examples")
    model = lgb.LGBMClassifier(random_state=cfg["seed"], **cfg["model"])
    model.fit(x_train, y_train, feature_name=list(FEATURES))
    private.mkdir(parents=True)
    model_path = private / "fragment_model.pkl"
    with model_path.open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir()
    write_json(public / "fit_freeze.json", {
        "classification": "exploratory_historical_train_only_lightgbm_fragment_model",
        "run": run_id, "training_organizations": len(train),
        "training_counts": dict(total), "training_counts_per_organization": by_org,
        "training_rows": len(y_train), "training_positive_rows": int(y_train.sum()),
        "training_negative_rows": int((y_train == 0).sum()),
        "features": list(FEATURES), "model_parameters": model.get_params(),
        "source_sha256": source, "model_sha256": sha256_file(model_path),
        "validation_holdout_unassigned_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "fit_frozen", "training_rows": len(y_train),
                      "positives": int(y_train.sum())}))


def decide(groups: list[list[str]], pairs: list[tuple[int, int]], x: np.ndarray,
           model, policy: dict):
    """Fixed non-cascading mutual-best policy; all proposals get a decision record."""
    if not pairs:
        return groups, [], {"proposed": 0, "accepted": 0, "review": 0,
                            "decision_counts": {}}
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        scores = model.predict_proba(x)[:, 1]
    decisions = []
    eligible = []
    for i, (ga, gb) in enumerate(pairs):
        evidence = {name: float(value) for name, value in zip(FEATURES, x[i])}
        score = float(scores[i])
        reason = None
        if x[i, FEATURES.index("combined_group_size")] > policy["maximum_combined_alerts"]:
            reason = "reject_component_cap"
        elif x[i, FEATURES.index("entity_group_frequency_min")] <= 0:
            reason = "reject_no_shared_entity"
        elif x[i, FEATURES.index("entity_group_frequency_min")] > policy["maximum_entity_group_frequency"]:
            reason = "reject_common_entity"
        elif policy["require_shared_category_or_technique"] and not (
                x[i, FEATURES.index("category_jaccard")] > 0 or
                x[i, FEATURES.index("technique_jaccard")] > 0):
            reason = "reject_no_descriptor_corroboration"
        elif policy["block_disjoint_category_and_technique"] and (
                x[i, FEATURES.index("category_conflict")] and
                x[i, FEATURES.index("technique_conflict")]):
            reason = "reject_conflicting_descriptors"
        elif np.expm1(x[i, BASE_FEATURES.index("log_cross_edges")]) + 1e-5 < policy["minimum_independent_cross_edges"]:
            reason = "reject_single_bridge"
        else:
            larger = ga if len(groups[ga]) >= len(groups[gb]) else gb
            touched = (x[i, BASE_FEATURES.index("log_touched_left")] if larger == ga
                       else x[i, BASE_FEATURES.index("log_touched_right")])
            if np.expm1(touched) + 1e-5 < policy["minimum_touched_alerts_larger_fragment"]:
                reason = "reject_single_alert_support"
        if reason is None and score < policy["review_probability"]:
            reason = "reject_low_confidence"
        elif reason is None and score < policy["accept_probability"]:
            reason = "abstain_review"
        if reason is None:
            reason = "eligible_pending_mutual_best"
            eligible.append(i)
        decisions.append({"base_group_left": ga, "base_group_right": gb,
                          "model_probability": score, "evidence": evidence,
                          "decision": reason})
    best = {}
    for i in eligible:
        ga, gb = pairs[i]
        score = (float(scores[i]), float(x[i, 0]), -min(ga, gb), -max(ga, gb))
        for group, neighbor in ((ga, gb), (gb, ga)):
            if group not in best or score > best[group][1]:
                best[group] = (neighbor, score)
    mutual = [i for i in eligible if best[pairs[i][0]][0] == pairs[i][1]
              and best[pairs[i][1]][0] == pairs[i][0]]
    used = set()
    accepted = []
    for i in sorted(mutual, key=lambda j: (-scores[j], pairs[j])):
        ga, gb = pairs[i]
        if ga not in used and gb not in used:
            accepted.append((ga, gb))
            used.update((ga, gb))
            decisions[i]["decision"] = "accepted"
    for i in eligible:
        if decisions[i]["decision"] == "eligible_pending_mutual_best":
            decisions[i]["decision"] = "reject_nonmutual_or_conflict"
    partner = {a: b for a, b in accepted} | {b: a for a, b in accepted}
    result = []
    for i, group in enumerate(groups):
        if i not in partner:
            result.append(group)
        elif i < partner[i]:
            result.append(sorted(group + groups[partner[i]]))
    result.sort(key=lambda group: group[0])
    counts = Counter(record["decision"] for record in decisions)
    return result, decisions, {"proposed": len(pairs), "accepted": len(accepted),
                                "review": counts["abstain_review"],
                                "decision_counts": dict(counts)}


def predict(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if not run_id.startswith(PREFIX) or (public / "prediction_freeze.json").exists():
        raise ValueError("New versioned run ID with no prediction freeze required")
    cfg = settings()
    fit_freeze = json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))
    if fit_freeze["source_sha256"] != lineage():
        raise ValueError("Source changed since model fit")
    model_path = private / "fragment_model.pkl"
    if sha256_file(model_path) != fit_freeze["model_sha256"]:
        raise ValueError("Fitted model changed")
    with model_path.open("rb") as stream:
        model = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if len(parent) != 499:
        raise ValueError("Queue cohort changed")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    rank_freeze = json.loads(RANK_FREEZE.read_text(encoding="utf-8"))
    candidate_freeze = json.loads(CANDIDATE_FREEZE.read_text(encoding="utf-8"))
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model, v4_model, v7_model, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    census = Counter()
    hashes = {}
    decision_hashes = {}
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    baseline_load_seconds = 0.0
    extra_seconds = 0.0
    baseline_peak = peak
    for number, org in enumerate(sorted(parent), 1):
        t0 = time.perf_counter()
        item, docs, edges, probability = _queue(
            org, parent, group_freeze, candidate_freeze, paths, manifest, sentinels,
            pair_model)
        score_path = ROOT / "data/derived" / RANK_RUN / f"scores_{key(org)}.pkl"
        if sha256_file(score_path) != rank_freeze["score_sha256"][key(org)]:
            raise ValueError("Frozen v7 score changed")
        with score_path.open("rb") as stream:
            base_scores = pickle.load(stream)
        baseline_load_seconds += time.perf_counter() - t0
        peak = max(peak, process.memory_info().rss)
        baseline_peak = max(baseline_peak, process.memory_info().rss)
        t1 = time.perf_counter()
        pairs, x = fragment_features(item["input_alert_keys"], item["groups"],
                                     docs, edges, probability)
        groups, decisions, counts = decide(item["groups"], pairs, x, model,
                                           cfg["decision"])
        if groups == item["groups"]:
            scores = base_scores
        else:
            scores = score_groups_v7(groups, docs, base_ranker, v4_model, v7_model,
                                     hasher)
        output = private / f"groups_{key(org)}.pkl"
        decision_path = private / f"decisions_{key(org)}.pkl"
        with output.open("wb") as stream:
            pickle.dump({"input_alert_keys": item["input_alert_keys"],
                         "groups": groups, "scores": scores,
                         "candidate_pairs": len(edges)}, stream,
                        protocol=pickle.HIGHEST_PROTOCOL)
        with decision_path.open("wb") as stream:
            pickle.dump(decisions, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[key(org)] = sha256_file(output)
        decision_hashes[key(org)] = sha256_file(decision_path)
        census.update({"organizations": 1, "alerts": len(item["input_alert_keys"]),
                       "candidate_pairs": len(edges), "groups": len(groups),
                       "proposed": counts["proposed"], "accepted": counts["accepted"],
                       "review": counts["review"],
                       **{f"decision_{reason}": count for reason, count in
                          counts["decision_counts"].items()}})
        extra_seconds += time.perf_counter() - t1
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Predicted {number}/499 queues", flush=True)
    if (census["organizations"], census["alerts"], census["candidate_pairs"]) != (
            499, 400039, 1942648):
        raise ValueError("Frozen input census changed")
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_frozen_ml_fragment_predictions",
        "run": run_id, "fit_freeze_sha256": sha256_file(public / "fit_freeze.json"),
        "model_sha256": sha256_file(model_path), "source_sha256": lineage(),
        "prediction_sha256": hashes, "decision_sha256": decision_hashes,
        "census": dict(census), "prediction_stage_evaluator_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "baseline_load_seconds_same_pass": baseline_load_seconds,
                     "fragment_extra_seconds_same_pass": extra_seconds,
                     "baseline_peak_rss_bytes_same_pass": baseline_peak,
                     "peak_process_rss_bytes": peak},
    })
    print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))


def _size_recovery(groups: list[list[str]], scores: list[float], keys: list[str],
                   truth: dict, ranks: dict) -> dict[str, dict[str, float]]:
    sizes = Counter(truth[a] for a in keys)
    buckets = {gold: ("absent" if sizes[gold] == 0 else "singleton" if sizes[gold] == 1
                      else "2_to_10" if sizes[gold] <= 10 else "11_plus") for gold in ranks}
    result = defaultdict(lambda: {"labels": 0, "expected_recovered_top20": 0.0,
                                  "recoverable": 0})
    for gold, bucket in buckets.items():
        result[bucket]["labels"] += 1
    ordered = sorted(zip(groups, scores), key=lambda item: (-item[1], item[0][0]))
    at = 0
    while at < len(ordered) and at < 20:
        end = at + 1
        while end < len(ordered) and ordered[end][1] == ordered[at][1]:
            end += 1
        weight = min(end - at, 20 - at) / (end - at)
        for group, _ in ordered[at:end]:
            membership = Counter(truth[a] for a in group)
            if not membership:
                continue
            gold, overlap = max(membership.items(), key=lambda row: (row[1], row[0]))
            if gold in ranks and overlap / sizes[gold] >= .8 and overlap / len(group) >= .8:
                result[buckets[gold]]["expected_recovered_top20"] += weight
        at = end
    for group in groups:
        membership = Counter(truth[a] for a in group)
        gold, overlap = max(membership.items(), key=lambda row: (row[1], row[0]))
        if gold in ranks and overlap / sizes[gold] >= .8 and overlap / len(group) >= .8:
            result[buckets[gold]]["recoverable"] += 1
    return dict(result)


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Metrics already frozen")
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (freeze["source_sha256"] != lineage() or
            freeze["fit_freeze_sha256"] != sha256_file(public / "fit_freeze.json")):
        raise ValueError("Source or fit freeze changed after prediction")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    rank_freeze = json.loads(RANK_FREEZE.read_text(encoding="utf-8"))
    candidate_freeze = json.loads(CANDIDATE_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    totals = defaultdict(Counter)
    size_totals = defaultdict(lambda: defaultdict(Counter))
    per_org = {}
    candidate_true_pairs = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        paths = ((private / f"groups_{name}.pkl", freeze["prediction_sha256"][name]),
                 (private / f"decisions_{name}.pkl", freeze["decision_sha256"][name]),
                 (ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl",
                  group_freeze["prediction_sha256"][name]),
                 (ROOT / "data/derived" / RANK_RUN / f"scores_{name}.pkl",
                  rank_freeze["score_sha256"][name]),
                 (CANDIDATES / f"{name}.pkl", candidate_freeze["prediction_sha256"][name]))
        if any(sha256_file(path) != digest for path, digest in paths):
            raise ValueError("Frozen prediction, decision, or input changed")
        with paths[0][0].open("rb") as stream:
            variant = pickle.load(stream)
        with paths[2][0].open("rb") as stream:
            base = pickle.load(stream)
        with paths[3][0].open("rb") as stream:
            base_scores = pickle.load(stream)
        with paths[4][0].open("rb") as stream:
            candidate = pickle.load(stream)
        keys = base["input_alert_keys"]
        if (variant["input_alert_keys"] != keys or candidate["input_alert_keys"] != keys
                or variant["candidate_pairs"] != len(candidate["candidate_edges"])):
            raise ValueError("Alert or candidate denominator changed")
        connected = connected_incidents(keys, candidate["candidate_edges"], truth,
                                        ranks[org])
        n = len(keys)
        candidate_true_pairs += sum(
            truth[keys[int(edge // n)]] == truth[keys[int(edge % n)]]
            for edge in candidate["candidate_edges"])
        organization = {}
        for method, groups, scores in (("reference", base["groups"], base_scores),
                                       ("fragment_ml", variant["groups"], variant["scores"])):
            metric = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            outcomes = incident_outcomes(groups, keys, truth, ranks[org], connected)
            if metric["recoverable"] != outcomes["recoverable"]:
                raise ValueError("Recoverability definitions disagree")
            rows[method][org] = {k: metric[k] for k in ("recall20", "p10", "ndcg20")}
            totals[method].update({k: metric[k] for k in ("tp", "fp", "fn")})
            totals[method].update(outcomes)
            for bucket, values in _size_recovery(groups, scores, keys, truth,
                                                 ranks[org]).items():
                size_totals[method][bucket].update(values)
            organization[method] = {**rows[method][org], "recoverable": metric["recoverable"],
                                    "incomplete": outcomes["incomplete"],
                                    "impure": outcomes["impure"],
                                    "pair_fp": metric["fp"],
                                    "mixed_predicted_groups": outcomes["mixed_predicted_groups"]}
        per_org[name] = {"split": split.get(org, "unassigned"), **organization,
                         "delta": {field: organization["fragment_ml"][field] -
                                   organization["reference"][field] for field in
                                   ("recall20", "p10", "ndcg20", "recoverable", "incomplete",
                                    "impure", "pair_fp", "mixed_predicted_groups")}}
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Evaluated {number}/499 queues", flush=True)
    cohorts = {"all_499_exploratory": orgs,
               "training_334_exploratory": [o for o in orgs if split.get(o) == "train"],
               "validation_67_exposed": [o for o in orgs if split.get(o) == "validation"],
               "holdout_68_exposed": [o for o in orgs if split.get(o) == "holdout"],
               "outside_fitting_135_exploratory": [o for o in orgs if split.get(o) in
                                                   ("validation", "holdout")],
               "unassigned_30_exploratory": [o for o in orgs if split.get(o) == "unassigned"]}
    comparison = {}
    for cohort, selected in cohorts.items():
        comparison[cohort] = {
            "organizations": len(selected), "expert_top20_denominator": 20 * len(selected),
            "methods": {method: {field: bootstrap([rows[method][o][field]
                                                   for o in selected]) for field in
                                 ("recall20", "p10", "ndcg20")}
                        for method in ("reference", "fragment_ml")},
            "paired_fragment_ml_minus_reference": {
                field: bootstrap([rows["fragment_ml"][o][field] -
                                  rows["reference"][o][field] for o in selected])
                for field in ("recall20", "p10", "ndcg20")},
        }
    aggregate = {}
    for method, counts in totals.items():
        tp, fp, fn = (counts[k] for k in ("tp", "fp", "fn"))
        aggregate[method] = {**dict(counts), "pair_precision": tp / (tp + fp),
                             "pair_recall": tp / (tp + fn),
                             "group_oracle_recall20_ceiling": counts["recoverable"] / 9980,
                             "complete_and_pure_top20_labels": counts["recoverable"],
                             "false_splits_top20_incomplete_labels": counts["incomplete"],
                             "false_merges_mixed_groups": counts["mixed_predicted_groups"]}
    reference = comparison["all_499_exploratory"]["methods"]["reference"]
    frozen = json.loads((ROOT / "outputs" / RANK_RUN / "metrics.json").read_text(encoding="utf-8"))
    recorded = frozen["cohorts"]["all_499_descriptive"]["methods"]["v7_selected"]
    if any(abs(reference[k]["mean"] - recorded[k]["mean"]) > 1e-10 for k in
           ("recall20", "p10", "ndcg20")):
        raise ValueError("Frozen v7 baseline metrics not reproduced")
    base, variant = aggregate["reference"], aggregate["fragment_ml"]
    if (base["recoverable"], base["fp"], base["incomplete"], base["impure"],
            base["mixed_predicted_groups"]) != (6969, 28606, 1451, 218, 4841):
        raise ValueError("Frozen v2 grouping baseline not reproduced")
    if any(sum(aggregate[method][name] for name in
               ("absent", "candidate_disconnected", "incomplete", "impure",
                "recoverable")) != 9980 for method in ("reference", "fragment_ml")):
        raise ValueError("Top-20 label denominator changed")
    gate = {
        "recoverability_gain_at_least_10_per_42_queues": variant["recoverable"] - base["recoverable"] >= 10 * 499 / 42,
        "impurity_not_increased": variant["impure"] <= base["impure"],
        "mixed_groups_not_increased": variant["mixed_predicted_groups"] <= base["mixed_predicted_groups"],
        "false_positive_pairs_not_increased": variant["fp"] <= base["fp"],
        "pair_precision_not_decreased": variant["pair_precision"] >= base["pair_precision"],
        "p10_not_decreased": comparison["all_499_exploratory"]["methods"]["fragment_ml"]["p10"]["mean"] >= reference["p10"]["mean"],
        "runtime_within_25_percent_same_pass": freeze["resource"]["baseline_load_seconds_same_pass"] + freeze["resource"]["fragment_extra_seconds_same_pass"] <= 1.25 * freeze["resource"]["baseline_load_seconds_same_pass"],
        "memory_within_25_percent_same_pass": freeze["resource"]["peak_process_rss_bytes"] <= 1.25 * freeze["resource"]["baseline_peak_rss_bytes_same_pass"],
    }
    result = {
        "classification": "exploratory_post_exposure_fragment_matching_ml_not_confirmatory",
        "run": run_id, "organizations": 499, "alerts": 400039,
        "candidate_pairs": 1942648, "expert_top20_denominator": 9980,
        "candidate_true_pairs": candidate_true_pairs,
        "candidate_false_pairs_unchanged": 1942648 - candidate_true_pairs,
        "cohorts": comparison, "pair_and_group": aggregate,
        "incident_size": {method: {bucket: dict(counts) for bucket, counts in values.items()}
                          for method, values in size_totals.items()},
        "per_organization_pseudonymous": per_org,
        "descriptive_acceptance_checks": gate,
        "resource": {"fit": json.loads((public / "fit_freeze.json").read_text(encoding="utf-8"))["resource"],
                     "prediction": freeze["resource"],
                     "evaluation": {"wall_seconds": time.perf_counter() - started,
                                    "peak_process_rss_bytes": peak}},
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "limits": ["All GUIDE_Test labels have been accessed previously",
                   "Training-only fit is exploratory; no validation or holdout labels used in fit",
                   "No parameter selected from this 499-queue comparison",
                   "Operational feature allowlist empty; point-in-time availability unresolved"],
    }
    write_json(public / "metrics.json", result)
    write_json(public / "run_manifest.json", {
        "classification": result["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), CONFIG, public / "fit_freeze.json",
                    private / "fragment_model.pkl", freeze_path, public / "metrics.json")},
        "prediction_sha256": freeze["prediction_sha256"],
        "decision_sha256": freeze["decision_sha256"],
    })
    print(json.dumps({"status": "evaluation_frozen",
                      "reference_recall20": reference["recall20"]["mean"],
                      "fragment_ml_recall20": comparison["all_499_exploratory"]["methods"]["fragment_ml"]["recall20"]["mean"],
                      "checks": gate}))


def self_test() -> None:
    cfg = settings()
    class Dummy:
        def predict_proba(self, matrix):
            return np.asarray([[0.01, 0.99] for _ in matrix])
    groups = [["a"], ["b", "c"], ["d"]]
    x = np.zeros((2, len(FEATURES)), dtype=np.float32)
    x[:, FEATURES.index("entity_group_frequency_min")] = 2
    x[:, FEATURES.index("category_jaccard")] = 1
    x[:, BASE_FEATURES.index("log_cross_edges")] = np.log1p(2)
    x[:, BASE_FEATURES.index("log_touched_right")] = np.log1p(2)
    x[:, BASE_FEATURES.index("log_touched_left")] = np.log1p(2)
    output, decisions, counts = decide(groups, [(0, 1), (1, 2)], x, Dummy(),
                                       cfg["decision"])
    assert output == [["a", "b", "c"], ["d"]] and counts["accepted"] == 1
    assert len(decisions) == 2 and {d["decision"] for d in decisions} == {
        "accepted", "reject_nonmutual_or_conflict"}
    x[:, FEATURES.index("entity_group_frequency_min")] = 11
    output, decisions, counts = decide(groups, [(0, 1), (1, 2)], x, Dummy(),
                                       cfg["decision"])
    assert output == groups and counts["accepted"] == 0
    output, decisions, counts = decide(groups, [], x[:0], Dummy(), cfg["decision"])
    assert output == groups and not decisions and counts["decision_counts"] == {}
    print(json.dumps({"status": "pass", "synthetic_assertions": 4,
                      "empirical_label_reads": 0}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "fit", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_fragment_matching_ml_v1_20261115_v1")
    args = parser.parse_args()
    {"self-test": self_test, "fit": fit, "predict": predict,
     "evaluate": evaluate}[args.stage](**({} if args.stage == "self-test" else
                                  {"run_id": args.run_id}))


if __name__ == "__main__":
    main()
