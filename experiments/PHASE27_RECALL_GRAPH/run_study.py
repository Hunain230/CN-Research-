"""Freeze label-blind graph predictions, then audit private development truth."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from graph import (HERE, build_edges, components, graph_features, hypotheses, legacy_features,
                   load, rank_groups, read)

CFG = json.loads((HERE / "config.json").read_text())
MANIFEST = json.loads((HERE / "datasets/manifest.json").read_text())
MODES = ("phase26_baseline", "phase25_veto", "graph_conservative", "graph_selective",
         "graph_no_uncertain", "graph_risk", "graph_bounded")
RANKERS = ("progression", "phase25_linear", "phase26_blend", "candidate_graph",
           "fragment_aggregation", "graph_progression", "train_fitted")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def dump_jsonl(path, values):
    with Path(path).open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def write_csv(path, values):
    values = list(values)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def read_incident_audit():
    with (HERE / "PHASE27_INCIDENT_AUDIT.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def historical_weights():
    a = json.loads((HERE.parent / "PHASE25_SAFE_RECALL/ranker_model.json").read_text())
    b = json.loads((HERE.parent / "PHASE26_POINT_IN_TIME_SAFETY/v2/ranker_model.json").read_text())
    return {"phase25_linear": a["linear_weights"], "phase26_blend": b["weights"],
            "source_hashes": {"phase25": sha(HERE.parent / "PHASE25_SAFE_RECALL/ranker_model.json"),
                              "phase26": sha(HERE.parent / "PHASE26_POINT_IN_TIME_SAFETY/v2/ranker_model.json")}}


def private(split, q):
    folder = HERE / "datasets" / split
    truth = {x["alert_id"]: x["incident_id"] for x in read(folder / "ground_truth_private" / f"{q}.jsonl")}
    priority = read(folder / "priority_private" / f"{q}.jsonl")
    priority.sort(key=lambda x: (-x["priority_score"], x["incident_id"]))
    ranks = {x["incident_id"]: pos for pos, x in enumerate(priority, 1)}
    return truth, ranks


def fit_train(train_rows):
    # Transparent lightweight supervised contrast: relevant versus other fixed groups.
    positives, negatives = [], []
    for q, alerts, edges, groups, hyp in train_rows:
        truth, ranks = private("train", q)
        lookup = {a["alert_id"]: a for a in alerts}
        total = Counter(truth[a] for a in lookup)
        for group in groups:
            counts = Counter(truth[a] for a in group)
            relevant = any(ranks.get(i, 99) <= 20 and n / total[i] >= .8 and
                           n / len(group) >= .8 for i, n in counts.items())
            vec = legacy_features(group, lookup) + graph_features(group, groups, edges, hyp)
            (positives if relevant else negatives).append(vec)
    means = [sum(v[i] for v in positives + negatives) / (len(positives) + len(negatives))
             for i in range(len(positives[0]))]
    stdev = [max(.1, (sum((v[i] - means[i]) ** 2 for v in positives + negatives) /
                        (len(positives) + len(negatives))) ** .5) for i in range(len(means))]
    weights = [(sum(v[i] for v in positives) / len(positives) -
                sum(v[i] for v in negatives) / len(negatives)) / stdev[i]
               for i in range(len(means))]
    return {"weights": weights, "positive_groups": len(positives),
            "negative_groups": len(negatives), "means": means, "stdev": stdev}


def predict_all():
    historical = historical_weights()
    train_rows = []
    for item in MANIFEST["queues"]["train"]:
        q = item["queue_id"]
        snap, sources = load("train", q)
        edges = build_edges(snap, sources)
        groups, _ = components(snap.alerts, edges, "graph_no_uncertain", snap)
        train_rows.append((q, snap.alerts, edges, groups, hypotheses(groups, edges)))
    model = fit_train(train_rows)
    dump_json(HERE / "ranker_model.json", {"fitted": model, "historical": historical})

    predictions, decisions, graph_rows, hypotheses_rows, availability = [], [], [], [], []
    for item in MANIFEST["queues"]["development"]:
        q = item["queue_id"]
        snap, sources = load("development", q)
        edges = build_edges(snap, sources)
        graph_rows.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                           "decision_minute": snap.cutoff, "edges": edges})
        availability.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                             "decision_minute": snap.cutoff, "visible_alerts": len(snap.alerts),
                             **dict(Counter(snap.states.values()))})
        for mode in MODES:
            groups, actions = components(snap.alerts, edges, mode, snap)
            hyp = hypotheses(groups, edges, bound=4 if mode == "graph_bounded" else 8)
            hypotheses_rows.append({"queue_id": q, "mode": mode,
                                    "snapshot_sha256": snap.sha256,
                                    "decision_minute": snap.cutoff, "hypotheses": hyp})
            decisions.append({"queue_id": q, "mode": mode,
                              "snapshot_sha256": snap.sha256,
                              "decision_minute": snap.cutoff, "decisions": actions})
            for ranker in RANKERS:
                ranked, scores = rank_groups(groups, snap.alerts, edges, hyp, ranker,
                                             historical, model["weights"])
                predictions.append({"queue_id": q, "mode": mode, "ranker": ranker,
                                    "snapshot_sha256": snap.sha256,
                                    "decision_minute": snap.cutoff,
                                    "eligible_alert_ids": sorted(a["alert_id"] for a in snap.alerts),
                                    "groups_ranked": ranked, "scores": scores})
    for name, data in (("development_predictions.jsonl", predictions),
                       ("development_decisions.jsonl", decisions),
                       ("development_graph.jsonl", graph_rows),
                       ("development_hypotheses.jsonl", hypotheses_rows),
                       ("evidence_availability.jsonl", availability)):
        dump_jsonl(HERE / name, data)
    source_names = ("config.json", "generate.py", "evidence.py", "graph.py", "run_study.py",
                    "datasets/manifest.json", "ranker_model.json", "development_predictions.jsonl",
                    "development_decisions.jsonl", "development_graph.jsonl",
                    "development_hypotheses.jsonl", "evidence_availability.jsonl")
    dump_json(HERE / "freeze_manifest.json", {"status": "development_predictions_frozen_before_private_audit",
              "locked_cohort_created": False,
              "hashes": {name: sha(HERE / name) for name in source_names}})
    return predictions, decisions, graph_rows, hypotheses_rows


def audit_group(pred, truth, ranks):
    groups = pred["groups_ranked"]
    eligible = set(pred["eligible_alert_ids"])
    assert eligible == {a for g in groups for a in g}
    assert sum(map(len, groups)) == len(eligible)
    sizes = Counter(truth[a] for a in eligible)
    qualifiers = defaultdict(list)
    tp = fp = mixed = 0
    for pos, group in enumerate(groups, 1):
        counts = Counter(truth[a] for a in group)
        tp += sum(n * (n - 1) // 2 for n in counts.values())
        fp += len(group) * (len(group) - 1) // 2 - sum(n * (n - 1) // 2 for n in counts.values())
        mixed += len(counts) > 1
        for incident, hits in counts.items():
            if ranks.get(incident, 99) <= 20 and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                qualifiers[incident].append(pos)
    recovered = {i for i, r in ranks.items() if r <= 20 and i in qualifiers}
    recall20 = {i for i in recovered if min(qualifiers[i]) <= 20}
    recall10 = {i for i in recovered if min(qualifiers[i]) <= 10}
    credited = set()
    p10 = 0
    dcg = 0.0
    for pos in range(1, min(20, len(groups)) + 1):
        candidates = [i for i, places in qualifiers.items() if pos in places and i not in credited]
        if candidates:
            incident = min(candidates, key=lambda i: ranks[i])
            credited.add(incident)
            if pos <= 10 and ranks[incident] <= 10:
                p10 += 1
            dcg += (26 - ranks[incident]) / math.log2(pos + 1)
    ideal = sum((26 - r) / math.log2(r + 1) for r in range(1, 21))
    row = {"queue_id": pred["queue_id"], "mode": pred["mode"], "ranker": pred["ranker"],
           "recoverable": len(recovered), "recall10_count": len(recall10),
           "recall20_count": len(recall20), "p10_count": p10, "ndcg20": dcg / ideal,
           "pair_tp": tp, "false_grouped_pairs": fp, "mixed_groups": mixed,
           "pair_precision": tp / (tp + fp) if tp + fp else 1.0,
           "groups": len(groups), "eligible_alerts": len(eligible)}
    incidents = []
    for incident, rank in ranks.items():
        if rank > 20:
            continue
        best = max((sum(truth[a] == incident for a in g) for g in groups), default=0)
        position = min(qualifiers[incident]) if incident in qualifiers else None
        status = "recalled" if position and position <= 20 else \
                 "ranking_only" if position else "fragmented" if best / sizes[incident] < .8 else "impure"
        incidents.append({"queue_id": pred["queue_id"], "mode": pred["mode"],
                          "ranker": pred["ranker"], "incident_id": incident,
                          "oracle_rank": rank, "eligible_alerts": sizes[incident],
                          "best_group_overlap": best, "qualifying_position": position or "",
                          "status": status})
    return row, incidents


def audit_hypotheses(row, truth, ranks, eligible):
    sizes = Counter(truth[a] for a in eligible)
    results = []
    for h in row["hypotheses"]:
        counts = Counter(truth[a] for a in h["alert_ids"])
        best_incident, hits = counts.most_common(1)[0]
        qualifies = hits / sizes[best_incident] >= .8 and hits / len(h["alert_ids"]) >= .8
        results.append({"queue_id": row["queue_id"], "mode": row["mode"],
                        "hypothesis_id": h["hypothesis_id"], "alert_count": len(h["alert_ids"]),
                        "fragments": len(h["fragments"]), "edge_count": h["edge_count"],
                        "independent_paths": h["independent_paths"], "confidence": h["confidence"],
                        "best_incident": best_incident, "best_hits": hits,
                        "qualifies": int(qualifies), "priority_rank": ranks.get(best_incident, 99),
                        "false_alerts": len(h["alert_ids"]) - hits,
                        "committed": int(h["committed"])})
    return results


def audit_unions(decisions, predictions):
    result = []
    cascade = []
    pred = {(p["queue_id"], p["mode"]): p for p in predictions if p["ranker"] == "progression"}
    for item in decisions:
        q, mode = item["queue_id"], item["mode"]
        truth, _ = private("development", q)
        eligible = set(pred[q, mode]["eligible_alert_ids"])
        parent = {a: a for a in eligible}
        counts = {a: Counter([truth[a]]) for a in eligible}
        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        order = 0
        for d in item["decisions"]:
            if d["decision"].lower() != "accept":
                continue
            a, b = root(d["left"][0]), root(d["right"][0])
            if a == b:
                continue
            ca, cb = counts[a], counts[b]
            new_false = sum(x * y for i, x in ca.items() for j, y in cb.items() if i != j)
            result.append({"queue_id": q, "mode": mode, "order": order,
                           "reason": d["reason"], "left_size": sum(ca.values()),
                           "right_size": sum(cb.values()), "new_false_pairs": new_false,
                           "premerge_pair_exposure": sum(ca.values()) * sum(cb.values())})
            parent[b] = a
            counts[a] += counts[b]
            del counts[b]
            order += 1
        final_fp = sum(len(g) * (len(g) - 1) // 2 -
                       sum(n * (n - 1) // 2 for n in Counter(truth[a] for a in g).values())
                       for g in pred[q, mode]["groups_ranked"])
        assert final_fp == sum(int(x["new_false_pairs"]) for x in result if
                               x["queue_id"] == q and x["mode"] == mode)
        cascade.append({"queue_id": q, "mode": mode, "accepted_unions": order,
                        "false_pair_creating_unions": sum(x["queue_id"] == q and x["mode"] == mode and
                                                           x["new_false_pairs"] > 0 for x in result),
                        "false_pairs": final_fp,
                        "worst_union_false_pairs": max((x["new_false_pairs"] for x in result if
                                                        x["queue_id"] == q and x["mode"] == mode), default=0)})
    return result, cascade


def audit(predictions, decisions, graphs, hypothesis_rows):
    queue_rows, incident_rows, hyp_audit, edge_audit = [], [], [], []
    pred_lookup = {(p["queue_id"], p["mode"], p["ranker"]): p for p in predictions}
    for graph_row in graphs:
        q = graph_row["queue_id"]
        truth, ranks = private("development", q)
        snap, _ = load("development", q)
        for edge in graph_row["edges"]:
            if not edge["source_node"].startswith("alert:"):
                continue
            a, b = edge["source_node"][6:], edge["destination_node"][6:]
            edge_audit.append({"queue_id": q, "source_node": edge["source_node"],
                               "destination_node": edge["destination_node"],
                               "outcome": edge["outcome"], "relationship_type": edge["relationship_type"],
                               "confidence": edge["confidence"], "independence": edge["independence"],
                               "same_incident": int(truth[a] == truth[b]),
                               "same_priority_incident": int(truth[a] == truth[b] and ranks.get(truth[a], 99) <= 20),
                               "receiver_visible_minute": edge["receiver_visible_minute"]})
        for mode in MODES:
            h = next(x for x in hypothesis_rows if x["queue_id"] == q and x["mode"] == mode)
            eligible = pred_lookup[q, mode, "progression"]["eligible_alert_ids"]
            hyp_audit.extend(audit_hypotheses(h, truth, ranks, eligible))
            for ranker in RANKERS:
                row, incidents = audit_group(pred_lookup[q, mode, ranker], truth, ranks)
                queue_rows.append(row)
                incident_rows.extend(incidents)
    unions, cascades = audit_unions(decisions, predictions)
    for name, values in (("PHASE27_QUEUE_METRICS.csv", queue_rows),
                         ("PHASE27_EDGE_AUDIT.csv", edge_audit),
                         ("PHASE27_INCIDENT_HYPOTHESES.csv", hyp_audit),
                         ("PHASE27_FAILURE_CASCADE.csv", cascades),
                         ("PHASE27_UNION_PAIR_AUDIT.csv", unions),
                         ("PHASE27_INCIDENT_AUDIT.csv", incident_rows)):
        write_csv(HERE / name, values)
    comparison = []
    for mode in MODES:
        for ranker in RANKERS:
            subset = [x for x in queue_rows if x["mode"] == mode and x["ranker"] == ranker]
            tp = sum(x["pair_tp"] for x in subset)
            fp = sum(x["false_grouped_pairs"] for x in subset)
            comparison.append({"mode": mode, "ranker": ranker, "queues": len(subset),
                               "recoverable": sum(x["recoverable"] for x in subset),
                               "recall10_count": sum(x["recall10_count"] for x in subset),
                               "recall20_count": sum(x["recall20_count"] for x in subset),
                               "p10_count": sum(x["p10_count"] for x in subset),
                               "ndcg20": sum(x["ndcg20"] for x in subset) / len(subset),
                               "pair_precision": tp / (tp + fp) if tp + fp else 1,
                               "false_grouped_pairs": fp,
                               "mixed_groups": sum(x["mixed_groups"] for x in subset),
                               "accepted_unions": sum(x["accepted_unions"] for x in cascades if x["mode"] == mode)})
    write_csv(HERE / "PHASE27_EXPERIMENT_COMPARISON.csv", comparison)
    return comparison, queue_rows, edge_audit, hyp_audit


def select(comparison, queues, edges, hypotheses_audit):
    base = next(x for x in comparison if x["mode"] == "phase26_baseline" and x["ranker"] == "progression")
    baseline_q = {x["queue_id"]: x for x in queues if x["mode"] == "phase26_baseline" and
                  x["ranker"] == "progression"}
    base_recovered = {x["incident_id"] for x in read_incident_audit() if
                      x["mode"] == "phase26_baseline" and x["ranker"] == "progression" and
                      x["status"] in ("recalled", "ranking_only")}
    gate = []
    for row in comparison:
        subset = [x for x in queues if x["mode"] == row["mode"] and x["ranker"] == row["ranker"]]
        discovered = {x["best_incident"] for x in hypotheses_audit if x["mode"] == row["mode"] and
                      x["qualifies"] and x["priority_rank"] <= 20}
        queue_safe = all(x["false_grouped_pairs"] <= baseline_q[x["queue_id"]]["false_grouped_pairs"] and
                         x["mixed_groups"] <= baseline_q[x["queue_id"]]["mixed_groups"] for x in subset)
        novel = discovered - base_recovered
        passed = (row["recall20_count"] > base["recall20_count"] and
                  (row["recoverable"] > base["recoverable"] or len(novel) > 0) and
                  row["pair_precision"] >= .9 and
                  row["false_grouped_pairs"] <= base["false_grouped_pairs"] and
                  row["mixed_groups"] <= base["mixed_groups"] and queue_safe)
        gate.append({"mode": row["mode"], "ranker": row["ranker"], "passed": passed,
                     "queue_safe": queue_safe, "hypothesis_recalled": len(discovered),
                     "novel_hypothesis_incidents": len(novel),
                     "recoverable": row["recoverable"], "recall20_count": row["recall20_count"],
                     "false_grouped_pairs": row["false_grouped_pairs"], "mixed_groups": row["mixed_groups"]})
    write_csv(HERE / "PHASE27_GATE_RESULTS.csv", gate)
    passed = [x for x in gate if x["passed"]]
    selected = max(passed, key=lambda x: (x["recall20_count"], x["recoverable"],
                                          -x["false_grouped_pairs"], x["mode"], x["ranker"])) if passed else None
    dump_json(HERE / "development_selection.json", {"baseline": base, "selected": selected,
                                                       "eligible_candidates": len(passed)})
    return selected


def main():
    predictions, decisions, graphs, hyps = predict_all()
    comparison, queues, edges, hypotheses_audit = audit(predictions, decisions, graphs, hyps)
    selected = select(comparison, queues, edges, hypotheses_audit)
    print(json.dumps({"selected": selected, "baseline": next(x for x in comparison if
                      x["mode"] == "phase26_baseline" and x["ranker"] == "progression")}, indent=2))


if __name__ == "__main__":
    main()
