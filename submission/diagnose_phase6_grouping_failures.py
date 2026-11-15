"""Evaluator-only diagnostics of frozen v2 candidate, split, and impurity misses.

This script fits no model, proposes no new links, and exports no raw identifiers,
entity values, or alert content. Existing model scores are recomputed only to
explain frozen decisions, then checked against the frozen group partition.
"""

from __future__ import annotations

import json
import pickle
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import psutil

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_full_entity_time import (
    PARENT, ENTITY_FIELDS, TIME_ENTITY_SECONDS, TIME_TECHNIQUE_SECONDS,
    MAX_TOKEN_FREQUENCY, generate, read_docs)
from src.submission_entity_time_pair_v2 import (
    PRIOR, PRIOR_FREEZE, SPLIT, shard_map, predict_probability, groups_at)
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


V2_RUN = "submission_entity_time_pair_v2_20261114_v1"
V2_FREEZE = ROOT / "outputs" / V2_RUN / "prediction_freeze.json"
FIT_FREEZE = ROOT / "outputs" / V2_RUN / "fit_freeze.json"
MODEL = ROOT / "data/derived" / V2_RUN / "pair_model.pkl"
OUTPUT = ROOT / "outputs/phase6_grouping_failure_analysis_20261115_v4.json"
FIELDS = ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")


def percentile(values: list[int], q: float) -> float:
    return float(np.quantile(values, q)) if values else 0.0


def size_bucket(n: int) -> str:
    return "absent" if n == 0 else "1" if n == 1 else "2-10" if n <= 10 else "11-100" if n <= 100 else ">100"


def route_signals(a: dict, b: dict, frequency: Counter,
                  technique_frequency: Counter) -> dict[str, bool]:
    gap = abs(a["stamp"] - b["stamp"])
    shared_entity = a["entities"] & b["entities"]
    shared_technique = a["fields"]["MitreTechniques"] & b["fields"]["MitreTechniques"]
    bounded_entity = any(frequency[token] <= MAX_TOKEN_FREQUENCY for token in shared_entity)
    bounded_technique = any(technique_frequency[token] <= MAX_TOKEN_FREQUENCY
                            for token in shared_technique)
    return {
        "shared_entity": bool(shared_entity),
        "entity_within_48h": bool(shared_entity) and gap <= TIME_ENTITY_SECONDS,
        "entity_beyond_48h": bool(shared_entity) and gap > TIME_ENTITY_SECONDS,
        "entity_only_over_frequency_cap": bool(shared_entity) and not bounded_entity,
        "entity_prefilter_eligible": bounded_entity and gap <= TIME_ENTITY_SECONDS,
        "shared_technique": bool(shared_technique),
        "technique_within_1h": bool(shared_technique) and gap <= TIME_TECHNIQUE_SECONDS,
        "technique_prefilter_eligible": bounded_technique and gap <= TIME_TECHNIQUE_SECONDS,
        "technique_beyond_1h": bounded_technique and gap > TIME_TECHNIQUE_SECONDS,
        "shared_detector": bool(a["fields"]["DetectorId"] & b["fields"]["DetectorId"]),
        "shared_category": bool(a["fields"]["Category"] & b["fields"]["Category"]),
        "shared_evidence_role": bool(a["fields"]["EvidenceRole"] & b["fields"]["EvidenceRole"]),
        "within_48h": gap <= TIME_ENTITY_SECONDS,
    }


def example(case_type: str, alert_count: int, component_sizes: list[int],
            fragment_sizes: list[int], extra: dict) -> dict:
    return {"case_type": case_type, "alerts_in_gold_incident": alert_count,
            "oracle_candidate_component_sizes": sorted(component_sizes, reverse=True)[:8],
            "predicted_fragment_gold_alert_counts": sorted(fragment_sizes, reverse=True)[:8],
            **extra}


