"""Development-only counterfactual study of receiver-attested trust roots.

Uses Phase 22 development observations and its private evaluator. No locked path is
opened. The registry is a separate trusted input, not a field supplied by a sensor.
"""
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
P22 = HERE.parent / "PHASE22_RECEIPT_ROBUSTNESS"
sys.path.insert(0, str(P22))
spec = importlib.util.spec_from_file_location("phase22_run_study", P22 / "run_study.py")
phase22 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase22)
audit_queue, decide, read, visible = (phase22.audit_queue, phase22.decide,
                                     phase22.read, phase22.visible)


def registry_for(receipts, scenario):
    """Synthetic authenticated topology; absent entries mean untrusted provenance."""
    roots = {r["source_record_id"]: "controller_" + r["sensor"] for r in receipts}
    if scenario in ("shared_controller", "missing_root"):
        for receipt in receipts:
            if receipt["sensor"] in ("auth", "network"):
                roots[receipt["source_record_id"]] = "controller_auth_network"
    if scenario == "missing_root":
        for source in list(roots):
            if "_endpoint_record_" in source:
                del roots[source]
    return roots


def decide_domains(alerts, claims, receipts, registry, exposure_cap=None):
    """Verify local edges, then require two distinct event and upstream roots."""
    by_source = {r["source_record_id"]: r for r in receipts}
    parent_fragments = defaultdict(set)
    for receipt in receipts:
        if receipt["origin_event_id"] and receipt["observed_fragment_ref"]:
            parent_fragments[receipt["origin_event_id"]].add(receipt["observed_fragment_ref"])
    groups = defaultdict(list)
    for alert in alerts:
        groups[alert["fragment_ref"] or alert["alert_id"]].append(alert)
    keys = sorted(groups)
    parent = {k: k for k in keys}
    members = {k: list(groups[k]) for k in keys}

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    proposals = defaultdict(list)
    decisions = []
    for claim in claims:
        left, right = claim["left_fragment_ref"], claim["right_fragment_ref"]
        record = by_source.get(claim["source_record_id"])
        if not left or not right or left not in groups or right not in groups or left == right:
            reason = "unavailable_or_same_fragment"
        elif not record or not (
            record["sensor"] == claim["sensor"]
            and record["origin_event_id"] == claim["origin_event_id"]
            and record["observed_fragment_ref"] == right
            and claim["parent_event_id"] in (record["observed_parent_event_ids"] or [])
            and left in parent_fragments[claim["parent_event_id"]]
        ):
            reason = "source_receipt_does_not_verify_edge"
        else:
            proposals[tuple(sorted((left, right)))].append(claim)
            continue
        decisions.append({"decision": "reject", "reason": reason, "claim_ids": [claim["claim_id"]],
                          "left": left, "right": right, "premerge_pair_exposure": 0})

    for (left, right), rows in sorted(proposals.items()):
        a, b = root(left), root(right)
        ids = [x["claim_id"] for x in rows]
        if a == b:
            decisions.append({"decision": "reject", "reason": "already_joined", "claim_ids": ids,
                              "left": left, "right": right, "premerge_pair_exposure": 0})
            continue
        roots = {x["origin_event_id"] for x in rows if x["origin_event_id"]}
        sensors = {x["sensor"] for x in rows}
        domains = {registry.get(x["source_record_id"]) for x in rows}
        exposure = len(members[a]) * len(members[b])
        if None in domains:
            state, reason = "abstain", "unattested_upstream_root"
        elif len(roots) < 2 or len(sensors) < 2 or len(domains) < 2:
            state, reason = "abstain", "insufficient_independent_roots"
        elif exposure_cap is not None and exposure > exposure_cap:
            state, reason = "abstain", "group_exposure_cap"
        else:
            state, reason = "accept", "verified_independent_trust_roots"
        decisions.append({"decision": state, "reason": reason, "claim_ids": ids,
                          "left": left, "right": right, "distinct_roots": len(roots),
                          "sensor_processes": len(sensors), "trust_domains": len(domains),
                          "premerge_pair_exposure": exposure})
        if state == "accept":
            parent[b] = a
            members[a] += members[b]
    final = defaultdict(list)
    for key in keys:
        final[root(key)].extend(groups[key])
    ranked = sorted(final.values(), key=lambda group: (
        -max(x["severity"] + x["asset_criticality"] for x in group),
        -len(group), min(x["alert_id"] for x in group)))
    assert sum(map(len, ranked)) == len(alerts)
    return [[a["alert_id"] for a in group] for group in ranked], decisions, groups


