"""Fixed, label-free fragment grouping on the frozen GUIDE candidate graph.

Predict does not open evaluator labels. Evaluate opens them only after all
organization predictions are frozen. This is retrospective exploratory work.
"""

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

from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json
from .submission_full_entity_time import PARENT, ENTITY_FIELDS
from .submission_group_merge_v10_v2 import load_models, load_queue, score_groups_v7
from .submission_entity_time_pair_v2 import shard_map
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


CONFIG = ROOT / "configs/fragment_aware_v1.json"
PREFIX = "submission_fragment_aware_v1_"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
RANK_RUN = "submission_descriptor_ranker_v7_20261114_v1"
CANDIDATE_RUN = "submission_full_entity_time_20261114_v1"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
RANK_FREEZE = ROOT / "outputs" / RANK_RUN / "prediction_freeze.json"
CANDIDATE_FREEZE = ROOT / "outputs" / CANDIDATE_RUN / "prediction_freeze.json"
PRIVATE_CANDIDATES = ROOT / "data/derived" / CANDIDATE_RUN


def config() -> dict:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if value["candidate_run"] != CANDIDATE_RUN or value["group_run"] != GROUP_RUN or value["rank_run"] != RANK_RUN:
        raise ValueError("Reference runs changed")
    if value["model_fitting"] or not value["single_pass_only"] or not value["mutual_best_only"]:
        raise ValueError("This version requires a fixed, label-free, single-pass rule")
    return value


def lineage() -> dict[str, str]:
    paths = (Path(__file__), CONFIG, GROUP_FREEZE, RANK_FREEZE, CANDIDATE_FREEZE,
             ROOT / "data/derived" / GROUP_RUN / "pair_model.pkl",
             ROOT / "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl",
             ROOT / "data/derived" / RANK_RUN / "descriptor_rank_model.pkl",
             ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl",
             ROOT / "src/submission_group_merge_v10_v2.py",
             ROOT / "src/submission_descriptor_ranker_v7.py")
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def fragment_groups(keys: list[str], base_groups: list[list[str]], docs: dict,
                    edges: np.ndarray, probability: np.ndarray,
                    rule: dict) -> tuple[list[list[str]], dict]:
    """One noncascading mutual-best merge pass; never reads incident labels."""
    n = len(keys)
    if len(edges) != len(probability):
        raise ValueError("Pair scores and candidate graph are misaligned")
    group_of = {}
    for g, group in enumerate(base_groups):
        for alert in group:
            if alert in group_of:
                raise ValueError("Duplicate alert in base groups")
            group_of[alert] = g
    if set(group_of) != set(keys):
        raise ValueError("Base groups do not partition alert scope")
    membership = [group_of[alert] for alert in keys]
    entity_sets = [set().union(*(docs[a]["entities"] for a in group)) for group in base_groups]
    category_sets = [set().union(*(docs[a]["fields"]["Category"] for a in group)) for group in base_groups]
    technique_sets = [set().union(*(docs[a]["fields"]["MitreTechniques"] for a in group)) for group in base_groups]
    entity_frequency = Counter(entity for values in entity_sets for entity in values)
    cross = defaultdict(lambda: {"edges": set(), "left": set(), "right": set(), "max": 0.0, "sum": 0.0})
    floor = float(rule["proposal_pair_probability_floor"])
    for at in np.flatnonzero(probability >= floor):
        a, b = divmod(int(edges[at]), n)
        ga, gb = membership[a], membership[b]
        if ga == gb:
            continue
        if ga > gb:
            ga, gb, a, b = gb, ga, b, a
        if len(base_groups[ga]) + len(base_groups[gb]) > rule["maximum_combined_alerts"]:
            continue
        record = cross[(ga, gb)]
        record["edges"].add((a, b))
        record["left"].add(a)
        record["right"].add(b)
        score = float(probability[at])
        record["max"] = max(record["max"], score)
        record["sum"] += score
    eligible = []
    for (ga, gb), record in cross.items():
        if (len(record["edges"]) < rule["minimum_independent_cross_edges"]
                or record["max"] < rule["minimum_max_pair_probability"]):
            continue
        larger = ga if len(base_groups[ga]) >= len(base_groups[gb]) else gb
        touched = record["left"] if larger == ga else record["right"]
        if len(touched) < rule["minimum_distinct_alerts_on_larger_side"]:
            continue
        shared = entity_sets[ga] & entity_sets[gb]
        rare_shared = [entity for entity in shared
                       if entity_frequency[entity] <= rule["maximum_entity_group_frequency"]]
        if rule["require_shared_entity"] and not rare_shared:
            continue
        descriptor_agreement = bool(category_sets[ga] & category_sets[gb]
                                    or technique_sets[ga] & technique_sets[gb])
        if rule["require_shared_category_or_technique"] and not descriptor_agreement:
            continue
        eligible.append((ga, gb, record["sum"], record["max"], len(record["edges"])))
    best = {}
    for ga, gb, total, highest, count in eligible:
        score = (total, highest, count)
        for source, target in ((ga, gb), (gb, ga)):
            if source not in best or (score, -target) > (best[source][1], -best[source][0]):
                best[source] = (target, score)
    mutual = [row for row in eligible if best.get(row[0], (None,))[0] == row[1]
              and best.get(row[1], (None,))[0] == row[0]]
    mutual.sort(key=lambda row: (-row[2], -row[3], -row[4], row[0], row[1]))
    used, selected = set(), []
    for ga, gb, *_ in mutual:
        if ga not in used and gb not in used:
            selected.append((ga, gb))
            used.update((ga, gb))
    partner = {a: b for a, b in selected} | {b: a for a, b in selected}
    result = []
    for g, group in enumerate(base_groups):
        if g not in partner:
            result.append(group)
        elif g < partner[g]:
            result.append(sorted(group + base_groups[partner[g]]))
    result.sort(key=lambda group: group[0])
    return result, {"cross_group_pairs_at_floor": len(cross),
                    "eligible_fragment_pairs": len(eligible),
                    "mutual_pairs": len(mutual),
                    "accepted_merges": len(selected)}


