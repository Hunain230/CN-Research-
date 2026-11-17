"""Freeze Phase 24 predictions, then evaluate development with private truth."""
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from predict import HERE, features, rank, reconstruct, rows, visible

CONFIG = json.loads((HERE / "config.json").read_text())
MANIFEST = json.loads((HERE / "datasets" / "manifest.json").read_text())


def dump_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dump_lines(path, values):
    with path.open("w", encoding="utf-8") as stream:
        for row in values:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def dump_csv(path, values):
    values = list(values)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def truth_for(split, queue):
    folder = HERE / "datasets" / split / "ground_truth_private"
    return ({x["alert_id"]: x["incident_id"] for x in rows(folder / f"{queue}.jsonl")},
            rows(folder / f"{queue}_priority.jsonl"))


def fit_ranker(train_groups):
    """Train pairwise linear ranker on train truth only; no development labels."""
    examples = []
    for queue, groups, alerts in train_groups:
        truth, priority = truth_for("train", queue)
        ranks = {x["incident_id"]: x["priority_rank"] for x in priority}
        eligible = Counter(truth[x["alert_id"]] for x in alerts)
        lookup = {x["alert_id"]: x for x in alerts}
        one = []
        for group in groups:
            counts = Counter(truth[x] for x in group)
            qualified = [i for i, n in counts.items() if i in ranks and
                         n / eligible[i] >= .8 and n / len(group) >= .8]
            relevance = max((26 - ranks[i] for i in qualified), default=0)
            one.append((features(group, lookup), relevance))
        examples.append(one)
    all_x = [x for queue in examples for x, _ in queue]
    means = [sum(x[j] for x in all_x) / len(all_x) for j in range(len(all_x[0]))]
    std = [max((sum((x[j]-means[j])**2 for x in all_x)/len(all_x))**.5, .1)
           for j in range(len(means))]
    weights = [0.0] * len(means)
    rng = random.Random(240424)
    for epoch in range(12):
        for queue in examples:
            positives = [(x, y) for x, y in queue if y > 0]
            negatives = [(x, y) for x, y in queue if y == 0]
            if not positives or not negatives:
                continue
            rng.shuffle(positives)
            for x, relevance in positives:
                for _ in range(2):
                    other, _ = rng.choice(negatives)
                    diff = [(a-b)/scale for a, b, scale in zip(x, other, std)]
                    margin = sum(w*d for w, d in zip(weights, diff))
                    gradient = (1/(1+math.exp(max(-30, min(30, margin))))) * (relevance/25)
                    rate = .035 / (1 + epoch*.15)
                    weights = [w + rate*(gradient*d-.015*w) for w, d in zip(weights, diff)]
    return [w/s for w, s in zip(weights, std)], {"raw_weights": weights, "feature_means": means,
                                               "feature_std": std, "train_queues": len(train_groups)}


def freeze_predictions():
    train = []
    train_files = []
    for item in MANIFEST["queues"]["train"]:
        q = item["queue_id"]
        alerts = visible("train", q)
        groups, decisions, candidates = reconstruct(alerts, "context")
        train.append((q, groups, alerts))
        train_files.append({"queue_id": q, "groups": groups, "candidate_proposals": candidates,
                            "decisions": decisions})
    dump_lines(HERE / "train_baseline_predictions.jsonl", train_files)
    weights, fit_info = fit_ranker(train)
    dump_json(HERE / "ranker_model.json", {"weights": weights, **fit_info})

    predictions = []
    decisions_all = []
    for item in MANIFEST["queues"]["development"]:
        q = item["queue_id"]
        alerts = visible("development", q)
        for rule in CONFIG["rules"]:
            groups, decisions, candidate_count = reconstruct(alerts, rule)
            for ranker in CONFIG["rankers"]:
                ranked = rank(groups, alerts, ranker, weights if ranker in ("learned", "blend") else None)
                predictions.append({"queue_id": q, "split": "development", "rule": rule,
                                    "ranker": ranker, "eligible_alert_ids": [a["alert_id"] for a in alerts],
                                    "groups_ranked": ranked, "candidate_proposals": candidate_count})
            decisions_all.append({"queue_id": q, "rule": rule, "decisions": decisions})
    dump_lines(HERE / "development_predictions.jsonl", predictions)
    dump_lines(HERE / "development_decisions.jsonl", decisions_all)
    source_files = ("config.json", "generate.py", "predict.py", "run_study.py",
                    "datasets/manifest.json", "train_baseline_predictions.jsonl", "ranker_model.json",
                    "development_predictions.jsonl", "development_decisions.jsonl")
    dump_json(HERE / "freeze_manifest.json", {
        "status": "development_predictions_frozen_before_private_development_audit",
        "locked_cohort_created": False, "phase19_locked_read": False, "phase22_locked_read": False,
        "hashes": {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in source_files}})
    return predictions, decisions_all


