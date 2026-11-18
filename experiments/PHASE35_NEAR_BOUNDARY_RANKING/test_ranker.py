"""Focused preservation tests for the one pairwise candidate."""
import json
import unittest
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent


def first(path):
    with path.open(encoding="utf-8") as stream:
        return json.loads(stream.readline())


class BoundaryRankerTests(unittest.TestCase):
    def test_preserves_top_ten_tail_and_groups(self):
        baseline = first(HERE / "artifacts/train_baseline_predictions.jsonl")
        decisions = first(HERE / "artifacts/train_baseline_decisions.jsonl")
        params = json.loads((HERE / "artifacts/pairwise_params.json").read_text(encoding="utf-8"))
        result = ranker.rerank(baseline, decisions, HERE / "dataset/receiver_visible/train", params)
        self.assertEqual(result["groups_ranked"][:10], baseline["groups_ranked"][:10])
        self.assertEqual(result["groups_ranked"][30:], baseline["groups_ranked"][30:])
        self.assertEqual(sorted(map(tuple, result["groups_ranked"])),
                         sorted(map(tuple, baseline["groups_ranked"])))
        self.assertEqual(result["eligible_alert_ids"], baseline["eligible_alert_ids"])
        self.assertFalse({"incident_id", "priority_rank", "true_relation"} & set(result))

    def test_training_window_and_features_frozen(self):
        params = json.loads((HERE / "artifacts/pairwise_params.json").read_text(encoding="utf-8"))
        self.assertEqual(params["window"], [11, 30])
        self.assertEqual(params["feature_order"], list(ranker.FEATURE_ORDER))


if __name__ == "__main__": unittest.main()
