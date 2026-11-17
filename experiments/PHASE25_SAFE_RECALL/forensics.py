"""Evaluator-only forensic replay of the opened Phase 24 development queue."""
import csv
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "PHASE24_RECALL_FIRST" / "v4"
spec = importlib.util.spec_from_file_location("phase24_predict", OLD / "predict.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
Q = "phase24d_development_q014"


def load_decisions():
    return next(x["decisions"] for x in old.rows(OLD / "development_decisions.jsonl")
                if x["queue_id"] == Q and x["rule"] == "coherent_rare")


def initial_components(alerts):
    parent = {a["alert_id"]: a["alert_id"] for a in alerts}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    by_source = defaultdict(list)
    by_process = defaultdict(list)
    for a in alerts:
        by_source[a["source_id"]].append(a["alert_id"])
        if a["process_tree_ref"]:
            by_process[a["process_tree_ref"]].append(a)
    for ids in by_source.values():
        for x in ids[1:]: parent[root(x)] = root(ids[0])
    for items in by_process.values():
        hosts = {x["host"] for x in items if x["host"]}
        accounts = {x["account"] for x in items if x["account"]}
        if len(hosts) == len(accounts) == 1:
            for x in items[1:]: parent[root(x["alert_id"])] = root(items[0]["alert_id"])
    return {x: root(x) for x in parent}


def metrics(decision, lookup, truth, initial):
    left, right = decision["left"], decision["right"]
    ref_field = next(iter(decision["support"]))
    ref = decision["support"][ref_field][0]
    ref_roots = {initial[a["alert_id"]] for a in lookup.values() if a[ref_field] == ref}
    def vals(side, field): return {lookup[a][field] for a in side if lookup[a][field] is not None}
    other = "network_flow_ref" if ref_field == "auth_session_ref" else "auth_session_ref"
    left_other, right_other = vals(left, other), vals(right, other)
    times_l, times_r = [lookup[a]["event_minute"] for a in left], [lookup[a]["event_minute"] for a in right]
    same_truth = len({truth[a] for a in left+right}) == 1
    return {"source_field": ref_field, "ref": ref, "ref_frequency_initial_components": len(ref_roots),
            "left_sources": len(vals(left, "source_id")), "right_sources": len(vals(right, "source_id")),
            "left_process_roots": len(vals(left, "process_tree_ref")),
            "right_process_roots": len(vals(right, "process_tree_ref")),
            "host_agreement": bool(vals(left, "host") & vals(right, "host")),
            "account_agreement": bool(vals(left, "account") & vals(right, "account")),
            "left_time": (min(times_l), max(times_l)), "right_time": (min(times_r), max(times_r)),
            "time_overlap": min(max(times_l), max(times_r)) >= max(min(times_l), min(times_r)),
            "other_ref_disjoint": bool(left_other and right_other and left_other.isdisjoint(right_other)),
            "physical_same_incident_evaluator_only": same_truth,
            "left_incidents_evaluator_only": dict(Counter(truth[a] for a in left)),
            "right_incidents_evaluator_only": dict(Counter(truth[a] for a in right))}


def main():
    alerts = old.visible("development", Q)
    lookup = {a["alert_id"]: a for a in alerts}
    raw = {a["alert_id"]: a for a in old.rows(
        OLD / "datasets" / "development" / "generated_alerts" / f"{Q}.jsonl")}
    ledger = {(x["artifact_id"], x["field"]): x["available_minute"] for x in old.rows(
        OLD / "datasets" / "development" / "field_ledger" / f"{Q}.jsonl")}
    truth = {x["alert_id"]: x["incident_id"] for x in old.rows(
        OLD / "datasets" / "development" / "ground_truth_private" / f"{Q}.jsonl")}
    initial = initial_components(alerts)
    decisions = load_decisions()
    audit = [x for x in csv.DictReader((OLD / "PHASE24_UNION_PAIR_AUDIT.csv").open(newline="", encoding="utf-8"))
             if x["queue_id"] == Q and x["rule"] == "coherent_rare" and int(x["new_false_pairs"]) > 0]
    assert [int(x["new_false_pairs"]) for x in audit] == [42, 12, 6, 40, 20]
    detail = []
    members = []
    cumulative = 0
    for entry in audit:
        order = int(entry["order"])
        decision = decisions[order]
        info = metrics(decision, lookup, truth, initial)
        cumulative += int(entry["new_false_pairs"])
        detail.append({"order": order, "new_false_pairs": int(entry["new_false_pairs"]),
                       "cumulative_false_pairs": cumulative, "left_size": len(decision["left"]),
                       "right_size": len(decision["right"]), **info})
        for side in ("left", "right"):
            for aid in decision[side]:
                item = lookup[aid]
                members.append({"order": order, "side": side, "alert_id": aid,
                                "source_id": item["source_id"], "initial_component": initial[aid],
                                "sensor_origin": "not_recorded_in_phase24",
                                "causal_parent": "not_recorded_in_phase24",
                                "incident_id_evaluator_only": truth[aid],
                                "event_minute": item["event_minute"],
                                "receiver_available_minute": item["evidence_available_minute"],
                                "host": item["host"], "account": item["account"],
                                "process_tree_ref": item["process_tree_ref"],
                                "auth_session_ref": item["auth_session_ref"],
                                "network_flow_ref": item["network_flow_ref"],
                                "host_field_available_minute": ledger[aid, "host"],
                                "account_field_available_minute": ledger[aid, "account"],
                                "auth_field_available_minute": ledger[aid, "auth_session_ref"],
                                "flow_field_available_minute": ledger[aid, "network_flow_ref"],
                                "raw_host_evaluator_only": raw[aid]["host"]})
    with (HERE / "PHASE25_Q014_UNION_MEMBERS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(members[0]))
        writer.writeheader(); writer.writerows(members)
    (HERE / "q014_forensic.json").write_text(json.dumps(detail, indent=2) + "\n")
    union_all = [x for x in csv.DictReader((OLD / "PHASE24_UNION_PAIR_AUDIT.csv").open(
        newline="", encoding="utf-8")) if x["rule"] == "coherent_rare" and x["reason"] == "rare_context_lineage"]
    by_queue = defaultdict(list)
    for x in union_all:by_queue[x["queue_id"]].append(x)
    comparison = Counter()
    for queue, entries in by_queue.items():
        observations = old.visible("development", queue)
        view = {a["alert_id"]: a for a in observations}
        roots = initial_components(observations)
        labels = {x["alert_id"]: x["incident_id"] for x in old.rows(
            OLD / "datasets" / "development" / "ground_truth_private" / f"{queue}.jsonl")}
        decisions_q = next(x["decisions"] for x in old.rows(OLD / "development_decisions.jsonl")
                           if x["queue_id"] == queue and x["rule"] == "coherent_rare")
        for entry in entries:
            info = metrics(decisions_q[int(entry["order"])], view, labels, roots)
            classification = "false" if int(entry["new_false_pairs"]) else "true"
            comparison[classification] += 1
            comparison[classification + "_orthogonal_disjoint"] += info["other_ref_disjoint"]
            comparison[classification + "_time_overlap"] += info["time_overlap"]
            comparison[classification + "_ref_frequency_two"] += info["ref_frequency_initial_components"] == 2
    (HERE / "q014_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps(detail, indent=2))


if __name__ == "__main__":
    main()
