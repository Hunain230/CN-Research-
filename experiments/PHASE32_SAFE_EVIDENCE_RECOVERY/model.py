"""Endpoint-process attestation fallback on the frozen Phase 31 C-P-V pipeline."""
import importlib.util
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31_PATH = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/model.py"
spec = importlib.util.spec_from_file_location("phase31_frozen_model", P31_PATH)
p31 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p31)


def endpoint_process_fallback(bundle, alerts, cutoff):
    """Return true only for a visible three-root process/auth/network attestation."""
    originals = [c for c in bundle if c["derived_from"] is None]
    if len(originals) != 2 or {c["family"] for c in originals} != {"authentication", "network_flow"}:
        return False, "not_exact_auth_network_pair"
    if len({c["upstream_root_id"] for c in originals}) != 2:
        return False, "shared_claim_root"
    if any(c["evidence_available_minute"] > cutoff for c in bundle):
        return False, "future_claim"
    left_id, right_id = originals[0]["left_alert_id"], originals[0]["right_alert_id"]
    if any(c["left_alert_id"] != left_id or c["right_alert_id"] != right_id for c in bundle):
        return False, "endpoint_conflict"
    if left_id not in alerts or right_id not in alerts:
        return False, "endpoint_unavailable"
    left, right = alerts[left_id], alerts[right_id]
    if left["duplicate_of"] is not None or right["duplicate_of"] is not None:
        return False, "derived_endpoint"
    if left["source_id"] == right["source_id"] or left["observation_id"] == right["observation_id"]:
        return False, "same_endpoint_observation"
    endpoint_root = left["endpoint_origin"]
    if endpoint_root != right["endpoint_origin"] or endpoint_root in {c["upstream_root_id"] for c in originals}:
        return False, "not_three_independent_roots"
    if left["host"] != right["host"] or left["account"] != right["account"]:
        return False, "context_conflict"
    if right["event_minute"] < left["event_minute"] - 3 or abs(right["event_minute"] - left["event_minute"]) > 25:
        return False, "time_conflict"
    if left["process_id"] != right["parent_process_id"] or left["auth_session_id"] != right["auth_session_id"] or left["flow_id"] != right["flow_id"]:
        return False, "causal_fields_conflict"
    for c in bundle:
        if (c["left_event_id"] != left["event_id"] or c["right_event_id"] != right["event_id"] or
            c["left_host"] != left["host"] or c["right_host"] != right["host"] or
            c["account"] != left["account"] or c["left_process_id"] != left["process_id"] or
            c["right_parent_process_id"] != right["parent_process_id"] or
            c["auth_session_id"] != left["auth_session_id"] or c["flow_id"] != left["flow_id"]):
            return False, "claim_fields_conflict"
    return True, "endpoint_process_attested"


def fallback_unions(groups, alerts, claims, accepted, rejected, cap):
    by_token = defaultdict(list)
    for c in claims: by_token[c["relationship_token"]].append(c)
    parent = list(range(len(groups)))
    sizes = [len(g) for g in groups]
    where = {a: i for i, g in enumerate(groups) for a in g}
    decisions = Counter(); promoted = []; retained = []

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    for item in rejected:
        token = item["relationship_token"]
        if item["reason"] != "missing_family":
            retained.append(item); continue
        good, reason = endpoint_process_fallback(by_token[token], alerts, 100)
        if not good:
            decisions[reason] += 1; retained.append(item); continue
        bundle = by_token[token]
        a, b = root(where[bundle[0]["left_alert_id"]]), root(where[bundle[0]["right_alert_id"]])
        if a == b:
            decisions["already_grouped"] += 1; continue
        if sizes[a] + sizes[b] > cap:
            decisions["cap_reject"] += 1; retained.append(item); continue
        left_hosts = {alerts[x]["host"] for i, g in enumerate(groups) if root(i) == a for x in g}
        right_hosts = {alerts[x]["host"] for i, g in enumerate(groups) if root(i) == b for x in g}
        left_accounts = {alerts[x]["account"] for i, g in enumerate(groups) if root(i) == a for x in g}
        right_accounts = {alerts[x]["account"] for i, g in enumerate(groups) if root(i) == b for x in g}
        if not (left_hosts & right_hosts and left_accounts & right_accounts):
            decisions["component_context_reject"] += 1; retained.append(item); continue
        parent[b] = a; sizes[a] += sizes[b]
        decisions["fallback_accepted"] += 1
        promoted.append({"relationship_token": token,
            "left_alert_id": bundle[0]["left_alert_id"], "right_alert_id": bundle[0]["right_alert_id"],
            "upstream_roots": sorted({alerts[bundle[0]["left_alert_id"]]["endpoint_origin"]} |
                                     {c["upstream_root_id"] for c in bundle if c["derived_from"] is None}),
            "evidence_kind": "endpoint_process_plus_auth_network"})
    result = defaultdict(list)
    for i, g in enumerate(groups): result[root(i)].extend(g)
    return list(result.values()), accepted + promoted, retained, dict(decisions)


def predict_queue(receiver_root, split, queue, rank_bonus):
    if rank_bonus not in (1, 2): raise ValueError(rank_bonus)
    start = time.perf_counter()
    alerts, claims = p31.visible_input(receiver_root, queue, 100)
    core = p31.core(alerts, claims, "original_subset")
    groups, edges, original_decisions, _ = p31.phase16.correlate(core, "lineage_one_context_v", 100)
    groups, verify_decisions, accepted, rejected = p31.verified_unions(groups, alerts, claims, 100)
    groups, accepted, rejected, fallback_decisions = fallback_unions(groups, alerts, claims, accepted, rejected, 100)
    decisions = Counter(original_decisions); decisions.update(verify_decisions); decisions.update(fallback_decisions)
    decisions["accepted"] = len(accepted)
    def score(group):
        members = set(group)
        return p31.source_depth(group, alerts) + rank_bonus * sum(x["left_alert_id"] in members for x in accepted)
    ranked = sorted((sorted(g) for g in groups), key=lambda g: (-score(g), g[0]))
    prediction = {"queue_id": queue, "split": split,
        "method": f"endpoint_fallback_bonus{rank_bonus}", "ranker": f"source_depth_plus_verified_{rank_bonus}",
        "cutoff": 100, "eligible_alert_ids": sorted(alerts), "groups_ranked": ranked,
        "candidate_pairs": edges + len(claims), "decisions": dict(decisions),
        "runtime_seconds": time.perf_counter() - start}
    audit = {"queue_id": queue, "accepted": accepted, "rejected": rejected,
        "visible_claims": len(claims), "decision_counts": dict(decisions)}
    return prediction, audit
