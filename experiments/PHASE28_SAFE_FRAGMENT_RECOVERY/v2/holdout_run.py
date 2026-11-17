"""Predict one frozen Phase 28 candidate and baseline, then open truth once."""
import csv
import json
from collections import Counter

from promote import HERE, PHASE27, load, promote, rank
from study import (audit_group, hypothesis_truth, private, sha, union_audit,
                   write_csv, write_json, write_jsonl)


def check_protocol():
    protocol = json.loads((HERE / "pre_evaluation_protocol.json").read_text())
    for name, expected in protocol["hashes"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in protocol["phase27_reference_hashes"].items():
        assert sha(PHASE27 / name) == expected, name
    assert protocol["selected"]["mode"] == "component"
    return protocol


def predict():
    protocol = check_protocol()
    model = json.loads((HERE / "promotion_model.json").read_text())
    manifest = json.loads((HERE / "datasets/locked_test/manifest.json").read_text())
    predictions, decisions, hypotheses_rows, graphs = [], [], [], []
    for item in manifest["queues"]:
        q = item["queue_id"]
        snap, source, edges, baseline_groups, baseline_decisions, hypotheses = load("locked_test", q)
        selected_groups, proposals = promote(baseline_groups, hypotheses, edges, snap.alerts,
                                              snap, model, "component")
        hypotheses_rows.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                                "decision_minute": snap.cutoff, "hypotheses": hypotheses})
        graphs.append({"queue_id": q, "snapshot_sha256": snap.sha256,
                       "decision_minute": snap.cutoff, "edges": edges})
        for mode, groups, proposal_rows in (("baseline", baseline_groups, []),
                                            ("component", selected_groups, proposals)):
            decisions.append({"queue_id": q, "mode": mode, "snapshot_sha256": snap.sha256,
                              "decision_minute": snap.cutoff, "baseline_decisions": baseline_decisions,
                              "promotion_decisions": proposal_rows})
            ranked, scores = rank(groups, snap.alerts, edges, hypotheses, "phase27_selected")
            predictions.append({"queue_id": q, "mode": mode, "ranker": "phase27_selected",
                                "snapshot_sha256": snap.sha256, "decision_minute": snap.cutoff,
                                "eligible_alert_ids": sorted(a["alert_id"] for a in snap.alerts),
                                "groups_ranked": ranked, "scores": scores})
    for name, values in (("locked_predictions.jsonl", predictions),
                         ("locked_decisions.jsonl", decisions),
                         ("locked_hypotheses.jsonl", hypotheses_rows),
                         ("locked_graph.jsonl", graphs)):
        write_jsonl(HERE / name, values)
    public = [HERE / "datasets/locked_test/manifest.json",
              HERE / "datasets/locked_test/injection_manifest.json"]
    for kind in ("alert_headers", "evidence_atoms", "evidence_expectations", "source_records"):
        public.extend(sorted((HERE / "datasets/locked_test" / kind).glob("*.jsonl")))
    write_json(HERE / "locked_prediction_freeze.json", {
        "status": "locked_predictions_frozen_before_truth_open",
        "selected": protocol["selected"],
        "public_input_hashes": {str(p.relative_to(HERE)): sha(p) for p in public},
        "prediction_hashes": {name: sha(HERE / name) for name in
                              ("locked_predictions.jsonl", "locked_decisions.jsonl",
                               "locked_hypotheses.jsonl", "locked_graph.jsonl")}})
    return predictions, decisions, hypotheses_rows, graphs


