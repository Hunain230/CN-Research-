"""Evaluator-only comparison of Phase 34's ten missed qualifying groups."""
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P34 = ROOT / "experiments/PHASE34_FROZEN_RANK_GENERALIZATION"
import importlib.util
spec = importlib.util.spec_from_file_location("phase34_visible_features", P34 / "ranker.py")
ranker = importlib.util.module_from_spec(spec); spec.loader.exec_module(ranker)


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    predictions = lines(P34 / "artifacts/development_top20_logistic_predictions.jsonl")
    audits = lines(P34 / "artifacts/development_baseline_decisions.jsonl")
    visible = P34 / "dataset/receiver_visible/development"
    truth_root = P34 / "dataset/evaluator_only/development/ground_truth_private"
    rows = []; position_counts = Counter()
    for pred, audit in zip(predictions, audits):
        q = pred["queue_id"]
        lookup, _ = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        for position, group in enumerate(pred["groups_ranked"], 1):
            if not 11 <= position <= 30: continue
            membership = Counter(truth[a] for a in group)
            qualifies = any(i in top20 and hits / sizes[i] >= .8 and hits / len(group) >= .8
                            for i, hits in membership.items())
            category = ("missed_top20" if position > 20 and qualifies else
                        "nonqualifying_occupant" if position <= 20 and not qualifies else None)
            if category is None: continue
            values = ranker.features(group, lookup, audit["accepted"])
            rows.append({"queue_id": q, "position": position, "category": category,
                         **dict(zip(ranker.FEATURE_ORDER, values))})
            if category == "missed_top20": position_counts[position] += 1
    (HERE / "artifacts").mkdir(exist_ok=True)
    with (HERE / "artifacts/boundary_diagnostic.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summaries = {}
    for category in ("missed_top20", "nonqualifying_occupant"):
        subset = [r for r in rows if r["category"] == category]
        summaries[category] = {"groups": len(subset), "median_features": {
            field: median(float(r[field]) for r in subset) for field in ranker.FEATURE_ORDER}}
    result = {"comparison": summaries, "missed_positions": dict(sorted(position_counts.items())),
              "use": "opened Phase 34 development diagnostic only; Phase 35 fitting uses new train"}
    (HERE / "artifacts/boundary_diagnostic.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
