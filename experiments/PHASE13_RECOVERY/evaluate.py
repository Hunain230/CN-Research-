"""Separate evaluator: opens GUIDE labels only after Phase 10 prediction freeze."""
from __future__ import annotations

import csv
import importlib.util
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import tie_aware_ranking
from src.submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from src.submission_group_merge_v10_v2 import pair_group_metrics

spec = importlib.util.spec_from_file_location("phase10_reconstruct", HERE / "reconstruct.py")
reconstruct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconstruct)


def recovered(groups, keys, truth, ranks):
    sizes = Counter(truth[a] for a in keys)
    result = set()
    for group in groups:
        counts = Counter(truth[a] for a in group)
        for incident, hits in counts.items():
            if incident in ranks and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                result.add(incident)
    return result


def evaluate():
    freeze_path = HERE / "predictions/prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    if freeze["stage"] != "predict" or freeze["evaluator_labels_read"] or len(freeze["prediction_sha256"]) != 499:
        raise ValueError("Full label-blind prediction freeze required")
    if freeze["config_sha256"] != sha256_file(HERE / "PHASE10_EXPERIMENT_CONFIG.json") or freeze["code_sha256"] != sha256_file(HERE / "reconstruct.py"):
        raise ValueError("Prediction source changed")
    reconstruct.verify_parents()
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499:
        raise ValueError("Queue denominator changed")
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    v2_freeze = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json").read_text())
    v7_freeze = json.loads((ROOT / "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json").read_text())
    blend_freeze = json.loads((ROOT / "outputs/sprint_rank_fusion_v1_20261116/prediction_freeze.json").read_text())
    candidate_freeze = json.loads((ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json").read_text())
    methods = ("E0", "E1", "E2", "E3", "E4", "E5")
    totals = {m: Counter() for m in methods}
    cohorts = {c: {m: Counter() for m in methods} for c in ("train", "validation", "holdout", "unassigned")}
    process = psutil.Process()
    start = time.perf_counter()
    peak = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        files = [
            (HERE / "predictions" / f"{name}.pkl", freeze["prediction_sha256"][name]),
            (ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1" / f"v2_{name}.pkl", v2_freeze["prediction_sha256"][name]),
            (ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1" / f"scores_{name}.pkl", v7_freeze["score_sha256"][name]),
            (ROOT / "data/derived/sprint_rank_fusion_v1_20261116" / f"scores_{name}.pkl", blend_freeze["score_sha256"][name]),
            (ROOT / "data/derived/submission_full_entity_time_20261114_v1" / f"{name}.pkl", candidate_freeze["prediction_sha256"][name]),
        ]
        if any(sha256_file(path) != expected for path, expected in files):
            raise ValueError("Frozen queue hash mismatch")
        items = []
        for path, _ in files:
            with path.open("rb") as stream:
                items.append(pickle.load(stream))
        proposed, base, v7, blend, candidate = items
        keys = base["input_alert_keys"]
        if proposed["input_alert_keys"] != keys or candidate["input_alert_keys"] != keys:
            raise ValueError("Alert scope changed")
        connected = connected_incidents(keys, candidate["candidate_edges"], truth, ranks[org])
        cases = {
            "E0": (base["groups"], v7, []),
            "E1": (base["groups"], blend["0.75"], []),
            "E2": (proposed["methods"]["E2"]["groups"], proposed["methods"]["E2"]["v7_scores"], proposed["methods"]["E2"]["decisions"]),
            "E3": (proposed["methods"]["E3"]["groups"], proposed["methods"]["E3"]["v7_scores"], proposed["methods"]["E3"]["decisions"]),
            "E4": (proposed["methods"]["E4"]["groups"], proposed["methods"]["E4"]["v7_scores"], proposed["methods"]["E4"]["decisions"]),
            "E5": (proposed["methods"]["E4"]["groups"], proposed["methods"]["E4"]["blend_scores"], proposed["methods"]["E4"]["decisions"]),
        }
        baseline_recovered = recovered(base["groups"], keys, truth, ranks[org])
        reference = None
        for method, (groups, scores, decisions) in cases.items():
            metric = pair_group_metrics(groups, scores, keys, truth, ranks[org])
            outcome = incident_outcomes(groups, keys, truth, ranks[org], connected)
            if metric["recoverable"] != outcome["recoverable"]:
                raise AssertionError("Recovery evaluators disagree")
            accepted = [d for d in decisions if d["decision"] == "accepted"]
            bad = 0
            for d in accepted:
                a, b = d["fragments"]
                if any(truth[x] != truth[y] for x in base["groups"][a] for y in base["groups"][b]):
                    bad += 1
            rec = recovered(groups, keys, truth, ranks[org])
            additional_alerts = sum(1 for alert in keys if truth[alert] in rec - baseline_recovered)
            record = Counter({**metric, **outcome})
            record.update({"reconstructed_incidents": len(accepted), "additional_correctly_recovered_alerts": additional_alerts,
                "incorrect_cross_incident_merges": bad, "rejected_fragment_merges": len(decisions)-len(accepted),
                "oversized_components": sum(len(g)>100 for g in groups)})
            if method == "E0":
                reference = record
            if method == "E1" and (record["recoverable"], record["fp"], record["mixed_predicted_groups"]) != (reference["recoverable"], reference["fp"], reference["mixed_predicted_groups"]):
                raise AssertionError("Baseline ranking changed groups")
            totals[method].update(record)
            cohorts[split.get(org, "unassigned")][method].update(record)
        peak = max(peak, process.memory_info().rss)
        if number % 25 == 0:
            print(f"Phase10 evaluated {number}/499", flush=True)
    if (totals["E0"]["recoverable"], totals["E0"]["fp"], totals["E0"]["mixed_predicted_groups"], round(totals["E0"]["recall20"] / 499, 5)) != (6969, 28606, 4841, round(4972/9980,5)):
        raise ValueError("E0 frozen baseline did not reproduce")
    if round(totals["E1"]["recall20"] / 499, 5) != round(0.5076653306613226, 5):
        raise ValueError("E1 selected blend did not reproduce")
    def summary(t, queues):
        succeeded = round(t["recall20"] * 20)
        return {"queues": queues, "expert_top20_denominator": queues*20,
            "incident_recall20_count": succeeded, "incident_recall20": t["recall20"]/queues,
            "group_recoverability_count": t["recoverable"], "group_recoverability": t["recoverable"]/(queues*20),
            "p10": t["p10"]/queues, "ndcg20": t["ndcg20"]/queues,
            "grouped_pair_precision": t["tp"]/(t["tp"]+t["fp"]), "grouped_pair_tp": t["tp"],
            "false_grouped_pairs": t["fp"], "mixed_predicted_groups": t["mixed_predicted_groups"],
            "reconstructed_incidents": t["reconstructed_incidents"],
            "additional_correctly_recovered_alerts": t["additional_correctly_recovered_alerts"],
            "incorrect_cross_incident_merges": t["incorrect_cross_incident_merges"],
            "rejected_fragment_merges": t["rejected_fragment_merges"], "oversized_components": t["oversized_components"],
            "predicted_groups": t["groups"], "error_cascade": {
                "outside_unambiguous_alert_scope": t["absent"], "candidate_disconnected": t["candidate_disconnected"],
                "candidate_connected_incomplete": t["incomplete"], "complete_but_impure": t["impure"],
                "recoverable_ranked_below20": t["recoverable"]-succeeded, "successfully_recovered": succeeded}}
    results = {m: summary(totals[m], 499) for m in methods}
    subgroup = {c: {m: summary(value, {"train":334,"validation":67,"holdout":68,"unassigned":30}[c]) for m,value in rows.items()} for c,rows in cohorts.items()}
    output = {"classification":"retrospective_exploratory_not_independent_confirmation", "prediction_freeze_sha256":sha256_file(freeze_path),
        "methods":results, "cohorts":subgroup, "evaluation_resource":{"wall_seconds":time.perf_counter()-start,
        "peak_process_rss_bytes":peak}, "prediction_resource":freeze["resource"]}
    (HERE / "PHASE10_EVALUATION.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    with (HERE / "PHASE10_METRICS_COMPARISON.csv").open("w", newline="", encoding="utf-8") as stream:
        cols = ["experiment"] + [k for k in results["E0"] if k != "error_cascade"] + list(results["E0"]["error_cascade"]) + ["shared_batch_prediction_seconds", "shared_batch_evaluation_seconds", "shared_batch_peak_rss_bytes"]
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        for method, row in results.items():
            writer.writerow({"experiment":method, **{k:v for k,v in row.items() if k != "error_cascade"}, **row["error_cascade"],
                "shared_batch_prediction_seconds": freeze["resource"]["wall_seconds"] if method in ("E2","E3","E4","E5") else "historical_frozen_artifact",
                "shared_batch_evaluation_seconds": output["evaluation_resource"]["wall_seconds"],
                "shared_batch_peak_rss_bytes": max(peak, freeze["resource"]["peak_process_rss_bytes"])})
    print(json.dumps({"status":"evaluated", "methods":results}, indent=2))


if __name__ == "__main__":
    evaluate()
