"""Post-freeze evaluator reporting for the final Phase 24 development cohort."""
import csv
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / "v4"
sys.path.insert(0, str(V))
from predict import features, ranking_score, rows, visible  # noqa: E402


def read_csv(name):
    with (V / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(name, data):
    data = list(data)
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def bootstrap(queue_rows, rule, ranker, rounds=2000):
    sample = [r for r in queue_rows if r["rule"] == rule and r["ranker"] == ranker]
    rng = random.Random(240424)
    values = {metric: [] for metric in ("recoverable", "recall20_count", "p10_count")}
    for _ in range(rounds):
        draw = rng.choices(sample, k=len(sample))
        for metric in values:
            denom = (10 if metric == "p10_count" else 20)*len(draw)
            values[metric].append(sum(int(x[metric]) for x in draw)/denom)
    return {metric: [sorted(v)[int(.025*rounds)], sorted(v)[int(.975*rounds)-1]]
            for metric, v in values.items()}


def main():
    freeze = json.loads((V / "freeze_manifest.json").read_text())
    for name, digest in freeze["hashes"].items():
        assert hashlib.sha256((V/name).read_bytes()).hexdigest() == digest
    assert not freeze["locked_cohort_created"] and not (V / "datasets" / "locked_test").exists()
    dataset_hashes = {str(path.relative_to(V)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted((V / "datasets").rglob("*.jsonl"))}
    dataset_hashes["datasets/manifest.json"] = hashlib.sha256(
        (V / "datasets" / "manifest.json").read_bytes()).hexdigest()
    (HERE / "dataset_hashes.json").write_text(json.dumps(dataset_hashes, indent=2) + "\n")
    comparisons = read_csv("PHASE24_EXPERIMENT_COMPARISON.csv")
    queues = read_csv("PHASE24_QUEUE_METRICS.csv")
    incidents = read_csv("PHASE24_RECONSTRUCTION_AUDIT.csv")
    unions = read_csv("PHASE24_UNION_PAIR_AUDIT.csv")
    cascades = read_csv("PHASE24_FAILURE_CASCADE.csv")
    baseline = next(x for x in comparisons if x["rule"] == "context" and x["ranker"] == "progression")
    base_by_q = {x["queue_id"]: x for x in queues if x["rule"] == "context" and x["ranker"] == "progression"}
    for result in comparisons:
        subset = [x for x in queues if x["rule"] == result["rule"] and x["ranker"] == result["ranker"]]
        queue_safe = all(int(x["false_grouped_pairs"]) <= int(base_by_q[x["queue_id"]]["false_grouped_pairs"])
                         and int(x["mixed_predicted_groups"]) <= int(base_by_q[x["queue_id"]]["mixed_predicted_groups"])
                         for x in subset)
        result["queue_safety_pass"] = queue_safe
        result["acceptance_pass"] = (int(result["recall20_count"]) > int(baseline["recall20_count"])
            and int(result["recoverable"]) > int(baseline["recoverable"])
            and float(result["grouped_pair_precision"]) >= .9
            and int(result["false_grouped_pairs"]) <= int(baseline["false_grouped_pairs"])
            and int(result["mixed_predicted_groups"]) <= int(baseline["mixed_predicted_groups"])
            and int(result["p10_count"]) >= int(baseline["p10_count"])-1 and queue_safe)
    write_csv("PHASE24_EXPERIMENT_COMPARISON.csv", comparisons)
    write_csv("PHASE24_QUEUE_METRICS.csv", queues)
    write_csv("PHASE24_RECONSTRUCTION_AUDIT.csv", incidents)
    write_csv("PHASE24_UNION_PAIR_AUDIT.csv", unions)
    write_csv("PHASE24_FAILURE_CASCADE.csv", cascades)

    preds = rows(V / "development_predictions.jsonl")
    selected = {(p["queue_id"], p["rule"], p["ranker"]): p for p in preds}
    rank_rows = []
    ranker_model = json.loads((V / "ranker_model.json").read_text())
    for rule, ranker in (("context", "progression"), ("context", "blend"),
                         ("coherent_rare", "blend")):
        for item in json.loads((V / "datasets" / "manifest.json").read_text())["queues"]["development"]:
            q = item["queue_id"]
            pred = selected[q, rule, ranker]
            alerts = visible("development", q)
            lookup = {x["alert_id"]: x for x in alerts}
            truth = {x["alert_id"]: x["incident_id"] for x in rows(
                V / "datasets" / "development" / "ground_truth_private" / f"{q}.jsonl")}
            priority = {x["incident_id"]: x for x in rows(
                V / "datasets" / "development" / "ground_truth_private" / f"{q}_priority.jsonl")}
            sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
            for pos, group in enumerate(pred["groups_ranked"], 1):
                counts = Counter(truth[a] for a in group)
                qualifying = [i for i, n in counts.items() if i in priority and
                              n/sizes[i] >= .8 and n/len(group) >= .8]
                vector = features(group, lookup)
                weights = ranker_model["weights"] if ranker == "blend" else None
                score = ranking_score(vector, ranker, weights)
                rank_rows.append({"queue_id": q, "rule": rule, "ranker": ranker, "position": pos,
                                  "group_size": len(group), "source_events": len({lookup[a]["source_id"] for a in group}),
                                  "score": round(score, 6), "max_severity": vector[0],
                                  "max_criticality": vector[1], "mean_severity": round(vector[2], 4),
                                  "event_type_count": vector[3], "relation_types": vector[5],
                                  "context_available_fraction": round(vector[8], 4),
                                  "duplicate_fraction": round(vector[7], 4),
                                  "qualifying_top20": sum(priority[i]["priority_rank"] <= 20 for i in qualifying),
                                  "qualifying_incident_ids_evaluator_only": "|".join(sorted(qualifying))})
    write_csv("PHASE24_RANKING_AUDIT.csv", rank_rows)

    availability = []
    manifest = json.loads((V / "datasets" / "manifest.json").read_text())
    for split, items in manifest["queues"].items():
        for item in items:
            q = item["queue_id"]
            raw = rows(V / "datasets" / split / "generated_alerts" / f"{q}.jsonl")
            ledger = rows(V / "datasets" / split / "field_ledger" / f"{q}.jsonl")
            vis = visible(split, q)
            visible_ids = {a["alert_id"] for a in vis}
            availability.append({"split": split, "queue_id": q, "raw_alerts": len(raw),
                                 "visible_alerts": len(vis), "late_alerts": len(raw)-len(vis),
                                 "late_fields_on_visible_alerts": sum(x["available_minute"] > 100 for x in ledger
                                                                   if x["artifact_id"] in visible_ids)})
    write_csv("PHASE24_FEATURE_AVAILABILITY_AUDIT.csv", availability)

    family_rows = []
    lookup = {(x["queue_id"], x["rule"], x["ranker"], x["incident_id"]): x for x in incidents}
    for rule, ranker in (("context", "progression"), ("coherent_rare", "blend")):
        by_family = defaultdict(Counter)
        by_failure = defaultdict(Counter)
        for item in manifest["queues"]["development"]:
            q = item["queue_id"]
            priorities = rows(V / "datasets" / "development" / "ground_truth_private" / f"{q}_priority.jsonl")
            faults = {x["incident_id"]: x["failure_mode"] for x in rows(
                V / "datasets" / "development" / "faults_private" / f"{q}.jsonl")}
            for p in priorities:
                if p["priority_rank"] > 20:
                    continue
                row = lookup[q, rule, ranker, p["incident_id"]]
                for kind, key, target in (("family", p["family"], by_family),
                                          ("failure_mode", faults[p["incident_id"]], by_failure)):
                    target[key]["incidents"] += 1
                    target[key]["recovered"] += row["status"] in ("recalled", "ranking_only")
                    target[key]["recalled"] += row["status"] == "recalled"
        for kind, groups in (("family", by_family), ("failure_mode", by_failure)):
            for key, count in groups.items():
                family_rows.append({"rule": rule, "ranker": ranker, "category": kind, "value": key,
                                    "incidents": count["incidents"], "recovered": count["recovered"],
                                    "recalled": count["recalled"]})
    write_csv("PHASE24_FAMILY_FAILURE_METRICS.csv", family_rows)

    key = lambda rule, ranker: next(x for x in comparisons if x["rule"] == rule and x["ranker"] == ranker)
    base = key("context", "progression")
    candidate = key("coherent_rare", "blend")
    statuses = Counter(x["status"] for x in incidents if x["rule"] == "context" and x["ranker"] == "progression")
    reasons = Counter()
    for x in incidents:
        if x["rule"] == "context" and x["ranker"] == "progression" and x["status"] == "fragmented_candidate":
            reasons.update(json.loads(x["candidate_reasons"]))
    ci_base = bootstrap(queues, "context", "progression")
    ci_candidate = bootstrap(queues, "coherent_rare", "blend")
    qbad = [x for x in queues if x["rule"] == "coherent_rare" and x["ranker"] == "blend" and
            int(x["false_grouped_pairs"]) > int(base_by_q[x["queue_id"]]["false_grouped_pairs"])]
    assert sum(int(x["new_false_pairs"]) for x in unions if x["rule"] == "coherent_rare") == int(candidate["false_grouped_pairs"])
    assert not any(x["acceptance_pass"] is True for x in comparisons)
    data = {"baseline": base, "candidate": candidate, "baseline_failure_counts": statuses,
            "baseline_fragmented_reasons": reasons, "baseline_ci": ci_base,
            "candidate_ci": ci_candidate, "queue_failures": qbad,
            "queue_worst_union": max(int(x["new_false_pairs"]) for x in unions if x["rule"] == "coherent_rare")}
    (HERE / "analysis_summary.json").write_text(json.dumps(data, indent=2, default=dict) + "\n")
    print(json.dumps(data, indent=2, default=dict))


if __name__ == "__main__":
    main()
