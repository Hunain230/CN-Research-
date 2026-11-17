"""Read-only diagnosis of previously opened cohorts; never selects a rule."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def diagnose(label, predictions, data):
    categories = Counter()
    rows = []
    for pred in lines(predictions):
        q = pred["queue_id"]
        truth = {x["alert_id"]: x for x in lines(data / "ground_truth_private" / f"{q}.jsonl")}
        priority = lines(data / "ground_truth_private" / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in priority if x["priority_rank"] <= 20}
        alerts = {x["alert_id"]: x for x in lines(data / "generated_alerts" / f"{q}.jsonl")}
        eligible = set(pred["eligible_alert_ids"])
        by_incident = defaultdict(set)
        all_incident = defaultdict(set)
        for aid, t in truth.items():
            all_incident[t["incident_id"]].add(aid)
            if aid in eligible:
                by_incident[t["incident_id"]].add(aid)
        for incident in top20:
            target = by_incident[incident]
            hits = [(pos, len(set(group) & target), len(group), group)
                    for pos, group in enumerate(pred["groups_ranked"], 1) if target.intersection(group)]
            qualifies = [x for x in hits if x[1] / len(target) >= .8 and x[1] / x[2] >= .8]
            late = len(all_incident[incident] - target)
            if qualifies:
                category = "recalled" if min(x[0] for x in qualifies) <= 20 else "ranking_failure"
            else:
                biggest = max(hits, key=lambda x: (x[1], -x[2]))
                category = "fragmented" if biggest[1] / len(target) < .8 else "impure"
            categories[category] += 1
            if late:
                categories["incidents_with_late_evidence"] += 1
            if category == "fragmented":
                fragments = [x for x in hits if x[1]]
                linked = set()
                context_match = False
                contradiction = False
                for i, left in enumerate(fragments):
                    for right in fragments[i + 1:]:
                        left_alerts = [alerts[a] for a in left[3] if a in target]
                        right_alerts = [alerts[a] for a in right[3] if a in target]
                        for field in ("process_tree_ref", "auth_session_ref", "network_flow_ref"):
                            a = {x[field] for x in left_alerts if x[field]}
                            b = {x[field] for x in right_alerts if x[field]}
                            if a & b:
                                linked.add(field)
                        lh = {x["host"] for x in left_alerts if x["host"]}
                        rh = {x["host"] for x in right_alerts if x["host"]}
                        la = {x["account"] for x in left_alerts if x["account"]}
                        ra = {x["account"] for x in right_alerts if x["account"]}
                        context_match |= bool(lh & rh and la & ra)
                        contradiction |= bool(lh and rh and not lh & rh and la and ra and not la & ra)
                categories["fragmented_with_any_direct_ref"] += bool(linked)
                categories["fragmented_with_dual_lineage"] += {"auth_session_ref", "network_flow_ref"} <= linked
                categories["fragmented_with_context_match"] += context_match
                categories["fragmented_with_contradiction"] += contradiction
                categories["fragmented_without_direct_ref"] += not linked
            rows.append({"cohort": label, "queue_id": q, "category": category,
                         "eligible_alerts": len(target), "late_alerts": late,
                         "fragments": len(hits), "best_hits": max(x[1] for x in hits),
                         "best_group_size": max(hits, key=lambda x: x[1])[2]})
    return dict(categories), rows


def main():
    dev, dr = diagnose("development", PREV / "artifacts/development_source_depth.jsonl",
                       V4 / "datasets/development")
    prior, pr = diagnose("opened_prior_holdout", PREV / "artifacts/fresh_candidate_predictions.jsonl",
                         PREV / "artifacts/fresh_cohort/datasets/locked_test")
    with (HERE / "artifacts/failure_categories.json").open("w", encoding="utf-8") as f:
        json.dump({"development": dev, "opened_prior_holdout_diagnostic_only": prior}, f, indent=2)
    with (HERE / "artifacts/failure_rows.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(dr[0]))
        writer.writeheader(); writer.writerows(dr + pr)
    print(json.dumps({"development": dev, "opened_prior_holdout_diagnostic_only": prior}, indent=2))


if __name__ == "__main__":
    main()
