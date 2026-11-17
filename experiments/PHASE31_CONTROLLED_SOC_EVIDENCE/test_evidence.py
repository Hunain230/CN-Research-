"""Controlled expected outcomes for provenance, corruption, and leakage."""
import json
import random
import tempfile
import unittest
from pathlib import Path

import generator
import model


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(31)
        self.left = generator.make_alert(self.rng, "q", "host_1", "account_1", "service_1", 10,
            "process", "tree_a", 4, 4)
        self.right = generator.make_alert(self.rng, "q", "host_1", "account_1", "service_1", 15,
            "authentication", "tree_b", 4, 4)
        self.right["parent_process_id"] = self.left["process_id"]
        self.right["auth_session_id"] = self.left["auth_session_id"]
        self.right["flow_id"] = self.left["flow_id"]
        self.alerts = {x["alert_id"]: x for x in (self.left, self.right)}

    def bundle(self):
        return [generator.claim(self.rng, "q", self.left, self.right, "rel", f) for f in model.FAMILIES]

    def test_three_independent_origins_verify(self):
        good, reason = model.validate_attestation_bundle(self.bundle(), self.alerts, 100)
        self.assertEqual((good, reason), (True, "verified"))

    def test_derived_copy_does_not_replace_independent_family(self):
        bundle = self.bundle()[:2]
        copy = generator.claim(self.rng, "q", self.left, self.right, "rel", "authentication",
            derived_from=bundle[1]["observation_id"], upstream_root=bundle[1]["upstream_root_id"])
        good, _ = model.validate_attestation_bundle(bundle + [copy], self.alerts, 100)
        self.assertFalse(good)

    def test_corrupted_triads_rejected(self):
        bundle = self.bundle()
        bundle[0]["right_parent_process_id"] = "wrong"
        good, reason = model.validate_attestation_bundle(bundle, self.alerts, 100)
        self.assertEqual((good, reason), (False, "attestation_fields_conflict"))

    def test_private_field_and_future_evidence_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("alerts", "claims", "evidence_ledger"):
                (root / name).mkdir()
            late = dict(self.right, evidence_available_minute=120)
            for directory, records in (("alerts", [self.left, late]), ("claims", []),
                ("evidence_ledger", [{"sequence": 1, "artifact_id": self.left["alert_id"],
                    "evidence_available_minute": self.left["evidence_available_minute"]},
                    {"sequence": 2, "artifact_id": late["alert_id"], "evidence_available_minute": 120}])):
                (root / directory / "q.jsonl").write_text("".join(json.dumps(x) + "\n" for x in records))
            alerts, _ = model.visible_input(root, "q", 100)
            self.assertEqual(set(alerts), {self.left["alert_id"]})
            bad = dict(self.left, incident_id="hidden")
            (root / "alerts/q.jsonl").write_text(json.dumps(bad) + "\n" + json.dumps(late) + "\n")
            with self.assertRaises(ValueError): model.visible_input(root, "q", 100)


if __name__ == "__main__":
    unittest.main()
