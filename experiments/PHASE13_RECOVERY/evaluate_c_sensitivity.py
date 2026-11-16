"""Evaluator-only Phase 13 C sensitivity and incident-level failure audit."""
from __future__ import annotations

import csv
import json
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from src.submission_full_entity_time import PARENT
from src.submission_full_guide import tie_aware_ranking


def group_counts(groups, truth):
    tp = fp = mixed = 0
    for group in groups:
        counts = Counter(truth[a] for a in group)
        size = len(group)
        good = sum(v * (v - 1) // 2 for v in counts.values())
        tp += good
        fp += size * (size - 1) // 2 - good
        mixed += len(counts) > 1
    return tp, fp, mixed


def main():
    pred = HERE / "c_predictions"
    freeze = json.loads((pred / "prediction_freeze.json").read_text())
    if freeze["sample"] or freeze["evaluator_labels_read"] or len(freeze["prediction_sha256"]) != 499:
        raise ValueError("Full label-blind prediction freeze required")
    if freeze["code_sha256"] != sha256_file(HERE / "run_c_sensitivity.py") or freeze["config_sha256"] != sha256_file(HERE / "PHASE13_EXPERIMENT_CONFIG.json"):
        raise ValueError("Prediction source changed")
    if (HERE / "PHASE13_C_EVALUATION.json").exists():
        raise FileExistsError("Refusing evaluation overwrite")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    group_freeze = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json").read_text())
    blend_freeze = json.loads((ROOT / "outputs/sprint_rank_fusion_v1_20261116/prediction_freeze.json").read_text())
    totals = defaultdict(Counter)
    routes = defaultdict(Counter)
    incident_rows = []
    started, process = time.perf_counter(), psutil.Process()
    peak = 0
    for number, org in enumerate(orgs, 1):
        name = key(org)
        path = pred / f"{name}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][name]:
            raise ValueError("Prediction hash mismatch")
        with path.open("rb") as stream:
            row = pickle.load(stream)
        keys, edges, flags, scores = row["keys"], row["edges"], row["flags"], row["probabilities"]
        if keys != parent[org]["input_alert_keys"]:
            raise ValueError("Alert scope changed")
        base_path = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1" / f"v2_{name}.pkl"
        if sha256_file(base_path) != group_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen group hash mismatch")
        with base_path.open("rb") as stream:
            base = pickle.load(stream)
        if row["groups"]["0.75"] != base["groups"]:
            raise ValueError("Frozen 0.75 partition changed")
        blend_path = ROOT / "data/derived/sprint_rank_fusion_v1_20261116" / f"scores_{name}.pkl"
        if sha256_file(blend_path) != blend_freeze["score_sha256"][name]:
            raise ValueError("Frozen blend hash mismatch")
        with blend_path.open("rb") as stream:
            blend = pickle.load(stream)["0.75"]
        connected = connected_incidents(keys, edges, truth, ranks[org])
        for route, mask in (("all", np.ones(len(edges), dtype=bool)),
                            ("parent_exact", (flags & 1) != 0),
                            ("entity", (flags & 6) != 0),
                            ("technique", (flags & 8) != 0)):
            chosen = edges[mask]
            linked = connected_incidents(keys, chosen, truth, ranks[org])
            n = len(keys)
            true_edges = sum(truth[keys[int(e // n)]] == truth[keys[int(e % n)]] for e in chosen)
            routes[route].update(edges=len(chosen), true_edges=true_edges,
                                 false_edges=len(chosen)-true_edges, connected_top20=len(linked), queues=1)
        for threshold, groups in row["groups"].items():
            tp, fp, mixed = group_counts(groups, truth)
            outcome = incident_outcomes(groups, keys, truth, ranks[org], connected)
            totals[threshold].update(tp=tp, fp=fp, mixed=mixed, groups=len(groups),
                                     oversized=sum(len(g) > 100 for g in groups),
                                     **{k: outcome[k] for k in ("absent", "candidate_disconnected", "incomplete", "impure", "recoverable")})
        groups = row["groups"]["0.75"]
        group_of = {a: i for i, group in enumerate(groups) for a in group}
        group_rank = {i: position for position, i in enumerate(sorted(range(len(groups)), key=lambda i: (-blend[i], groups[i][0])), 1)}
        sizes = Counter(truth[a] for a in keys)
        fragments = defaultdict(list)
        for i, group in enumerate(groups):
            for gold, hit in Counter(truth[a] for a in group).items():
                if gold in ranks[org]:
                    fragments[gold].append((i, hit, len(group)))
        cross_count = Counter()
        strongest_true, strongest_false = {}, {}
        for edge, score in zip(edges, scores):
            a, b = divmod(int(edge), len(keys))
            left, right = keys[a], keys[b]
            if group_of[left] == group_of[right]:
                continue
            gl, gr = truth[left], truth[right]
            if gl == gr:
                if gl in ranks[org]:
                    cross_count[gl] += 1
                    strongest_true[gl] = max(strongest_true.get(gl, 0), float(score))
            else:
                for gold in (gl, gr):
                    if gold in ranks[org]:
                        strongest_false[gold] = max(strongest_false.get(gold, 0), float(score))
        for gold, expert_rank in ranks[org].items():
            size = sizes[gold]
            parts = fragments[gold]
            complete = [(i, hit, total) for i, hit, total in parts if size and hit / size >= .8]
            pure = [(i, hit, total) for i, hit, total in complete if hit / total >= .8]
            if not size:
                state = "outside_scope"
            elif gold not in connected:
                state = "candidate_disconnected"
            elif not complete:
                state = "incomplete"
            elif not pure:
                state = "impure"
            else:
                state = "recoverable"
            best_group = max(parts, key=lambda x: (x[1], -group_rank[x[0]])) if parts else None
            final_position = min((group_rank[i] for i, _, _ in pure), default=None)
            if state == "incomplete":
                reason = "cap_possible" if size > 125 else "no_genuine_edge_at_0.75" if strongest_true.get(gold, 0) < .75 else "cap_or_union_order"
            elif state == "impure":
                reason = "complete_fragment_mixed"
            else:
                reason = "not_applicable"
            incident_rows.append({"queue_key": name, "incident_key": gold, "expert_rank": expert_rank,
                                  "expert_alerts_in_scope": size, "predicted_fragments": len(parts),
                                  "candidate_connected": int(gold in connected),
                                  "genuine_cross_fragment_edges": cross_count[gold],
                                  "strongest_genuine_cross_fragment_score": strongest_true.get(gold, ""),
                                  "strongest_false_cross_fragment_score": strongest_false.get(gold, ""),
                                  "grouping_rejection_reason": reason,
                                  "best_overlap_group_position": group_rank[best_group[0]] if best_group else "",
                                  "qualifying_group_position": final_position if final_position is not None else "",
                                  "recoverability_status": state,
                                  "largest_fragment_alerts": best_group[1] if best_group else 0})
        peak = max(peak, process.memory_info().rss)
        if number % 25 == 0:
            print(f"Phase13 C evaluated {number}/499", flush=True)
    baseline = json.loads((HERE / "PHASE10_EVALUATION.json").read_text())["methods"]["E1"]
    ref = totals["0.75"]
    if (ref["recoverable"], ref["tp"], ref["fp"], ref["mixed"]) != (baseline["group_recoverability_count"], baseline["grouped_pair_tp"], baseline["false_grouped_pairs"], baseline["mixed_predicted_groups"]):
        raise ValueError("C metric evaluator failed frozen baseline check")
    report = {"classification": "retrospective_exploratory_not_independent_confirmation",
              "prediction_freeze_sha256": sha256_file(pred / "prediction_freeze.json"),
              "group_thresholds": {k: dict(v) | {"pair_precision": v["tp"]/(v["tp"]+v["fp"]),
                                                    "recoverability": v["recoverable"]/9980} for k, v in totals.items()},
              "candidate_routes": {k: dict(v) | {"true_edge_fraction": v["true_edges"]/v["edges"] if v["edges"] else None} for k,v in routes.items()},
              "resource": {"wall_seconds": time.perf_counter()-started, "peak_process_rss_bytes": peak}}
    (HERE / "PHASE13_C_EVALUATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (HERE / "PHASE13_ERROR_ANALYSIS.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(incident_rows[0]))
        writer.writeheader()
        writer.writerows(incident_rows)
    print(json.dumps({"status":"evaluated", "thresholds": report["group_thresholds"], "routes": report["candidate_routes"]}, indent=2))


if __name__ == "__main__":
    main()
