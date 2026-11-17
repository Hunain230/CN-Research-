"""Downstream hypothesis promotion; Phase 27 graph and baseline remain frozen."""
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE27 = HERE.parents[1] / "PHASE27_RECALL_GRAPH" / "v3"
sys.path.append(str(PHASE27))
from evidence import snapshot  # noqa: E402
from graph import (build_edges, components, disjoint_root_witness_count, hypotheses,
                   rank_groups, read)  # noqa: E402

CONFIG = json.loads((HERE / "config.json").read_text())
PHASE27_MODEL = json.loads((PHASE27 / "ranker_model.json").read_text())


def load(split, queue):
    folder = HERE / "datasets" / split
    snap = snapshot(folder, queue, CONFIG["cutoff"])
    source = {x["source_id"]: x for x in read(folder / "source_records" / f"{queue}.jsonl")
              if x["receiver_arrival_timestamp"] <= snap.cutoff}
    edges = build_edges(snap, source)
    groups, baseline_decisions = components(snap.alerts, edges, "phase26_baseline", snap)
    candidates = hypotheses(groups, edges, bound=CONFIG["hypothesis_bound"])
    return snap, source, edges, groups, baseline_decisions, candidates


def features(hypothesis, groups, edges, alerts):
    ids = set(hypothesis["alert_ids"])
    group_of = {a: i for i, group in enumerate(groups) for a in group}
    lookup = {a["alert_id"]: a for a in alerts}
    cross = [e for e in edges if e["outcome"] == "CANDIDATE" and
             e["source_node"].startswith("alert:") and
             e["source_node"][6:] in ids and e["destination_node"][6:] in ids and
             group_of[e["source_node"][6:]] != group_of[e["destination_node"][6:]]]
    lineage = [e for e in cross if set(e["support"]) & {"auth_session_ref", "network_flow_ref"}]
    witness_pairs = {tuple(e["source_provenance"]) for e in lineage}
    lineage_types = {field for e in lineage for field in e["support"] if field in
                     ("auth_session_ref", "network_flow_ref")}
    roots = {r for e in lineage for r in e["controller_roots"]}
    same_root_pairs = sum(len(set(e["controller_roots"])) < 2 for e in lineage)
    hosts = {lookup[a]["host"] for a in ids if lookup[a]["host"]}
    accounts = {lookup[a]["account"] for a in ids if lookup[a]["account"]}
    sources = {lookup[a]["source_id"] for a in ids}
    missing = sum(not lookup[a]["host"] or not lookup[a]["account"] for a in ids)
    exposure = (len(ids) ** 2 - sum(len(groups[i]) ** 2 for i in hypothesis["fragments"])) // 2
    times = [lookup[a]["event_minute"] for a in ids]
    result = {"fragments": len(hypothesis["fragments"]), "alert_count": len(ids),
              "lineage_types": len(lineage_types), "root_disjoint_witnesses":
                  disjoint_root_witness_count(lineage),
              "unique_lineage_source_pairs": len(witness_pairs),
              "distinct_controller_roots": len(roots),
              "shared_root_lineage_edges": same_root_pairs,
              "host_contradiction": len(hosts) > 1,
              "account_contradiction": len(accounts) > 1,
              "missing_critical_fraction": missing / len(ids),
              "duplicate_fraction": 1 - len(sources) / len(ids),
              "event_span": max(times) - min(times),
              "max_arrival": max(lookup[a]["evidence_available_minute"] for a in ids),
              "cross_pair_exposure": exposure}
    return result


BINARIES = ("dual_lineage", "two_root_disjoint", "single_context", "low_exposure",
            "low_duplicate", "no_shared_root_edges", "recent_arrival")


def bins(f):
    return {"dual_lineage": int(f["lineage_types"] >= 2),
            "two_root_disjoint": int(f["root_disjoint_witnesses"] >= 2),
            "single_context": int(not f["host_contradiction"] and not f["account_contradiction"]),
            "low_exposure": int(f["cross_pair_exposure"] <= CONFIG["promotion"]["maximum_cross_pair_exposure"]),
            "low_duplicate": int(f["duplicate_fraction"] <= .2),
            "no_shared_root_edges": int(f["shared_root_lineage_edges"] == 0),
            "recent_arrival": int(f["max_arrival"] <= 90)}


def fit_model(training):
    """Training-only naive Bayes log-odds; threshold excludes training false hypotheses."""
    classes = Counter(label for _, label in training)
    counts = {label: Counter() for label in (0, 1)}
    for f, label in training:
        counts[label].update({k: value for k, value in bins(f).items() if value})
    weights = {}
    for name in BINARIES:
        p1 = (counts[1][name] + 1) / (classes[1] + 2)
        p0 = (counts[0][name] + 1) / (classes[0] + 2)
        weights[name] = (math.log(p1 / p0), math.log((1 - p1) / (1 - p0)))
    model = {"class_counts": dict(classes), "weights": weights,
             "prior": math.log((classes[1] + 1) / (classes[0] + 1))}
    def guarded(f):
        return (f["lineage_types"] >= 2 and f["root_disjoint_witnesses"] >= 2 and
                f["shared_root_lineage_edges"] == 0 and not f["host_contradiction"] and
                not f["account_contradiction"] and
                f["cross_pair_exposure"] <= CONFIG["promotion"]["maximum_cross_pair_exposure"])
    eligible_false = [score(f, model) for f, y in training if not y and guarded(f)]
    eligible_true = [score(f, model) for f, y in training if y and guarded(f)]
    model["training_guarded_true"] = len(eligible_true)
    model["training_guarded_false"] = len(eligible_false)
    model["threshold"] = round(max(eligible_false) + 1e-6 if eligible_false else
                               min(eligible_true) - 1e-6 if eligible_true else 100.0, 8)
    model["training_true_above_threshold"] = sum(x >= model["threshold"] for x in eligible_true)
    return model


