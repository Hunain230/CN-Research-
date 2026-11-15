"""Separate retrospective evaluator for one frozen Phase 9C grouping rule."""

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
from src.phase9c_small_fragment_heuristic_v1 import (RUN, V2_RUN, V7_RUN,
                                                        CANDIDATE_RUN, CONFIG, config,
                                                        verify_freezes)


def recoverable_set(groups: list[list[str]], keys: list[str], truth: dict,
                    ranks: dict) -> set[str]:
    sizes = Counter(truth[a] for a in keys)
    result = set()
    for group in groups:
        count = Counter(truth[a] for a in group)
        for gold, hit in count.items():
            if gold in ranks and hit / sizes[gold] >= .8 and hit / len(group) >= .8:
                result.add(gold)
    return result


def count_false_merge_pairs(groups: list[list[str]], selected: list[tuple[int, int]],
                            truth: dict) -> tuple[int, int]:
    bad_decisions = added_fp = 0
    for left, right in selected:
        mismatch = sum(truth[a] != truth[b] for a in groups[left] for b in groups[right])
        added_fp += mismatch
        bad_decisions += mismatch > 0
    return bad_decisions, added_fp


def self_test() -> None:
    groups = [["a", "b"], ["c"], ["d"]]
    truth = {"a": "x", "b": "x", "c": "x", "d": "y"}
    ranks = {"x": 1, "y": 2}
    assert recoverable_set(groups, list(truth), truth, ranks) == {"y"}
    assert count_false_merge_pairs(groups, [(0, 1)], truth) == (0, 0)
    assert count_false_merge_pairs(groups, [(0, 2)], truth) == (1, 2)
    print(json.dumps({"status": "pass", "synthetic_assertions": 3}))


