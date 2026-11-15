"""Label-side preflight and matched evaluation of frozen Phase 9E predictions."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import psutil

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from src.submission_group_merge_v10_v2 import pair_group_metrics
from src.phase9e_bounded_candidate_v1 import (CONFIG, RUN, V2_RUN, V7_RUN,
    CANDIDATE_RUN, config, verify_frozen)


def inputs():
    verify_frozen()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    candidate_freeze_path = public / "candidate_freeze.json"
    prediction_freeze_path = public / "prediction_freeze.json"
    cf = json.loads(candidate_freeze_path.read_text())
    pf = json.loads(prediction_freeze_path.read_text())
    if (cf["config_sha256"] != sha256_file(CONFIG) or
            pf["candidate_freeze_sha256"] != sha256_file(candidate_freeze_path) or
            pf["config_sha256"] != sha256_file(CONFIG) or
            pf["source_sha256"] != sha256_file(ROOT / "src/phase9e_bounded_candidate_v1.py") or
            cf["evaluation_labels_read"] or pf["evaluation_labels_read"] or
            len(cf["candidate_sha256"]) != 499 or len(pf["prediction_sha256"]) != 499):
        raise ValueError("Prediction or candidate freeze changed")
    gf = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    rf = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    old_cf = json.loads((ROOT / f"outputs/{CANDIDATE_RUN}/prediction_freeze.json").read_text())
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499:
        raise ValueError("Ranked scope changed")
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    return public, private, cf, pf, gf, rf, old_cf, orgs, truth, ranks, split


def queue_files(org, private, cf, pf, gf, rf, old_cf):
    name = key(org)
    files = [
        (private / f"candidates_{name}.pkl", cf["candidate_sha256"][name]),
        (private / f"prediction_{name}.pkl", pf["prediction_sha256"][name]),
        (ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl", gf["prediction_sha256"][name]),
        (ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl", rf["score_sha256"][name]),
        (ROOT / "data/derived" / CANDIDATE_RUN / f"{name}.pkl", old_cf["prediction_sha256"][name]),
    ]
    if any(sha256_file(path) != expected for path, expected in files):
        raise ValueError("Per-queue frozen file changed")
    result = []
    for path, _ in files:
        with path.open("rb") as stream:
            result.append(pickle.load(stream))
    return result


def preflight() -> None:
    public, private, cf, pf, gf, rf, old_cf, orgs, truth, _, _ = inputs()
    out = public / "negative_pair_preflight.json"
    if out.exists():
        raise FileExistsError("Preflight already exists")
    counts = Counter()
    started = time.perf_counter()
    for org in orgs:
        added, predicted, base, _, frozen = queue_files(org, private, cf, pf, gf, rf, old_cf)
        keys = base["input_alert_keys"]
        n = len(keys)
        if (keys != added["input_alert_keys"] or keys != predicted["input_alert_keys"] or
                keys != frozen["input_alert_keys"] or
                predicted["candidate_pairs"] != len(frozen["candidate_edges"]) + len(added["added_edges"])):
            raise ValueError("Candidate alignment changed")
        limit = min(config()["max_new_edges_per_queue"],
                    int(len(frozen["candidate_edges"]) * config()["max_new_edges_fraction_of_original_queue"]))
        if len(added["added_edges"]) > limit or added["counts"]["added_pairs"] != len(added["added_edges"]):
            raise ValueError("Candidate budget exceeded")
        group_of = {a: i for i, group in enumerate(base["groups"]) for a in group}
        for edge, score in zip(added["added_edges"], predicted["added_edge_scores"]):
            a, b = divmod(int(edge), n)
            left, right = keys[a], keys[b]
            positive = truth[left] == truth[right]
            counts["positive" if positive else "negative"] += 1
            counts["cross_existing_group"] += group_of[left] != group_of[right]
            if score >= config()["pair_threshold"]:
                counts["high_score_positive" if positive else "high_score_negative"] += 1
        counts["queues"] += 1
        counts["raw_sixth_neighbor_pairs"] += added["counts"]["raw_sixth_neighbor_pairs"]
        counts["budget_excluded"] += added["counts"]["budget_excluded"]
    if counts["queues"] != 499 or counts["positive"] + counts["negative"] != pf["census"]["added_pairs"]:
        raise ValueError("Preflight candidate totals did not reconcile")
    write_json(out, {"classification": "exploratory_post_prediction_label_side_collision_audit",
                     "run": RUN, "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
                     "counts": dict(counts),
                     "added_candidate_positive_fraction": counts["positive"] / (counts["positive"] + counts["negative"]) if counts["positive"] + counts["negative"] else None,
                     "wall_seconds": time.perf_counter() - started,
                     "note": "This audit does not select another budget or threshold; final grouping safety gate is evaluated separately."})
    print(json.dumps({"status": "preflight_frozen", "counts": dict(counts)}))


def recoverable_set(groups, keys, truth, ranks):
    sizes = Counter(truth[a] for a in keys)
    output = set()
    for group in groups:
        member = Counter(truth[a] for a in group)
        for gold, count in member.items():
            if gold in ranks and count / sizes[gold] >= .8 and count / len(group) >= .8:
                output.add(gold)
    return output


def evaluate() -> None:
    public, private, cf, pf, gf, rf, old_cf, orgs, truth, ranks, split = inputs()
    out = public / "metrics.json"
    if out.exists():
        raise FileExistsError("Metrics already exist")
    pre = json.loads((public / "negative_pair_preflight.json").read_text())
    if pre["prediction_freeze_sha256"] != sha256_file(public / "prediction_freeze.json") or pre["counts"]["queues"] != 499:
        raise ValueError("Preflight did not complete for frozen predictions")
    total = {"reference": Counter(), "proposed": Counter()}
    per_org = {}
    candidate_positive_before = candidate_positive_after = 0
    gained = lost = 0
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    for index, org in enumerate(orgs, 1):
        added, pred, base, base_scores, frozen = queue_files(org, private, cf, pf, gf, rf, old_cf)
        keys = base["input_alert_keys"]
        n = len(keys)
        old_edges = frozen["candidate_edges"]
        new_edges = added["added_edges"]
        candidate_positive_before += sum(truth[keys[int(e // n)]] == truth[keys[int(e % n)]] for e in old_edges)
        candidate_positive_after += sum(truth[keys[int(e // n)]] == truth[keys[int(e % n)]] for e in new_edges)
        # Original graph and expanded graph are assessed separately, using labels only here.
        old_connected = connected_incidents(keys, old_edges, truth, ranks[org])
        import numpy as np
        new_connected = connected_incidents(keys, np.concatenate((old_edges, new_edges)), truth, ranks[org])
        row = {"split": split.get(org, "unassigned")}
        for name, groups, scores, connected in (
                ("reference", base["groups"], base_scores, old_connected),
                ("proposed", pred["groups"], pred["scores"], new_connected)):
            metrics = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            outcome = incident_outcomes(groups, keys, truth, ranks[org], connected)
            if metrics["recoverable"] != outcome["recoverable"]:
                raise AssertionError("Grouping evaluator disagreement")
            row[name] = {**metrics, **outcome}
            total[name].update(row[name])
        before = recoverable_set(base["groups"], keys, truth, ranks[org])
        after = recoverable_set(pred["groups"], keys, truth, ranks[org])
        gained += len(after - before)
        lost += len(before - after)
        per_org[key(org)] = row
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Phase 9E evaluated {index}/499", flush=True)
    old, new = total["reference"], total["proposed"]
    if (old["recoverable"], old["fp"], old["mixed_predicted_groups"], round(old["recall20"], 5)) != (6969, 28606, 4841, 248.6):
        raise ValueError("Frozen baseline metrics did not reproduce")
    if candidate_positive_before != 699790 or candidate_positive_after != pre["counts"]["positive"]:
        raise ValueError("Candidate positive totals did not reconcile")
    if gained - lost != new["recoverable"] - old["recoverable"]:
        raise AssertionError("Recoverability transitions did not reconcile")
    def summary(t, pairs, positives):
        return {"candidate_pairs": pairs, "candidate_positive_pairs": positives,
                "candidate_positive_pair_recall": positives / 159186107,
                "group_recoverable": t["recoverable"], "group_recoverability": t["recoverable"] / 9980,
                "recall20": t["recall20"] / 499, "p10": t["p10"] / 499,
                "ndcg20": t["ndcg20"] / 499, "pair_tp": t["tp"], "pair_fp": t["fp"],
                "pair_fn": t["fn"], "pair_precision": t["tp"] / (t["tp"] + t["fp"]),
                "mixed_predicted_groups": t["mixed_predicted_groups"],
                "incomplete_top20": t["incomplete"], "impure_top20": t["impure"],
                "candidate_connected_top20": 9980 - t["absent"] - t["candidate_disconnected"],
                "groups": t["groups"]}
    before = summary(old, 1942648, candidate_positive_before)
    after = summary(new, pf["census"]["candidate_pairs"], candidate_positive_before + candidate_positive_after)
    safety = config()["safety"]
    gates = {
        "group_recoverability_gain": after["group_recoverable"] - before["group_recoverable"] >= safety["minimum_group_recoverability_gain"],
        "recall20_gain": after["recall20"] - before["recall20"] > safety["minimum_recall20_gain"],
        "false_positive_grouped_pairs": after["pair_fp"] - before["pair_fp"] <= safety["maximum_added_false_positive_grouped_pairs"],
        "mixed_groups": after["mixed_predicted_groups"] - before["mixed_predicted_groups"] <= safety["maximum_added_mixed_groups"],
        "pair_precision": after["pair_precision"] >= safety["minimum_pair_precision"],
        "p10": after["p10"] - before["p10"] >= safety["minimum_p10_change"],
    }
    cohorts = {}
    for cohort, selected in (
            ("all_499_exploratory", orgs),
            ("outside_fitting_135_exploratory", [o for o in orgs if split.get(o) in ("validation", "holdout")])):
        cohorts[cohort] = {"queues": len(selected), "expert_top20_denominator": 20 * len(selected),
            "reference_recall20": sum(per_org[key(o)]["reference"]["recall20"] for o in selected) / len(selected),
            "proposed_recall20": sum(per_org[key(o)]["proposed"]["recall20"] for o in selected) / len(selected)}
    write_json(out, {"classification": "exploratory_post_exposure_GUIDE_Test_not_confirmatory",
        "run": RUN, "reference": before, "proposed": after,
        "gained_complete_pure_labels": gained, "lost_complete_pure_labels": lost,
        "gates": gates, "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
        "cohorts": cohorts, "per_organization_pseudonymous": per_org,
        "negative_pair_preflight_sha256": sha256_file(public / "negative_pair_preflight.json"),
        "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
        "resource": {"candidate_generation": cf["resource"], "prediction": pf["resource"],
                     "evaluation_wall_seconds": time.perf_counter() - started,
                     "evaluation_peak_rss_bytes": peak},
        "limits": ["Previously accessed GUIDE_Test labels", "No point-in-time provenance approval",
                   "No independent confirmation cohort", "One fixed candidate budget, no post-evaluation tuning"]})
    print(json.dumps({"status": "evaluated", "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
                      "reference": before, "proposed": after}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("preflight", "evaluate"))
    {"preflight": preflight, "evaluate": evaluate}[parser.parse_args().stage]()


if __name__ == "__main__":
    main()
