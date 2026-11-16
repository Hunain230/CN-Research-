"""Evaluator-only comparison for the frozen consensus-split predictions."""

from __future__ import annotations

import json
import pickle
import time
from collections import Counter

import psutil

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_group_merge_v10_v2 import pair_group_metrics
from src.sprint_consensus_split_v1 import RUN, CONFIG, V2, V7, G


def evaluate():
    public = ROOT / "outputs" / RUN
    private = ROOT / "data/derived" / RUN
    out = public / "metrics.json"
    if out.exists():
        raise FileExistsError("Metrics already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    if freeze["source_sha256"] != sha256_file(ROOT / "src/sprint_consensus_split_v1.py") or \
       freeze["config_sha256"] != sha256_file(CONFIG) or freeze["evaluation_labels_read"]:
        raise ValueError("Prediction lineage changed")
    for name, run in (("v2", V2), ("v7", V7), ("phase9g", G)):
        field = name + "_prediction_freeze_sha256"
        if freeze[field] != sha256_file(ROOT / "outputs" / run / "prediction_freeze.json"):
            raise ValueError("Frozen comparator changed")
    v2f = json.loads((ROOT / "outputs" / V2 / "prediction_freeze.json").read_text())
    v7f = json.loads((ROOT / "outputs" / V7 / "prediction_freeze.json").read_text())
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499 or len(freeze["prediction_sha256"]) != 499:
        raise ValueError("Evaluation scope changed")
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    started = time.perf_counter()
    process = psutil.Process()
    peak = process.memory_info().rss
    rows = {}
    for number, org in enumerate(orgs, 1):
        name = key(org)
        paths = ((private / f"prediction_{name}.pkl", freeze["prediction_sha256"][name]),
                 (ROOT / "data/derived" / V2 / f"v2_{name}.pkl", v2f["prediction_sha256"][name]),
                 (ROOT / "data/derived" / V7 / f"scores_{name}.pkl", v7f["score_sha256"][name]))
        if any(sha256_file(path) != expected for path, expected in paths):
            raise ValueError("Matched prediction hash changed")
        with paths[0][0].open("rb") as stream: proposed = pickle.load(stream)
        with paths[1][0].open("rb") as stream: reference = pickle.load(stream)
        with paths[2][0].open("rb") as stream: scores = pickle.load(stream)
        keys = reference["input_alert_keys"]
        if keys != proposed["input_alert_keys"] or reference["candidate_pairs"] != proposed["candidate_pairs"]:
            raise ValueError("Matched alert/candidate scope changed")
        row = {"split": split.get(org, "unassigned")}
        for method, groups, rankscores in (("reference", reference["groups"], scores),
                                           ("proposed", proposed["groups"], proposed["scores"])):
            metric = pair_group_metrics(groups, rankscores, keys, truth, ranks[org])
            metric["mixed_groups"] = sum(len({truth[a] for a in group}) > 1 for group in groups)
            row[method] = metric
        rows[name] = row
        peak = max(peak, process.memory_info().rss)
        if number % 50 == 0:
            print(f"Consensus split evaluated {number}/499", flush=True)

    def cohort(chosen):
        result = {}
        for method in ("reference", "proposed"):
            items = [rows[key(org)][method] for org in chosen]
            tp, fp, fn = (sum(item[field] for item in items) for field in ("tp", "fp", "fn"))
            result[method] = {"organizations": len(chosen), "expert_top20_denominator": 20*len(chosen),
                "group_recoverable": sum(item["recoverable"] for item in items),
                "group_recoverability": sum(item["recoverable"] for item in items)/(20*len(chosen)),
                "recall20": sum(item["recall20"] for item in items)/len(chosen),
                "p10": sum(item["p10"] for item in items)/len(chosen),
                "ndcg20": sum(item["ndcg20"] for item in items)/len(chosen),
                "pair_tp": tp, "pair_fp": fp, "pair_fn": fn,
                "pair_precision": tp/(tp+fp) if tp+fp else None,
                "pair_recall": tp/(tp+fn) if tp+fn else None,
                "mixed_groups": sum(item["mixed_groups"] for item in items),
                "predicted_groups": sum(item["groups"] for item in items)}
        return result

    cohorts = {"all_499_exploratory": cohort(orgs),
               "outside_fitting_135_exploratory": cohort([o for o in orgs if split.get(o) in ("validation", "holdout")]),
               "holdout_68_previously_exposed": cohort([o for o in orgs if split.get(o) == "holdout"])}
    base, proposed = cohorts["all_499_exploratory"].values()
    if (base["group_recoverable"], base["pair_tp"], base["pair_fp"], base["mixed_groups"],
        round(base["recall20"], 6), round(base["p10"], 6)) != (6969, 269832, 28606, 4841,
                                                              round(4972/9980, 6), round(.6158316633266533, 6)):
        raise ValueError("Frozen baseline not reproduced")
    acceptance = json.loads(CONFIG.read_text())["acceptance"]
    gates = {
        "recoverability_gain": proposed["group_recoverable"]-base["group_recoverable"] >= acceptance["minimum_all499_group_recoverability_gain"],
        "recall20_gain": proposed["recall20"]-base["recall20"] > acceptance["minimum_all499_recall20_gain"],
        "no_added_false_pairs": proposed["pair_fp"]-base["pair_fp"] <= acceptance["maximum_added_false_grouped_pairs"],
        "no_added_mixed_groups": proposed["mixed_groups"]-base["mixed_groups"] <= acceptance["maximum_added_mixed_groups"],
        "pair_precision": proposed["pair_precision"] >= acceptance["minimum_pair_precision"],
        "p10": proposed["p10"] >= acceptance["minimum_p10"]}
    result = {"run": RUN, "classification": "retrospective_exploratory_GUIDE_Test_not_independent_confirmation",
              "cohorts": cohorts, "gates": gates,
              "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
              "per_organization_pseudonymous": rows,
              "prediction_freeze_sha256": sha256_file(freeze_path),
              "resource": {"predict": freeze["resource"], "evaluation_wall_seconds": time.perf_counter()-started,
                           "evaluation_peak_process_rss_bytes": peak}}
    write_json(out, result)
    print(json.dumps({"status": "evaluated", "decision": result["decision"],
                      "all499": cohorts["all_499_exploratory"], "gates": gates}))


if __name__ == "__main__":
    evaluate()
