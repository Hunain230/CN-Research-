"""Evaluator-only matched full versus hard-negative ranking comparison."""

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
from src.submission_hard_negative_ablation_v1 import (
    PREFIX, GROUP_RUN, V7_RUN, GROUP_FREEZE, METHODS, source_hashes, configuration)
from submission.evaluate_ranking_ltr_v1 import inclusion_probabilities, positive_group_incident


V7_FREEZE = ROOT / "outputs" / V7_RUN / "prediction_freeze.json"
ALL_METHODS = ("frozen_v7", *METHODS)
PAIRS = (("full_40", "hard_40"), ("full_60", "hard_60"))


def run(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Wrong experiment family")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    metrics_path = public / "metrics.json"
    if metrics_path.exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != source_hashes() or freeze["methods"] != list(METHODS):
        raise ValueError("Prediction lineage or method set changed")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    model_params = {}
    for method in METHODS:
        model_path = private / f"{method}_model.pkl"
        if sha256_file(model_path) != freeze["model_sha256"][method]:
            raise ValueError("Fitted model changed")
        with model_path.open("rb") as stream:
            model_params[method] = pickle.load(stream).get_params()
    for full, hard in PAIRS:
        if model_params[full] != model_params[hard]:
            raise ValueError("A matched model pair has different hyperparameters")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499:
        raise ValueError("Organization cohort changed")
    truth = read_truth(set(orgs), {alert for item in parent.values()
                                  for alert in item["input_alert_keys"]})
    rank = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    transitions_from_v7 = defaultdict(Counter)
    transitions_matched = defaultdict(Counter)
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
        checks = ((group_path, group_freeze["prediction_sha256"][name]),
                  (v7_path, v7_freeze["score_sha256"][name]),
                  (score_path, freeze["score_sha256"][name]))
        if any(sha256_file(path) != digest for path, digest in checks):
            raise ValueError("Frozen group or score file changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        with v7_path.open("rb") as stream:
            v7_scores = pickle.load(stream)
        with score_path.open("rb") as stream:
            new_scores = pickle.load(stream)
        groups, keys = item["groups"], item["input_alert_keys"]
        if keys != parent[org]["input_alert_keys"] or set(new_scores) != set(METHODS):
            raise ValueError("Candidate method or alert scope changed")
        scores = {"frozen_v7": v7_scores, **new_scores}
        if any(len(value) != len(groups) for value in scores.values()):
            raise ValueError("Score/group alignment changed")
        positive, gold_sizes = positive_group_incident(groups, keys, truth, rank[org])
        oracle += len(positive)
        probabilities = {method: inclusion_probabilities(groups, values)
                         for method, values in scores.items()}
        org_metrics = {}
        for method in ALL_METHODS:
            scored = tie_aware_ranking(groups, scores[method], truth, rank[org])
            row = {"recall20": scored["recall_at_20"],
                   "p10": scored["precision_at_10"],
                   "ndcg20": scored["ndcg_at_20_rank1_highest"]}
            rows[method][org] = row
            org_metrics[method] = row
            for index, gold in positive.items():
                kind = "singleton" if gold_sizes[gold] == 1 else "multi_alert"
                size_recovery[method][kind] += probabilities[method][index]
        for gold in rank[org]:
            kind = ("absent" if not gold_sizes[gold] else
                    "singleton" if gold_sizes[gold] == 1 else "multi_alert")
            size_recovery["denominator"][kind] += 1
        for method in METHODS:
            for index in positive:
                old, new = probabilities["frozen_v7"][index], probabilities[method][index]
                transitions_from_v7[method]["newly_recovered_expected"] += new * (1 - old)
                transitions_from_v7[method]["previously_recovered_lost_expected"] += old * (1 - new)
        for full, hard in PAIRS:
            for index in positive:
                old, new = probabilities[full][index], probabilities[hard][index]
                transitions_matched[hard]["newly_recovered_expected"] += new * (1 - old)
                transitions_matched[hard]["previously_recovered_lost_expected"] += old * (1 - new)
        per_org[name] = {
            "cohort": split.get(org, "unassigned"), "methods": org_metrics,
            "paired_hard_minus_full": {
                hard: {metric: org_metrics[hard][metric] - org_metrics[full][metric]
                       for metric in ("recall20", "p10", "ndcg20")}
                for full, hard in PAIRS},
            "paired_vs_v7": {
                method: {metric: org_metrics[method][metric] - org_metrics["frozen_v7"][metric]
                         for metric in ("recall20", "p10", "ndcg20")}
                for method in METHODS}}
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Evaluated sampling ablation {number}/499", flush=True)
    if (oracle, size_recovery["denominator"]["absent"]) != (6969, 855):
        raise ValueError("Fixed-group recovery denominator changed")
    cohorts = {
        "all_499_descriptive": orgs,
        "historical_train_334": [o for o in orgs if split.get(o) == "train"],
        "historical_validation_67_exposed": [o for o in orgs if split.get(o) == "validation"],
        "historical_holdout_68_exposed": [o for o in orgs if split.get(o) == "holdout"],
        "outside_fitting_135_exploratory": [o for o in orgs if split.get(o) in ("validation", "holdout")]}
    comparisons = {}
    for label, chosen in cohorts.items():
        comparisons[label] = {
            "organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
            "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                 for metric in ("recall20", "p10", "ndcg20")}
                        for method in ALL_METHODS},
            "paired_hard_minus_full": {
                hard: {metric: bootstrap([rows[hard][o][metric] - rows[full][o][metric]
                                          for o in chosen])
                       for metric in ("recall20", "p10", "ndcg20")}
                for full, hard in PAIRS},
            "paired_vs_v7": {
                method: {metric: bootstrap([rows[method][o][metric] - rows["frozen_v7"][o][metric]
                                            for o in chosen])
                         for metric in ("recall20", "p10", "ndcg20")}
                for method in METHODS}}
    v7_metrics = json.loads((ROOT / "outputs" / V7_RUN / "metrics.json").read_text(encoding="utf-8"))
    reference = v7_metrics["cohorts"]["all_499_descriptive"]["methods"]["v7_selected"]
    for metric in ("recall20", "p10", "ndcg20"):
        actual = comparisons["all_499_descriptive"]["methods"]["frozen_v7"][metric]["mean"]
        if abs(actual - reference[metric]["mean"]) > 1e-10:
            raise ValueError("Reference metric not reproduced")
    result = {
        "classification": "exploratory_post_exposure_matched_hard_negative_ablation_not_confirmatory",
        "run": run_id, "candidate_pairs": 1942648, "alerts": 400039,
        "organizations": 499, "expert_top20_denominator": 9980,
        "fixed_group_oracle_recoverable": oracle,
        "fixed_group_oracle_recall20_ceiling": oracle / 9980,
        "comparison_pairs": [list(pair) for pair in PAIRS],
        "cohorts": comparisons,
        "recovered_by_incident_size_expected": {method: dict(counts)
                                                for method, counts in size_recovery.items()},
        "transitions_from_v7_expected": {method: dict(counts)
                                         for method, counts in transitions_from_v7.items()},
        "transitions_matched_hard_minus_full_expected": {method: dict(counts)
                                                         for method, counts in transitions_matched.items()},
        "transition_definition": "Tie-aware expected newly recovered and lost positive groups under independent uniform tie ordering",
        "per_organization_pseudonymous": per_org,
        "training_examples_per_organization_pseudonymous":
            freeze["per_training_organization_pseudonymous"],
        "resource": {**freeze["resource"], "evaluation_wall_seconds": time.perf_counter() - started,
                     "evaluation_peak_process_rss_bytes": peak},
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "limits": ["All GUIDE_Test labels previously accessed; results exploratory",
                   "Validation and historical holdout are not untouched",
                   "Each matched pair has identical LightGBM parameters; only sampled training rows differ",
                   "Frozen v2 groups and all 499 evaluation queues are identical",
                   "Production model-field allowlist remains empty"]}
    write_json(metrics_path, result)
    write_json(public / "run_manifest.json", {
        "classification": result["classification"],
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                   for path in (Path(__file__), ROOT / "src/submission_hard_negative_ablation_v1.py",
                                ROOT / "configs/hard_negative_ablation_v1.json",
                                freeze_path, metrics_path)},
        "private_score_sha256": freeze["score_sha256"],
        "private_model_sha256": freeze["model_sha256"]})
    print(json.dumps({
        "status": "exploratory_ablation_evaluation_frozen",
        "recall20_all_499": {
            method: comparisons["all_499_descriptive"]["methods"][method]["recall20"]["mean"]
            for method in ALL_METHODS}}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="submission_hard_negative_ablation_v1_20261115_v1")
    args = parser.parse_args()
    run(args.run_id)


if __name__ == "__main__":
    main()
