"""Point-in-time, label-blind reconstruction and ranking candidates."""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ("host", "account", "indicator", "process_tree_ref", "auth_session_ref",
          "network_flow_ref", "event_type", "severity", "asset_criticality")
ALLOWED = set(FIELDS) | {"alert_id", "source_id", "queue_id", "event_minute", "evidence_available_minute"}
CUTOFF = 100


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def visible(split, queue):
    folder = HERE / "datasets" / split
    alerts = rows(folder / "generated_alerts" / f"{queue}.jsonl")
    ledger = {x["artifact_id"]: x for x in rows(folder / "evidence_ledger" / f"{queue}.jsonl")}
    fields = {(x["artifact_id"], x["field"]): x for x in rows(folder / "field_ledger" / f"{queue}.jsonl")}
    if len(ledger) != len(alerts) or len(fields) != len(alerts) * len(FIELDS):
        raise ValueError("incomplete availability ledgers")
    result = []
    for raw in alerts:
        if set(raw) - ALLOWED or raw["evidence_available_minute"] != ledger[raw["alert_id"]]["evidence_available_minute"]:
            raise ValueError("unapproved or inconsistent model input")
        if raw["evidence_available_minute"] > CUTOFF:
            continue
        item = dict(raw)
        for field in FIELDS:
            entry = fields[item["alert_id"], field]
            if not entry["permitted"] or entry["available_minute"] > CUTOFF:
                item[field] = None
        result.append(item)
    return sorted(result, key=lambda x: x["alert_id"])


