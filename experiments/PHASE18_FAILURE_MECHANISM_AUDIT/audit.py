"""Evaluator-only retrospective audit. No prediction, selection, or new model."""
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P17 = ROOT / "experiments/PHASE17_INDEPENDENT_PROVENANCE"
P16 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
sys.path.insert(0, str(P17))
from model import FIELDS, candidates, fragments, lines, visible


def write_csv(name, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"Empty audit: {name}")
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quantiles(values):
    values = sorted(values)
    return {"min": values[0], "p25": values[len(values)//4],
            "median": values[len(values)//2], "p75": values[3*len(values)//4],
            "max": values[-1]}


def baseline_and_sensor_audit(manifest, cutoff):
    rows, queue_rows, sensor_rows = [], [], []
    for split, queues in manifest["queues"].items():
        for item in queues:
            queue = item["queue_id"]
            folder = P17 / "datasets" / split
            a = visible(P17 / "datasets", split, queue, cutoff)
            raw = lines(folder / "generated_alerts" / f"{queue}.jsonl")
            source = lines(folder / "source_observations" / f"{queue}.jsonl")
            field_ledger = lines(folder / "field_ledger" / f"{queue}.jsonl")
            truth = {x["alert_id"]: x["incident_id"] for x in lines(folder / "ground_truth_private" / f"{queue}.jsonl")}
            oracle = lines(folder / "ground_truth_private" / f"{queue}_priority.jsonl")
            groups = fragments(a, 100)
            raw_groups = fragments(raw, 100)  # retrospective upper diagnostic, never inference
            sizes = Counter(truth[x["alert_id"]] for x in a)
            raw_sizes = Counter(truth[x["alert_id"]] for x in raw)
            by_incident = defaultdict(list)
            for group in groups:
                counts = Counter(truth[a[i]["alert_id"]] for i in group)
                for incident, hits in counts.items():
                    by_incident[incident].append((hits, len(group)))
            raw_best = defaultdict(int)
            for group in raw_groups:
                counts = Counter(truth[raw[i]["alert_id"]] for i in group)
                for incident, hits in counts.items():
                    raw_best[incident] = max(raw_best[incident], hits)
            qualifying = 0
            for item_oracle in oracle:
                if item_oracle["priority_rank"] > 20:
                    continue
                incident = item_oracle["incident_id"]
                incident_size = sizes[incident]
                if not incident_size:
                    raise AssertionError("Top-20 incident has no eligible alerts")
                parts = by_incident[incident]
                best = max((hits for hits, _ in parts), default=0)
                complete = any(hits/incident_size >= .8 for hits, _ in parts)
                recoverable = any(hits/incident_size >= .8 and hits/total >= .8 for hits,total in parts)
                qualifying += recoverable
                rows.append({"split": split, "queue_id": queue, "incident_id": incident,
                             "family": item_oracle["family"], "eligible_alerts": incident_size,
                             "baseline_fragments": len(parts), "largest_overlap": best,
                             "largest_overlap_fraction": best/incident_size,
                             "raw_all_fields_largest_fraction": raw_best[incident]/raw_sizes[incident],
                             "raw_all_fields_complete": int(raw_best[incident]/raw_sizes[incident] >= .8),
                             "has_80pct_complete_group": int(complete),
                             "recoverable": int(recoverable)})
            by_action = defaultdict(set)
            for x in source:
                by_action[x["action_ref_private"]].add(x["sensor"])
            sensor_counts = Counter(x["sensor"] for x in source)
            field_available = Counter(x["field"] for x in field_ledger if x["available_minute"] <= cutoff)
            field_total = Counter(x["field"] for x in field_ledger)
            for field in sorted(FIELDS):
                sensor_rows.append({"split": split, "queue_id": queue, "field": field,
                                    "raw_nonnull": sum(x[field] is not None for x in raw),
                                    "field_available_by_cutoff": field_available[field],
                                    "field_records": field_total[field],
                                    "visible_nonnull": sum(x[field] is not None for x in a)})
            queue_rows.append({"split": split, "queue_id": queue, "eligible_alerts": len(a),
                               "raw_alerts": len(raw), "baseline_groups": len(groups),
                               "baseline_recoverable_top20": qualifying,
                               "actions_with_2plus_sensors": sum(len(v)>=2 for v in by_action.values()),
                               "actions_with_3plus_sensors": sum(len(v)>=3 for v in by_action.values()),
                               "actions_with_4_sensors": sum(len(v)==4 for v in by_action.values()),
                               **{f"sensor_{s}": sensor_counts[s] for s in ("auth","endpoint","network","identity")}})
            if split in ("development", "locked_test"):
                pred = P17 / "experiments/predictions" / f"{split}_baseline.jsonl"
                frozen = next(x for x in lines(pred) if x["queue_id"] == queue)
                if set(frozen["eligible_alert_ids"]) != {x["alert_id"] for x in a}:
                    raise AssertionError("Frozen prediction differs from point-in-time replay")
                replay_groups = {frozenset(a[i]["alert_id"] for i in group) for group in groups}
                frozen_groups = {frozenset(group) for group in frozen["groups_ranked"]}
                if replay_groups != frozen_groups:
                    raise AssertionError("Frozen baseline partition differs from code replay")
    write_csv("PHASE18_BASELINE_INCIDENT_AUDIT.csv", rows)
    write_csv("PHASE18_QUEUE_DISTRIBUTION.csv", queue_rows)
    write_csv("PHASE18_FIELD_AVAILABILITY.csv", sensor_rows)
    return rows, queue_rows, sensor_rows


def false_pair_replay(manifest):
    merge_rows = []
    queue_rows = []
    for item in manifest["queues"]["development"]:
        queue = item["queue_id"]
        a = visible(P17 / "datasets", "development", queue, 100)
        base = fragments(a, 100)
        candidate = {(x["left"], x["right"]): x for x in candidates(a, base)}
        truth = {x["alert_id"]: x["incident_id"] for x in lines(P17 / "datasets/development/ground_truth_private" / f"{queue}.jsonl")}
        decisions = next(x for x in lines(P17 / "experiments/decisions/development_t0p8_progression.jsonl") if x["queue_id"]==queue)["records"]
        parent = list(range(len(base)))
        membership = [Counter(truth[a[i]["alert_id"]] for i in group) for group in base]
        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        new_fp = new_tp = 0
        for order, d in enumerate(decisions):
            if d["decision"] != "accept":
                continue
            left, right = d["left"], d["right"]
            ra, rb = root(left), root(right)
            if ra == rb:
                raise AssertionError("Accepted already-joined fragments")
            ca, cb = membership[ra], membership[rb]
            tp = sum(ca[i]*cb[i] for i in ca.keys() & cb.keys())
            fp = sum(ca.values())*sum(cb.values()) - tp
            info = candidate.get((left,right)) or candidate.get((right,left))
            if info is None:
                raise AssertionError("Accepted merge has no frozen candidate")
            merge_rows.append({"queue_id": queue, "merge_order": order,
                               "left_fragment": left, "right_fragment": right,
                               "probability": d["probability"], "signature": d["key"],
                               "auth_support": int(info["auth"]), "flow_support": int(info["flow"]),
                               "host_agree": int(info["host_agree"]),
                               "account_agree": int(info["account_agree"]),
                               "sensor_origins": info["sensor_origins"],
                               "source_witnesses": info["source_witnesses"],
                               "rare_reference": int(info["rare"]),
                               "left_group_size": sum(ca.values()), "right_group_size": sum(cb.values()),
                               "new_true_pairs": tp, "new_false_pairs": fp,
                               "was_false_merge": int(fp>0)})
            parent[rb] = ra
            membership[ra] += membership[rb]
            new_fp += fp
            new_tp += tp
        queue_rows.append({"queue_id": queue, "accepted_merges": sum(x["queue_id"]==queue for x in merge_rows),
                           "new_false_pairs": new_fp, "new_true_pairs": new_tp})
    write_csv("PHASE18_ACCEPTED_MERGE_PAIR_INCREMENTS.csv", merge_rows)
    write_csv("PHASE18_FALSE_PAIR_QUEUE_RECONCILIATION.csv", queue_rows)
    base_eval = json.loads((P17 / "experiments/evaluations/development_baseline.json").read_text())["summary"]
    candidate_eval = json.loads((P17 / "experiments/evaluations/development_t0p8_progression.json").read_text())["summary"]
    if sum(x["new_false_pairs"] for x in merge_rows) != candidate_eval["false_grouped_pairs"]-base_eval["false_grouped_pairs"]:
        raise AssertionError("False-pair increments do not reconcile")
    if sum(x["new_true_pairs"] for x in merge_rows) != candidate_eval["pair_tp"]-base_eval["pair_tp"]:
        raise AssertionError("True-pair increments do not reconcile")
    return merge_rows, queue_rows


def main():
    cfg = json.loads((P17 / "configs/study.json").read_text())
    manifest = json.loads((P17 / "datasets/manifest.json").read_text())
    rows, queues, fields = baseline_and_sensor_audit(manifest, cfg["decision_minute"])
    merges, merge_queues = false_pair_replay(manifest)
    split_summary = {}
    for split in ("train","development","locked_test"):
        incidents = [x for x in rows if x["split"]==split]
        q = [x for x in queues if x["split"]==split]
        split_summary[split] = {"queues": len(q), "top20_labels": len(incidents),
            "baseline_recoverable": sum(x["recoverable"] for x in incidents),
            "complete_80pct": sum(x["has_80pct_complete_group"] for x in incidents),
            "raw_all_fields_complete_80pct": sum(x["raw_all_fields_complete"] for x in incidents),
            "largest_overlap_fraction": quantiles([x["largest_overlap_fraction"] for x in incidents]),
            "mean_eligible_alerts_per_top20": statistics.mean(x["eligible_alerts"] for x in incidents),
            "mean_baseline_fragments_per_top20": statistics.mean(x["baseline_fragments"] for x in incidents),
            "mean_visible_alerts_per_queue": statistics.mean(x["eligible_alerts"] for x in q),
            "actions_with_2plus_sensors": sum(x["actions_with_2plus_sensors"] for x in q)}
    bad = [x for x in merges if x["new_false_pairs"]]
    top = sorted(bad, key=lambda x: x["new_false_pairs"], reverse=True)
    false_summary = {"accepted_merges": len(merges),
                     "merges_creating_false_pairs": len(bad),
                     "new_false_pairs": sum(x["new_false_pairs"] for x in merges),
                     "new_true_pairs": sum(x["new_true_pairs"] for x in merges),
                     "top_1_false_pairs": top[0]["new_false_pairs"] if top else 0,
                     "top_5_false_pairs": sum(x["new_false_pairs"] for x in top[:5]),
                     "top_10_false_pairs": sum(x["new_false_pairs"] for x in top[:10]),
                     "false_pairs_from_nonrare_ref": sum(x["new_false_pairs"] for x in bad if not x["rare_reference"]),
                     "false_pairs_with_auth_and_flow": sum(x["new_false_pairs"] for x in bad if x["auth_support"] and x["flow_support"]),
                     "false_pairs_with_host_account_agreement": sum(x["new_false_pairs"] for x in bad if x["host_agree"] and x["account_agree"])}
    phase16_misses = list(csv.DictReader((P17 / "PHASE17_PHASE16_RANKING_MISSES.csv").open(newline="",encoding="utf-8")))
    summary = {"classification": "retrospective_mechanism_audit_no_model_selection",
               "split_summary": split_summary, "false_pair_replay": false_summary,
               "phase16_ranking_only_count": len(phase16_misses),
               "phase16_ranking_median_qualifying_position": quantiles([int(x["first_qualifying_group_position"]) for x in phase16_misses])["median"],
               "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (P17/"model.py",P17/"generate.py",P17/"configs/study.json",
                    P17/"experiments/selection_freeze.json",P17/"experiments/evaluations/development_baseline.json",
                    P17/"experiments/evaluations/development_t0p8_progression.json",
                    P17/"experiments/evaluations/locked_test_baseline.json")}}
    (HERE / "PHASE18_AUDIT_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"split_summary":split_summary,"false_pair_replay":false_summary},indent=2))


if __name__ == "__main__":
    main()
