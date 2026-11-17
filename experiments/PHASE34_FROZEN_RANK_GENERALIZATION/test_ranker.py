"""Check exact top-10 preservation and visible-feature-only ranking."""
import json
import unittest
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent


def first_line(path):
    with path.open(encoding="utf-8") as stream:
        return json.loads(stream.readline())


class FrozenTopTenTests(unittest.TestCase):
    def test_both_models_preserve_top_ten_and_partition(self):
        pred = first_line(HERE / "artifacts/train_frozen_predictions.jsonl")
        audit = first_line(HERE / "artifacts/train_frozen_decisions.jsonl")
        for name in ("top20_logistic", "priority_ridge"):
            params = json.loads((HERE / f"artifacts/{name}_params.json").read_text(encoding="utf-8"))
            result = ranker.rerank(pred, audit, HERE / "dataset/receiver_visible/train", params, name)
            self.assertEqual(result["groups_ranked"][:10], pred["groups_ranked"][:10])
            self.assertEqual(sorted(map(tuple, result["groups_ranked"])),
                             sorted(map(tuple, pred["groups_ranked"])))
            self.assertEqual(result["eligible_alert_ids"], pred["eligible_alert_ids"])
            self.assertFalse({"incident_id", "priority_rank", "scenario_id"} & set(result))

    def test_features_exclude_hidden_truth_fields(self):
        self.assertEqual(ranker.FEATURE_ORDER, ("frozen_score", "unique_sources", "max_severity",
            "mean_severity", "max_criticality", "mean_criticality", "event_diversity",
            "group_size", "time_span", "verified_unions"))


if __name__ == "__main__": unittest.main()