def audit() -> dict:
    if OUTPUT.exists():
        raise FileExistsError("Phase 6 diagnostic already exists")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    candidate_freeze = json.loads(PRIOR_FREEZE.read_text(encoding="utf-8"))
    fit_freeze = json.loads(FIT_FREEZE.read_text(encoding="utf-8"))
    if sha256_file(MODEL) != fit_freeze["model_sha256"]:
        raise ValueError("Frozen pair model changed")
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    with PARENT.open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    if len(orgs) != 499:
        raise ValueError("Organization cohort changed")
    truth = read_truth(set(orgs), {alert for item in baseline.values()
                                  for alert in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    overall = Counter()
    by_size = defaultdict(Counter)
    by_split = defaultdict(Counter)
    by_queue_size = defaultdict(Counter)
    org_counts = defaultdict(Counter)
    feature_missing = Counter()
    category_missing = defaultdict(Counter)
    disconnected_small_signals = Counter()
    disconnected_small_combinations = Counter()
    incomplete_fragments = Counter()
    incomplete_cross_score = Counter()
    incomplete_support = Counter()
    incomplete_strongest_route = Counter()
    impure_features = Counter()
    impure_false_route = Counter()
    cases = {}
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    all_candidate_pairs = 0
    all_alerts = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        candidate_path = PRIOR / f"{name}.pkl"
        group_path = ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl"
        shard = paths[org]
        if (sha256_file(candidate_path) != candidate_freeze["prediction_sha256"][name]
                or sha256_file(group_path) != v2_freeze["prediction_sha256"][name]
                or sha256_file(shard) != shard_manifest["parquet_sha256"][str(shard.relative_to(ROOT))]):
            raise ValueError("Frozen candidate, group, or projection changed")
        with candidate_path.open("rb") as stream:
            candidate = pickle.load(stream)
        with group_path.open("rb") as stream:
            predicted = pickle.load(stream)
        keys = predicted["input_alert_keys"]
        if keys != candidate["input_alert_keys"] or keys != baseline[org]["input_alert_keys"]:
            raise ValueError("Alert scope changed")
        docs = read_docs(org, shard, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, baseline[org]["candidate_edges"])
        if not np.array_equal(edges, candidate["candidate_edges"]):
            raise ValueError("Candidate graph changed")
        probability = predict_probability(keys, docs, edges, flags, model)
        if groups_at(keys, edges, probability, .75) != predicted["groups"]:
            raise ValueError("Recomputed threshold groups differ from frozen v2 groups")
        n = len(keys)
        all_alerts += n
        all_candidate_pairs += len(edges)
        for alert in keys:
            doc = docs[alert]
            feature_missing["alerts"] += 1
            feature_missing["no_entity"] += not bool(doc["entities"])
            for field in FIELDS:
                feature_missing[f"no_{field}"] += not bool(doc["fields"][field])
        frequency = Counter(token for doc in docs.values() for token in doc["entities"])
        technique_frequency = Counter(token for doc in docs.values()
                                      for token in doc["fields"]["MitreTechniques"])
        parent = list(range(n))

        def root(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for edge in edges:
            a, b = divmod(int(edge), n)
            if truth[keys[a]] != truth[keys[b]]:
                continue
            ra, rb = root(a), root(b)
            if ra != rb:
                parent[rb] = ra
        group_of = {}
        group_memberships = []
        for group_index, group in enumerate(predicted["groups"]):
            member = Counter(truth[alert] for alert in group)
            group_memberships.append(member)
            for alert in group:
                group_of[alert] = group_index
        if len(group_of) != n:
            raise ValueError("V2 groups do not partition alerts")
        gold_alerts = defaultdict(list)
        oracle_parts = defaultdict(Counter)
        group_parts = defaultdict(list)
        for i, alert in enumerate(keys):
            gold = truth[alert]
            gold_alerts[gold].append(i)
            if gold in ranks[org]:
                oracle_parts[gold][root(i)] += 1
        for group_index, member in enumerate(group_memberships):
            for gold, overlap in member.items():
                if gold in ranks[org]:
                    group_parts[gold].append((group_index, overlap, len(predicted["groups"][group_index])))
        # These are existing candidate edges, with existing model scores.
        cross_fragment = defaultdict(lambda: {"count": 0, "max": -1.0, "flag": 0,
                                               "alerts_left": set(), "alerts_right": set(),
                                               "best_pair": None})
        false_in_group = defaultdict(lambda: {"count": 0, "max": -1.0, "flag": 0,
                                              "best_pair": None})
        for at, edge in enumerate(edges):
            a, b = divmod(int(edge), n)
            ga, gb = group_of[keys[a]], group_of[keys[b]]
            gold_a, gold_b = truth[keys[a]], truth[keys[b]]
            score = float(probability[at])
            if gold_a == gold_b and ga != gb and gold_a in ranks[org]:
                record = cross_fragment[gold_a]
                record["count"] += 1
                record["alerts_left"].add(keys[a])
                record["alerts_right"].add(keys[b])
                if score > record["max"]:
                    record["max"], record["flag"], record["best_pair"] = score, int(flags[at]), (keys[a], keys[b])
            if ga == gb and gold_a != gold_b and score >= .75:
                record = false_in_group[ga]
                record["count"] += 1
                if score > record["max"]:
                    record["max"], record["flag"], record["best_pair"] = score, int(flags[at]), (keys[a], keys[b])
        queue_bucket = "<=500" if n <= 500 else "501-2000" if n <= 2000 else ">2000"
        for gold in ranks[org]:
            indices = gold_alerts[gold]
            size = len(indices)
            components = list(oracle_parts[gold].values())
            parts = group_parts[gold]
            complete = [(i, overlap, group_size) for i, overlap, group_size in parts
                        if size and overlap / size >= .8]
            if size == 0:
                reason = "absent"
            elif max(components, default=0) / size < .8:
                reason = "candidate_disconnected"
            elif not complete:
                reason = "incomplete"
            elif not any(overlap / group_size >= .8 for _, overlap, group_size in complete):
                reason = "impure"
            else:
                reason = "recoverable"
            overall[reason] += 1
            by_size[size_bucket(size)][reason] += 1
            by_split[split.get(org, "unassigned")][reason] += 1
            by_queue_size[queue_bucket][reason] += 1
            org_counts[org][reason] += 1
            if reason not in ("candidate_disconnected", "incomplete", "impure"):
                continue
            category_missing[reason]["labels"] += 1
            category_missing[reason]["all_alerts_no_entity"] += bool(indices) and all(not docs[keys[i]]["entities"] for i in indices)
            for field in FIELDS:
                category_missing[reason][f"all_alerts_no_{field}"] += bool(indices) and all(
                    not docs[keys[i]]["fields"][field] for i in indices)
            stamps = [docs[keys[i]]["stamp"] for i in indices]
            category_missing[reason]["span_over_48h"] += bool(stamps) and max(stamps) - min(stamps) > TIME_ENTITY_SECONDS
            category_missing[reason]["span_over_7d"] += bool(stamps) and max(stamps) - min(stamps) > 7 * 24 * 3600
            if reason == "candidate_disconnected":
                category_missing[reason]["more_than_one_oracle_component"] += len(components) > 1
                if size <= 10:
                    disconnected_small_signals["incidents"] += 1
                    found = set()
                    for a, b in combinations(indices, 2):
                        if root(a) == root(b):
                            continue
                        found.update(k for k, value in route_signals(docs[keys[a]], docs[keys[b]], frequency, technique_frequency).items() if value)
                    for signal in found:
                        disconnected_small_signals[signal] += 1
                    if not any(s in found for s in ("shared_entity", "shared_technique")):
                        disconnected_small_combinations["no_shared_entity_or_technique"] += 1
                    if "shared_entity" in found and "entity_within_48h" not in found:
                        disconnected_small_combinations["shared_entity_only_beyond_48h"] += 1
                    if "shared_technique" in found and "technique_within_1h" not in found:
                        disconnected_small_combinations["shared_technique_only_beyond_1h"] += 1
                    if ("entity_prefilter_eligible" in found
                            or "technique_prefilter_eligible" in found):
                        disconnected_small_combinations["route_eligible_pair_missing_from_graph"] += 1
                    if "disconnected_no_shared" not in cases and not any(
                            s in found for s in ("shared_entity", "shared_technique")):
                        cases["disconnected_no_shared"] = example(
                            "disconnected_no_entity_or_technique", size, components,
                            [overlap for _, overlap, _ in parts],
                            {"shared_detector": "shared_detector" in found,
                             "shared_category": "shared_category" in found,
                             "span_over_48h": max(stamps) - min(stamps) > TIME_ENTITY_SECONDS})
                    if ("disconnected_eligible_pair" not in cases
                            and "route_eligible_pair_missing_from_graph" in
                            {key for key, val in disconnected_small_combinations.items() if val}
                            and ("entity_prefilter_eligible" in found or "technique_prefilter_eligible" in found)):
                        cases["disconnected_eligible_pair"] = example(
                            "disconnected_route_eligible_pair_not_proposed", size, components,
                            [overlap for _, overlap, _ in parts],
                            {"shared_entity": "shared_entity" in found,
                             "entity_within_48h": "entity_within_48h" in found,
                             "shared_technique": "shared_technique" in found,
                             "technique_within_1h": "technique_within_1h" in found})
            elif reason == "incomplete":
                incomplete_fragments[f"fragments_{min(len(parts), 6)}+"] += 1
                incomplete_fragments[f"largest_fragment_{min(max((overlap for _, overlap, _ in parts), default=0), 10)}+"] += 1
                incomplete_fragments["incidents_2_to_10_alerts"] += size <= 10
                record = cross_fragment[gold]
                incomplete_support["cross_positive_candidate_edges_total"] += record["count"]
                incomplete_support["with_at_least_one_cross_positive_edge"] += record["count"] > 0
                incomplete_support["with_at_least_two_cross_positive_edges"] += record["count"] >= 2
                if record["max"] < .25:
                    incomplete_cross_score["best_lt_0.25"] += 1
                elif record["max"] < .5:
                    incomplete_cross_score["best_0.25_to_0.5"] += 1
                elif record["max"] < .65:
                    incomplete_cross_score["best_0.5_to_0.65"] += 1
                elif record["max"] < .75:
                    incomplete_cross_score["best_0.65_to_0.75"] += 1
                else:
                    incomplete_cross_score["best_ge_0.75_cap_blocked"] += 1
                for route, bit in (("baseline", 1), ("entity", 6), ("technique", 8)):
                    incomplete_strongest_route[route] += bool(record["flag"] & bit)
                if record["best_pair"]:
                    a, b = record["best_pair"]
                    signals = route_signals(docs[a], docs[b], frequency, technique_frequency)
                    for signal, value in signals.items():
                        incomplete_strongest_route[signal] += value
                if ("incomplete_2_to_10" not in cases and size <= 10
                        and record["count"] > 0):
                    cases["incomplete_2_to_10"] = example(
                        "candidate_connected_but_v2_split", size, components,
                        [overlap for _, overlap, _ in parts],
                        {"cross_fragment_positive_candidate_edges": record["count"],
                         "strongest_cross_fragment_pair_probability": round(record["max"], 4),
                         "strongest_edge_entity_route": bool(record["flag"] & 6),
                         "strongest_edge_technique_route": bool(record["flag"] & 8)})
            else:
                group_index, overlap, group_size = max(complete, key=lambda row: (row[1], -row[2]))
                impure_features["impure_gold_labels"] += 1
                impure_features["unrelated_alerts_in_selected_group"] += group_size - overlap
                impure_features["group_size_over_10"] += group_size > 10
                impure_features["singleton_gold_incident"] += size == 1
                false_record = false_in_group[group_index]
                impure_features["group_has_direct_high_score_false_edge"] += false_record["count"] > 0
                impure_features["single_direct_high_score_false_edge"] += false_record["count"] == 1
                impure_features["direct_high_score_false_edges_total"] += false_record["count"]
                for route, bit in (("baseline", 1), ("entity", 6), ("technique", 8)):
                    impure_false_route[route] += bool(false_record["flag"] & bit)
                if false_record["best_pair"]:
                    a, b = false_record["best_pair"]
                    signals = route_signals(docs[a], docs[b], frequency, technique_frequency)
                    for signal, value in signals.items():
                        impure_false_route[signal] += value
                if "impure_direct_edge" not in cases and false_record["count"] > 0:
                    cases["impure_direct_edge"] = example(
                        "complete_incident_contaminated_by_unrelated_alerts",
                        size, components, [overlap for _, overlap, _ in parts],
                        {"selected_group_size": group_size,
                         "selected_group_gold_alerts": overlap,
                         "direct_high_score_cross_incident_edges": false_record["count"],
                         "strongest_false_edge_probability": round(false_record["max"], 4),
                         "strongest_false_edge_entity_route": bool(false_record["flag"] & 6)})
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Diagnosed {number}/499 frozen queues", flush=True)
    if all_alerts != 400039 or all_candidate_pairs != 1942648:
        raise ValueError("Alert or candidate denominator changed")
    expected = {"absent": 855, "candidate_disconnected": 487,
                "incomplete": 1451, "impure": 218, "recoverable": 6969}
    if dict(overall) != expected:
        raise ValueError(f"Loss categories differ from frozen audit: {dict(overall)}")
    org_patterns = {}
    for category in ("candidate_disconnected", "incomplete", "impure"):
        values = [org_counts[org][category] for org in orgs]
        ordered = sorted(values, reverse=True)
        org_patterns[category] = {
            "organizations_with_at_least_one": sum(value > 0 for value in values),
            "median_labels_per_organization": percentile(values, .5),
            "p90_labels_per_organization": percentile(values, .9),
            "maximum_labels_one_organization": max(values),
            "share_in_top_50_organizations": sum(ordered[:50]) / sum(values)}
    result = {
        "classification": "exploratory_evaluator_only_frozen_grouping_failure_analysis",
        "organizations": 499, "alerts": all_alerts,
        "candidate_pairs": all_candidate_pairs, "expert_top20_denominator": 9980,
        "categories": dict(overall),
        "by_incident_size": {k: dict(v) for k, v in by_size.items()},
        "by_historical_split": {k: dict(v) for k, v in by_split.items()},
        "by_queue_alert_count": {k: dict(v) for k, v in by_queue_size.items()},
        "organization_patterns": org_patterns,
        "all_alert_feature_missing": dict(feature_missing),
        "failure_incident_feature_missing": {k: dict(v) for k, v in category_missing.items()},
        "candidate_disconnected_2_to_10_cross_component_signals": dict(disconnected_small_signals),
        "candidate_disconnected_2_to_10_pattern_counts": dict(disconnected_small_combinations),
        "incomplete_fragment_histograms": dict(incomplete_fragments),
        "incomplete_best_cross_positive_edge_score": dict(incomplete_cross_score),
        "incomplete_cross_positive_edge_support": dict(incomplete_support),
        "incomplete_strongest_cross_edge_signals": dict(incomplete_strongest_route),
        "impure_group_diagnostics": dict(impure_features),
        "impure_strongest_false_edge_signals": dict(impure_false_route),
        "anonymized_examples": cases,
        "method_notes": [
            "Candidate components use only same-incident frozen edges to define an oracle bound; labels are evaluator-only.",
            "Small disconnected incidents (2-10 alerts) have exhaustive cross-component pair signal checks; larger incidents receive field-missing and span summaries only.",
            "For disconnected cross-component pairs only, prefilter eligibility plus graph absence is consistent with the nearest-five posting rule. Prefilter eligibility on existing candidate edges has no 'unproposed' meaning.",
            "The strongest incomplete-edge diagnostics recompute probabilities with the frozen v2 pair model; no model is fitted or threshold selected.",
            "V2 groups_at uses the shared DSU, whose MAX_COMPONENT=100 can reject an edge even when its probability is at least 0.75; recomputed groups are asserted equal to the frozen partition.",
            "Examples disclose counts, Boolean signals and rounded scores only; no alert, incident, organization or entity identifiers."
        ],
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in
                          (Path(__file__), V2_FREEZE, PRIOR_FREEZE, FIT_FREEZE,
                           ROOT / "src/submission_entity_time_pair_v2.py",
                           ROOT / "src/submission_full_entity_time.py",
                           ROOT / "configs/entity_time_sensitivity_policy.yaml")},
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "peak_process_rss_bytes": peak}}
    return result


def main() -> None:
    result = audit()
    write_json(OUTPUT, result)
    print(json.dumps({"status": "diagnostic_frozen",
                      "categories": result["categories"],
                      "resource": result["resource"]}, sort_keys=True))


if __name__ == "__main__":
    main()
