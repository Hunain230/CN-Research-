"""Separate label-side evaluator for frozen Phase 9G pair-scorer predictions."""

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
from src.submission_fragment_aware_v1 import incident_outcomes
from src.submission_group_merge_v10_v2 import pair_group_metrics
from src.phase9g_pair_boundary_v1 import (RUN, CONFIG, V2_RUN, V7_RUN,
    config, verify_freezes)


def recoverable_set(groups, keys, truth, ranks):
    sizes = Counter(truth[a] for a in keys)
    result = set()
    for group in groups:
        membership = Counter(truth[a] for a in group)
        for gold, overlap in membership.items():
            if gold in ranks and overlap / sizes[gold] >= .8 and overlap / len(group) >= .8:
                result.add(gold)
    return result


def synthetic_test():
    groups = [["a", "b"], ["c"], ["d"]]
    truth = {"a": "x", "b": "x", "c": "x", "d": "y"}
    assert recoverable_set(groups, list(truth), truth, {"x": 1, "y": 2}) == {"y"}
    assert recoverable_set([["a", "b", "c"], ["d"]], list(truth), truth, {"x": 1, "y": 2}) == {"x", "y"}
    print(json.dumps({"status": "pass", "synthetic_checks": 2}))


def evaluate() -> None:
    c = config()
    verify_freezes()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    out = public / "metrics.json"
    if out.exists():
        raise FileExistsError("Phase 9G metrics already frozen")
    freeze_path = public / "prediction_freeze.json"
    fit_path = public / "fit_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    fit = json.loads(fit_path.read_text())
    model_path = private / "boundary_pair_model.pkl"
    if (freeze["fit_freeze_sha256"] != sha256_file(fit_path) or
            freeze["source_sha256"] != sha256_file(ROOT / "src/phase9g_pair_boundary_v1.py") or
            freeze["config_sha256"] != sha256_file(CONFIG) or
            freeze["evaluation_labels_read"] or
            fit["model_sha256"] != sha256_file(model_path)):
        raise ValueError("Phase 9G prediction lineage changed")
    v2f = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    v7f = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    if len(orgs) != 499 or len(freeze["prediction_sha256"]) != 499:
        raise ValueError("Evaluation scope changed")
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    rows = {}
    gained = lost = 0
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    for number, org in enumerate(orgs, 1):
        name = key(org)
        paths = [
            (private / f"prediction_{name}.pkl", freeze["prediction_sha256"][name]),
            (ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl", v2f["prediction_sha256"][name]),
            (ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl", v7f["score_sha256"][name]),
        ]
        if any(sha256_file(path) != expected for path, expected in paths):
            raise ValueError("Matched per-queue prediction changed")
        with paths[0][0].open("rb") as stream: proposed = pickle.load(stream)
        with paths[1][0].open("rb") as stream: baseline = pickle.load(stream)
        with paths[2][0].open("rb") as stream: base_scores = pickle.load(stream)
        keys = baseline["input_alert_keys"]
        if (keys != proposed["input_alert_keys"] or
                proposed["candidate_pairs"] != baseline["candidate_pairs"] or
                len(proposed["groups"]) != len(proposed["scores"])):
            raise ValueError("Matched alert/candidate/rank scope changed")
        item = {"split": split.get(org, "unassigned")}
        for name2, groups, scores in (
                ("reference", baseline["groups"], base_scores),
                ("proposed", proposed["groups"], proposed["scores"])):
            metric = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            # Connectivity is unchanged by this experiment. Only grouping outcomes are needed here.
            mixed = sum(len({truth[a] for a in group}) > 1 for group in groups)
            item[name2] = {**metric, "mixed_groups": mixed}
            if metric["recoverable"] != len(recoverable_set(groups, keys, truth, ranks[org])):
                raise AssertionError("Recoverability definition mismatch")
        before = recoverable_set(baseline["groups"], keys, truth, ranks[org])
        after = recoverable_set(proposed["groups"], keys, truth, ranks[org])
        gained += len(after - before)
        lost += len(before - after)
        rows[key(org)] = item
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Phase 9G evaluated {number}/499 queues", flush=True)
    def cohort(chosen):
        denominator = 20 * len(chosen)
        def summarize(method):
            items = [rows[key(org)][method] for org in chosen]
            tp = sum(item["tp"] for item in items)
            fp = sum(item["fp"] for item in items)
            fn = sum(item["fn"] for item in items)
            return {"organizations": len(chosen), "expert_top20_denominator": denominator,
                "group_recoverable": sum(item["recoverable"] for item in items),
                "group_recoverability": sum(item["recoverable"] for item in items) / denominator,
                "recall20": sum(item["recall20"] for item in items) / len(items),
                "p10": sum(item["p10"] for item in items) / len(items),
                "ndcg20": sum(item["ndcg20"] for item in items) / len(items),
                "pair_tp": tp, "pair_fp": fp, "pair_fn": fn,
                "pair_precision": tp / (tp + fp) if tp + fp else None,
                "pair_recall": tp / (tp + fn) if tp + fn else None,
                "mixed_groups": sum(item["mixed_groups"] for item in items),
                "predicted_groups": sum(item["groups"] for item in items)}
        return {"reference": summarize("reference"), "proposed": summarize("proposed")}
    cohorts = {"all_499_exploratory": cohort(orgs),
               "outside_fitting_135_exploratory": cohort([o for o in orgs if split.get(o) in ("validation", "holdout")]),
               "holdout_68_previously_exposed": cohort([o for o in orgs if split.get(o) == "holdout"]),
               "training_334_in_sample": cohort([o for o in orgs if split.get(o) == "train"])}
    full = cohorts["all_499_exploratory"]
    disjoint = cohorts["outside_fitting_135_exploratory"]
    b, p = full["reference"], full["proposed"]
    bd, pd = disjoint["reference"], disjoint["proposed"]
    if (b["group_recoverable"], b["pair_tp"], b["pair_fp"], b["mixed_groups"],
            round(b["recall20"], 6), round(b["p10"], 6)) != (6969, 269832, 28606, 4841, round(4972/9980, 6), round(.6158316633266533, 6)):
        raise ValueError("Frozen v2+v7 reference did not reproduce")
    if gained - lost != p["group_recoverable"] - b["group_recoverable"]:
        raise AssertionError("Recovery changes do not reconcile")
    a = c["acceptance"]
    gates = {
        "disjoint_recoverability_gain": pd["group_recoverable"] - bd["group_recoverable"] >= a["minimum_disjoint_recoverability_gain"],
        "disjoint_recall20_gain": pd["recall20"] - bd["recall20"] > a["minimum_disjoint_recall20_gain"],
        "disjoint_no_added_false_pairs": pd["pair_fp"] - bd["pair_fp"] <= a["maximum_disjoint_added_false_positive_grouped_pairs"],
        "disjoint_no_added_mixed_groups": pd["mixed_groups"] - bd["mixed_groups"] <= a["maximum_disjoint_added_mixed_groups"],
        "disjoint_precision_not_below_matched_baseline": pd["pair_precision"] >= bd["pair_precision"],
        "disjoint_p10_not_lower": pd["p10"] - bd["p10"] >= a["minimum_disjoint_p10_change"],
        "all499_precision_at_least_90_4148_percent": p["pair_precision"] >= .9041475951453903,
        "all499_no_added_false_pairs": p["pair_fp"] <= b["pair_fp"],
        "all499_no_added_mixed_groups": p["mixed_groups"] <= b["mixed_groups"],
        "all499_p10_not_lower": p["p10"] >= b["p10"],
    }
    result = {"classification": "retrospective_exploratory_GUIDE_Test_not_independent_confirmation",
        "run": RUN, "cohorts": cohorts,
        "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
        "gates": gates, "gained_complete_pure_labels_all499": gained,
        "lost_complete_pure_labels_all499": lost,
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "model_sha256": sha256_file(model_path),
        "per_organization_pseudonymous": rows,
        "resource": {"fit": fit["resource"], "predict": freeze["resource"],
                     "evaluation_wall_seconds": time.perf_counter()-started,
                     "evaluation_peak_process_rss_bytes": peak},
        "limitations": ["GUIDE_Test labels previously accessed", "Historical validation used in earlier v7 blend selection",
                        "No new untouched cohort", "No approved operational evidence timing/field policy",
                        "One fixed model and fixed 0.75 threshold; no post-evaluation selection"]}
    write_json(out, result)
    print(json.dumps({"status": "evaluated", "decision": result["decision"],
                      "all499": full, "outside_fitting_135": disjoint, "gates": gates}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "evaluate"))
    {"self-test": synthetic_test, "evaluate": evaluate}[parser.parse_args().stage]()


if __name__ == "__main__":
    main()
