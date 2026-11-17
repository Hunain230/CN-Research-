import hashlib
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from run_study import decide_domains, read, registry_for  # noqa: E402


class TrustDomainStudyTests(unittest.TestCase):
    def test_independent_sensor_labels_can_share_one_controller(self):
        receipts = [
            {"source_record_id": "a", "sensor": "auth"},
            {"source_record_id": "n", "sensor": "network"},
            {"source_record_id": "e", "sensor": "endpoint"},
        ]
        registry = registry_for(receipts, "shared_controller")
        self.assertEqual(registry["a"], registry["n"])
        self.assertNotEqual(registry["a"], registry["e"])

    def test_unattested_root_abstains(self):
        alerts = [{"alert_id": key, "fragment_ref": key, "severity": 1,
                   "asset_criticality": 1} for key in ("L", "R")]
        claims = []
        receipts = []
        for sensor, source, child in (("auth", "a", "c1"), ("endpoint", "e", "c2")):
            claims.append({"claim_id": source, "sensor": sensor, "source_record_id": source,
                           "origin_event_id": child, "parent_event_id": "p",
                           "left_fragment_ref": "L", "right_fragment_ref": "R"})
            receipts.append({"source_record_id": source, "sensor": sensor,
                             "origin_event_id": child, "observed_parent_event_ids": ["p"],
                             "observed_fragment_ref": "R"})
        receipts.append({"source_record_id": "parent", "sensor": "network",
                         "origin_event_id": "p", "observed_parent_event_ids": [],
                         "observed_fragment_ref": "L"})
        _, decisions, _ = decide_domains(alerts, claims, receipts, {"a": "root_a"})
        self.assertEqual(decisions[-1]["reason"], "unattested_upstream_root")

    def test_frozen_predictions_and_union_accounting(self):
        freeze = json.loads((HERE / "freeze_manifest.json").read_text())
        self.assertFalse(freeze["phase19_locked_truth_read"])
        self.assertFalse(freeze["phase22_locked_truth_read"])
        self.assertFalse(freeze["phase22_locked_predictions_created"])
        self.assertEqual(freeze["predictions_sha256"], hashlib.sha256(
            (HERE / "predictions_and_decisions.jsonl").read_bytes()).hexdigest())
        queues = read(HERE / "queue_audit.jsonl")
        unions = read(HERE / "union_pair_increments.jsonl")
        self.assertEqual(len(queues), 90)
        self.assertFalse(any(row["split"] != "development" for row in queues))
        by_key = defaultdict(list)
        for row in unions:
            by_key[row["scenario"], row["rule"], row["queue_id"]].append(row)
        for row in queues:
            increments = by_key[row["scenario"], row["rule"], row["queue_id"]]
            self.assertEqual(row["accepted_unions"], len(increments))
            self.assertEqual(row["false_pairs"], sum(x["new_false_pairs"] for x in increments))

    def test_common_mode_blocked_but_independent_corruption_remains(self):
        summary = json.loads((HERE / "summary.json").read_text())
        shared = summary["shared_controller"]["trust_domains"]
        independent = summary["independent_corruption"]["trust_domains"]
        self.assertEqual(shared["false_pairs"], 0)
        self.assertEqual(shared["false_pair_creating_unions"], 0)
        self.assertGreater(independent["false_pairs"], 0)
        self.assertGreater(independent["false_pair_creating_unions"], 0)
        self.assertEqual(summary["missing_root"]["trust_domains"]["accepted_unions"], 0)


if __name__ == "__main__":
    unittest.main()
