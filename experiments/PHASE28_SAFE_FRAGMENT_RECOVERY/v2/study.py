"""Freeze Phase 28 development predictions before evaluator-only private audit."""
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from promote import (CONFIG, HERE, PHASE27, features, fit_model, load, promote, rank, read)

import sys
sys.path.append(str(PHASE27))
from run_study import audit_group  # noqa: E402; frozen Phase 27 metric definition

MANIFEST = json.loads((HERE / "datasets/manifest.json").read_text())
PIPELINES = (("baseline", "progression"), ("baseline", "phase27_selected"),
             ("baseline", "hypothesis_aware"), ("calibrated", "phase27_selected"),
             ("component", "phase27_selected"), ("selective", "phase27_selected"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def write_jsonl(path, values):
    with Path(path).open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def write_csv(path, values):
    values = list(values)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def private(split, q):
    folder = HERE / "datasets" / split
    truth = {x["alert_id"]: x["incident_id"] for x in read(folder / "ground_truth_private" / f"{q}.jsonl")}
    priority = read(folder / "priority_private" / f"{q}.jsonl")
    priority.sort(key=lambda x: (-x["priority_score"], x["incident_id"]))
    ranks = {x["incident_id"]: i for i, x in enumerate(priority, 1)}
    family = {x["incident_id"]: x["family"] for x in priority}
    return truth, ranks, family


def hypothesis_truth(h, truth, eligible):
    counts = Counter(truth[a] for a in h["alert_ids"])
    incident, hits = counts.most_common(1)[0]
    size = sum(truth[a] == incident for a in eligible)
    return int(hits / size >= .8 and hits / len(h["alert_ids"]) >= .8), incident, hits


def train():
    samples = []
    for item in MANIFEST["queues"]["train"]:
        q = item["queue_id"]
        snap, source, edges, groups, baseline_decisions, hyp = load("train", q)
        truth, _, _ = private("train", q)
        eligible = [a["alert_id"] for a in snap.alerts]
        for h in hyp:
            f = features(h, groups, edges, snap.alerts)
            label, _, _ = hypothesis_truth(h, truth, eligible)
            samples.append((f, label))
    model = fit_model(samples)
    model["training_hypotheses"] = len(samples)
    write_json(HERE / "promotion_model.json", model)
    return model


def predict(split, model, names):
    predictions, decisions, hypothesis_rows, graph_rows = [], [], [], []
    for item in MANIFEST["queues"][split]:
        q = item["queue_id"]
        snap, source, edges, baseline_groups, baseline_decisions, candidates = load(split, q)
        graph_rows.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                           "decision_minute": snap.cutoff, "edges": edges})
        hypothesis_rows.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                                "decision_minute": snap.cutoff, "hypotheses": candidates})
        groups_by_mode = {"baseline": baseline_groups}
        decisions.append({"queue_id": q, "mode": "baseline", "snapshot_sha256": snap.sha256,
                          "decision_minute": snap.cutoff, "baseline_decisions": baseline_decisions,
                          "promotion_decisions": []})
        for mode in ("calibrated", "component", "selective"):
            groups, proposals = promote(baseline_groups, candidates, edges, snap.alerts, snap, model, mode)
            groups_by_mode[mode] = groups
            decisions.append({"queue_id": q, "mode": mode, "snapshot_sha256": snap.sha256,
                              "decision_minute": snap.cutoff, "baseline_decisions": baseline_decisions,
                              "promotion_decisions": proposals})
        for mode, ranker in PIPELINES:
            groups = groups_by_mode[mode]
            ranked, scores = rank(groups, snap.alerts, edges, candidates, ranker)
            predictions.append({"queue_id": q, "mode": mode, "ranker": ranker,
                                "snapshot_sha256": snap.sha256, "decision_minute": snap.cutoff,
                                "eligible_alert_ids": sorted(a["alert_id"] for a in snap.alerts),
                                "groups_ranked": ranked, "scores": scores})
    for name, value in ((names[0], predictions), (names[1], decisions),
                        (names[2], hypothesis_rows), (names[3], graph_rows)):
        write_jsonl(HERE / name, value)
    return predictions, decisions, hypothesis_rows, graph_rows