def score(f, model):
    values = bins(f)
    return model["prior"] + sum(model["weights"][k][v] for k, v in values.items())


def promote(groups, hypotheses_rows, edges, alerts, snap, model, mode):
    """Reevaluate full components after each proposed union; preserve all hypotheses."""
    assert mode in ("calibrated", "component", "selective")
    lookup = {a["alert_id"]: a for a in alerts}
    original_groups = [set(g) for g in groups]
    parent = list(range(len(groups)))
    members = {i: set(g) for i, g in enumerate(groups)}
    group_of = {a: i for i, g in enumerate(groups) for a in g}
    decisions = []
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    candidates = []
    for h in hypotheses_rows:
        f = features(h, groups, edges, alerts)
        candidates.append((score(f, model), h, f))
    for initial_value, h, initial_f in sorted(candidates, key=lambda x: (-x[0], x[1]["hypothesis_id"])):
        active = sorted({root(group_of[a]) for a in h["alert_ids"]})
        if len(active) < 2:
            continue
        joined = set().union(*(members[i] for i in active))
        current_groups = [sorted(members[i]) for i in active]
        current_hypothesis = {"alert_ids": sorted(joined), "fragments": list(range(len(active)))}
        f = features(current_hypothesis, current_groups, edges, alerts)
        value = score(f, model)
        hosts = {lookup[a]["host"] for a in joined if lookup[a]["host"]}
        accounts = {lookup[a]["account"] for a in joined if lookup[a]["account"]}
        contradictions = len(hosts) > 1 or len(accounts) > 1
        current_exposure = (len(joined) ** 2 - sum(len(members[i]) ** 2 for i in active)) // 2
        reason = "calibrated_score"
        outcome = "PROMOTE" if value >= model["threshold"] else "RETAIN AS HYPOTHESIS"
        if contradictions:
            outcome, reason = "REJECT", "component_context_contradiction"
        elif len(joined) > CONFIG["component_cap"]:
            outcome, reason = "REJECT", "component_cap"
        elif mode in ("component", "selective"):
            if f["lineage_types"] < 2 or f["root_disjoint_witnesses"] < 2:
                outcome, reason = "RETAIN AS HYPOTHESIS", "insufficient_independent_lineage"
            elif f["shared_root_lineage_edges"] and f["root_disjoint_witnesses"] < 3:
                outcome, reason = "RETAIN AS HYPOTHESIS", "common_upstream_dependency"
            elif current_exposure > CONFIG["promotion"]["maximum_cross_pair_exposure"]:
                outcome, reason = "RETAIN AS HYPOTHESIS", "cumulative_pair_exposure"
        if mode == "selective" and outcome != "REJECT" and value < model["threshold"] + CONFIG["promotion"]["selective_threshold_margin"]:
            outcome, reason = "RETAIN AS HYPOTHESIS", "selective_abstention"
        decision = {"hypothesis_id": h["hypothesis_id"], "decision": outcome, "reason": reason,
                    "predicted_log_odds": round(value, 8), "threshold": model["threshold"],
                    "features": f, "pre_components": [sorted(members[i]) for i in active],
                    "post_component": sorted(joined) if outcome == "PROMOTE" else [],
                    "pair_exposure": current_exposure, "snapshot_sha256": snap.sha256,
                    "decision_minute": snap.cutoff}
        decisions.append(decision)
        if outcome == "PROMOTE":
            anchor = active[0]
            for other in active[1:]:
                parent[other] = anchor
                members[anchor] |= members[other]
                del members[other]
    output = sorted((sorted(x) for x in members.values()), key=lambda x: x[0])
    assert {a for g in output for a in g} == {a for g in original_groups for a in g}
    assert sum(map(len, output)) == sum(map(len, original_groups))
    return output, decisions


def rank(groups, alerts, edges, hypotheses_rows, strategy):
    historical = PHASE27_MODEL["historical"]
    fitted = PHASE27_MODEL["fitted"]["weights"]
    if strategy in ("progression", "phase27_selected"):
        return rank_groups(groups, alerts, edges, hypotheses_rows,
                           "progression" if strategy == "progression" else "train_fitted",
                           historical, fitted)
    if strategy == "hypothesis_aware":
        ordered, scores = rank_groups(groups, alerts, edges, hypotheses_rows,
                                      "train_fitted", historical, fitted)
        # Uncertain hypotheses add a small, explicitly unverified discovery signal.
        for group in groups:
            ids = set(group)
            relevant = [h["confidence"] for h in hypotheses_rows if ids.intersection(h["alert_ids"])]
            scores[group[0]] += .10 * max(relevant, default=0)
        return sorted(groups, key=lambda g: (-scores[g[0]], g[0])), scores
    raise ValueError(strategy)
