"""Evaluate only the frozen selected pipeline and its same-cohort baseline once."""
import json
from pathlib import Path

from graph import HERE, build_edges, components, hypotheses, load, rank_groups
from run_study import (audit_group, audit_hypotheses, audit_unions, dump_json,
                       dump_jsonl, historical_weights, private, read, sha, write_csv)


def frozen_selection():
    protocol = json.loads((HERE / "pre_evaluation_protocol.json").read_text())
    for name, expected in protocol["hashes"].items():
        assert sha(HERE / name) == expected, name
    selection = protocol["selected"]
    assert selection["passed"] and selection["mode"] == "phase26_baseline"
    assert selection["ranker"] == "train_fitted"
    return selection


def predict():
    selected = frozen_selection()
    manifest = json.loads((HERE / "datasets/locked_test/manifest.json").read_text())
    model = json.loads((HERE / "ranker_model.json").read_text())
    historical = historical_weights()
    predictions, decisions, graphs, hyps = [], [], [], []
    for item in manifest["queues"]:
        q = item["queue_id"]
        snap, sources = load("locked_test", q)
        edges = build_edges(snap, sources)
        groups, actions = components(snap.alerts, edges, selected["mode"], snap)
        hypotheses_rows = hypotheses(groups, edges)
        graphs.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                       "decision_minute": snap.cutoff, "edges": edges})
        hyps.append({"queue_id": q, "mode": selected["mode"], "snapshot_sha256": snap.sha256,
                     "decision_minute": snap.cutoff, "hypotheses": hypotheses_rows})
        decisions.append({"queue_id": q, "mode": selected["mode"], "snapshot_sha256": snap.sha256,
                          "decision_minute": snap.cutoff, "decisions": actions})
        for ranker in ("progression", selected["ranker"]):
            ranked, scores = rank_groups(groups, snap.alerts, edges, hypotheses_rows, ranker,
                                         historical, model["fitted"]["weights"])
            predictions.append({"queue_id": q, "mode": selected["mode"], "ranker": ranker,
                                "snapshot_sha256": snap.sha256, "decision_minute": snap.cutoff,
                                "eligible_alert_ids": sorted(a["alert_id"] for a in snap.alerts),
                                "groups_ranked": ranked, "scores": scores})
    for name, value in (("locked_predictions.jsonl", predictions),
                        ("locked_decisions.jsonl", decisions),
                        ("locked_graph.jsonl", graphs),
                        ("locked_hypotheses.jsonl", hyps)):
        dump_jsonl(HERE / name, value)
    public = [HERE / "datasets/locked_test/manifest.json"]
    for kind in ("alert_headers", "evidence_atoms", "evidence_expectations", "source_records"):
        public.extend(sorted((HERE / "datasets/locked_test" / kind).glob("*.jsonl")))
    dump_json(HERE / "locked_prediction_freeze.json", {
        "status": "locked_predictions_frozen_before_truth_open",
        "selected": selected,
        "public_input_hashes": {str(p.relative_to(HERE)): sha(p) for p in public},
        "prediction_hashes": {name: sha(HERE / name) for name in
                              ("locked_predictions.jsonl", "locked_decisions.jsonl",
                               "locked_graph.jsonl", "locked_hypotheses.jsonl")}})
    return predictions, decisions, graphs, hyps


def audit(predictions, decisions, graphs, hyps):
    assert json.loads((HERE / "locked_prediction_freeze.json").read_text())["status"] == \
           "locked_predictions_frozen_before_truth_open"
    metrics, incidents, hypotheses_audit, edges_audit = [], [], [], []
    for graph_row in graphs:
        q = graph_row["queue_id"]
        truth, ranks = private("locked_test", q)
        for edge in graph_row["edges"]:
            if edge["source_node"].startswith("alert:"):
                a, b = edge["source_node"][6:], edge["destination_node"][6:]
                edges_audit.append({"queue_id": q, "outcome": edge["outcome"],
                                    "same_incident": int(truth[a] == truth[b]),
                                    "relationship_type": edge["relationship_type"]})
        h = next(x for x in hyps if x["queue_id"] == q)
        eligible = next(x for x in predictions if x["queue_id"] == q)["eligible_alert_ids"]
        hypotheses_audit.extend(audit_hypotheses(h, truth, ranks, eligible))
        for pred in (x for x in predictions if x["queue_id"] == q):
            result, details = audit_group(pred, truth, ranks)
            metrics.append(result)
            incidents.extend(details)
    union_rows, cascades = audit_unions(decisions, predictions, split="locked_test")
    for name, values in (("PHASE27_LOCKED_QUEUE_METRICS.csv", metrics),
                         ("PHASE27_LOCKED_INCIDENT_AUDIT.csv", incidents),
                         ("PHASE27_LOCKED_HYPOTHESES.csv", hypotheses_audit),
                         ("PHASE27_LOCKED_EDGE_AUDIT.csv", edges_audit),
                         ("PHASE27_LOCKED_UNION_AUDIT.csv", union_rows),
                         ("PHASE27_LOCKED_FAILURE_CASCADE.csv", cascades)):
        write_csv(HERE / name, values)
    summary = {}
    for ranker in ("progression", "train_fitted"):
        rows = [x for x in metrics if x["ranker"] == ranker]
        tp = sum(x["pair_tp"] for x in rows)
        fp = sum(x["false_grouped_pairs"] for x in rows)
        summary[ranker] = {"queues": len(rows),
                           "recoverable": sum(x["recoverable"] for x in rows),
                           "recall10_count": sum(x["recall10_count"] for x in rows),
                           "recall20_count": sum(x["recall20_count"] for x in rows),
                           "p10_count": sum(x["p10_count"] for x in rows),
                           "ndcg20": sum(x["ndcg20"] for x in rows) / len(rows),
                           "pair_precision": tp / (tp + fp) if tp + fp else 1,
                           "false_grouped_pairs": fp,
                           "mixed_groups": sum(x["mixed_groups"] for x in rows)}
    baseline = {x["queue_id"]: x for x in metrics if x["ranker"] == "progression"}
    candidate = [x for x in metrics if x["ranker"] == "train_fitted"]
    safety = all(x["false_grouped_pairs"] <= baseline[x["queue_id"]]["false_grouped_pairs"] and
                 x["mixed_groups"] <= baseline[x["queue_id"]]["mixed_groups"] for x in candidate)
    go = (safety and summary["train_fitted"]["recall20_count"] > summary["progression"]["recall20_count"]
          and summary["train_fitted"]["pair_precision"] >= .9)
    dump_json(HERE / "locked_result.json", {"baseline": summary["progression"],
             "selected": summary["train_fitted"], "queue_safe": safety,
             "decision": "GO" if go else "NO-GO"})
    print(json.dumps(json.loads((HERE / "locked_result.json").read_text()), indent=2))


def main():
    predictions, decisions, graphs, hyps = predict()
    audit(predictions, decisions, graphs, hyps)


if __name__ == "__main__":
    main()