def freeze_development():
    model = train()
    predictions, decisions, hypotheses_rows, graphs = predict("development", model,
        ("development_predictions.jsonl", "development_decisions.jsonl",
         "development_hypotheses.jsonl", "development_graph.jsonl"))
    names = ("config.json", "generate.py", "promote.py", "study.py", "datasets/manifest.json",
             "promotion_model.json", "development_predictions.jsonl",
             "development_decisions.jsonl", "development_hypotheses.jsonl", "development_graph.jsonl")
    write_json(HERE / "development_freeze.json", {
        "status": "development_predictions_frozen_before_private_audit",
        "phase27_reference_hashes": {"graph.py": sha(PHASE27 / "graph.py"),
                                     "evidence.py": sha(PHASE27 / "evidence.py"),
                                     "ranker_model.json": sha(PHASE27 / "ranker_model.json")},
        "hashes": {name: sha(HERE / name) for name in names}})
    return predictions, decisions, hypotheses_rows, graphs


def union_audit(split, predictions, decisions):
    pred = {(x["queue_id"], x["mode"]): x for x in predictions if x["ranker"] == "phase27_selected"}
    rows, cascade = [], []
    for item in decisions:
        q, mode = item["queue_id"], item["mode"]
        truth, _, _ = private(split, q)
        ids = pred[q, mode]["eligible_alert_ids"]
        parent = {a: a for a in ids}
        counts = {a: Counter([truth[a]]) for a in ids}
        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        order = 0
        actions = []
        for d in item["baseline_decisions"]:
            if d["decision"] == "accept":
                actions.append((d["left"][0], d["right"][0], "baseline_" + d["reason"], ""))
        for d in item["promotion_decisions"]:
            if d["decision"] == "PROMOTE":
                parts = d["pre_components"]
                for part in parts[1:]:
                    actions.append((parts[0][0], part[0], "promotion_" + d["reason"], d["hypothesis_id"]))
        for a, b, reason, hypothesis_id in actions:
            ra, rb = root(a), root(b)
            if ra == rb:
                continue
            ca, cb = counts[ra], counts[rb]
            false = sum(x * y for i, x in ca.items() for j, y in cb.items() if i != j)
            rows.append({"queue_id": q, "mode": mode, "order": order, "reason": reason,
                         "hypothesis_id": hypothesis_id, "left_size": sum(ca.values()),
                         "right_size": sum(cb.values()), "new_false_pairs": false,
                         "premerge_pair_exposure": sum(ca.values()) * sum(cb.values())})
            parent[rb] = ra
            counts[ra] += counts[rb]
            del counts[rb]
            order += 1
        final = sum(len(g) * (len(g) - 1) // 2 -
                    sum(n * (n - 1) // 2 for n in Counter(truth[a] for a in g).values())
                    for g in pred[q, mode]["groups_ranked"])
        increment = sum(x["new_false_pairs"] for x in rows if x["queue_id"] == q and x["mode"] == mode)
        assert final == increment, (q, mode, final, increment)
        cascade.append({"queue_id": q, "mode": mode, "accepted_unions": order,
                        "false_pair_creating_unions": sum(x["queue_id"] == q and x["mode"] == mode and
                                                           x["new_false_pairs"] > 0 for x in rows),
                        "false_pairs": final,
                        "worst_union_false_pairs": max((x["new_false_pairs"] for x in rows if
                                                        x["queue_id"] == q and x["mode"] == mode), default=0)})
    return rows, cascade


def opportunity_audit(split, predictions, hypotheses_rows, graphs):
    by_pred = {(x["queue_id"], x["ranker"]): x for x in predictions if x["mode"] == "baseline"}
    by_hyp = {x["queue_id"]: x["hypotheses"] for x in hypotheses_rows}
    by_graph = {x["queue_id"]: x["edges"] for x in graphs}
    output = []
    for q in by_hyp:
        truth, ranks, families = private(split, q)
        p = by_pred[q, "phase27_selected"]
        groups = p["groups_ranked"]
        eligible = p["eligible_alert_ids"]
        size = Counter(truth[a] for a in eligible)
        snap, source, edges, baseline_groups, _, _ = load(split, q)
        for incident, oracle_rank in ranks.items():
            if oracle_rank > 20:
                continue
            qualifying = []
            for pos, group in enumerate(groups, 1):
                hits = sum(truth[a] == incident for a in group)
                if hits / size[incident] >= .8 and hits / len(group) >= .8:
                    qualifying.append(pos)
            if qualifying and min(qualifying) <= 20:
                continue
            incident_ids = {a for a in eligible if truth[a] == incident}
            touching = [h for h in by_hyp[q] if incident_ids.intersection(h["alert_ids"])]
            good = [h for h in touching if hypothesis_truth(h, truth, eligible)[0] and
                    hypothesis_truth(h, truth, eligible)[1] == incident]
            if qualifying:
                category = "G_ranked_outside_top20"
            elif not touching:
                incident_edges = [e for e in by_graph[q] if e["outcome"] == "CANDIDATE" and
                                  e["source_node"].startswith("alert:") and
                                  e["source_node"][6:] in incident_ids and e["destination_node"][6:] in incident_ids]
                category = "B_edges_insufficient_hypothesis" if incident_edges else "A_no_candidate_relationship"
            elif not good:
                category = "B_hypothesis_incomplete"
            else:
                best = max(good, key=lambda h: h["confidence"])
                f = features(best, baseline_groups, edges, snap.alerts)
                if f["host_contradiction"] or f["account_contradiction"]:
                    category = "D_visible_contradiction"
                elif any(snap.states[a, field] == "NOT_YET_AVAILABLE" for a in best["alert_ids"]
                         for field in ("host", "account")):
                    category = "E_pending_evidence"
                elif f["root_disjoint_witnesses"] < 2 or f["duplicate_fraction"] > .2:
                    category = "F_correlated_or_duplicate_witnesses"
                else:
                    category = "C_positive_evidence_needs_commit_check"
            output.append({"split": split, "queue_id": q, "incident_id": incident,
                           "oracle_rank": oracle_rank, "family": families[incident],
                           "category": category, "visible_alerts": size[incident],
                           "touching_hypotheses": len(touching), "qualifying_hypotheses": len(good)})
    return output


def audit(split, predictions, decisions, hypotheses_rows, graphs, prefix="PHASE28"):
    queue_rows, incident_rows, hypothesis_audit, promotion_audit = [], [], [], []
    dlookup = {(x["queue_id"], x["mode"]): x for x in decisions}
    for p in predictions:
        truth, ranks, families = private(split, p["queue_id"])
        metrics, incidents = audit_group(p, truth, ranks)
        queue_rows.append(metrics)
        for x in incidents:
            x["family"] = families[x["incident_id"]]
        incident_rows.extend(incidents)
    for row in hypotheses_rows:
        q = row["queue_id"]
        truth, ranks, families = private(split, q)
        eligible = next(x for x in predictions if x["queue_id"] == q)["eligible_alert_ids"]
        for h in row["hypotheses"]:
            label, incident, hits = hypothesis_truth(h, truth, eligible)
            hypothesis_audit.append({"queue_id": q, "hypothesis_id": h["hypothesis_id"],
                                     "qualifies": label, "best_incident": incident,
                                     "oracle_rank": ranks.get(incident, 99),
                                     "family": families.get(incident, "benign"),
                                     "best_hits": hits, "alert_count": len(h["alert_ids"]),
                                     "fragment_count": len(h["fragments"]),
                                     "confidence": h["confidence"]})
    for row in decisions:
        q = row["queue_id"]
        truth, ranks, families = private(split, q)
        eligible = next(x for x in predictions if x["queue_id"] == q)["eligible_alert_ids"]
        for d in row["promotion_decisions"]:
            candidate = next(h for h in next(x for x in hypotheses_rows if x["queue_id"] == q)["hypotheses"]
                             if h["hypothesis_id"] == d["hypothesis_id"])
            label, incident, hits = hypothesis_truth(candidate, truth, eligible)
            promotion_audit.append({"queue_id": q, "mode": row["mode"],
                                    "hypothesis_id": d["hypothesis_id"], "decision": d["decision"],
                                    "reason": d["reason"], "score": d["predicted_log_odds"],
                                    "threshold": d["threshold"], "qualifies": label,
                                    "best_incident": incident, "oracle_rank": ranks.get(incident, 99),
                                    "family": families.get(incident, "benign"),
                                    "fragments": d["features"]["fragments"],
                                    "lineage_types": d["features"]["lineage_types"],
                                    "root_disjoint_witnesses": d["features"]["root_disjoint_witnesses"],
                                    "pair_exposure": d["pair_exposure"]})
    unions, cascade = union_audit(split, predictions, decisions)
    opportunities = opportunity_audit(split, predictions, hypotheses_rows, graphs)
    for name, data in (("QUEUE_METRICS", queue_rows), ("INCIDENT_AUDIT", incident_rows),
                       ("HYPOTHESIS_AUDIT", hypothesis_audit), ("PROMOTION_AUDIT", promotion_audit),
                       ("UNION_PAIR_AUDIT", unions), ("FAILURE_CASCADE", cascade),
                       ("RECOVERY_OPPORTUNITIES", opportunities)):
        write_csv(HERE / f"{prefix}_{name}.csv", data)
    comparison = []
    for mode, ranker in PIPELINES:
        subset = [x for x in queue_rows if x["mode"] == mode and x["ranker"] == ranker]
        tp = sum(x["pair_tp"] for x in subset)
        fp = sum(x["false_grouped_pairs"] for x in subset)
        d = [x for x in promotion_audit if x["mode"] == mode]
        comparison.append({"mode": mode, "ranker": ranker, "queues": len(subset),
                           "recoverable": sum(x["recoverable"] for x in subset),
                           "recall10_count": sum(x["recall10_count"] for x in subset),
                           "recall20_count": sum(x["recall20_count"] for x in subset),
                           "p10_count": sum(x["p10_count"] for x in subset),
                           "ndcg20": sum(x["ndcg20"] for x in subset) / len(subset),
                           "pair_precision": tp / (tp + fp) if tp + fp else 1,
                           "false_grouped_pairs": fp,
                           "mixed_groups": sum(x["mixed_groups"] for x in subset),
                           "promotions": sum(x["decision"] == "PROMOTE" for x in d),
                           "true_promotions": sum(x["decision"] == "PROMOTE" and x["qualifies"] for x in d),
                           "abstentions": sum(x["decision"] == "RETAIN AS HYPOTHESIS" for x in d),
                           "rejections": sum(x["decision"] == "REJECT" for x in d)})
    write_csv(HERE / f"{prefix}_EXPERIMENT_COMPARISON.csv", comparison)
    return comparison, queue_rows, promotion_audit, opportunities


def select(comparison, queues):
    baseline = next(x for x in comparison if x["mode"] == "baseline" and x["ranker"] == "phase27_selected")
    base_q = {x["queue_id"]: x for x in queues if x["mode"] == "baseline" and
              x["ranker"] == "phase27_selected"}
    gates = []
    for row in comparison:
        subset = [x for x in queues if x["mode"] == row["mode"] and x["ranker"] == row["ranker"]]
        queue_safe = all(x["false_grouped_pairs"] <= base_q[x["queue_id"]]["false_grouped_pairs"] and
                         x["mixed_groups"] <= base_q[x["queue_id"]]["mixed_groups"] for x in subset)
        passed = (row["mode"] != "baseline" and row["recoverable"] > baseline["recoverable"] and
                  row["recall20_count"] > baseline["recall20_count"] and
                  row["p10_count"] >= baseline["p10_count"] and row["pair_precision"] >= .9 and
                  row["false_grouped_pairs"] <= baseline["false_grouped_pairs"] and
                  row["mixed_groups"] <= baseline["mixed_groups"] and queue_safe)
        gates.append({"mode": row["mode"], "ranker": row["ranker"], "passed": passed,
                      "queue_safe": queue_safe, "recoverable": row["recoverable"],
                      "recall20_count": row["recall20_count"], "p10_count": row["p10_count"],
                      "false_grouped_pairs": row["false_grouped_pairs"],
                      "mixed_groups": row["mixed_groups"]})
    write_csv(HERE / "PHASE28_DEVELOPMENT_GATES.csv", gates)
    passed = [x for x in gates if x["passed"]]
    selected = max(passed, key=lambda x: (int(x["recall20_count"]), int(x["recoverable"]),
                                          x["mode"])) if passed else None
    write_json(HERE / "development_selection.json", {"baseline": baseline,
        "selected": selected, "eligible_candidates": len(passed), "decision": "SELECT" if selected else "NO-GO"})
    return selected


def main():
    predictions, decisions, hypotheses_rows, graphs = freeze_development()
    comparison, queues, promotions, opportunities = audit("development", predictions, decisions,
                                                             hypotheses_rows, graphs)
    selected = select(comparison, queues)
    print(json.dumps({"model": json.loads((HERE / "promotion_model.json").read_text()),
                      "selected": selected, "comparison": comparison}, indent=2))


if __name__ == "__main__":
    main()
