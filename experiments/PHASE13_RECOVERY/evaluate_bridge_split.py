"""Evaluator-only exact C metrics and paired recovery for label-blind bridge split."""
from __future__ import annotations

import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from src.submission_full_entity_time import PARENT
from evaluate_c_sensitivity import group_counts
from compare_c_status import recoverable


def main():
    target = HERE / "PHASE13_BRIDGE_EVALUATION.json"
    if target.exists():
        raise FileExistsError("Refusing overwrite")
    frozen = json.loads((HERE / "bridge_predictions/prediction_freeze.json").read_text())
    if frozen["sample"] or frozen["evaluator_labels_read"] or len(frozen["prediction_sha256"]) != 499:
        raise ValueError("Full label-blind bridge freeze required")
    if frozen["code_sha256"] != sha256_file(HERE / "run_bridge_split.py"):
        raise ValueError("Bridge predictor changed")
    source = json.loads((HERE / "c_predictions/prediction_freeze.json").read_text())
    if frozen["base_prediction_freeze_sha256"] != sha256_file(HERE / "c_predictions/prediction_freeze.json"):
        raise ValueError("C source freeze changed")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for row in parent.values() for a in row["input_alert_keys"]})
    ranks = labels(set(orgs))
    totals = Counter()
    started, process = time.perf_counter(), psutil.Process()
    peak = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        base_path = HERE / "c_predictions" / f"{name}.pkl"
        bridge_path = HERE / "bridge_predictions" / f"{name}.pkl"
        if sha256_file(base_path) != source["prediction_sha256"][name] or sha256_file(bridge_path) != frozen["prediction_sha256"][name]:
            raise ValueError("Prediction file hash changed")
        with base_path.open("rb") as stream: base = pickle.load(stream)
        with bridge_path.open("rb") as stream: bridge = pickle.load(stream)
        keys, groups = bridge["keys"], bridge["groups"]
        if keys != base["keys"]:
            raise ValueError("Alert scope changed")
        connected = connected_incidents(keys, base["edges"], truth, ranks[org])
        outcome = incident_outcomes(groups, keys, truth, ranks[org], connected)
        tp, fp, mixed = group_counts(groups, truth)
        base_rec = recoverable(base["groups"]["0.75"], keys, truth, ranks[org])
        new_rec = recoverable(groups, keys, truth, ranks[org])
        gained, lost = new_rec-base_rec, base_rec-new_rec
        totals.update(tp=tp, fp=fp, mixed=mixed, groups=len(groups),
                      oversized=sum(len(g)>100 for g in groups), bridges_cut=bridge["bridges_cut"],
                      newly_recoverable=len(gained), lost_recoverability=len(lost),
                      gained_alerts=sum(truth[a] in gained for a in keys),
                      lost_alerts=sum(truth[a] in lost for a in keys),
                      **{k: outcome[k] for k in ("absent", "candidate_disconnected", "incomplete", "impure", "recoverable")})
        peak = max(peak, process.memory_info().rss)
        if number % 25 == 0:
            print(f"Bridge evaluated {number}/499", flush=True)
    if totals["bridges_cut"] != frozen["bridges_cut"]:
        raise ValueError("Bridge count changed")
    report = dict(totals) | {"pair_precision": totals["tp"]/(totals["tp"]+totals["fp"]),
                             "recoverability": totals["recoverable"]/9980,
                             "net_recoverability": totals["newly_recoverable"]-totals["lost_recoverability"]}
    target.write_text(json.dumps({"classification": "retrospective_exploratory_C_only",
                                  "prediction_freeze_sha256": sha256_file(HERE / "bridge_predictions/prediction_freeze.json"),
                                  "metrics": report, "resource": {"wall_seconds": time.perf_counter()-started,
                                                                   "peak_process_rss_bytes": peak}}, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
