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


def visible_receipts(split, queue):
    folder = HERE / "datasets" / split
    receipts = rows(folder / "receiver_receipts" / f"{queue}.jsonl")
    ledger = {(x["source_id"], x["field"]): x for x in rows(
        folder / "receipt_field_ledger" / f"{queue}.jsonl")}
    if len(ledger) != 3*len(receipts):
        raise ValueError("incomplete receipt ledger")
    result = []
    for raw in receipts:
        if set(raw) != {"source_id", "parent_source_id", "sensor_origin", "controller_root",
                        "receiver_available_minute"}:
            raise ValueError("unapproved receipt field")
        if raw["receiver_available_minute"] > CUTOFF:
            continue
        item = dict(raw)
        for field in ("parent_source_id", "sensor_origin", "controller_root"):
            entry = ledger[item["source_id"], field]
            if not entry["permitted"] or entry["available_minute"] > CUTOFF:
                item[field] = None
        result.append(item)
    return result


def reconstruct(alerts, rule, cap=100, receipts=None):
    if rule not in ("context", "dual", "coherent_rare", "orthogonal_veto",
                    "partial_orthogonal", "collision_guard", "receipt_two", "receipt_one_rare"):
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
                if field == "process_tree_ref":
                    if rule in ("coherent_rare", "orthogonal_veto", "partial_orthogonal", "collision_guard",
                                "receipt_two", "receipt_one_rare"):
                        by_value[item[field]].append(i)
                    elif item["host"] and item["account"]:
                        by_value[item[field], item["host"], item["account"]].append(i)
                else:
                    by_value[item[field]].append(i)
        for indices in by_value.values():
            if field == "process_tree_ref" and rule in ("coherent_rare", "orthogonal_veto",
                                                         "partial_orthogonal", "collision_guard",
                                                         "receipt_two", "receipt_one_rare"):
                hosts = {alerts[i]["host"] for i in indices if alerts[i]["host"]}
                accounts = {alerts[i]["account"] for i in indices if alerts[i]["account"]}
                if len(hosts) != 1 or len(accounts) != 1:
                    decisions.append({"decision": "abstain", "reason": "process_context_ambiguous",
                                      "left": [alerts[indices[0]]["alert_id"]],
                                      "right": [alerts[i]["alert_id"] for i in indices[1:]],
                                      "support": {}, "premerge_pair_exposure": 0})
                    continue
            for i in indices[1:]:
                union(indices[0], i, "same_source" if field == "source_id" else "process_tree")

    # Candidate pairs and evidence are formed from source-deduplicated initial fragments.
    support = defaultdict(lambda: {"auth_session_ref": set(), "network_flow_ref": set(), "receipt": set()})
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

    if rule in ("receipt_two", "receipt_one_rare"):
        source_index = {}
        for i, item in enumerate(alerts):
            source_index.setdefault(item["source_id"], i)
        for receipt in receipts or []:
            child, upstream = receipt["source_id"], receipt["parent_source_id"]
            if not child or not upstream or not receipt["sensor_origin"] or not receipt["controller_root"]:
                continue
            if child not in source_index or upstream not in source_index:
                continue
            a, b = root(source_index[child]), root(source_index[upstream])
            if a == b:
                continue
            key = tuple(sorted((a, b)))
            support[key]["receipt"].add((child, upstream, receipt["sensor_origin"], receipt["controller_root"]))

    proposals = []
    by_source = defaultdict(list)
    context_processes = defaultdict(set)
    for item in alerts:
        by_source[item["source_id"]].append(item)
        if item["host"] and item["account"] and item["process_tree_ref"]:
            context_processes[item["host"], item["account"]].add(item["process_tree_ref"])

    def orthogonal_conflict(evidence):
        """Every supporting source pair contradicts another visible lineage field."""
        tested = []
        for field, pairs in evidence.items():
            if field == "receipt":continue
            other = "network_flow_ref" if field == "auth_session_ref" else "auth_session_ref"
            for _, left_source, right_source in pairs:
                left = {x[other] for x in by_source[left_source] if x[other]}
                right = {x[other] for x in by_source[right_source] if x[other]}
                tested.append(bool(left and right and left.isdisjoint(right)))
        return bool(tested) and all(tested)

    for (a, b), evidence in support.items():
        fields = [f for f in ("auth_session_ref", "network_flow_ref") if evidence[f]]
        if not fields and rule not in ("receipt_two", "receipt_one_rare"):
            continue
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
        orthogonal_veto = orthogonal_conflict(evidence)
        context_pairs = {(alerts[i]["host"], alerts[i]["account"]) for i in ma | mb
                         if alerts[i]["host"] and alerts[i]["account"]}
        collision_risk = any(len(context_processes[pair]) > 8 for pair in context_pairs)
        receipts_here = evidence["receipt"]
        receipt_sources = {x[0] for x in receipts_here}
        receipt_sensors = {x[2] for x in receipts_here}
        receipt_roots = {x[3] for x in receipts_here}
        diverse_receipts = (len(receipts_here) >= 2 and len(receipt_sources) >= 2
                            and len(receipt_sensors) >= 2 and len(receipt_roots) >= 2)
        if not coherent:
            state, reason = "reject", "component_context_contradiction"
        elif rule == "dual":
            state, reason = ("accept", "dual_lineage") if len(fields) == 2 and distinct >= 4 and agreement else ("abstain", "insufficient_dual_lineage")
        elif rule == "coherent_rare":
            state, reason = ("accept", "rare_context_lineage") if agreement and rare else ("abstain", "nonrare_or_missing_context")
        elif rule in ("orthogonal_veto", "collision_guard"):
            if agreement and rare and orthogonal_veto:
                state, reason = "abstain", "orthogonal_lineage_conflict"
            elif rule == "collision_guard" and collision_risk and len(fields) < 2:
                state, reason = "abstain", "shared_context_collision_risk"
            else:
                state, reason = ("accept", "vetted_rare_lineage") if agreement and rare else ("abstain", "nonrare_or_missing_context")
        elif rule == "partial_orthogonal":
            if orthogonal_veto:
                state, reason = "abstain", "orthogonal_lineage_conflict"
            else:
                state, reason = ("accept", "vetted_partial_lineage") if agreement or rare else ("abstain", "ambiguous_partial_support")
        elif rule == "receipt_two":
            state, reason = ("accept", "two_receiver_receipts") if diverse_receipts and agreement else ("abstain", "insufficient_receiver_receipts")
        elif rule == "receipt_one_rare":
            if diverse_receipts and agreement:
                state, reason = "accept", "two_receiver_receipts"
            elif receipts_here and fields and rare and agreement and not orthogonal_veto:
                state, reason = "accept", "receipt_and_rare_lineage"
            else:
                state, reason = "abstain", "partial_receipt_or_lineage"
        elif rule == "context":
            state, reason = ("accept", "context_lineage") if agreement else ("abstain", "missing_context")
        else:
            raise AssertionError(rule)
        witness = {f: sorted({ref for ref, _, _ in evidence[f]}) for f in fields}
        if receipts_here:
            witness["receipt"] = sorted({x[0] for x in receipts_here})
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
    if ranker in ("learned", "linear") and weights is not None:
        return sum(x*w for x, w in zip(vector, weights))
    if ranker == "blend" and weights is not None:
        progression = ranking_score(vector, "progression")
        learned = ranking_score(vector, "learned", weights)
        return .8*progression + .4*learned
    raise ValueError(ranker)


def rank(groups, alerts, ranker, weights=None):
    lookup = {a["alert_id"]: a for a in alerts}
    scores = {g[0]: ranking_score(features(g, lookup), ranker, weights) for g in groups}
    return sorted(groups, key=lambda g: (-scores[g[0]], g[0]))