def self_test() -> None:
    rule = config()
    keys = ["a", "b", "c", "d", "e"]
    groups = [["a"], ["b", "c"], ["d"], ["e"]]
    docs = {x: {"entities": {("DeviceId", "shared" if x in ("a", "b", "c") else x)},
                "fields": {"Category": {"same" if x in ("a", "b", "c") else x},
                           "MitreTechniques": set()}} for x in keys}
    edges = np.asarray([0 * 5 + 1, 0 * 5 + 2, 3 * 5 + 4], dtype=np.int64)
    scores = np.asarray([.72, .63, .9], dtype=np.float32)
    output, counts = fragment_groups(keys, groups, docs, edges, scores, rule)
    assert output == [["a", "b", "c"], ["d"], ["e"]]
    assert counts["accepted_merges"] == 1
    altered = {k: {"entities": set(v["entities"]), "fields": v["fields"]} for k, v in docs.items()}
    altered["a"]["entities"].clear()
    output, counts = fragment_groups(keys, groups, altered, edges, scores, rule)
    assert output == groups and counts["accepted_merges"] == 0
    print(json.dumps({"status": "pass", "synthetic_assertions": 3, "guide_label_reads": 0}))


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Use a versioned fragment-aware run ID")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Run path already exists")
    rule = config()
    source_hashes = lineage()
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    rank_freeze = json.loads(RANK_FREEZE.read_text(encoding="utf-8"))
    candidate_freeze = json.loads(CANDIDATE_FREEZE.read_text(encoding="utf-8"))
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if len(parent) != 499:
        raise ValueError("Reference cohort changed")
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    pair_model, v4_model, v7_model, base_ranker = load_models()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    process = psutil.Process()
    started = time.perf_counter()
    peak = process.memory_info().rss
    census = Counter()
    hashes = {}
    private.mkdir(parents=True)
    try:
        for index, org in enumerate(sorted(parent), 1):
            from .guide_rerun_v2 import key
            name = key(org)
            item, docs, edges, probability = load_queue(org, parent, group_freeze, paths,
                                                         shard_manifest, sentinels, pair_model)
            candidate_path = PRIVATE_CANDIDATES / f"{name}.pkl"
            if sha256_file(candidate_path) != candidate_freeze["prediction_sha256"][name]:
                raise ValueError("Candidate file changed")
            with candidate_path.open("rb") as stream:
                candidate = pickle.load(stream)
            if (item["input_alert_keys"] != candidate["input_alert_keys"]
                    or not np.array_equal(edges, candidate["candidate_edges"])):
                raise ValueError("Candidate graph differs from frozen reference")
            new_groups, diagnostics = fragment_groups(item["input_alert_keys"], item["groups"],
                                                       docs, edges, probability, rule)
            if new_groups == item["groups"]:
                score_path = ROOT / "data/derived" / RANK_RUN / f"scores_{name}.pkl"
                if sha256_file(score_path) != rank_freeze["score_sha256"][name]:
                    raise ValueError("Frozen v7 scores changed")
                with score_path.open("rb") as stream:
                    new_scores = pickle.load(stream)
            else:
                new_scores = score_groups_v7(new_groups, docs, base_ranker,
                                             v4_model, v7_model, hasher)
            output = private / f"fragment_{name}.pkl"
            with output.open("wb") as stream:
                pickle.dump({"input_alert_keys": item["input_alert_keys"], "groups": new_groups,
                             "scores": new_scores, "candidate_pairs": len(edges),
                             "diagnostics": diagnostics}, stream, protocol=pickle.HIGHEST_PROTOCOL)
            hashes[name] = sha256_file(output)
            census.update({"organizations": 1, "alerts": len(item["input_alert_keys"]),
                           "candidate_pairs": len(edges), "predicted_groups": len(new_groups),
                           **diagnostics})
            peak = max(peak, process.memory_info().rss)
            if index % 50 == 0:
                print(f"Predicted {index}/499 fragment queues", flush=True)
        public.mkdir()
        write_json(public / "prediction_freeze.json", {
            "classification": "exploratory_post_exposure_fixed_label_free_fragment_rule",
            "run": run_id, "reference": "frozen_v2_groups_plus_v7_ranking",
            "census": dict(census), "prediction_sha256": hashes,
            "source_sha256": source_hashes,
            "prediction_stage_guide_labels_read": False,
            "supervised_model_fitted": False, "parameter_selection_performed": False,
            "historical_method_design_informed_by_previously_exposed_guide_analyses": True,
            "resource": {"wall_seconds": time.perf_counter() - started,
                         "peak_process_rss_bytes": peak}})
        print(json.dumps({"status": "predictions_frozen", "census": dict(census)}))
    except BaseException:
        # Preserve any partial private files for inspection; never leave a valid freeze.
        raise


