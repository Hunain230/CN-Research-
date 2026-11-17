"""Read-only Phase 27 retrospective analysis; frozen inference is untouched."""
import csv
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / "v3"
sys.path.insert(0, str(V))
from graph import graph_features, load  # noqa: E402


def read_csv(name):
    with (V / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(name):
    with (V / name).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def write_csv(name, values):
    values = list(values)
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def interval(queue_rows, ranker, rounds=2000):
    by_q = defaultdict(dict)
    for row in queue_rows:
        if row["mode"] == "phase26_baseline" and row["ranker"] in ("progression", ranker):
            by_q[row["queue_id"]][row["ranker"]] = row
    pairs = list(by_q.values())
    rng = random.Random(270777)
    values = []
    for _ in range(rounds):
        sample = rng.choices(pairs, k=len(pairs))
        values.append(sum(int(x[ranker]["recall20_count"]) -
                          int(x["progression"]["recall20_count"]) for x in sample) /
                      (20 * len(sample)))
    values.sort()
    return [round(values[49], 6), round(values[1949], 6)]


def edge_coverage(split, graph_name, pred_name):
    graphs = read_jsonl(graph_name)
    predictions = {(x["queue_id"], x["ranker"]): x for x in read_jsonl(pred_name)
                   if x["mode"] == "phase26_baseline" and x["ranker"] == "progression"}
    counts = Counter()
    for graph in graphs:
        q = graph["queue_id"]
        group_of = {a: i for i, group in enumerate(predictions[q, "progression"]["groups_ranked"])
                    for a in group}
        truth = {x["alert_id"]: x["incident_id"] for x in read_jsonl(
            f"datasets/{split}/ground_truth_private/{q}.jsonl")}
        by_incident = defaultdict(list)
        for a in group_of:
            by_incident[truth[a]].append(a)
        for alerts in by_incident.values():
            for pos, a in enumerate(alerts):
                counts["eligible_same_incident_cross_group_pairs"] += sum(
                    group_of[a] != group_of[b] for b in alerts[pos + 1:])
        for edge in graph["edges"]:
            if edge["outcome"] != "CANDIDATE" or not edge["source_node"].startswith("alert:"):
                continue
            a, b = edge["source_node"][6:], edge["destination_node"][6:]
            if group_of[a] != group_of[b] and truth[a] == truth[b]:
                counts["candidate_true_cross_group_pairs"] += 1
    counts["candidate_cross_group_pair_recall"] = round(
        counts["candidate_true_cross_group_pairs"] /
        counts["eligible_same_incident_cross_group_pairs"], 6)
    return dict(counts)


def hypothesis_summary(split, hyp_file, incident_file, mode="phase26_baseline"):
    hyps = [x for x in read_csv(hyp_file) if x["mode"] == mode]
    incidents = [x for x in read_csv(incident_file) if x["mode"] == mode and
                 x["ranker"] == "progression"]
    discovered = {x["best_incident"] for x in hyps if x["qualifies"] == "1" and
                  int(x["priority_rank"]) <= 20}
    recovered = {x["incident_id"] for x in incidents if x["status"] in ("recalled", "ranking_only")}
    return {"hypotheses": len(hyps), "qualifying_hypotheses": sum(x["qualifies"] == "1" for x in hyps),
            "hypothesis_precision": sum(x["qualifies"] == "1" for x in hyps) / len(hyps),
            "top20_incidents_hypothesized": len(discovered),
            "top20_incidents_new_beyond_groups": len(discovered - recovered),
            "official_group_recoverable": len(recovered),
            "top20_incident_denominator": 20 * (20 if split == "development" else 30)}


def hypothesis_ranking(split, hyp_file, mode="phase26_baseline"):
    by_queue = defaultdict(list)
    for x in read_csv(hyp_file):
        if x["mode"] == mode:
            by_queue[x["queue_id"]].append(x)
    output = []
    for q, items in by_queue.items():
        ordered = sorted(items, key=lambda x: (-float(x["confidence"]), x["hypothesis_id"]))[:20]
        correct = {x["best_incident"] for x in ordered if x["qualifies"] == "1" and
                   int(x["priority_rank"]) <= 20}
        output.append({"split": split, "queue_id": q, "top20_hypotheses": len(ordered),
                       "false_hypothesis_rankings": sum(x["qualifies"] != "1" for x in ordered),
                       "off_priority_hypothesis_rankings": sum(x["qualifies"] == "1" and
                                                               int(x["priority_rank"]) > 20 for x in ordered),
                       "distinct_top20_incidents_found": len(correct)})
    return output


def fragment_counts(split, pred_name):
    predictions = [x for x in read_jsonl(pred_name) if x["mode"] == "phase26_baseline" and
                   x["ranker"] == "progression"]
    output = []
    for pred in predictions:
        q = pred["queue_id"]
        folder = f"datasets/{split}"
        truth = {x["alert_id"]: x["incident_id"] for x in read_jsonl(
            f"{folder}/ground_truth_private/{q}.jsonl")}
        groups = pred["groups_ranked"]
        counts = Counter(truth[a] for a in pred["eligible_alert_ids"])
        priority = read_jsonl(f"{folder}/priority_private/{q}.jsonl")
        priority.sort(key=lambda x: (-x["priority_score"], x["incident_id"]))
        for rank, record in enumerate(priority[:20], 1):
            incident = record["incident_id"]
            touched = [sum(truth[a] == incident for a in g) for g in groups]
            touched = [x for x in touched if x]
            output.append({"split": split, "queue_id": q, "incident_id": incident,
                           "oracle_rank": rank, "eligible_alerts": counts[incident],
                           "committed_fragments": len(touched),
                           "largest_fragment": max(touched),
                           "largest_fragment_share": round(max(touched) / counts[incident], 6)})
    return output


def rank_attribution():
    model = json.loads((V / "ranker_model.json").read_text())["fitted"]["weights"]
    graphs = {x["queue_id"]: x["edges"] for x in read_jsonl("locked_graph.jsonl")}
    hyps = {x["queue_id"]: x["hypotheses"] for x in read_jsonl("locked_hypotheses.jsonl")}
    values = []
    for pred in read_jsonl("locked_predictions.jsonl"):
        if pred["ranker"] != "train_fitted":
            continue
        q = pred["queue_id"]
        for group in pred["groups_ranked"]:
            gf = graph_features(group, pred["groups_ranked"], graphs[q], hyps[q])
            values.append(sum(w * x for w, x in zip(model[9:], gf)))
    return {"fitted_graph_weights": [round(x, 6) for x in model[9:]],
            "groups_scored": len(values), "mean_graph_score_contribution": sum(values) / len(values),
            "negative_contribution_groups": sum(x < 0 for x in values),
            "positive_contribution_groups": sum(x > 0 for x in values)}


def main():
    freeze = json.loads((V / "freeze_manifest.json").read_text())
    protocol = json.loads((V / "pre_evaluation_protocol.json").read_text())
    locked = json.loads((V / "locked_prediction_freeze.json").read_text())
    for mapping in (freeze["hashes"], protocol["hashes"], locked["prediction_hashes"],
                    locked["public_input_hashes"]):
        for name, expected in mapping.items():
            assert digest(V / name) == expected, name
    for name in ("PHASE27_EXPERIMENT_COMPARISON.csv", "PHASE27_QUEUE_METRICS.csv",
                 "PHASE27_EDGE_AUDIT.csv", "PHASE27_INCIDENT_HYPOTHESES.csv",
                 "PHASE27_FAILURE_CASCADE.csv", "PHASE27_UNION_PAIR_AUDIT.csv",
                 "PHASE27_INCIDENT_AUDIT.csv", "PHASE27_GATE_RESULTS.csv",
                 "PHASE27_LOCKED_QUEUE_METRICS.csv", "PHASE27_LOCKED_HYPOTHESES.csv",
                 "PHASE27_LOCKED_EDGE_AUDIT.csv", "PHASE27_LOCKED_FAILURE_CASCADE.csv"):
        shutil.copyfile(V / name, HERE / name)
    dev_edges = read_csv("PHASE27_EDGE_AUDIT.csv")
    locked_edges = read_csv("PHASE27_LOCKED_EDGE_AUDIT.csv")
    edge_summary = {}
    for label, data in (("development", dev_edges), ("locked_test", locked_edges)):
        candidates = [x for x in data if x["outcome"] == "CANDIDATE"]
        edge_summary[label] = {"candidate_edges": len(candidates),
                               "same_incident_candidate_edges": sum(x["same_incident"] == "1" for x in candidates),
                               "candidate_edge_precision": sum(x["same_incident"] == "1" for x in candidates) /
                                                          len(candidates),
                               "verified_edges": sum(x["outcome"] == "VERIFIED" for x in data),
                               "rejected_edges": sum(x["outcome"] == "REJECTED" for x in data),
                               **edge_coverage(label, "development_graph.jsonl" if label == "development" else
                                               "locked_graph.jsonl", "development_predictions.jsonl" if
                                               label == "development" else "locked_predictions.jsonl")}
    dev_q = read_csv("PHASE27_QUEUE_METRICS.csv")
    locked_q = read_csv("PHASE27_LOCKED_QUEUE_METRICS.csv")
    hypothesis_queue = (hypothesis_ranking("development", "PHASE27_INCIDENT_HYPOTHESES.csv") +
                        hypothesis_ranking("locked_test", "PHASE27_LOCKED_HYPOTHESES.csv"))
    write_csv("PHASE27_HYPOTHESIS_RANKING.csv", hypothesis_queue)
    write_csv("PHASE27_FRAGMENT_COUNTS.csv", fragment_counts("development", "development_predictions.jsonl") +
              fragment_counts("locked_test", "locked_predictions.jsonl"))
    out = {"development": {"hypotheses": hypothesis_summary("development",
                                       "PHASE27_INCIDENT_HYPOTHESES.csv", "PHASE27_INCIDENT_AUDIT.csv"),
                           "edges": edge_summary["development"],
                           "paired_recall20_delta_ci95": interval(dev_q, "train_fitted")},
           "locked_test": {"hypotheses": hypothesis_summary("locked_test",
                                       "PHASE27_LOCKED_HYPOTHESES.csv", "PHASE27_LOCKED_INCIDENT_AUDIT.csv"),
                           "edges": edge_summary["locked_test"],
                           "paired_recall20_delta_ci95": interval(locked_q, "train_fitted"),
                           "rank_attribution": rank_attribution()},
           "locked_result": json.loads((V / "locked_result.json").read_text()),
           "hypothesis_ranking": {split: {"top20_hypothesis_slots": sum(int(x["top20_hypotheses"]) for x in hypothesis_queue if x["split"] == split),
                                        "false_hypothesis_rankings": sum(int(x["false_hypothesis_rankings"]) for x in hypothesis_queue if x["split"] == split),
                                        "distinct_incidents_found": sum(int(x["distinct_top20_incidents_found"]) for x in hypothesis_queue if x["split"] == split)}
                                  for split in ("development", "locked_test")}}
    (HERE / "analysis_summary.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"development_novel_hypotheses": out["development"]["hypotheses"]["top20_incidents_new_beyond_groups"],
                      "holdout_novel_hypotheses": out["locked_test"]["hypotheses"]["top20_incidents_new_beyond_groups"],
                      "holdout_delta_ci95": out["locked_test"]["paired_recall20_delta_ci95"]}, indent=2))


if __name__ == "__main__":
    main()
