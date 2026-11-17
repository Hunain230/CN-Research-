"""Point-in-time, label-blind reconstruction and ranking candidates."""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from evidence import snapshot as evidence_snapshot

HERE = Path(__file__).resolve().parent
FIELDS = ("host", "account", "indicator", "process_tree_ref", "auth_session_ref",
          "network_flow_ref", "event_type", "severity", "asset_criticality")
ALLOWED = set(FIELDS) | {"alert_id", "source_id", "queue_id", "event_minute", "evidence_available_minute"}
CUTOFF = 100


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def visible(split, queue):
    return get_snapshot(split,queue).alerts


def get_snapshot(split,queue,cutoff=CUTOFF):
    return evidence_snapshot(HERE/"datasets"/split,queue,cutoff)


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


def reconstruct(alerts, rule, cap=100, receipts=None, states=None, snapshot_hash=None, decision_minute=100):
    if rule not in ("context", "orthogonal_veto", "pit_complete", "pit_maturity",
                    "pit_selective", "pit_group", "pit_combined"):
        raise ValueError(rule)
    states=states or {}
    receipts=receipts or []
    n = len(alerts)
    parent = list(range(n))
    members = {i: {i} for i in range(n)}
    decisions = []

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def component_evidence(indices):
        source_map={}
        for i in sorted(indices):
            sid=alerts[i]["source_id"]
            quality=sum(states.get((alerts[i]["alert_id"],f))=="SUPPORTED" for f in ("host","account"))
            if sid not in source_map or quality>sum(states.get((alerts[source_map[sid]]["alert_id"],f))=="SUPPORTED"
                                                    for f in ("host","account")):
                source_map[sid]=i
        known=sum(bool(alerts[i]["host"] and alerts[i]["account"]) for i in source_map.values())
        independent=sum(states.get((alerts[i]["alert_id"],"host"))=="SUPPORTED" and
                        states.get((alerts[i]["alert_id"],"account"))=="SUPPORTED"
                        for i in source_map.values())
        missing=sum(not alerts[i]["host"] or not alerts[i]["account"] for i in source_map.values())
        contradicted=sum(states.get((alerts[i]["alert_id"],f))=="CONTRADICTED"
                         for i in source_map.values() for f in ("host","account"))
        maturity=(.5*known/max(1,len(source_map)) + .3*min(independent/2,1)
                  +.2*len(source_map)/max(1,len(indices)))
        return {"distinct_sources":len(source_map),"independent_sources":independent,
                "missing_critical_fields":missing,"contradictory_fields":contradicted,
                "duplicate_ratio":round(1-len(source_map)/max(1,len(indices)),6),
                "maturity":round(maturity,6)}

    def receipt_corroboration(indices):
        sources={alerts[i]["source_id"] for i in indices}
        matching=[x for x in receipts if x["source_id"] in sources and
                  x["parent_source_id"] in sources and x["controller_root"] and x["sensor_origin"]]
        return len({x["source_id"] for x in matching})>=2 and len({x["controller_root"] for x in matching})>=2

    def union(i, j, reason, support=None):
        a, b = root(i), root(j)
        if a == b:
            return False
        left = sorted(alerts[k]["alert_id"] for k in members[a])
        right = sorted(alerts[k]["alert_id"] for k in members[b])
        evidence=component_evidence(members[a]|members[b])
        if len(left) + len(right) > cap:
            decisions.append({"decision": "reject", "reason": "component_cap", "left": left,
                              "right": right, "support": support or {},"evidence":evidence,
                              "decision_minute":decision_minute,"snapshot_sha256":snapshot_hash})
            return False
        decisions.append({"decision": "accept", "reason": reason, "left": left, "right": right,
                          "support": support or {}, "premerge_pair_exposure": len(left) * len(right),
                          "postmerge_size":len(left)+len(right),"evidence":evidence,
                          "predicted_confidence":evidence["maturity"],
                          "decision_minute":decision_minute,"snapshot_sha256":snapshot_hash})
        parent[b] = a
        members[a] |= members[b]
        del members[b]
        return True

    for field in ("source_id", "process_tree_ref"):
        by_value = defaultdict(list)
        for i, item in enumerate(alerts):
            if item[field]:
                if field == "process_tree_ref":
                    if rule != "context":
                        by_value[item[field]].append(i)
                    elif item["host"] and item["account"]:
                        by_value[item[field], item["host"], item["account"]].append(i)
                else:
                    by_value[item[field]].append(i)
        for indices in by_value.values():
            if field == "process_tree_ref" and rule != "context":
                hosts = {alerts[i]["host"] for i in indices if alerts[i]["host"]}
                accounts = {alerts[i]["account"] for i in indices if alerts[i]["account"]}
                evidence=component_evidence(indices)
                complete=evidence["missing_critical_fields"]==0
                contradicted=evidence["contradictory_fields"]>0
                if len(hosts) != 1 or len(accounts) != 1 or contradicted:
                    reason="process_context_contradiction" if len(hosts)>1 or len(accounts)>1 or contradicted else "process_context_ambiguous"
                elif rule in ("pit_complete","pit_group") and not complete:
                    reason="process_evidence_not_complete"
                elif rule=="pit_maturity" and evidence["maturity"]<.85:
                    reason="process_evidence_immature"
                elif rule in ("pit_selective","pit_combined") and not complete and not receipt_corroboration(indices):
                    reason="process_missing_without_independent_receipts"
                else:
                    reason=None
                if reason:
                    decisions.append({"decision": "abstain", "reason": reason,
                                      "left": [alerts[indices[0]]["alert_id"]],
                                      "right": [alerts[i]["alert_id"] for i in indices[1:]],
                                      "support": {"process_tree_ref":[alerts[indices[0]]["process_tree_ref"]]},
                                      "premerge_pair_exposure": 0,"evidence":evidence,
                                      "decision_minute":decision_minute,"snapshot_sha256":snapshot_hash})
                    continue
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
    by_source = defaultdict(list)
    for item in alerts:
        by_source[item["source_id"]].append(item)

    def orthogonal_conflict(evidence):
        """Every supporting source pair contradicts another visible lineage field."""
        tested = []
        for field, pairs in evidence.items():
            other = "network_flow_ref" if field == "auth_session_ref" else "auth_session_ref"
            for _, left_source, right_source in pairs:
                left = {x[other] for x in by_source[left_source] if x[other]}
                right = {x[other] for x in by_source[right_source] if x[other]}
                tested.append(bool(left and right and left.isdisjoint(right)))
        return bool(tested) and all(tested)

    for (a, b), evidence in support.items():
        fields = [f for f in ("auth_session_ref", "network_flow_ref") if evidence[f]]
        if not fields:
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
        orthogonal_veto = orthogonal_conflict(evidence)
        union_evidence=component_evidence(ma|mb)
        if not coherent:
            state, reason = "reject", "component_context_contradiction"
        elif rule in ("orthogonal_veto","pit_complete","pit_maturity","pit_selective","pit_group","pit_combined"):
            if agreement and rare and orthogonal_veto:
                state, reason = "abstain", "orthogonal_lineage_conflict"
            elif rule in ("pit_group","pit_combined") and union_evidence["maturity"]<.85:
                state, reason = "abstain", "component_evidence_immature"
            elif rule=="pit_combined" and union_evidence["missing_critical_fields"]>0 and len(fields)<2:
                state, reason = "abstain", "component_missing_without_dual_lineage"
            else:
                state, reason = ("accept", "vetted_rare_lineage") if agreement and rare else ("abstain", "nonrare_or_missing_context")
        elif rule == "context":
            state, reason = ("accept", "context_lineage") if agreement else ("abstain", "missing_context")
        else:
            raise AssertionError(rule)
        witness = {f: sorted({ref for ref, _, _ in evidence[f]}) for f in fields}
        if state == "accept":
            union(a, b, reason, witness)
        else:
            decisions.append({"decision": state, "reason": reason,
                              "left": sorted(alerts[i]["alert_id"] for i in ma),
                              "right": sorted(alerts[i]["alert_id"] for i in mb),
                              "support": witness, "premerge_pair_exposure": len(ma) * len(mb),
                              "evidence":union_evidence,"decision_minute":decision_minute,
                              "snapshot_sha256":snapshot_hash})
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
