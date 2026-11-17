"""Evaluator-only Phase 28 audit of frozen development and one holdout."""
import csv
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / "v2"


def read_csv(name):
    with (V / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(name):
    with (V / name).open(encoding="utf-8") as stream:
        return [json.loads(x) for x in stream]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(name, values):
    values = list(values)
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def bootstrap(rows, mode_a, mode_b, rounds=2000):
    by_q = defaultdict(dict)
    for row in rows:
        if row["ranker"] == "phase27_selected" and row["mode"] in (mode_a, mode_b):
            by_q[row["queue_id"]][row["mode"]] = row
    pairs = list(by_q.values())
    rng = random.Random(280928)
    out = {}
    for field, denominator in (("recoverable", 20), ("recall20_count", 20), ("p10_count", 10)):
        values = sorted(sum(int(x[mode_b][field]) - int(x[mode_a][field]) for x in
                            rng.choices(pairs, k=len(pairs))) / (denominator * len(pairs))
                        for _ in range(rounds))
        out[field] = [round(values[49], 6), round(values[1949], 6)]
    return out


def replay_counterfactual():
    decisions = read_jsonl("locked_decisions.jsonl")
    injections = {x["queue_id"]: x for x in json.loads((V / "datasets/locked_test/injection_manifest.json").read_text())}
    result = []
    for row in decisions:
        if row["mode"] != "component":
            continue
        q = row["queue_id"]
        truth = {x["alert_id"]: x["incident_id"] for x in read_jsonl(
            f"datasets/locked_test/ground_truth_private/{q}.jsonl")}
        headers = {x["alert_id"]: x["source_id"] for x in read_jsonl(
            f"datasets/locked_test/alert_headers/{q}.jsonl")}
        actions = []
        for d in row["baseline_decisions"]:
            if d["decision"] == "accept":
                actions.append((d["left"][0], d["right"][0], ""))
        promoted = [d for d in row["promotion_decisions"] if d["decision"] == "PROMOTE"]
        for d in promoted:
            parts = d["pre_components"]
            actions.extend((parts[0][0], part[0], d["hypothesis_id"]) for part in parts[1:])

        def replay(skip):
            parent = {a: a for a in truth}
            def root(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a
            for a, b, identifier in actions:
                if identifier and identifier == skip:
                    continue
                ra, rb = root(a), root(b)
                if ra != rb:
                    parent[rb] = ra
            groups = defaultdict(Counter)
            for a, incident in truth.items():
                groups[root(a)][incident] += 1
            return sum(sum(c.values()) * (sum(c.values()) - 1) // 2 -
                       sum(v * (v - 1) // 2 for v in c.values()) for c in groups.values())

        full = replay(None)
        for d in promoted:
            identifier = d["hypothesis_id"]
            source_ids = {headers[a] for a in d["post_component"]}
            result.append({"queue_id": q, "hypothesis_id": identifier,
                           "full_false_pairs": full, "skip_false_pairs": replay(identifier),
                           "pairs_avoided": full - replay(identifier),
                           "touches_injected_false_sources": int(bool(source_ids.intersection(
                               injections[q]["source_ids"]))),
                           "score": d["predicted_log_odds"],
                           "root_disjoint_witnesses": d["features"]["root_disjoint_witnesses"],
                           "lineage_types": d["features"]["lineage_types"]})
    return result


def family_metrics():
    output = []
    development = read_csv("PHASE28_INCIDENT_AUDIT.csv")
    aggregate = defaultdict(Counter)
    for row in development:
        if row["ranker"] != "phase27_selected" or row["mode"] not in ("baseline", "component"):
            continue
        key = ("development", row["mode"], row["family"])
        aggregate[key]["incidents"] += 1
        aggregate[key]["recoverable"] += row["status"] in ("recalled", "ranking_only")
        aggregate[key]["recalled"] += row["status"] == "recalled"
    predictions = read_jsonl("locked_predictions.jsonl")
    for pred in predictions:
        q = pred["queue_id"]
        truth = {x["alert_id"]: x["incident_id"] for x in read_jsonl(
            f"datasets/locked_test/ground_truth_private/{q}.jsonl")}
        priority = read_jsonl(f"datasets/locked_test/priority_private/{q}.jsonl")
        priority.sort(key=lambda x: (-x["priority_score"], x["incident_id"]))
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        for item in priority[:20]:
            incident = item["incident_id"]
            positions = [pos for pos, group in enumerate(pred["groups_ranked"], 1)
                         if sum(truth[a] == incident for a in group) / sizes[incident] >= .8 and
                         sum(truth[a] == incident for a in group) / len(group) >= .8]
            key = ("locked_test", pred["mode"], item["family"])
            aggregate[key]["incidents"] += 1
            aggregate[key]["recoverable"] += bool(positions)
            aggregate[key]["recalled"] += bool(positions and min(positions) <= 20)
    for (split, mode, family), count in sorted(aggregate.items()):
        output.append({"split": split, "mode": mode, "family": family,
                       "incidents": count["incidents"], "recoverable": count["recoverable"],
                       "recalled": count["recalled"]})
    return output


def main():
    dev = json.loads((V / "development_freeze.json").read_text())
    protocol = json.loads((V / "pre_evaluation_protocol.json").read_text())
    locked = json.loads((V / "locked_prediction_freeze.json").read_text())
    for mapping in (dev["hashes"], protocol["hashes"], locked["prediction_hashes"],
                    locked["public_input_hashes"]):
        for name, expected in mapping.items():
            assert digest(V / name) == expected, name
    for name, expected in dev["phase27_reference_hashes"].items():
        assert digest(HERE.parent / "PHASE27_RECALL_GRAPH/v3" / name) == expected
    for name in ("PHASE28_EXPERIMENT_COMPARISON.csv", "PHASE28_QUEUE_METRICS.csv",
                 "PHASE28_PROMOTION_AUDIT.csv", "PHASE28_UNION_PAIR_AUDIT.csv",
                 "PHASE28_FAILURE_CASCADE.csv", "PHASE28_RECOVERY_OPPORTUNITIES.csv",
                 "PHASE28_HYPOTHESIS_AUDIT.csv", "PHASE28_INCIDENT_AUDIT.csv",
                 "PHASE28_DEVELOPMENT_GATES.csv", "PHASE28_LOCKED_QUEUE_METRICS.csv",
                 "PHASE28_LOCKED_PROMOTION_AUDIT.csv", "PHASE28_LOCKED_UNION_PAIR_AUDIT.csv",
                 "PHASE28_LOCKED_FAILURE_CASCADE.csv", "PHASE28_LOCKED_HYPOTHESIS_AUDIT.csv"):
        shutil.copyfile(V / name, HERE / name)
    counterfactual = replay_counterfactual()
    write_csv("PHASE28_COMPONENT_COUNTERFACTUAL.csv", counterfactual)
    write_csv("PHASE28_FAMILY_METRICS.csv", family_metrics())
    dev_rows = read_csv("PHASE28_QUEUE_METRICS.csv")
    lock_rows = read_csv("PHASE28_LOCKED_QUEUE_METRICS.csv")
    opportunities = read_csv("PHASE28_RECOVERY_OPPORTUNITIES.csv")
    dev_promotions = read_csv("PHASE28_PROMOTION_AUDIT.csv")
    lock_promotions = read_csv("PHASE28_LOCKED_PROMOTION_AUDIT.csv")
    dev_h = read_csv("PHASE28_HYPOTHESIS_AUDIT.csv")
    lock_h = read_csv("PHASE28_LOCKED_HYPOTHESIS_AUDIT.csv")
    gate = json.loads((V / "development_selection.json").read_text())
    locked_result = json.loads((V / "locked_result.json").read_text())
    summary = {"development_selection": gate, "locked_result": locked_result,
               "training_model": json.loads((V / "promotion_model.json").read_text()),
               "opportunities": dict(Counter(x["category"] for x in opportunities)),
               "development_hypotheses": {"total": len(dev_h), "qualifying": sum(x["qualifies"] == "1" for x in dev_h),
                   "top20_incidents": len({x["best_incident"] for x in dev_h if x["qualifies"] == "1" and
                                           int(x["oracle_rank"]) <= 20})},
               "locked_hypotheses": {"total": len(lock_h), "qualifying": sum(x["qualifies"] == "1" for x in lock_h),
                   "top20_incidents": len({x["best_incident"] for x in lock_h if x["qualifies"] == "1" and
                                           int(x["oracle_rank"]) <= 20})},
               "development_promotions": dict(Counter((x["mode"], x["decision"], x["qualifies"]) for x in dev_promotions)),
               "locked_promotions": dict(Counter((x["decision"], x["qualifies"]) for x in lock_promotions)),
               "counterfactual": {"promoted": len(counterfactual),
                   "false_pair_avoiding_skips": sum(x["pairs_avoided"] > 0 for x in counterfactual),
                   "pairs_avoided_total": sum(x["pairs_avoided"] for x in counterfactual),
                   "injection_touching": sum(x["touches_injected_false_sources"] for x in counterfactual)},
               "bootstrap": {"development": bootstrap(dev_rows, "baseline", "component"),
                             "locked_test": bootstrap(lock_rows, "baseline", "component")}}
    # JSON object keys cannot be tuples.
    summary["development_promotions"] = {"|".join(k): v for k, v in summary["development_promotions"].items()}
    summary["locked_promotions"] = {"|".join(k): v for k, v in summary["locked_promotions"].items()}
    (HERE / "analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"decision": locked_result["decision"],
                      "false_pair_avoiding_skips": summary["counterfactual"]["false_pair_avoiding_skips"],
                      "opportunities": summary["opportunities"]}, indent=2))


if __name__ == "__main__":
    main()