def main():
    manifest = json.loads((P22 / "datasets" / "manifest.json").read_text())
    queues = manifest["splits"]["development"]
    scenarios = ("shared_controller", "independent_corruption", "missing_root")
    rules = ("phase22_verified", "trust_domains", "trust_domains_cap100")
    frozen = []
    # All model decisions are frozen before any private audit data is opened.
    for item in queues:
        q = item["queue_id"]
        alerts, claims, receipts = visible("development", q)
        for scenario in scenarios:
            registry = registry_for(receipts, scenario)
            for rule in rules:
                if rule == "phase22_verified":
                    ranked, decisions, _ = decide(alerts, claims, "verified_edges", receipts)
                else:
                    ranked, decisions, _ = decide_domains(
                        alerts, claims, receipts, registry,
                        100 if rule == "trust_domains_cap100" else None)
                frozen.append({"queue_id": q, "failure_mode": item["failure_mode"],
                               "scenario": scenario, "rule": rule,
                               "groups_ranked": ranked, "decisions": decisions})
    HERE.mkdir(exist_ok=True)
    predictions = HERE / "predictions_and_decisions.jsonl"
    with predictions.open("w", encoding="utf-8") as stream:
        for row in frozen:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    digest = hashlib.sha256(predictions.read_bytes()).hexdigest()
    (HERE / "freeze_manifest.json").write_text(json.dumps({
        "status": "development_only_predictions_frozen_before_private_audit",
        "phase19_locked_truth_read": False, "phase22_locked_truth_read": False,
        "phase22_locked_predictions_created": False,
        "phase22_manifest_sha256": hashlib.sha256((P22 / "datasets" / "manifest.json").read_bytes()).hexdigest(),
        "predictions_sha256": digest}, indent=2) + "\n")

    queue_rows = []
    increments = []
    for row in frozen:
        q = row["queue_id"]
        alerts, claims, receipts = visible("development", q)
        groups = defaultdict(list)
        for alert in alerts:
            groups[alert["fragment_ref"] or alert["alert_id"]].append(alert)
        audit, union_rows = audit_queue("development", q, alerts, claims, receipts, groups,
                                        row["decisions"], row["groups_ranked"])
        for key in ("scenario", "rule", "failure_mode"):
            audit[key] = row[key]
            for union in union_rows:
                union[key] = row[key]
        queue_rows.append(audit)
        increments.extend(union_rows)
    for name, rows in (("queue_audit.jsonl", queue_rows), ("union_pair_increments.jsonl", increments)):
        with (HERE / name).open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {}
    for scenario in scenarios:
        summary[scenario] = {}
        for rule in rules:
            subset = [r for r in queue_rows if r["scenario"] == scenario and r["rule"] == rule]
            union_subset = [r for r in increments if r["scenario"] == scenario and r["rule"] == rule]
            summary[scenario][rule] = {
                "queues": len(subset), "recoverable": sum(r["recoverable"] for r in subset),
                "eligible_incidents": sum(r["eligible_incidents"] for r in subset),
                "false_pairs": sum(r["false_pairs"] for r in subset),
                "accepted_unions": len(union_subset),
                "false_pair_creating_unions": sum(r["new_false_pairs"] > 0 for r in union_subset),
                "worst_queue_false_pairs": max(r["false_pairs"] for r in subset),
                "worst_union_false_pairs": max((r["new_false_pairs"] for r in union_subset), default=0),
                "accepted_invalid_unions": sum(r["accepted_invalid_unions"] for r in subset)}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
