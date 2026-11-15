"""Evaluator-only matched comparison of frozen ranking scores on fixed v2 groups."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, tie_aware_ranking, write_json
from src.submission_group_ranker_v4 import bootstrap
from src.submission_entity_time_pair_v2 import SPLIT
from src.submission_ranking_ltr_v1 import GROUP_RUN, V7_RUN, GROUP_FREEZE, V7_FREEZE, sources


RUN_PREFIX = "submission_ranking_ltr_v1_"
METHODS = ("frozen_v7", "lightgbm_full", "xgboost_full", "lightgbm_hardneg")


def inclusion_probabilities(groups: list[list[str]], scores: list[float],
                            cutoff: int = 20) -> list[float]:
    order = sorted(range(len(groups)), key=lambda i: (-scores[i], groups[i][0]))
    probability = [0.0] * len(groups)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and scores[order[end]] == scores[order[start]]:
            end += 1
        included = max(0, min(end, cutoff) - start)
        chance = included / (end - start)
        for j in range(start, end):
            probability[order[j]] = chance
        start = end
    return probability


def positive_group_incident(groups: list[list[str]], keys: list[str],
                            truth: dict, ranks: dict) -> tuple[dict[int, str], Counter]:
    sizes = Counter(truth[a] for a in keys)
    positive = {}
    for index, group in enumerate(groups):
        members = Counter(truth[a] for a in group)
        gold, hit = max(members.items(), key=lambda row: (row[1], row[0]))
        if gold in ranks and hit / sizes[gold] >= .8 and hit / len(group) >= .8:
            positive[index] = gold
    return positive, sizes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="submission_ranking_ltr_v1_20261115_v1")
    args = parser.parse_args()
    if not args.run_id.startswith(RUN_PREFIX):
        raise ValueError("Wrong experiment family")
    public = ROOT / "outputs" / args.run_id
    private = ROOT / "data/derived" / args.run_id
    metrics_path = public / "metrics.json"
    if metrics_path.exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources():
        raise ValueError("Prediction method changed after freeze")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    for method, digest in freeze["model_sha256"].items():
        if sha256_file(private / f"{method}_model.pkl") != digest:
            raise ValueError("Fitted model changed")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499:
        raise ValueError("Organization cohort changed")
    truth = read_truth(set(orgs), {alert for item in parent.values()
                                  for alert in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    transitions = defaultdict(Counter)
    size_recovery = defaultdict(Counter)
    per_org = {}
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    oracle = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        v7_path = ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl"
        score_path = private / f"scores_{name}.pkl"
        feature_path = private / f"features_{name}.npz"
        checks = ((group_path, group_freeze["prediction_sha256"][name]),
                  (v7_path, v7_freeze["score_sha256"][name]),
                  (score_path, freeze["score_sha256"][name]),
                  (feature_path, freeze["feature_sha256"][name]))
        if any(sha256_file(path) != digest for path, digest in checks):
            raise ValueError("A frozen input changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        with v7_path.open("rb") as stream:
            baseline_scores = pickle.load(stream)
        with score_path.open("rb") as stream:
            candidate_scores = pickle.load(stream)
        keys, groups = item["input_alert_keys"], item["groups"]
        if keys != parent[org]["input_alert_keys"]:
            raise ValueError("Alert scope changed")
        if len(baseline_scores) != len(groups) or any(len(s) != len(groups) for s in candidate_scores.values()):
            raise ValueError("Group score alignment changed")
        positives, gold_sizes = positive_group_incident(groups, keys, truth, ranks[org])
        oracle += len(positives)
        scores = {"frozen_v7": baseline_scores, **candidate_scores}
        if set(scores) != set(METHODS):
            raise ValueError("Method set changed")
        chances = {method: inclusion_probabilities(groups, value)
                   for method, value in scores.items()}
        org_row = {}
        for method in METHODS:
            metric = tie_aware_ranking(groups, scores[method], truth, ranks[org])
            row = {"recall20": metric["recall_at_20"],
                   "p10": metric["precision_at_10"],
                   "ndcg20": metric["ndcg_at_20_rank1_highest"]}
            rows[method][org] = row
            org_row[method] = row
            for index, gold in positives.items():
                kind = "singleton" if gold_sizes[gold] == 1 else "multi_alert"
                size_recovery[method][kind] += chances[method][index]
        for gold in ranks[org]:
            kind = "absent" if not gold_sizes[gold] else "singleton" if gold_sizes[gold] == 1 else "multi_alert"
            size_recovery["denominator"][kind] += 1
        for method in METHODS[1:]:
            for index in positives:
                old, new = chances["frozen_v7"][index], chances[method][index]
                transitions[method]["newly_recovered_expected"] += new * (1 - old)
                transitions[method]["previously_recovered_lost_expected"] += old * (1 - new)
        per_org[name] = {
            "cohort": split.get(org, "unassigned"),
            "methods": org_row,
            "paired_minus_v7": {
                method: {metric: org_row[method][metric] - org_row["frozen_v7"][metric]
                         for metric in ("recall20", "p10", "ndcg20")}
                for method in METHODS[1:]}}
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Evaluated ranking scores {number}/499", flush=True)
    if oracle != 6969 or size_recovery["denominator"]["absent"] != 855:
        raise ValueError("Fixed-group recovery denominator changed")
    cohorts = {
        "all_499_descriptive": orgs,
        "historical_train_334": [o for o in orgs if split.get(o) == "train"],
        "historical_validation_67_used_for_selection": [o for o in orgs if split.get(o) == "validation"],
        "historical_holdout_68_previously_exposed": [o for o in orgs if split.get(o) == "holdout"],
        "outside_fitting_135_exploratory": [o for o in orgs if split.get(o) in ("validation", "holdout")]}
    comparisons = {}
    for label, chosen in cohorts.items():
        comparisons[label] = {
            "organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
            "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                 for metric in ("recall20", "p10", "ndcg20")}
                        for method in METHODS},
            "paired_candidate_minus_v7": {
                method: {metric: bootstrap([rows[method][o][metric] - rows["frozen_v7"][o][metric]
                                            for o in chosen])
                         for metric in ("recall20", "p10", "ndcg20")}
                for method in METHODS[1:]}}
    recorded = json.loads((ROOT / "outputs" / V7_RUN / "metrics.json").read_text(encoding="utf-8"))
    frozen_metrics = recorded["cohorts"]["all_499_descriptive"]["methods"]["v7_selected"]
    for metric in ("recall20", "p10", "ndcg20"):
        actual = comparisons["all_499_descriptive"]["methods"]["frozen_v7"][metric]["mean"]
        if abs(actual - frozen_metrics[metric]["mean"]) > 1e-10:
            raise ValueError("Frozen v7 metric not reproduced")
    result = {
        "classification": "exploratory_post_exposure_fixed_group_ranking_comparison_not_confirmatory",
        "run": args.run_id,
        "candidate_pairs": 1942648, "alerts": 400039,
        "organizations": 499, "expert_top20_denominator": 9980,
        "fixed_group_oracle_recoverable": oracle,
        "fixed_group_oracle_recall20_ceiling": oracle / 9980,
        "selected_method_on_historical_validation": freeze["selected_method"],
        "cohorts": comparisons,
        "recovered_by_incident_size_expected": {k: dict(v) for k, v in size_recovery.items()},
        "transitions_from_v7_expected": {k: dict(v) for k, v in transitions.items()},
        "transition_definition": "Tie-aware expected newly recovered and lost positive groups under independent uniform tie ordering",
        "per_organization_pseudonymous": per_org,
        "resource": {**freeze["resource"], "evaluation_wall_seconds": time.perf_counter() - started,
                     "evaluation_peak_process_rss_bytes": peak},
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "limits": ["GUIDE_Test labels previously accessed; all results exploratory",
                   "Historical holdout is not untouched",
                   "All candidate methods use identical frozen v2 groups",
                   "No evaluator-only field used as a model input",
                   "Production feature allowlist remains empty"]}
    write_json(metrics_path, result)
    write_json(public / "run_manifest.json", {
        "classification": result["classification"],
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                   for path in (Path(__file__), ROOT / "src/submission_ranking_ltr_v1.py",
                                ROOT / "configs/ranking_ltr_v1.json", freeze_path, metrics_path)},
        "private_score_sha256": freeze["score_sha256"],
        "private_model_sha256": freeze["model_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_frozen",
                      "selected_method": freeze["selected_method"],
                      "recall20": {method: comparisons["all_499_descriptive"]["methods"][method]["recall20"]["mean"]
                                   for method in METHODS}}, sort_keys=True))


if __name__ == "__main__":
    main()
