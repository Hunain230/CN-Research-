"""Three fixed, visible-feature rank ablations on frozen Phase 16 groups.

This script never reads locked-test data. Truth is used only by the official
evaluator after each development prediction has been written.
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
sys.path.insert(0, str(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation"))
from evaluate import evaluate  # noqa: E402

BASE = V4 / "experiments/predictions/development_lineage_one_context_v.jsonl"
DATA = V4 / "datasets/development"
TRUTH = DATA / "ground_truth_private"
OUT = HERE / "artifacts"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def score(group, lookup, candidate):
    items = list({lookup[aid]["source_id"]: lookup[aid] for aid in group}.values())
    severity = max(a["severity"] for a in items)
    criticality = max(a["asset_criticality"] for a in items)
    diversity = len({a["event_type"] for a in items})
    sources = min(len(items), 10)
    baseline = 1.2 * severity + .7 * criticality + .55 * diversity + .1 * sources
    if candidate == "source_depth":
        return baseline + .6 * sources
    if candidate == "diverse_depth":
        return baseline + .4 * sources + .5 * diversity
    if candidate == "temporal_depth":
        span = max(a["event_minute"] for a in items) - min(a["event_minute"] for a in items)
        return baseline + .4 * sources + .3 * min(span / 10, 5)
    raise ValueError(candidate)


def main():
    OUT.mkdir(exist_ok=True)
    baseline = read_jsonl(BASE)
    baseline_eval_path = OUT / "development_baseline_evaluation.json"
    if not baseline_eval_path.exists():
        evaluate(BASE, TRUTH, baseline_eval_path)
    b = json.loads(baseline_eval_path.read_text(encoding="utf-8"))
    results = []
    for candidate in ("source_depth", "diverse_depth", "temporal_depth"):
        predictions = OUT / f"development_{candidate}.jsonl"
        evaluation = OUT / f"development_{candidate}_evaluation.json"
        if not predictions.exists():
            with predictions.open("w", encoding="utf-8", newline="\n") as stream:
                for row in baseline:
                    queue = row["queue_id"]
                    alerts = read_jsonl(DATA / "generated_alerts" / f"{queue}.jsonl")
                    ledger = read_jsonl(DATA / "evidence_ledger" / f"{queue}.jsonl")
                    availability = {x["artifact_id"]: x["evidence_available_minute"] for x in ledger}
                    visible = {a["alert_id"]: a for a in alerts if availability[a["alert_id"]] <= row["cutoff"]}
                    assert set(visible) == set(row["eligible_alert_ids"])
                    assert all(a["evidence_available_minute"] <= row["cutoff"] for a in visible.values())
                    ranked = sorted(row["groups_ranked"], key=lambda g: (-score(g, visible, candidate), g[0]))
                    changed = dict(row, groups_ranked=ranked, ranker=candidate)
                    stream.write(json.dumps(changed, sort_keys=True) + "\n")
        if not evaluation.exists():
            evaluate(predictions, TRUTH, evaluation)
        e = json.loads(evaluation.read_text(encoding="utf-8"))
        base_queues = {x["queue_id"]: x for x in b["queues"]}
        queue_regressions = [q["queue_id"] for q in e["queues"] if q["false_grouped_pairs"] > base_queues[q["queue_id"]]["false_grouped_pairs"] or q["mixed_predicted_groups"] > base_queues[q["queue_id"]]["mixed_predicted_groups"]]
        s, bs = e["summary"], b["summary"]
        gate = all((s["recall20_count"] > bs["recall20_count"],
                    s["recoverable"] >= bs["recoverable"],
                    s["p10_count"] >= bs["p10_count"],
                    s["grouped_pair_precision"] >= bs["grouped_pair_precision"],
                    s["false_grouped_pairs"] <= bs["false_grouped_pairs"],
                    s["mixed_predicted_groups"] <= bs["mixed_predicted_groups"],
                    not queue_regressions))
        results.append({"candidate": candidate, "recall20_count": s["recall20_count"],
                        "recall20_denominator": s["expert_top20"], "recoverable": s["recoverable"],
                        "p10_count": s["p10_count"], "p10_denominator": 10 * s["queues"],
                        "pair_precision": s["grouped_pair_precision"],
                        "false_grouped_pairs": s["false_grouped_pairs"],
                        "mixed_groups": s["mixed_predicted_groups"],
                        "queue_safety_regressions": len(queue_regressions),
                        "development_gate": gate, "prediction_sha256": hashlib.sha256(predictions.read_bytes()).hexdigest()})
    for filename in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv"):
        with (HERE / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
