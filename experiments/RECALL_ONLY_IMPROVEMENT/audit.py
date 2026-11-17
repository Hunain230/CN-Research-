"""Post-evaluation integrity audit; no candidate selection or tuning."""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
ART = HERE / "artifacts"


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def audit(split, baseline, candidate, data):
    b, c = lines(baseline), lines(candidate)
    assert len(b) == len(c)
    result = Counter()
    p10_losses = []
    for x, y in zip(b, c):
        q = x["queue_id"]
        assert q == y["queue_id"]
        assert x["eligible_alert_ids"] == y["eligible_alert_ids"]
        assert sorted(map(tuple, x["groups_ranked"])) == sorted(map(tuple, y["groups_ranked"]))
        assert x["cutoff"] == y["cutoff"] == 100
        alerts = lines(data / "generated_alerts" / f"{q}.jsonl")
        ledger = lines(data / "evidence_ledger" / f"{q}.jsonl")
        availability = {a["artifact_id"]: a["evidence_available_minute"] for a in ledger}
        visible = {a["alert_id"] for a in alerts if availability[a["alert_id"]] <= 100}
        assert visible == set(x["eligible_alert_ids"])
        assert all(availability[aid] <= 100 for aid in x["eligible_alert_ids"])
        result["queues"] += 1
        result["eligible_alerts"] += len(visible)
        result["unchanged_groups"] += len(x["groups_ranked"])
    be = json.loads((ART / f"{split}_baseline_evaluation.json").read_text(encoding="utf-8"))
    candidate_name = "development_source_depth_evaluation.json" if split == "development" else "fresh_candidate_evaluation.json"
    ce = json.loads((ART / candidate_name).read_text(encoding="utf-8"))
    for x, y in zip(be["queues"], ce["queues"]):
        assert x["queue_id"] == y["queue_id"]
        assert x["pair_tp"] == y["pair_tp"]
        assert x["false_grouped_pairs"] == y["false_grouped_pairs"]
        assert x["mixed_predicted_groups"] == y["mixed_predicted_groups"]
        result["recall_gain"] += max(0, y["recall20_count"] - x["recall20_count"])
        result["recall_loss"] += max(0, x["recall20_count"] - y["recall20_count"])
        result["p10_gain"] += max(0, y["p10_count"] - x["p10_count"])
        result["p10_loss"] += max(0, x["p10_count"] - y["p10_count"])
        if y["p10_count"] < x["p10_count"]:
            p10_losses.append(x["queue_id"])
    return {**result, "p10_regression_queues": p10_losses}


def main():
    dev = audit("development", V4 / "experiments/predictions/development_lineage_one_context_v.jsonl",
                ART / "development_source_depth.jsonl", V4 / "datasets/development")
    hold = audit("fresh", ART / "fresh_baseline_predictions.jsonl",
                 ART / "fresh_candidate_predictions.jsonl", ART / "fresh_cohort/datasets/locked_test")
    output = {"development": dev, "fresh_holdout": hold,
              "visible_fields": ["severity", "asset_criticality", "event_type", "source_id", "event_minute"],
              "private_truth_feature_access": False}
    (ART / "post_evaluation_audit.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