def reconstruct(alerts, rule, cap=100):
    if rule not in ("context", "dual", "expanded", "partial"):
        raise ValueError(rule)
    n = len(alerts)
    parent = list(range(n))
    members = {i: {i} for i in range(n)}
    decisions = []

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j, reason, support=None):
        a, b = root(i), root(j)
        if a == b:
            return False
        left = sorted(alerts[k]["alert_id"] for k in members[a])
        right = sorted(alerts[k]["alert_id"] for k in members[b])
        if len(left) + len(right) > cap:
            decisions.append({"decision": "reject", "reason": "component_cap", "left": left,
                              "right": right, "support": support or {}})
            return False
        decisions.append({"decision": "accept", "reason": reason, "left": left, "right": right,
                          "support": support or {}, "premerge_pair_exposure": len(left) * len(right)})
        parent[b] = a
        members[a] |= members[b]
        del members[b]
        return True

    for field in ("source_id", "process_tree_ref"):
        by_value = defaultdict(list)
        for i, item in enumerate(alerts):
            if item[field]:
                by_value[item[field]].append(i)
        for indices in by_value.values():
            for i in indices[1:]:
                union(indices[0], i, "same_source" if field == "source_id" else "process_tree")

    # Candidate pairs and evidence are formed from source-deduplicated initial fragments.
    support = defaultdict(lambda: {"auth_session_ref": set(), "network_flow_ref": set()})
    frequency = {}
    for field in ("auth_session_ref", "network_flow_ref"):
        by_ref = defaultdict(list)
        for i, item in enumerate(alerts):
            if item[field]:
                by_ref[item[field]].append(i)
        for ref, indices in by_ref.items():
            frequency[ref] = len({root(i) for i in indices})
            for pos, i in enumerate(indices):
                for j in indices[pos + 1:]:
                    a, b = root(i), root(j)
                    if a == b or alerts[i]["source_id"] == alerts[j]["source_id"]:
                        continue
                    if abs(alerts[i]["event_minute"] - alerts[j]["event_minute"]) > 30:
                        continue
                    key = tuple(sorted((a, b)))
                    support[key][field].add((ref, alerts[i]["source_id"], alerts[j]["source_id"]))

    proposals = []
    for (a, b), evidence in support.items():
        fields = [f for f in ("auth_session_ref", "network_flow_ref") if evidence[f]]
        source_ids = {s for f in fields for _, x, y in evidence[f] for s in (x, y)}
        rare = all(frequency[ref] <= 2 for f in fields for ref, _, _ in evidence[f])
        proposals.append((-(len(fields)), -len(source_ids), a, b, fields, rare, evidence))
    for _, __, a, b, fields, rare, evidence in sorted(proposals, key=lambda x: x[:4]):
        ra, rb = root(a), root(b)
        if ra == rb:
            continue
        ma, mb = members[ra], members[rb]
        vals = lambda ids, field: {alerts[i][field] for i in ids if alerts[i][field] is not None}
        ha, hb = vals(ma, "host"), vals(mb, "host")
        aa, ab = vals(ma, "account"), vals(mb, "account")
        coherent = len(ha | hb) <= 1 and len(aa | ab) <= 1
        agreement = bool(ha and hb and ha & hb and aa and ab and aa & ab)
        distinct = len({s for f in fields for _, x, y in evidence[f] for s in (x, y)})
        if not coherent:
            state, reason = "reject", "component_context_contradiction"
        elif rule == "dual":
            state, reason = ("accept", "dual_lineage") if len(fields) == 2 and distinct >= 4 and agreement else ("abstain", "insufficient_dual_lineage")
        elif rule == "context":
            state, reason = ("accept", "context_lineage") if agreement else ("abstain", "missing_context")
        elif rule == "expanded":
            state, reason = ("accept", "expanded_lineage") if agreement or (len(fields) == 2 and distinct >= 4 and rare) else ("abstain", "insufficient_independent_support")
        else:
            state, reason = ("accept", "partial_lineage") if agreement or rare else ("abstain", "ambiguous_partial_support")
        witness = {f: sorted({ref for ref, _, _ in evidence[f]}) for f in fields}
        if state == "accept":
            union(a, b, reason, witness)
        else:
            decisions.append({"decision": state, "reason": reason,
                              "left": sorted(alerts[i]["alert_id"] for i in ma),
                              "right": sorted(alerts[i]["alert_id"] for i in mb),
                              "support": witness, "premerge_pair_exposure": len(ma) * len(mb)})
    groups = defaultdict(list)
    for i, item in enumerate(alerts):
        groups[root(i)].append(item["alert_id"])
    groups = [sorted(x) for x in groups.values()]
    assert sum(map(len, groups)) == n and max(map(len, groups), default=0) <= cap
    return groups, decisions, len(support)


def features(group, lookup):
    items = list({lookup[x]["source_id"]: lookup[x] for x in group}.values())
    severities = [a["severity"] or 0 for a in items]
    criticalities = [a["asset_criticality"] or 0 for a in items]
    events = {a["event_type"] for a in items if a["event_type"]}
    relation_types = sum(any(a[field] for a in items) for field in
                         ("process_tree_ref", "auth_session_ref", "network_flow_ref"))
    times = [a["event_minute"] for a in items]
    return [max(severities), max(criticalities), sum(severities)/len(items),
            len(events), min(len(items), 15), relation_types,
            min(max(times)-min(times), 50)/10, 1-len(items)/len(group),
            sum(bool(a["host"] and a["account"]) for a in items)/len(items)]


def ranking_score(vector, ranker, weights=None):
    if ranker == "progression":
        return 1.2*vector[0] + .7*vector[1] + .55*vector[3] + .1*min(vector[4], 10)
    if ranker == "severity":
        return vector[0] + .5*vector[1]
    if ranker == "learned" and weights is not None:
        return sum(x*w for x, w in zip(vector, weights))
    raise ValueError(ranker)


def rank(groups, alerts, ranker, weights=None):
    lookup = {a["alert_id"]: a for a in alerts}
    scores = {g[0]: ranking_score(features(g, lookup), ranker, weights) for g in groups}
    return sorted(groups, key=lambda g: (-scores[g[0]], g[0]))