def incident_outcomes(groups: list[list[str]], keys: list[str], truth: dict, ranks: dict,
                      connected: set) -> Counter:
    sizes = Counter(truth[a] for a in keys)
    parts = defaultdict(list)
    mixed = 0
    for group in groups:
        membership = Counter(truth[a] for a in group)
        if len(membership) > 1:
            mixed += 1
        for gold, overlap in membership.items():
            if gold in ranks:
                parts[gold].append((overlap, len(group)))
    result = Counter({"mixed_predicted_groups": mixed})
    for gold in ranks:
        size = sizes[gold]
        if size == 0:
            name = "absent"
        elif gold not in connected:
            name = "candidate_disconnected"
        else:
            complete = [(hit, total) for hit, total in parts[gold] if hit / size >= .8]
            if not complete:
                name = "incomplete"
            elif not any(hit / total >= .8 for hit, total in complete):
                name = "impure"
            else:
                name = "recoverable"
        result[name] += 1
    return result


def connected_incidents(keys: list[str], edges, truth: dict, ranks: dict) -> set:
    n = len(keys)
    parent = list(range(n))
    def root(i):
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
    sizes = Counter(truth[a] for a in keys)
    pieces = defaultdict(Counter)
    for i, alert in enumerate(keys):
        gold = truth[alert]
        if gold in ranks:
            pieces[gold][root(i)] += 1
    return {gold for gold in ranks if sizes[gold] and max(pieces[gold].values(), default=0) / sizes[gold] >= .8}


