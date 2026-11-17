"""Write paired development audits and check historical regression contracts."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
ART = HERE / "artifacts"


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def main():
    frozen = json.loads((PREV / "BASELINE_METRICS.json").read_text(encoding="utf-8"))
    for name, expected in frozen["frozen_file_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    historical = json.loads((PREV / "artifacts/historical_reproduction.json").read_text(encoding="utf-8"))["summary"]
    assert historical["recall20_count"] == 407 and historical["expert_top20"] == 600
    assert historical["false_grouped_pairs"] == 440 and historical["mixed_predicted_groups"] == 257
    previous = json.loads((PREV / "artifacts/fresh_candidate_evaluation.json").read_text(encoding="utf-8"))["summary"]
    assert previous["recall20_count"] == 444 and previous["p10_count"] == 190
    reference = json.loads((PREV / "artifacts/development_source_depth_evaluation.json").read_text(encoding="utf-8"))
    baseline_predictions = lines(PREV / "artifacts/development_source_depth.jsonl")
    data = V4 / "datasets/development"
    rows = []
    for candidate in ("trained_rank", "recovery_source_depth", "hybrid"):
        result = json.loads((ART / f"development_{candidate}_evaluation.json").read_text(encoding="utf-8"))
        predictions = lines(ART / f"development_{candidate}.jsonl")
        assert len(predictions) == len(baseline_predictions) == 15
        for b, c, bp, cp in zip(reference["queues"], result["queues"], baseline_predictions, predictions):
            assert b["queue_id"] == c["queue_id"] == bp["queue_id"] == cp["queue_id"]
            assert bp["eligible_alert_ids"] == cp["eligible_alert_ids"]
            q = bp["queue_id"]
            alerts = lines(data / "generated_alerts" / f"{q}.jsonl")
            ledger = lines(data / "evidence_ledger" / f"{q}.jsonl")
            available = {x["artifact_id"]: x["evidence_available_minute"] for x in ledger}
            assert set(bp["eligible_alert_ids"]) == {x["alert_id"] for x in alerts if available[x["alert_id"]] <= 100}
            assert all(available[aid] <= 100 for aid in cp["eligible_alert_ids"])
            assert {a for g in cp["groups_ranked"] for a in g} == set(cp["eligible_alert_ids"])
            rows.append({"candidate": candidate, "queue_id": q,
                "baseline_recall": b["recall20_count"], "candidate_recall": c["recall20_count"],
                "baseline_recoverable": b["recoverable"], "candidate_recoverable": c["recoverable"],
                "baseline_p10": b["p10_count"], "candidate_p10": c["p10_count"],
                "baseline_false_pairs": b["false_grouped_pairs"], "candidate_false_pairs": c["false_grouped_pairs"],
                "baseline_mixed_groups": b["mixed_predicted_groups"], "candidate_mixed_groups": c["mixed_predicted_groups"]})
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"historical_regression": "pass", "queues_checked": len(rows),
                      "temporal_eligibility": "pass", "queue_false_merge_regressions": sum(
                          r["candidate_false_pairs"] > r["baseline_false_pairs"] or
                          r["candidate_mixed_groups"] > r["baseline_mixed_groups"] for r in rows)}))


if __name__ == "__main__":
    main()
