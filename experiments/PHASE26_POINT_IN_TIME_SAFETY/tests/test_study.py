import csv
import hashlib
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "v2"
sys.path.insert(0, str(V2))
from predict import get_snapshot, reconstruct, visible_receipts  # noqa: E402


def records(name):
    with (V2 / name).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def table(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class FrozenStudyTests(unittest.TestCase):
    def test_freeze_and_no_holdout(self):
        freeze = json.loads((V2 / "freeze_manifest.json").read_text())
        self.assertFalse((V2 / "datasets/locked_test").exists())
        for name, expected in freeze["hashes"].items():
            self.assertEqual(hashlib.sha256((V2 / name).read_bytes()).hexdigest(), expected, name)

    def test_all_predictions_and_decisions_have_same_cutoff_snapshot(self):
        predictions = records("development_predictions.jsonl")
        decisions = records("development_decisions.jsonl")
        hashes = {q: get_snapshot("development", q).sha256 for q in
                  {x["queue_id"] for x in predictions}}
        self.assertEqual(len(predictions), 20 * 9 * 3)
        self.assertEqual(len(decisions), 20 * 9)
        for prediction in predictions:
            self.assertEqual(prediction["decision_minute"], 100)
            self.assertEqual(prediction["evidence_snapshot_sha256"], hashes[prediction["queue_id"]])
        for row in decisions:
            for decision in row["decisions"]:
                self.assertEqual(decision["decision_minute"], 100)
                self.assertEqual(decision["snapshot_sha256"], hashes[row["queue_id"]])
                self.assertIn("evidence", decision)
                self.assertIn("support", decision)

    def test_delayed_contradiction_and_correlated_receipts(self):
        q = "phase26b_development_q000"
        snap = get_snapshot("development", q)
        late = f"{q}_benign_005_a0"
        self.assertEqual(snap.states[late, "host"], "NOT_YET_AVAILABLE")
        receipts = visible_receipts("development", q)
        for rule, expected in (("orthogonal_veto", True), ("pit_complete", False),
                               ("pit_selective", False), ("pit_direct", False)):
            _, decisions, _ = reconstruct(snap.alerts, rule, receipts=receipts,
                                          states=snap.states, snapshot_hash=snap.sha256)
            merged = any(d["decision"] == "accept" and
                         {f"{q}_benign_004_a0", late}.issubset(set(d["left"] + d["right"]))
                         for d in decisions)
            self.assertEqual(merged, expected, rule)
        stress = table("PHASE26_DELAY_STRESS_RESULTS.csv")
        self.assertEqual(sum(int(x["new_false_pair_at_100"]) for x in stress if
                             x["rule"] == "pit_selective"), 0)
        self.assertEqual(sum(int(x["new_false_pair_at_100"]) for x in stress if
                             x["rule"] == "orthogonal_veto"), 80)
        self.assertEqual(sum(int(x["new_false_pair_at_100"]) for x in stress if
                             x["rule"] == "pit_direct"), 20)

    def test_union_and_queue_metric_reconciliation(self):
        unions = defaultdict(lambda: [0, 0])
        for row in table("PHASE26_UNION_PAIR_AUDIT.csv"):
            key = row["queue_id"], row["rule"]
            unions[key][0] += 1
            unions[key][1] += int(row["new_false_pairs"])
        cascades = table("PHASE26_FAILURE_CASCADE.csv")
        for row in cascades:
            count, false_pairs = unions[row["queue_id"], row["rule"]]
            self.assertEqual(count, int(row["accepted_unions"]))
            self.assertEqual(false_pairs, int(row["false_pairs"]))
        self.assertTrue(all(x["passed"] == "False" for x in table("PHASE26_GATE_RESULTS.csv")))


if __name__ == "__main__":
    unittest.main()