def evaluate(run_id: str) -> None:
    from .guide_rerun_v2 import key, labels
    from .offline_joint_comparison import read_truth
    from .submission_group_merge_v10_v2 import pair_group_metrics
    from .submission_group_ranker_v4 import bootstrap
    from .submission_entity_time_pair_v2 import SPLIT

    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != lineage():
        raise ValueError("Method or reference changed after freeze")
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
    per_org = {}
    for index, org in enumerate(orgs, 1):
        name = key(org)
        variant_path = private / f"fragment_{name}.pkl"
        base_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        score_path = ROOT / "data/derived" / RANK_RUN / f"scores_{name}.pkl"
        candidate_path = PRIVATE_CANDIDATES / f"{name}.pkl"
        expected = ((variant_path, freeze["prediction_sha256"][name]),
                    (base_path, group_freeze["prediction_sha256"][name]),
                    (score_path, rank_freeze["score_sha256"][name]),
                    (candidate_path, candidate_freeze["prediction_sha256"][name]))
        if any(sha256_file(path) != digest for path, digest in expected):
            raise ValueError("Frozen per-organization output changed")
        with variant_path.open("rb") as stream:
            variant = pickle.load(stream)
        with base_path.open("rb") as stream:
            base = pickle.load(stream)
        with score_path.open("rb") as stream:
            base_scores = pickle.load(stream)
        with candidate_path.open("rb") as stream:
            candidate = pickle.load(stream)
        keys = base["input_alert_keys"]
        if (variant["input_alert_keys"] != keys or candidate["input_alert_keys"] != keys
                or variant["candidate_pairs"] != len(candidate["candidate_edges"])
                or base["candidate_pairs"] != len(candidate["candidate_edges"])):
            raise ValueError("Comparison alert or candidate scope changed")
        connected = connected_incidents(keys, candidate["candidate_edges"], truth, ranks[org])
        organization = {}
        for method, groups, scores in (("reference", base["groups"], base_scores),
                                        ("fragment", variant["groups"], variant["scores"])):
            metric = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            outcomes = incident_outcomes(groups, keys, truth, ranks[org], connected)
            rows[method][org] = {field: metric[field] for field in ("recall20", "p10", "ndcg20")}
            totals[method].update({field: metric[field] for field in ("tp", "fp", "fn", "recoverable")})
            totals[method].update(outcomes)
            organization[method] = {**rows[method][org], "recoverable": metric["recoverable"],
                                    "pair_fp": metric["fp"], "mixed_predicted_groups": outcomes["mixed_predicted_groups"]}
        per_org[name] = {**organization, "delta_fragment_minus_reference": {
            field: organization["fragment"][field] - organization["reference"][field]
            for field in ("recall20", "p10", "ndcg20", "recoverable", "pair_fp", "mixed_predicted_groups")}}
        if index % 50 == 0:
            print(f"Evaluated {index}/499 fragment queues", flush=True)
    cohorts = {"all_499_descriptive": orgs,
               "outside_fitting_135_exploratory": [o for o in orgs if split.get(o) in ("validation", "holdout")],
               "historical_holdout_68_exposed": [o for o in orgs if split.get(o) == "holdout"]}
    comparisons = {}
    for cohort, selected in cohorts.items():
        comparisons[cohort] = {
            "organizations": len(selected), "expert_top20_denominator": 20 * len(selected),
            "methods": {method: {field: bootstrap([rows[method][o][field] for o in selected])
                                 for field in ("recall20", "p10", "ndcg20")}
                        for method in ("reference", "fragment")},
            "paired_fragment_minus_reference": {
                field: bootstrap([rows["fragment"][o][field] - rows["reference"][o][field] for o in selected])
                for field in ("recall20", "p10", "ndcg20")}}
    aggregate = {}
    for method, counts in totals.items():
        tp, fp, fn = (counts[field] for field in ("tp", "fp", "fn"))
        aggregate[method] = {
            **dict(counts), "pair_precision": tp / (tp + fp) if tp + fp else 0,
            "pair_recall": tp / (tp + fn) if tp + fn else 0,
            "group_oracle_recall20_ceiling": counts["recoverable"] / 9980,
            "false_merge_definition": "mixed_predicted_groups: number of predicted groups containing alerts from at least two distinct expert incidents; each group counted once"}
    reference = comparisons["all_499_descriptive"]["methods"]["reference"]
    frozen = json.loads((ROOT / "outputs" / RANK_RUN / "metrics.json").read_text(encoding="utf-8"))
    recorded = frozen["cohorts"]["all_499_descriptive"]["methods"]["v7_selected"]
    for field in ("recall20", "p10", "ndcg20"):
        if abs(reference[field]["mean"] - recorded[field]["mean"]) > 1e-10:
            raise ValueError("Reference metric not reproduced")
    if (aggregate["reference"]["recoverable"] != 6969 or aggregate["reference"]["fp"] != 28606
            or sum(aggregate["fragment"][name] for name in
                   ("absent", "candidate_disconnected", "incomplete", "impure", "recoverable")) != 9980):
        raise ValueError("Evaluation denominator or reference changed")
    gates = config()["acceptance"]
    variant = aggregate["fragment"]
    base = aggregate["reference"]
    var_metric = comparisons["all_499_descriptive"]["methods"]["fragment"]
    gate_results = {
        "group_recoverable_labels_strictly_greater": variant["recoverable"] > base["recoverable"],
        "recall20_strictly_greater": var_metric["recall20"]["mean"] > reference["recall20"]["mean"],
        "pair_precision_floor": variant["pair_precision"] >= gates["pair_precision_minimum_fraction_of_baseline"] * base["pair_precision"],
        "false_positive_pair_ceiling": variant["fp"] <= gates["false_positive_pairs_maximum_fraction_of_baseline"] * base["fp"],
        "impure_top20_ceiling": variant["impure"] <= gates["impure_top20_labels_maximum_fraction_of_baseline"] * base["impure"],
        "p10_floor": var_metric["p10"]["mean"] >= gates["p10_minimum_fraction_of_baseline"] * reference["p10"]["mean"],
        "ndcg20_floor": var_metric["ndcg20"]["mean"] >= gates["ndcg20_minimum_fraction_of_baseline"] * reference["ndcg20"]["mean"]}
    result = {
        "classification": "exploratory_post_exposure_fragment_aware_grouping_not_confirmatory",
        "run": run_id, "organizations": 499, "alerts": 400039,
        "candidate_pairs": freeze["census"]["candidate_pairs"],
        "positive_pair_denominator": aggregate["reference"]["tp"] + aggregate["reference"]["fn"],
        "candidate_coverage": "unchanged_from_frozen_entity_time_graph",
        "cohorts": comparisons, "pair_and_group": aggregate,
        "per_organization_pseudonymous": per_org,
        "acceptance_gates": gate_results,
        "accepted_over_reference": all(gate_results.values()),
        "resource": freeze["resource"],
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "limits": ["GUIDE_Test labels previously accessed; all comparisons exploratory",
                   "No GUIDE_Test labels used for this variant's fitting or parameter selection",
                   "Historical method design informed by prior GUIDE analyses",
                   "Entity/time point-in-time availability and operational approval unresolved"]}
    write_json(public / "metrics.json", result)
    write_json(public / "run_manifest.json", {
        "classification": result["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p)
                   for p in (Path(__file__), CONFIG, freeze_path, public / "metrics.json")},
        "private_prediction_sha256": freeze["prediction_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete",
                      "accepted_over_reference": result["accepted_over_reference"],
                      "gates": gate_results,
                      "reference_recall20": reference["recall20"]["mean"],
                      "fragment_recall20": var_metric["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_fragment_aware_v1_20261115_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": lambda: predict(args.run_id),
     "evaluate": lambda: evaluate(args.run_id)}[args.stage]()


if __name__ == "__main__":
    main()
