"""Matched leave-one-route-out ablation on frozen GUIDE pair and rank models."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
from sklearn.feature_extraction import FeatureHasher

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_full_entity_time import PARENT, read_docs, generate
from .submission_entity_time_pair_v2 import SPLIT, shard_map, groups_at, predict_probability
from .submission_descriptor_ranker_v7 import GROUP_FREEZE, GROUP_RUN
from .submission_specialist_ranker_v8 import V7_FREEZE, v7_scores
from .submission_group_merge_v10_v2 import load_models, score_groups_v7
from .submission_group_ranker_v4 import bootstrap
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_candidate_route_ablation_v11_"
ROUTES = {"full": 0, "drop_descriptor": 1, "drop_entity": 6, "drop_technique": 8}
THRESHOLD = .75


def source_hashes() -> dict:
    paths = (Path(__file__), ROOT / "src/submission_group_merge_v10_v2.py",
             ROOT / "src/submission_full_entity_time.py",
             ROOT / "src/submission_entity_time_pair_v2.py",
             ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl",
             ROOT / "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl",
             ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1/descriptor_rank_model.pkl",
             GROUP_FREEZE, V7_FREEZE, SPLIT,
             ROOT / "outputs/submission_entity_time_shards_20261114_v1.json")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v11 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v7_freeze = json.loads(V7_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if len(parent) != 499:
        raise ValueError("Ranked cohort changed")
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model, v4, v7, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    private.mkdir(parents=True)
    hashes = {}
    census = defaultdict(Counter)
    process = psutil.Process()
    peak = 0
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        keys = parent[org]["input_alert_keys"]
        projection = paths[org]
        if sha256_file(projection) != shard_manifest["parquet_sha256"][str(projection.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        docs = read_docs(org, projection, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        base_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{key(org)}.pkl"
        if sha256_file(base_path) != group_freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen base groups changed")
        with base_path.open("rb") as stream:
            base = pickle.load(stream)
        if keys != base["input_alert_keys"] or len(edges) != base["candidate_pairs"]:
            raise ValueError("Base candidate population changed")
        variants = {}
        for name, dropped in ROUTES.items():
            new_flags = flags & np.uint8(15 ^ dropped)
            mask = new_flags != 0
            route_edges = edges[mask]
            if name == "full":
                groups, scores = base["groups"], v7_scores(org, v7_freeze)
            else:
                probabilities = predict_probability(keys, docs, route_edges, new_flags[mask], pair_model)
                groups = groups_at(keys, route_edges, probabilities, THRESHOLD)
                scores = score_groups_v7(groups, docs, base_ranker, v4, v7, hasher)
            variants[name] = {"groups": groups, "scores": scores, "candidate_edges": route_edges}
            census[name].update({"alerts": len(keys), "candidate_pairs": len(route_edges),
                                 "predicted_groups": len(groups)})
        output = private / f"routes_{key(org)}.pkl"
        with output.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "variants": variants}, stream,
                        protocol=pickle.HIGHEST_PROTOCOL)
        hashes[key(org)] = sha256_file(output)
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Frozen route ablation {index}/499 queues", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_leave_one_candidate_route_out_fixed_models",
        "run": run_id, "organizations": 499, "route_flags_removed": ROUTES,
        "pair_link_threshold": THRESHOLD,
        "census": {name: dict(value) for name, value in census.items()},
        "prediction_sha256": hashes, "source_sha256": source_hashes(),
        "evaluation_labels_read": False,
        "resource": {"wall_seconds": time.perf_counter()-started,
                     "peak_process_rss_bytes": peak}})
    print(json.dumps({"status": "predictions_frozen",
                      "candidate_pairs": {name: c["candidate_pairs"] for name, c in census.items()}}))


def candidate_connectivity(keys: list[str], edges: np.ndarray, truth: dict,
                           rank: dict) -> tuple[int, int]:
    n = len(keys)
    parent = list(range(n))
    sizes = [1]*n

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    positive_edges = 0
    for edge in edges:
        a, b = divmod(int(edge), n)
        if truth[keys[a]] != truth[keys[b]]:
            continue
        positive_edges += 1
        ra, rb = root(a), root(b)
        if ra != rb:
            if sizes[ra] < sizes[rb]:
                ra, rb = rb, ra
            parent[rb] = ra
            sizes[ra] += sizes[rb]
    gold_sizes = Counter(truth[alert] for alert in keys)
    max_connected = Counter()
    seen = set()
    for i, alert in enumerate(keys):
        gold = truth[alert]
        if gold not in rank:
            continue
        component = root(i)
        if (gold, component) in seen:
            continue
        seen.add((gold, component))
        max_connected[gold] = max(max_connected[gold], sizes[component])
    bound = sum(max_connected[gold]/gold_sizes[gold] >= .8 for gold in rank if gold_sizes[gold])
    return positive_edges, bound


def group_recoverable(groups: list[list[str]], truth: dict, rank: dict,
                      gold_sizes: Counter) -> int:
    recovered = set()
    for group in groups:
        counts = Counter(truth[alert] for alert in group)
        gold, overlap = max(counts.items(), key=lambda item: (item[1], item[0]))
        if gold in rank and overlap/gold_sizes[gold] >= .8 and overlap/len(group) >= .8:
            recovered.add(gold)
    return len(recovered)


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != source_hashes():
        raise ValueError("Method source changed")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {alert for item in parent.values() for alert in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    totals = defaultdict(Counter)
    for index, org in enumerate(orgs, 1):
        path = private / f"routes_{key(org)}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen route output changed")
        with path.open("rb") as stream:
            output = pickle.load(stream)
        keys = output["input_alert_keys"]
        if keys != parent[org]["input_alert_keys"]:
            raise ValueError("Alert population changed")
        gold_sizes = Counter(truth[alert] for alert in keys)
        totals["full"]["positive_pairs"] += sum(v*(v-1)//2 for v in gold_sizes.values())
        for name, item in output["variants"].items():
            groups, scores, edges = item["groups"], item["scores"], item["candidate_edges"]
            positive, bound = candidate_connectivity(keys, edges, truth, ranks[org])
            ranking = tie_aware_ranking(groups, scores, truth, ranks[org])
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": .8,
                             "top20_recovery_min_purity": .8})
            recovered = group_recoverable(groups, truth, ranks[org], gold_sizes)
            rows[name][org] = {"recall20": ranking["recall_at_20"],
                               "p10": ranking["precision_at_10"],
                               "ndcg20": ranking["ndcg_at_20_rank1_highest"]}
            totals[name].update({"candidate_pairs": len(edges), "positive_candidate_pairs": positive,
                                 "candidate_connected_labels": bound,
                                 "group_recoverable_labels": recovered,
                                 "tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"]})
        if index % 50 == 0:
            print(f"Evaluated route ablation {index}/499 queues", flush=True)
    positive_pairs = totals["full"]["positive_pairs"]
    if positive_pairs != 159186107:
        raise ValueError("Positive pair denominator changed")
    cohorts = {"all_499_descriptive": orgs,
               "outside_training_135": [org for org in orgs if split.get(org) in ("validation", "holdout")],
               "historical_holdout_68_previously_exposed": [org for org in orgs if split.get(org) == "holdout"]}
    comparisons = {}
    for cohort, chosen in cohorts.items():
        comparisons[cohort] = {"organizations": len(chosen),
                               "expert_top20_denominator": 20*len(chosen),
                               "methods": {name: {metric: bootstrap([rows[name][org][metric] for org in chosen])
                                                  for metric in ("recall20", "p10", "ndcg20")}
                                           for name in ROUTES},
                               "paired_drop_minus_full_recall20": {
                                   name: bootstrap([rows[name][org]["recall20"]-rows["full"][org]["recall20"]
                                                    for org in chosen]) for name in ROUTES if name != "full"}}
    stage = {}
    for name, c in totals.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        stage[name] = {"candidate_pairs": c["candidate_pairs"],
                       "positive_candidate_pairs": c["positive_candidate_pairs"],
                       "candidate_pair_recall_all_pairs": c["positive_candidate_pairs"]/positive_pairs,
                       "candidate_connected_top20": c["candidate_connected_labels"],
                       "candidate_connectivity_ceiling": c["candidate_connected_labels"]/(20*len(orgs)),
                       "recoverable_top20": c["group_recoverable_labels"],
                       "group_ceiling": c["group_recoverable_labels"]/(20*len(orgs)),
                       "pair_tp": tp, "pair_fp": fp, "pair_fn": fn,
                       "pair_precision": tp/(tp+fp) if tp+fp else 0,
                       "pair_recall": tp/(tp+fn),
                       "pair_f1": 2*tp/(2*tp+fp+fn)}
    write_json(public / "metrics.json", {"classification": "exploratory_post_exposure_candidate_route_ablation",
                                         "run": run_id, "positive_pair_denominator": positive_pairs,
                                         "cohorts": comparisons, "stages": stage,
                                         "prediction_freeze_sha256": sha256_file(freeze_path),
                                         "resource": freeze["resource"],
                                         "limits": ["GUIDE_Test labels previously accessed",
                                                    "Entity/time point-in-time availability unconfirmed",
                                                    "Full variant reuses frozen v2 groups and v7 rank scores",
                                                    "Removed routes change candidate flags used by the fixed pair model"]})
    write_json(public / "run_manifest.json", {"sha256": {str(path.relative_to(ROOT)): sha256_file(path)
                                                           for path in (Path(__file__), freeze_path, public/"metrics.json")},
                                              "private_prediction_sha256": freeze["prediction_sha256"]})
    print(json.dumps({"status": "exploratory_ablation_complete",
                      "full_recall20": comparisons["all_499_descriptive"]["methods"]["full"]["recall20"]["mean"],
                      "stage_summary": {name: {"candidate_pairs": value["candidate_pairs"],
                                               "candidate_connectivity_ceiling": value["candidate_connectivity_ceiling"],
                                               "group_ceiling": value["group_ceiling"]}
                                        for name, value in stage.items()}}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_candidate_route_ablation_v11_20261115_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
