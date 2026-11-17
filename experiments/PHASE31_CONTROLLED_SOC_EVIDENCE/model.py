"""Existing C-P-V grouping/ranking with optional receiver-visible attestations.

Inference accepts only a receiver-visible directory. It never imports or reads
the evaluator-only tree. All links are checked against visible event attributes.
"""
import importlib.util
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4_PREDICT = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/predict.py"
spec = importlib.util.spec_from_file_location("frozen_phase16_predict", V4_PREDICT)
phase16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase16)

PRIVATE_FIELDS = {"incident_id", "scenario_id", "template_id", "true_relation", "priority_rank",
                  "priority_score", "malicious", "attack_stage", "condition"}
CORE_FIELDS = phase16.ALLOWED
FAMILIES = ("process", "authentication", "network_flow")


def lines(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def visible_input(receiver_root, queue, cutoff):
    root = Path(receiver_root)
    alerts = lines(root / "alerts" / f"{queue}.jsonl")
    ledger = lines(root / "evidence_ledger" / f"{queue}.jsonl")
    claims = lines(root / "claims" / f"{queue}.jsonl")
    if any(set(x) & PRIVATE_FIELDS for x in alerts + ledger + claims):
        raise ValueError("private field in receiver input")
    if [x["sequence"] for x in ledger] != list(range(1, len(ledger) + 1)):
        raise ValueError("ledger order")
    availability = {x["artifact_id"]: x["evidence_available_minute"] for x in ledger}
    if len(availability) != len(ledger) or set(availability) != {x["alert_id"] for x in alerts}:
        raise ValueError("ledger coverage")
    if any(x["evidence_available_minute"] != availability[x["alert_id"]] for x in alerts):
        raise ValueError("ledger mismatch")
    eligible = {x["alert_id"]: x for x in alerts if availability[x["alert_id"]] <= cutoff}
    visible_claims = [x for x in claims if x["evidence_available_minute"] <= cutoff and
                      x["left_alert_id"] in eligible and x["right_alert_id"] in eligible]
    return eligible, visible_claims


def source_depth(group, lookup):
    items = list({lookup[a]["source_id"]: lookup[a] for a in group}.values())
    return (1.2 * max(a["severity"] for a in items) +
            .7 * max(a["asset_criticality"] for a in items) +
            .55 * len({a["event_type"] for a in items}) +
            .7 * min(len(items), 10))


def core(alerts, claims, arm):
    projected = {aid: {k: a[k] for k in CORE_FIELDS} for aid, a in alerts.items()}
    if arm == "legacy_rich":
        # Existing one-lineage C sees richer observations without new V logic.
        for c in sorted(claims, key=lambda x: x["observation_id"]):
            field = "auth_session_ref" if c["family"] == "authentication" else (
                "network_flow_ref" if c["family"] == "network_flow" else None)
            if field:
                for aid in (c["left_alert_id"], c["right_alert_id"]):
                    if projected[aid][field] is None:
                        projected[aid][field] = c["relationship_token"]
    return [projected[aid] for aid in sorted(projected)]


def validate_attestation_bundle(bundle, alerts, cutoff):
    if {x["family"] for x in bundle} != set(FAMILIES): return False, "missing_family"
    original = [x for x in bundle if x["derived_from"] is None]
    if len(original) != 3 or {x["family"] for x in original} != set(FAMILIES):
        return False, "derived_or_duplicate_family"
    if len({x["upstream_root_id"] for x in original}) != 3:
        return False, "shared_upstream_root"
    if any(x["evidence_available_minute"] > cutoff for x in original):
        return False, "late_claim"
    left_id = original[0]["left_alert_id"]; right_id = original[0]["right_alert_id"]
    if any(x["left_alert_id"] != left_id or x["right_alert_id"] != right_id for x in original):
        return False, "endpoint_conflict"
    left, right = alerts[left_id], alerts[right_id]
    if any(x["left_event_id"] != left["event_id"] or x["right_event_id"] != right["event_id"] for x in original):
        return False, "event_conflict"
    if left["host"] != right["host"] or left["account"] != right["account"]:
        return False, "context_conflict"
    if right["event_minute"] < left["event_minute"] - 3 or abs(right["event_minute"] - left["event_minute"]) > 25:
        return False, "time_conflict"
    if any(x["left_host"] != left["host"] or x["right_host"] != right["host"] or
           x["account"] != left["account"] for x in original):
        return False, "claim_context_conflict"
    if left["process_id"] != right["parent_process_id"] or left["auth_session_id"] != right["auth_session_id"] or left["flow_id"] != right["flow_id"]:
        return False, "causal_fields_conflict"
    if any(x["left_process_id"] != left["process_id"] or
           x["right_parent_process_id"] != right["parent_process_id"] or
           x["auth_session_id"] != left["auth_session_id"] or
           x["flow_id"] != left["flow_id"] for x in original):
        return False, "attestation_fields_conflict"
    return True, "verified"


def verified_unions(groups, alerts, claims, cap):
    by_token = defaultdict(list)
    for c in claims: by_token[c["relationship_token"]].append(c)
    parent = list(range(len(groups)))
    sizes = [len(g) for g in groups]
    where = {aid: i for i, g in enumerate(groups) for aid in g}
    decisions = Counter(); accepted = []; rejected = []

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    for token in sorted(by_token):
        bundle = by_token[token]
        good, reason = validate_attestation_bundle(bundle, alerts, 100)
        if not good:
            decisions[reason] += 1; rejected.append({"relationship_token": token, "reason": reason}); continue
        left = where[bundle[0]["left_alert_id"]]; right = where[bundle[0]["right_alert_id"]]
        a, b = root(left), root(right)
        if a == b:
            decisions["already_grouped"] += 1; continue
        if sizes[a] + sizes[b] > cap:
            decisions["cap_reject"] += 1; rejected.append({"relationship_token": token, "reason": "cap_reject"}); continue
        # Existing pure fragment context remains the component guard.
        ha = {alerts[x]["host"] for i, g in enumerate(groups) if root(i) == a for x in g}
        hb = {alerts[x]["host"] for i, g in enumerate(groups) if root(i) == b for x in g}
        aa = {alerts[x]["account"] for i, g in enumerate(groups) if root(i) == a for x in g}
        ab = {alerts[x]["account"] for i, g in enumerate(groups) if root(i) == b for x in g}
        if not (ha & hb and aa & ab):
            decisions["component_context_reject"] += 1
            rejected.append({"relationship_token": token, "reason": "component_context_reject"}); continue
        parent[b] = a; sizes[a] += sizes[b]
        decisions["accepted"] += 1
        accepted.append({"relationship_token": token,
            "left_alert_id": bundle[0]["left_alert_id"], "right_alert_id": bundle[0]["right_alert_id"],
            "upstream_roots": sorted({x["upstream_root_id"] for x in bundle if x["derived_from"] is None})})
    result = defaultdict(list)
    for i, group in enumerate(groups): result[root(i)].extend(group)
    return list(result.values()), dict(decisions), accepted, rejected


def predict_queue(receiver_root, split, queue, arm, cutoff=100, cap=100):
    if arm not in ("original_subset", "legacy_rich", "evidence_aware", "evidence_aware_ranked"):
        raise ValueError(arm)
    start = time.perf_counter()
    alerts, claims = visible_input(receiver_root, queue, cutoff)
    base_alerts = core(alerts, claims, "legacy_rich" if arm == "legacy_rich" else "original_subset")
    groups, edges, original_decisions, _ = phase16.correlate(base_alerts, "lineage_one_context_v", cap)
    decisions = Counter(original_decisions)
    accepted = []; rejected = []
    if arm in ("evidence_aware", "evidence_aware_ranked"):
        groups, verify_decisions, accepted, rejected = verified_unions(groups, alerts, claims, cap)
        decisions.update(verify_decisions)
    def rank_score(group):
        score = source_depth(group, alerts)
        if arm == "evidence_aware_ranked":
            members = set(group)
            score += sum(x["left_alert_id"] in members for x in accepted)
        return score
    ranked = sorted((sorted(g) for g in groups), key=lambda g: (-rank_score(g), g[0]))
    prediction = {"queue_id": queue, "split": split, "method": arm,
        "ranker": "source_depth", "cutoff": cutoff,
        "eligible_alert_ids": sorted(alerts), "groups_ranked": ranked,
        "candidate_pairs": edges + len(claims), "decisions": dict(decisions),
        "runtime_seconds": time.perf_counter() - start}
    audit = {"queue_id": queue, "accepted": accepted, "rejected": rejected,
        "visible_claims": len(claims), "decision_counts": dict(decisions)}
    return prediction, audit
