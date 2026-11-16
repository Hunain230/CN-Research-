import csv
import json
import math
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class AuditTests(unittest.TestCase):
    def setUp(self):
        with (HERE / "PHASE14_UPPER_BOUND_AUDIT.csv").open(newline="", encoding="utf-8") as stream:
            self.bound = list(csv.DictReader(stream))
        with (HERE / "PHASE14_ERROR_CLASSIFICATION.csv").open(newline="", encoding="utf-8") as stream:
            self.rows = list(csv.DictReader(stream))

    def test_baseline_reproduction(self):
        result = json.loads((HERE / "PHASE14_BASELINE_REPRODUCTION.json").read_text())
        self.assertEqual(result["status"], "exact_match")
        self.assertEqual(result["methods"]["E1"]["group_recoverability_count"], 6969)
        self.assertEqual(result["methods"]["E1"]["incident_recall20_count"], 5066)

    def test_bound_and_cap(self):
        self.assertEqual(len(self.bound), 9980)
        self.assertEqual(sum(int(x["phase13_bound_included"]) for x in self.bound), 8596)
        self.assertEqual(sum(int(x["corrected_cap_scope_bound_included"]) for x in self.bound), 9063)
        for row in self.bound:
            n = int(row["expert_alerts_in_scope"])
            self.assertEqual(bool(int(row["cap_feasible_80pct"])), n > 0 and math.ceil(.8*n-1e-12) <= 100)

    def test_failure_reconciliation(self):
        from collections import Counter
        self.assertEqual(len(self.rows), 9980)
        self.assertEqual(len({(x["queue_key"], x["incident_key"]) for x in self.rows}), 9980)
        self.assertEqual(Counter(x["primary_category"] for x in self.rows), {
            "A_outside_scope": 855, "E_component_cap": 62,
            "B_candidate_disconnected": 467, "C_candidate_connected_fragmented": 1409,
            "D_impure_predicted_group": 218, "G_ranking_only_or_success": 6969})

    def test_true_only_connectivity_is_not_necessary_for_eighty_percent_purity(self):
        # Four true alerts in two components, joined through one competing alert:
        # all four true alerts fit in a five-alert group with purity 4/5.
        graph = {"t1": {"t2"}, "t2": {"t1", "f"},
                 "f": {"t2", "t3"}, "t3": {"f", "t4"}, "t4": {"t3"}}
        self.assertEqual(len(graph), 5)
        self.assertEqual(sum(k.startswith("t") for k in graph)/len(graph), .8)
        self.assertFalse(any(k in graph["t2"] for k in ("t3", "t4")))

    def test_metric_arithmetic_and_group_purity(self):
        b = json.loads((HERE / "PHASE14_BASELINE_REPRODUCTION.json").read_text())["methods"]["E1"]
        # The legacy count is a rounded integer; recall is a tie-aware expectation.
        self.assertAlmostEqual(b["incident_recall20"] * 9980, 5066.5)
        self.assertAlmostEqual(b["group_recoverability"], 6969/9980)
        self.assertAlmostEqual(b["grouped_pair_precision"], 269832/(269832+28606))
        self.assertEqual(b["error_cascade"]["complete_but_impure"], 218)
        self.assertEqual(sum(b["error_cascade"].values()), 9980)

    def test_provenance_and_availability_are_not_invented(self):
        with (HERE / "PHASE14_CANDIDATE_EDGE_AUDIT.csv").open(newline="", encoding="utf-8") as stream:
            edge = list(csv.DictReader(stream))
        self.assertEqual(len(edge), 3011)
        self.assertTrue(all(x["decision_time_provenance_verified"] == "no" for x in edge))
        with (HERE / "PHASE14_FEATURE_AVAILABILITY_AUDIT.csv").open(newline="", encoding="utf-8") as stream:
            clocks = list(csv.DictReader(stream))
        self.assertEqual(len(clocks), 6)
        self.assertTrue(all(x["operational_allowlist"] == "no" for x in clocks))

    def test_evaluator_is_not_prediction_input(self):
        code = (HERE / "audit.py").read_text(encoding="utf-8")
        self.assertIn("Evaluator-only", code)
        self.assertNotIn("from src.guide_rerun_v2 import labels", code)
        self.assertNotIn("candidate_edges.append", code)


if __name__ == "__main__":
    unittest.main()
