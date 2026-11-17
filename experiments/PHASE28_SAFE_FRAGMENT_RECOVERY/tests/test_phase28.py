import csv
import hashlib
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "v2"
sys.path.insert(0, str(V))
from promote import load, features, promote  # noqa: E402


def table(name):
    with (V / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def jsonl(name):
    with (V / name).open(encoding="utf-8") as stream:
        return [json.loads(x) for x in stream]


class Phase28Tests(unittest.TestCase):
    def test_fresh_splits_and_one_holdout(self):
        manifest = json.loads((V / "datasets/manifest.json").read_text())
        locked = json.loads((V / "datasets/locked_test/manifest.json").read_text())
        self.assertEqual((len(manifest["queues"]["train"]),
                          len(manifest["queues"]["development"]),
                          len(locked["queues"])), (12, 20, 30))
        self.assertEqual(manifest["namespace"], "phase28b")
        self.assertEqual(locked["namespace"], "phase28h")
        self.assertTrue(set(manifest["scenario_variants"]["train"]).isdisjoint(
                        manifest["scenario_variants"]["development"]))

    def test_freeze_and_point_in_time_predictions(self):
        for name in ("development_freeze.json", "pre_evaluation_protocol.json"):
            frozen = json.loads((V / name).read_text())
            for path, expected in frozen["hashes"].items():
                self.assertEqual(hashlib.sha256((V / path).read_bytes()).hexdigest(), expected)
        locked = json.loads((V / "locked_prediction_freeze.json").read_text())
        for mapping in (locked["public_input_hashes"], locked["prediction_hashes"]):
            for path, expected in mapping.items():
                self.assertEqual(hashlib.sha256((V / path).read_bytes()).hexdigest(), expected)
        for name in ("development_predictions.jsonl", "locked_predictions.jsonl"):
            for row in jsonl(name):
                self.assertEqual(row["decision_minute"], 100)
                self.assertEqual(len(row["snapshot_sha256"]), 64)

    def test_no_future_evidence_in_promotion_features(self):
        q = "phase28b_development_q000"
        snap, source, edges, groups, baseline, hyp = load("development", q)
        self.assertTrue(all(e["receiver_visible_minute"] <= 100 for e in edges))
        self.assertTrue(hyp)
        f = features(hyp[0], groups, edges, snap.alerts)
        self.assertLessEqual(f["max_arrival"], 100)
        self.assertGreaterEqual(f["root_disjoint_witnesses"], 0)

    def test_training_guard_and_holdout_failure_visible(self):
        model = json.loads((V / "promotion_model.json").read_text())
        self.assertEqual(model["training_guarded_false"], 0)
        self.assertGreater(model["training_guarded_true"], 0)
        result = json.loads((V / "locked_result.json").read_text())
        self.assertEqual(result["decision"], "NO-GO")
        self.assertEqual(result["selected"]["false_grouped_pairs"] -
                         result["baseline"]["false_grouped_pairs"], 35)

    def test_union_accounting_and_counterfactual(self):
        by_key = defaultdict(int)
        for name in ("PHASE28_UNION_PAIR_AUDIT.csv", "PHASE28_LOCKED_UNION_PAIR_AUDIT.csv"):
            by_key.clear()
            for row in table(name):
                by_key[row["queue_id"], row["mode"]] += int(row["new_false_pairs"])
            cascade = name.replace("UNION_PAIR_AUDIT", "FAILURE_CASCADE")
            for row in table(cascade):
                self.assertEqual(by_key[row["queue_id"], row["mode"]], int(row["false_pairs"]))
        with (ROOT / "PHASE28_COMPONENT_COUNTERFACTUAL.csv").open(newline="", encoding="utf-8") as stream:
            counter = list(csv.DictReader(stream))
        self.assertEqual(sum(int(x["pairs_avoided"]) > 0 for x in counter), 7)
        self.assertEqual(sum(int(x["pairs_avoided"]) for x in counter), 35)
        self.assertEqual(sum(int(x["touches_injected_false_sources"]) for x in counter), 7)

    def test_rejected_hypotheses_are_retained_for_discovery(self):
        q = "phase28b_development_q000"
        snap, source, edges, groups, baseline, hyp = load("development", q)
        model = json.loads((V / "promotion_model.json").read_text())
        final_groups, decisions = promote(groups, hyp, edges, snap.alerts, snap, model, "component")
        self.assertTrue(any(x["decision"] == "RETAIN AS HYPOTHESIS" for x in decisions))
        self.assertEqual(sum(map(len, groups)), sum(map(len, final_groups)))
        self.assertTrue(all(x["snapshot_sha256"] == snap.sha256 for x in decisions))


if __name__ == "__main__":
    unittest.main()