def evaluate() -> None:
    cfg = config()
    frozen = verify_freezes()
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    output = public / "metrics.json"
    if output.exists():
        raise FileExistsError("Versioned metrics already exist")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (freeze["config_sha256"] != sha256_file(CONFIG) or
            freeze["frozen_parent_sha256"] != frozen or
            freeze["code_sha256"] != sha256_file(ROOT / "src/phase9c_small_fragment_heuristic_v1.py") or
            freeze["evaluator_labels_read"]):
        raise ValueError("Prediction freeze or source changed")
    v2_freeze = json.loads((ROOT / f"outputs/{V2_RUN}/prediction_freeze.json").read_text())
    v7_freeze = json.loads((ROOT / f"outputs/{V7_RUN}/prediction_freeze.json").read_text())
    candidate_freeze = json.loads((ROOT / f"outputs/{CANDIDATE_RUN}/prediction_freeze.json").read_text())
    orgs = sorted(json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text()))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499 or len(freeze["prediction_sha256"]) != 499:
        raise ValueError("Queue scope changed")
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    totals = {"reference": Counter(), "proposed": Counter()}
    per_org = {}
    bad_merge_decisions = cross_false_pairs = gained = lost = 0
    start = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    for index, org in enumerate(orgs, 1):
        name = key(org)
        paths = (
            (private / f"groups_{name}.pkl", freeze["prediction_sha256"][name]),
            (ROOT / "data/derived" / V2_RUN / f"v2_{name}.pkl", v2_freeze["prediction_sha256"][name]),
            (ROOT / "data/derived" / V7_RUN / f"scores_{name}.pkl", v7_freeze["score_sha256"][name]),
            (ROOT / "data/derived" / CANDIDATE_RUN / f"{name}.pkl", candidate_freeze["prediction_sha256"][name]),
        )
        if any(sha256_file(path) != expected for path, expected in paths):
            raise ValueError("Prediction or parent hash changed")
        with paths[0][0].open("rb") as stream:
            variant = pickle.load(stream)
        with paths[1][0].open("rb") as stream:
            base = pickle.load(stream)
        with paths[2][0].open("rb") as stream:
            base_scores = pickle.load(stream)
        with paths[3][0].open("rb") as stream:
            candidate = pickle.load(stream)
        keys = base["input_alert_keys"]
        if (variant["input_alert_keys"] != keys or candidate["input_alert_keys"] != keys or
                len(candidate["candidate_edges"]) != base["candidate_pairs"] or
                variant["candidate_pairs"] != base["candidate_pairs"]):
            raise ValueError("Matched alert or candidate scope changed")
        connected = connected_incidents(keys, candidate["candidate_edges"], truth, ranks[org])
        entry = {"split": split.get(org, "unassigned")}
        for method, groups, scores in (("reference", base["groups"], base_scores),
                                       ("proposed", variant["groups"], variant["scores"])):
            metric = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            outcome = incident_outcomes(groups, keys, truth, ranks[org], connected)
            if metric["recoverable"] != outcome["recoverable"]:
                raise AssertionError("Recovery evaluator mismatch")
            entry[method] = {**metric, **outcome}
            totals[method].update({**metric, **outcome})
        before = recoverable_set(base["groups"], keys, truth, ranks[org])
        after = recoverable_set(variant["groups"], keys, truth, ranks[org])
        if len(before) != entry["reference"]["recoverable"] or len(after) != entry["proposed"]["recoverable"]:
            raise AssertionError("Recovery set mismatch")
        gained += len(after - before)
        lost += len(before - after)
        bad, added = count_false_merge_pairs(base["groups"],
                                              variant["selected_original_group_pairs"], truth)
        bad_merge_decisions += bad
        cross_false_pairs += added
        entry["bad_merge_decisions"] = bad
        entry["added_cross_false_pairs"] = added
        per_org[name] = entry
        peak = max(peak, process.memory_info().rss)
        if index % 50 == 0:
            print(f"Phase 9C evaluated {index}/499", flush=True)
    reference, proposed = totals["reference"], totals["proposed"]
    observed_reference = (reference["recoverable"], reference["fp"],
                          reference["mixed_predicted_groups"],
                          round(reference["recall20"], 5))
    if observed_reference != (6969, 28606, 4841, 248.6):
        raise ValueError(f"Frozen v2+v7 baseline did not reproduce: {observed_reference}")
    if proposed["fp"] - reference["fp"] != cross_false_pairs:
        raise AssertionError("Added false pairs do not match merge decisions")
    if gained - lost != proposed["recoverable"] - reference["recoverable"]:
        raise AssertionError("Recovery transitions do not reconcile")
    def summary(t: Counter) -> dict:
        return {"candidate_pairs": freeze["census"]["candidate_pairs"],
                "group_recoverable": t["recoverable"],
                "group_recoverability": t["recoverable"] / 9980,
                "recall20": t["recall20"] / 499,
                "p10": t["p10"] / 499,
                "ndcg20": t["ndcg20"] / 499,
                "pair_tp": t["tp"], "pair_fp": t["fp"], "pair_fn": t["fn"],
                "pair_precision": t["tp"] / (t["tp"] + t["fp"]),
                "mixed_predicted_groups": t["mixed_predicted_groups"],
                "incomplete_top20": t["incomplete"], "impure_top20": t["impure"],
                "groups": t["groups"]}
    base_summary, new_summary = summary(reference), summary(proposed)
    accept = cfg["acceptance"]
    gates = {
        "recoverability_gain": new_summary["group_recoverable"] > base_summary["group_recoverable"],
        "recall20_gain": new_summary["recall20"] > base_summary["recall20"],
        "pair_precision": new_summary["pair_precision"] >= accept["minimum_pair_precision"],
        "false_positive_pairs": new_summary["pair_fp"] - base_summary["pair_fp"] <= accept["maximum_added_false_positive_grouped_pairs"],
        "mixed_groups": new_summary["mixed_predicted_groups"] - base_summary["mixed_predicted_groups"] <= accept["maximum_added_mixed_groups"],
        "p10": new_summary["p10"] - base_summary["p10"] >= accept["minimum_p10_change"],
    }
    cohorts = {}
    for cohort, chosen in (("all_499_exploratory", orgs),
                           ("outside_fitting_135_exploratory", [o for o in orgs if split.get(o) in ("validation", "holdout")]),
                           ("holdout_68_previously_exposed", [o for o in orgs if split.get(o) == "holdout"])):
        cohorts[cohort] = {"organizations": len(chosen),
                           "denominator": 20 * len(chosen),
                           "reference_recall20": sum(per_org[key(o)]["reference"]["recall20"] for o in chosen) / len(chosen),
                           "proposed_recall20": sum(per_org[key(o)]["proposed"]["recall20"] for o in chosen) / len(chosen),
                           "reference_p10": sum(per_org[key(o)]["reference"]["p10"] for o in chosen) / len(chosen),
                           "proposed_p10": sum(per_org[key(o)]["proposed"]["p10"] for o in chosen) / len(chosen)}
    result = {
        "classification": "exploratory_post_exposure_guide_retrospective_not_operational",
        "run": RUN, "organizations": 499, "alerts": 400039, "expert_top20_denominator": 9980,
        "reference": base_summary, "proposed": new_summary,
        "gates": gates, "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
        "gained_complete_pure_labels": gained, "lost_complete_pure_labels": lost,
        "wrong_merge_decisions": bad_merge_decisions,
        "added_cross_false_pairs": cross_false_pairs,
        "selected_merges": freeze["census"]["selected_merges"],
        "single_edge_review": freeze["census"]["single_edge_review"],
        "budget_excluded": freeze["census"]["budget_excluded"],
        "cohorts": cohorts, "per_organization_pseudonymous": per_org,
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "resource": {"evaluation_wall_seconds": time.perf_counter() - start,
                     "evaluation_peak_rss_bytes": peak,
                     "prediction": freeze["resource"]},
        "limitations": ["Previously accessed GUIDE_Test labels", "No authoritative observation provenance or evidence-arrival time",
                        "Phase 7 proposal floor 0.40 excludes 429 historical small-incident cases",
                        "No independent confirmation cohort", "No model or threshold tuning in this experiment"],
    }
    write_json(output, result)
    print(json.dumps({"status": "evaluated", "decision": result["decision"],
                      "reference": base_summary, "proposed": new_summary,
                      "selected_merges": result["selected_merges"],
                      "wrong_merge_decisions": bad_merge_decisions}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "evaluate"))
    stage = parser.parse_args().stage
    {"self-test": self_test, "evaluate": evaluate}[stage]()


if __name__ == "__main__":
    main()
