"""Point-in-time candidate graph, separate committed components and hypotheses."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE26 = HERE.parents[1] / "PHASE26_POINT_IN_TIME_SAFETY" / "v2"
sys.path.append(str(PHASE26))
from predict import reconstruct as legacy_reconstruct, features as legacy_features, ranking_score  # noqa: E402
from evidence import snapshot  # noqa: E402


def read(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def disjoint_root_witness_count(edges):
    """Count witnesses with nonoverlapping upstream roots, once per source pair."""
    by_sources = {}
    for edge in edges:
        pair = tuple(edge["source_provenance"])
        roots = frozenset(edge["controller_roots"])
        if len(pair) == 2 and len(roots) == 2:
            by_sources[pair] = roots
    used = set()
    count = 0
    for roots in sorted(by_sources.values(), key=lambda r: tuple(sorted(r))):
        if roots.isdisjoint(used):
            used.update(roots)
            count += 1
    return count


def load(split, queue, cutoff=100):
    folder = HERE / "datasets" / split
    snap = snapshot(folder, queue, cutoff)
    source = {x["source_id"]: x for x in read(folder / "source_records" / f"{queue}.jsonl")
              if x["receiver_arrival_timestamp"] <= cutoff}
    return snap, source


def build_edges(snap, source):
    alerts = snap.alerts
    edges = []
    # Source observations are explicit graph nodes, with one emission edge per visible alert.
    for a in alerts:
        s = source[a["source_id"]]
        edges.append({"source_node": "source:" + a["source_id"],
                      "destination_node": "alert:" + a["alert_id"],
                      "relationship_type": "emits", "support": ["source_observation"],
                      "contradictions": [], "receiver_visible_minute": max(
                          a["evidence_available_minute"], s["receiver_arrival_timestamp"]),
                      "source_provenance": [a["source_id"]],
                      "controller_roots": [s["controller_root"]],
                      "independence": "single_root", "confidence": 1.0,
                      "uncertainty": 0.0, "outcome": "VERIFIED"})
    by_field = {f: defaultdict(list) for f in ("source_id", "process_tree_ref",
                                                "auth_session_ref", "network_flow_ref")}
    for a in alerts:
        for field, values in by_field.items():
            if a[field]:
                values[a[field]].append(a)
    pair_support = defaultdict(set)
    for field, values in by_field.items():
        for group in values.values():
            for pos, a in enumerate(group):
                for b in group[pos + 1:]:
                    if a["alert_id"] == b["alert_id"]:
                        continue
                    pair_support[tuple(sorted((a["alert_id"], b["alert_id"])))].add(field)
    lookup = {a["alert_id"]: a for a in alerts}
    for (left, right), support_fields in sorted(pair_support.items()):
        a, b = lookup[left], lookup[right]
        roots = {source[a["source_id"]]["controller_root"],
                 source[b["source_id"]]["controller_root"]}
        independent = a["source_id"] != b["source_id"] and len(roots) == 2
        contradict = [f for f in ("host", "account") if a[f] and b[f] and a[f] != b[f]]
        complete = bool(a["host"] and b["host"] and a["account"] and b["account"])
        duplicate = a["source_id"] == b["source_id"]
        lineage = len(support_fields & {"auth_session_ref", "network_flow_ref"})
        if duplicate:
            outcome, confidence = "VERIFIED", 1.0
        elif contradict:
            outcome, confidence = "REJECTED", 0.0
        elif "process_tree_ref" in support_fields and complete and independent:
            outcome, confidence = "VERIFIED", 0.98
        else:
            confidence = .29 + .21 * lineage + (.18 if "process_tree_ref" in support_fields else 0)
            confidence += .12 if complete else 0
            confidence += .09 if independent else -.08
            confidence = round(min(.93, max(.05, confidence)), 4)
            outcome = "CANDIDATE"
        edges.append({"source_node": "alert:" + left, "destination_node": "alert:" + right,
                      "relationship_type": "+".join(sorted(support_fields)),
                      "support": sorted(support_fields), "contradictions": contradict,
                      "receiver_visible_minute": max(a["evidence_available_minute"],
                                                     b["evidence_available_minute"]),
                      "source_provenance": sorted({a["source_id"], b["source_id"]}),
                      "controller_roots": sorted(roots),
                      "independence": "verified_distinct_roots" if independent else
                                      "shared_or_unverified", "confidence": confidence,
                      "uncertainty": round(1 - confidence, 4), "outcome": outcome})
    assert all(e["receiver_visible_minute"] <= snap.cutoff for e in edges)
    return edges


def components(alerts, edges, mode, snap):
    """Only VERIFIED edges are mandatory unions; candidate commits have separate gates."""
    if mode == "phase26_baseline":
        return legacy_reconstruct(alerts, "context", states=snap.states,
                                  snapshot_hash=snap.sha256, decision_minute=snap.cutoff)[:2]
    if mode == "phase25_veto":
        return legacy_reconstruct(alerts, "orthogonal_veto", states=snap.states,
                                  snapshot_hash=snap.sha256, decision_minute=snap.cutoff)[:2]
    allowed = {a["alert_id"] for a in alerts}
    lookup = {a["alert_id"]: a for a in alerts}
    parent = {x: x for x in allowed}
    members = {x: {x} for x in allowed}
    decisions = []

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for edge in sorted(edges, key=lambda x: (x["outcome"] != "VERIFIED", -x["confidence"],
                                             x["source_node"], x["destination_node"])):
        if not edge["source_node"].startswith("alert:"):
            continue
        a, b = edge["source_node"][6:], edge["destination_node"][6:]
        ra, rb = root(a), root(b)
        if ra == rb:
            continue
        left, right = members[ra], members[rb]
        status, reason = "ABSTAIN", "candidate_uncommitted"
        if edge["outcome"] == "REJECTED":
            status, reason = "REJECT", "visible_contradiction"
        elif edge["outcome"] == "VERIFIED":
            status, reason = "ACCEPT", "verified_edge"
        elif mode in ("graph_selective", "graph_risk"):
            threshold = .86 if mode == "graph_selective" else .92
            hosts = {lookup[x]["host"] for x in left | right if lookup[x]["host"]}
            accounts = {lookup[x]["account"] for x in left | right if lookup[x]["account"]}
            complete = all(lookup[x]["host"] and lookup[x]["account"] for x in left | right)
            if (edge["confidence"] >= threshold and edge["independence"] == "verified_distinct_roots"
                    and len(hosts) == len(accounts) == 1 and complete):
                status, reason = "ACCEPT", "selective_candidate"
        if len(left) + len(right) > 100:
            status, reason = "REJECT", "component_cap"
        decisions.append({"decision": status, "reason": reason, "left": sorted(left),
                          "right": sorted(right), "edge": edge,
                          "premerge_pair_exposure": len(left) * len(right),
                          "snapshot_sha256": snap.sha256, "decision_minute": snap.cutoff})
        if status == "ACCEPT":
            parent[rb] = ra
            members[ra] |= members[rb]
            del members[rb]
    return sorted((sorted(g) for g in members.values()), key=lambda g: g[0]), decisions


def hypotheses(groups, edges, threshold=.52, bound=8):
    """Bounded multi-fragment hypotheses; never modifies committed groups."""
    group_of = {a: i for i, g in enumerate(groups) for a in g}
    proposals = defaultdict(list)
    for edge in edges:
        if edge["outcome"] != "CANDIDATE" or edge["confidence"] < threshold:
            continue
        if not edge["source_node"].startswith("alert:"):
            continue
        a, b = edge["source_node"][6:], edge["destination_node"][6:]
        x, y = group_of[a], group_of[b]
        if x != y:
            proposals[tuple(sorted((x, y)))].append(edge)
    forbidden = set()
    for edge in edges:
        if edge["outcome"] == "REJECTED" and edge["source_node"].startswith("alert:"):
            a, b = edge["source_node"][6:], edge["destination_node"][6:]
            if group_of[a] != group_of[b]:
                forbidden.add(tuple(sorted((group_of[a], group_of[b]))))
    parent = list(range(len(groups)))
    fragments = {i: {i} for i in range(len(groups))}
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    order = sorted(proposals, key=lambda pair: (-max(e["confidence"] for e in proposals[pair]), pair))
    for x, y in order:
        a, b = root(x), root(y)
        if a == b:
            continue
        joined = fragments[a] | fragments[b]
        if len(joined) > bound or sum(len(groups[i]) for i in joined) > 100:
            continue
        if any((min(i, j), max(i, j)) in forbidden for i in fragments[a] for j in fragments[b]):
            continue
        parent[b] = a
        fragments[a] = joined
        del fragments[b]
    result = []
    for joined in sorted((sorted(v) for v in fragments.values() if len(v) > 1)):
        witnesses = [e for (x, y), pair_edges in proposals.items() if x in joined and y in joined
                     for e in pair_edges]
        roots = {r for edge in witnesses for r in edge["controller_roots"]}
        types = {f for edge in witnesses for f in edge["support"]}
        independent = disjoint_root_witness_count(witnesses)
        score = max(e["confidence"] for e in witnesses) + .04 * min(len(types), 3)
        if independent == 0:
            score -= .12
        result.append({"hypothesis_id": ":".join(map(str, joined)), "fragments": joined,
                       "alert_ids": sorted(a for i in joined for a in groups[i]),
                       "edge_count": len({tuple(e["source_provenance"]) for e in witnesses}),
                       "distinct_roots": len(roots),
                       "relationship_types": sorted(types), "independent_paths": independent,
                       "confidence": round(score, 4), "committed": False})
    assert all(len(x["fragments"]) <= bound for x in result)
    return result


def graph_features(group, groups, edges, hypotheses_rows):
    ids = set(group)
    candidate = [e for e in edges if e["outcome"] == "CANDIDATE" and
                 e["source_node"].startswith("alert:") and
                 ((e["source_node"][6:] in ids) != (e["destination_node"][6:] in ids))]
    unique_pairs = {tuple(e["source_provenance"]) for e in candidate}
    roots = {r for e in candidate for r in e["controller_roots"]}
    independent = disjoint_root_witness_count(candidate)
    relevant = [h for h in hypotheses_rows if ids.intersection(h["alert_ids"])]
    return [min(len(unique_pairs), 5), min(independent, 4), min(len(roots), 6),
            max((e["confidence"] for e in candidate), default=0),
            max((h["confidence"] for h in relevant), default=0),
            min(len(relevant), 4)]


def rank_groups(groups, alerts, edges, hypotheses_rows, ranker, historical, fitted=None):
    lookup = {a["alert_id"]: a for a in alerts}
    scores = {}
    for group in groups:
        vec = legacy_features(group, lookup)
        gf = graph_features(group, groups, edges, hypotheses_rows)
        prog = ranking_score(vec, "progression")
        if ranker == "progression":
            score = prog
        elif ranker == "phase25_linear":
            score = ranking_score(vec, "linear", historical["phase25_linear"])
        elif ranker == "phase26_blend":
            score = ranking_score(vec, "blend", historical["phase26_blend"])
        elif ranker == "candidate_graph":
            score = prog + .8 * gf[0] + .45 * gf[1] - .15 * max(0, gf[0] - gf[1])
        elif ranker == "fragment_aggregation":
            score = prog + 1.6 * gf[4] + .5 * gf[5]
        elif ranker == "graph_progression":
            score = prog + .5 * gf[0] + .5 * gf[1] + .7 * gf[4]
        elif ranker == "train_fitted":
            feat = vec + gf
            score = sum(w * v for w, v in zip(fitted, feat))
        else:
            raise ValueError(ranker)
        scores[group[0]] = round(score, 7)
    return sorted(groups, key=lambda g: (-scores[g[0]], g[0])), scores