def audit(predictions, decisions, hypotheses_rows, graphs):
    assert json.loads((HERE / "locked_prediction_freeze.json").read_text())["status"] == \
           "locked_predictions_frozen_before_truth_open"
    queue_rows, promotion_rows, hypothesis_audit = [], [], []
    for p in predictions:
        truth, ranks, families = private("locked_test", p["queue_id"])
        row, _ = audit_group(p, truth, ranks)
        queue_rows.append(row)
    for hrow in hypotheses_rows:
        q = hrow["queue_id"]
        truth, ranks, families = private("locked_test", q)
        eligible = next(p for p in predictions if p["queue_id"] == q)["eligible_alert_ids"]
        lookup = {h["hypothesis_id"]: h for h in hrow["hypotheses"]}
        for h in hrow["hypotheses"]:
            label, incident, hits = hypothesis_truth(h, truth, eligible)
            hypothesis_audit.append({"queue_id": q, "hypothesis_id": h["hypothesis_id"],
                                     "qualifies": label, "best_incident": incident,
                                     "oracle_rank": ranks.get(incident, 99),
                                     "family": families.get(incident, "benign"),
                                     "best_hits": hits, "alert_count": len(h["alert_ids"])})
        decisions_row = next(d for d in decisions if d["queue_id"] == q and d["mode"] == "component")
        for d in decisions_row["promotion_decisions"]:
            h = lookup[d["hypothesis_id"]]
            label, incident, hits = hypothesis_truth(h, truth, eligible)
            promotion_rows.append({"queue_id": q, "hypothesis_id": d["hypothesis_id"],
                                   "decision": d["decision"], "reason": d["reason"],
                                   "score": d["predicted_log_odds"], "threshold": d["threshold"],
                                   "qualifies": label, "best_incident": incident,
                                   "oracle_rank": ranks.get(incident, 99),
                                   "family": families.get(incident, "benign"),
                                   "root_disjoint_witnesses": d["features"]["root_disjoint_witnesses"],
                                   "lineage_types": d["features"]["lineage_types"],
                                   "pair_exposure": d["pair_exposure"]})
    union_rows, cascade = union_audit("locked_test", predictions, decisions)
    for name, values in (("PHASE28_LOCKED_QUEUE_METRICS.csv", queue_rows),
                         ("PHASE28_LOCKED_PROMOTION_AUDIT.csv", promotion_rows),
                         ("PHASE28_LOCKED_HYPOTHESIS_AUDIT.csv", hypothesis_audit),
                         ("PHASE28_LOCKED_UNION_PAIR_AUDIT.csv", union_rows),
                         ("PHASE28_LOCKED_FAILURE_CASCADE.csv", cascade)):
        write_csv(HERE / name, values)
    summary = {}
    for mode in ("baseline", "component"):
        rows = [x for x in queue_rows if x["mode"] == mode]
        tp = sum(x["pair_tp"] for x in rows)
        fp = sum(x["false_grouped_pairs"] for x in rows)
        summary[mode] = {"queues": len(rows), "recoverable": sum(x["recoverable"] for x in rows),
                         "recall10_count": sum(x["recall10_count"] for x in rows),
                         "recall20_count": sum(x["recall20_count"] for x in rows),
                         "p10_count": sum(x["p10_count"] for x in rows),
                         "ndcg20": sum(x["ndcg20"] for x in rows) / len(rows),
                         "pair_precision": tp / (tp + fp) if tp + fp else 1,
                         "false_grouped_pairs": fp,
                         "mixed_groups": sum(x["mixed_groups"] for x in rows)}
    baseline_q = {x["queue_id"]: x for x in queue_rows if x["mode"] == "baseline"}
    candidates = [x for x in queue_rows if x["mode"] == "component"]
    queue_safe = all(x["false_grouped_pairs"] <= baseline_q[x["queue_id"]]["false_grouped_pairs"] and
                     x["mixed_groups"] <= baseline_q[x["queue_id"]]["mixed_groups"] for x in candidates)
    passed = (queue_safe and summary["component"]["recoverable"] > summary["baseline"]["recoverable"]
              and summary["component"]["recall20_count"] > summary["baseline"]["recall20_count"]
              and summary["component"]["p10_count"] >= summary["baseline"]["p10_count"]
              and summary["component"]["pair_precision"] >= .9
              and summary["component"]["false_grouped_pairs"] <= summary["baseline"]["false_grouped_pairs"]
              and summary["component"]["mixed_groups"] <= summary["baseline"]["mixed_groups"])
    write_json(HERE / "locked_result.json", {"baseline": summary["baseline"],
        "selected": summary["component"], "queue_safe": queue_safe,
        "promotions": sum(x["decision"] == "PROMOTE" for x in promotion_rows),
        "true_promotions": sum(x["decision"] == "PROMOTE" and x["qualifies"] for x in promotion_rows),
        "decision": "GO" if passed else "NO-GO"})
    print(json.dumps(json.loads((HERE / "locked_result.json").read_text()), indent=2))


def main():
    predictions, decisions, hypotheses_rows, graphs = predict()
    audit(predictions, decisions, hypotheses_rows, graphs)


if __name__ == "__main__":
    main()
