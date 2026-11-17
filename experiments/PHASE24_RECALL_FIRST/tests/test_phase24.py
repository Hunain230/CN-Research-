import csv
import hashlib
import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
V = HERE / "v4"
sys.path.insert(0, str(V))
from predict import rows, visible  # noqa: E402


def csv_rows(name):
    with (HERE / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class Phase24Tests(unittest.TestCase):
    def test_split_and_lock_boundary(self):
        manifest = json.loads((V / "datasets" / "manifest.json").read_text())
        self.assertEqual(set(manifest["queues"]), {"train", "development"})
        self.assertEqual([len(manifest["queues"][x]) for x in ("train", "development")], [10, 16])
        self.assertFalse((V / "datasets" / "locked_test").exists())
        self.assertTrue(set(manifest["split_templates"]["train"]).isdisjoint(
            manifest["split_templates"]["development"]))

    def test_freeze_hashes_and_prediction_scope(self):
        freeze = json.loads((V / "freeze_manifest.json").read_text())
        self.assertFalse(freeze["locked_cohort_created"])
        for name, digest in freeze["hashes"].items():
            self.assertEqual(hashlib.sha256((V / name).read_bytes()).hexdigest(), digest)
        predictions = rows(V / "development_predictions.jsonl")
        self.assertEqual(len(predictions), 16 * 7 * 4)
        self.assertEqual({x["split"] for x in predictions}, {"development"})
        self.assertFalse(any("incident_id" in x or "priority_rank" in x for x in predictions))

    def test_visibility_masks_late_fields(self):
        q = "phase24d_development_q000"
        raw = {x["alert_id"]: x for x in rows(V / "datasets/development/generated_alerts" / f"{q}.jsonl")}
        field_ledger = rows(V / "datasets/development/field_ledger" / f"{q}.jsonl")
        late = {(x["artifact_id"], x["field"]) for x in field_ledger if x["available_minute"] > 100}
        exposed = visible("development", q)
        self.assertTrue(late)
        for alert in exposed:
            self.assertLessEqual(alert["evidence_available_minute"], 100)
            for field in ("host", "account", "process_tree_ref", "auth_session_ref", "network_flow_ref"):
                if (alert["alert_id"], field) in late:
                    self.assertIsNone(alert[field])
                elif raw[alert["alert_id"]][field] is not None:
                    self.assertEqual(alert[field], raw[alert["alert_id"]][field])

    def test_union_increments_and_gate(self):
        unions = csv_rows("PHASE24_UNION_PAIR_AUDIT.csv")
        queues = csv_rows("PHASE24_QUEUE_METRICS.csv")
        by_key = defaultdict(list)
        for row in unions:
            by_key[row["queue_id"], row["rule"]].append(row)
        for row in queues:
            increments = by_key[row["queue_id"], row["rule"]]
            self.assertEqual(int(row["accepted_unions"]), len(increments))
            self.assertEqual(int(row["false_grouped_pairs"]),
                             sum(int(x["new_false_pairs"]) for x in increments))
        compare = csv_rows("PHASE24_EXPERIMENT_COMPARISON.csv")
        self.assertFalse(any(x["acceptance_pass"] == "True" for x in compare))
        rare = next(x for x in compare if x["rule"] == "coherent_rare" and x["ranker"] == "blend")
        self.assertEqual(rare["queue_safety_pass"], "False")

    def test_trust_counterfactuals(self):
        stress = csv_rows("PHASE24_TRUST_STRESS.csv")
        self.assertEqual(len(stress), 40)
        by_mode = defaultdict(list)
        for row in stress:
            by_mode[row["mode"]].append(row)
        self.assertTrue(all(int(x["false_pairs"]) == 0 for x in by_mode["shared_controller_corruption"]))
        self.assertTrue(all(int(x["false_pairs"]) == 9 for x in by_mode["independent_corruption"]))
        self.assertTrue(all(x["accepted"] == "False" for x in by_mode["missing_attestation"]))


if __name__ == "__main__":
    unittest.main()
