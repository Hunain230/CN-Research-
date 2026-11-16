import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validate_package import validate


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "fixtures/synthetic_valid.json").read_text(encoding="utf-8"))

    def test_fixture_valid(self):
        errors, warnings = validate(copy.deepcopy(self.fixture))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_source_reference_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["derivations"][0]["observation_id"] = "missing"
        self.assertTrue(any("unresolved" in e for e in validate(value)[0]))

    def test_available_before_generation_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["availability_events"][3]["available_at"] = "2026-01-01T00:00:01Z"
        self.assertTrue(any("available before generated_at" in e for e in validate(value)[0]))

    def test_family_crossing_split_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["splits"][1]["partition"] = "sealed_test"
        self.assertTrue(any("scenario family crosses" in e for e in validate(value)[0]))

    def test_unjudged_is_warning_not_negative(self):
        value = copy.deepcopy(self.fixture)
        value["memberships"].pop()
        errors, warnings = validate(value)
        self.assertEqual(errors, [])
        self.assertTrue(any("membership judgment coverage 2/3" in w for w in warnings))

    def test_contradictory_membership_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["memberships"].append({"alert_id": "a1", "incident_id": None,
                                     "judgment": "negative", "adjudicator_ref": "fixture-second-reviewer",
                                     "decided_at": "2026-01-02T00:00:01Z"})
        self.assertTrue(any("contradictory" in e for e in validate(value)[0]))

    def test_ledger_correction_before_availability_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["availability_events"][0]["kind"] = "corrected"
        self.assertTrue(any("first ledger event" in e for e in validate(value)[0]))


if __name__ == "__main__":
    unittest.main()
