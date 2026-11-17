"""Endpoint fallback accepts only a visible three-root causal relationship."""
import importlib.util
import random
import unittest
from pathlib import Path

import model

P31 = Path(__file__).resolve().parents[1] / "PHASE31_CONTROLLED_SOC_EVIDENCE"
spec = importlib.util.spec_from_file_location("frozen_generator", P31 / "generator.py")
generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)


class FallbackTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(32)
        self.left = generator.make_alert(rng, "q", "host_1", "account_1", "service_1", 10,
            "process", "tree_1", 4, 4)
        self.right = generator.make_alert(rng, "q", "host_1", "account_1", "service_1", 15,
            "authentication", "tree_2", 4, 4)
        self.right["parent_process_id"] = self.left["process_id"]
        self.right["auth_session_id"] = self.left["auth_session_id"]
        self.right["flow_id"] = self.left["flow_id"]
        self.bundle = [generator.claim(rng, "q", self.left, self.right, "token", f)
                       for f in ("authentication", "network_flow")]
        self.lookup = {x["alert_id"]: x for x in (self.left, self.right)}

    def test_existing_endpoint_observation_supplies_third_root(self):
        self.assertEqual(model.endpoint_process_fallback(self.bundle, self.lookup, 100),
                         (True, "endpoint_process_attested"))

    def test_same_context_without_process_parent_link_rejected(self):
        self.right["parent_process_id"] = "unrelated"
        good, reason = model.endpoint_process_fallback(self.bundle, self.lookup, 100)
        self.assertFalse(good)
        self.assertIn(reason, ("causal_fields_conflict", "claim_fields_conflict"))

    def test_derived_endpoint_does_not_supply_independence(self):
        self.right["duplicate_of"] = self.left["observation_id"]
        good, reason = model.endpoint_process_fallback(self.bundle, self.lookup, 100)
        self.assertEqual((good, reason), (False, "derived_endpoint"))

    def test_available_contradictory_process_claim_not_replaced(self):
        rng = random.Random(33)
        process = generator.claim(rng, "q", self.left, self.right, "token", "process", corrupt=True)
        good, reason = model.endpoint_process_fallback(self.bundle + [process], self.lookup, 100)
        self.assertEqual((good, reason), (False, "not_exact_auth_network_pair"))


if __name__ == "__main__": unittest.main()