def audit_one(pred, decision_row):
    q = pred["queue_id"]
    truth, priority = truth_for("development", q)
    rank_truth = {x["incident_id"]: x["priority_rank"] for x in priority}
    eligible = set(pred["eligible_alert_ids"])
    groups = pred["groups_ranked"]
    assert eligible == {a for group in groups for a in group}
    assert sum(map(len, groups)) == len(eligible) and max(map(len, groups), default=0) <= 100
    size = Counter(truth[a] for a in eligible)
    qualifiers = defaultdict(list)
    tp = fp = mixed = 0
    for pos, group in enumerate(groups, 1):
        counts = Counter(truth[a] for a in group)
        mixed += len(counts) > 1
        tp += sum(n*(n-1)//2 for n in counts.values())
        fp += len(group)*(len(group)-1)//2 - sum(n*(n-1)//2 for n in counts.values())
        for incident, hits in counts.items():
            if incident in rank_truth and hits/size[incident] >= .8 and hits/len(group) >= .8:
                qualifiers[incident].append(pos)
    recovered = {i for i, r in rank_truth.items() if r <= 20 and i in qualifiers}
    recall20 = {i for i in recovered if min(qualifiers[i]) <= 20}
    recall10 = {i for i in recovered if min(qualifiers[i]) <= 10}
    p10 = 0
    credited = set()
    dcg = 0.0
    for pos in range(1, min(20, len(groups)) + 1):
        candidates = [i for i, places in qualifiers.items() if pos in places and i not in credited]
        if candidates:
            incident = min(candidates, key=lambda i: rank_truth[i])
            credited.add(incident)
            if pos <= 10 and rank_truth[incident] <= 10:
                p10 += 1
            dcg += (26-rank_truth[incident])/math.log2(pos+1)
    ideal = sum((26-r)/math.log2(r+1) for r in range(1,21))
    result = {"queue_id": q, "rule": pred["rule"], "ranker": pred["ranker"],
              "eligible_alerts": len(eligible), "expert_top20": 20,
              "recoverable": len(recovered), "recall10_count": len(recall10),
              "recall20_count": len(recall20), "p10_count": p10,
              "ndcg20": dcg/ideal, "pair_tp": tp, "false_grouped_pairs": fp,
              "mixed_predicted_groups": mixed, "candidate_proposals": pred["candidate_proposals"],
              "accepted_unions": sum(d["decision"] == "accept" for d in decision_row["decisions"]),
              "abstained": sum(d["decision"] == "abstain" for d in decision_row["decisions"])}
    incident_rows = []
    for incident, oracle_rank in rank_truth.items():
        if oracle_rank > 20:
            continue
        positions = qualifiers.get(incident, [])
        best = max((sum(truth[a] == incident for a in group) for group in groups), default=0)
        touching = [d for d in decision_row["decisions"] if d["decision"] != "accept" and
                    any(truth[a] == incident for a in d["left"]) and
                    any(truth[a] == incident for a in d["right"])]
        if positions:
            status = "recalled" if min(positions) <= 20 else "ranking_only"
        elif best / size[incident] < .8:
            status = "fragmented_candidate" if touching else "candidate_absent"
        else:
            status = "impure"
        reasons = Counter(d["reason"] for d in touching)
        incident_rows.append({"queue_id": q, "rule": pred["rule"], "ranker": pred["ranker"],
                              "incident_id": incident, "oracle_rank": oracle_rank,
                              "eligible_alerts": size[incident], "best_overlap": best,
                              "completeness": round(best/size[incident], 6),
                              "qualifying_position": min(positions) if positions else "",
                              "status": status, "candidate_reasons": json.dumps(reasons, sort_keys=True)})
    return result, incident_rows


def audit_unions(decision_rows, prediction_rows):
    outputs = []
    cascades = []
    base = {(p["queue_id"], p["rule"]): p for p in prediction_rows if p["ranker"] == "progression"}
    for row in decision_rows:
        q, rule = row["queue_id"], row["rule"]
        truth, _ = truth_for("development", q)
        parent = {a: a for a in base[q, rule]["eligible_alert_ids"]}
        counts = {a: Counter([truth[a]]) for a in parent}
        def root(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        total = 0
        for index, d in enumerate(row["decisions"]):
            if d["decision"] != "accept":
                continue
            a, b = root(d["left"][0]), root(d["right"][0])
            if a == b:
                raise AssertionError("duplicate accepted union")
            left, right = counts[a], counts[b]
            true = sum(left[k]*right[k] for k in left.keys() & right.keys())
            false = sum(left.values())*sum(right.values()) - true
            total += false
            outputs.append({"queue_id": q, "rule": rule, "order": index,
                            "reason": d["reason"], "left_size": len(d["left"]),
                            "right_size": len(d["right"]), "new_true_pairs": true,
                            "new_false_pairs": false,
                            "premerge_pair_exposure": d["premerge_pair_exposure"]})
            counts[a] += counts[b]
            del counts[b]
            parent[b] = a
        pred_groups = base[q, rule]["groups_ranked"]
        final_fp = sum(len(g)*(len(g)-1)//2 - sum(n*(n-1)//2 for n in
                       Counter(truth[a] for a in g).values()) for g in pred_groups)
        assert total == final_fp
        cascades.append({"queue_id": q, "rule": rule, "accepted_unions": sum(x["queue_id"] == q and x["rule"] == rule for x in outputs),
                         "false_pair_creating_unions": sum(x["queue_id"] == q and x["rule"] == rule and x["new_false_pairs"] > 0 for x in outputs),
                         "false_pairs": total, "worst_union_false_pairs": max((x["new_false_pairs"] for x in outputs if x["queue_id"] == q and x["rule"] == rule), default=0)})
    return outputs, cascades


def summarize(queue_rows):
    result = []
    for rule in CONFIG["rules"]:
        for ranker in CONFIG["rankers"]:
            subset = [r for r in queue_rows if r["rule"] == rule and r["ranker"] == ranker]
            sums = {k: sum(r[k] for r in subset) for k in
                    ("recoverable", "recall10_count", "recall20_count", "p10_count", "pair_tp",
                     "false_grouped_pairs", "mixed_predicted_groups", "accepted_unions", "abstained")}
            result.append({"rule": rule, "ranker": ranker, "queues": len(subset),
                           "recoverable": sums["recoverable"], "recall10_count": sums["recall10_count"],
                           "recall20_count": sums["recall20_count"], "p10_count": sums["p10_count"],
                           "group_recoverability": sums["recoverable"]/(20*len(subset)),
                           "incident_recall10": sums["recall10_count"]/(20*len(subset)),
                           "incident_recall20": sums["recall20_count"]/(20*len(subset)),
                           "p10": sums["p10_count"]/(10*len(subset)),
                           "ndcg20": sum(r["ndcg20"] for r in subset)/len(subset),
                           "grouped_pair_precision": sums["pair_tp"]/(sums["pair_tp"]+sums["false_grouped_pairs"]),
                           "false_grouped_pairs": sums["false_grouped_pairs"],
                           "mixed_predicted_groups": sums["mixed_predicted_groups"],
                           "accepted_unions": sums["accepted_unions"], "abstained": sums["abstained"],
                           "macro_recall20": sum(r["recall20_count"]/20 for r in subset)/len(subset)})
    return result


def main():
    if (HERE / "freeze_manifest.json").exists():
        raise FileExistsError("Phase 24 predictions already frozen")
    predictions, decisions = freeze_predictions()
    decision_lookup = {(d["queue_id"], d["rule"]): d for d in decisions}
    queue_rows = []
    incident_rows = []
    for pred in predictions:
        result, incidents = audit_one(pred, decision_lookup[pred["queue_id"], pred["rule"]])
        queue_rows.append(result)
        incident_rows.extend(incidents)
    union_rows, cascades = audit_unions(decisions, predictions)
    summary = summarize(queue_rows)
    dump_csv(HERE / "PHASE24_EXPERIMENT_COMPARISON.csv", summary)
    dump_csv(HERE / "PHASE24_QUEUE_METRICS.csv", queue_rows)
    dump_csv(HERE / "PHASE24_RECONSTRUCTION_AUDIT.csv", incident_rows)
    dump_csv(HERE / "PHASE24_UNION_PAIR_AUDIT.csv", union_rows)
    dump_csv(HERE / "PHASE24_FAILURE_CASCADE.csv", cascades)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
