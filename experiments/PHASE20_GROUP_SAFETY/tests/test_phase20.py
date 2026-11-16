import csv
import json
import unittest
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]

class Phase20StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=json.loads((HERE/"study_summary.json").read_text())
        with (HERE/"merge_increments.csv").open(newline="",encoding="utf-8") as stream:
            cls.merges=list(csv.DictReader(stream))

    def test_union_replay_reconciles_every_cohort(self):
        for cohort,metrics in self.summary.items():
            expected=metrics.get("false_grouped_pairs",metrics.get("summary",{}).get("false_grouped_pairs"))
            observed=metrics["seed_false_pairs"]+sum(int(r["new_false_pairs"]) for r in self.merges if r["cohort"]==cohort)
            self.assertEqual(observed,expected,cohort)
            self.assertEqual(sum(r["cohort"]==cohort for r in self.merges),metrics["accepted_unions"])

    def test_stress_covers_all_queues_and_collision_types(self):
        with (HERE/"stress/injections.csv").open(newline="",encoding="utf-8") as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len({r["queue_id"] for r in rows}),15)
        counts=Counter(r["pattern"] for r in rows)
        self.assertTrue(all(counts[x]>=20 for x in ("context_only","auth","network","auth_network")))
        self.assertGreaterEqual(len(rows),100)

    def test_guard_has_no_false_pairs_but_fails_recovery_gate(self):
        for cohort in ("ordinary","stress"):
            row=self.summary[cohort]
            self.assertEqual(row["summary"]["false_grouped_pairs"],0)
            self.assertEqual(row["summary"]["mixed_predicted_groups"],0)
        self.assertLess(self.summary["ordinary"]["summary"]["recoverable"],
                        self.summary["ordinary_baseline"]["recoverable"])
        self.assertEqual(self.summary["stress"]["summary"]["recoverable"],0)

    def test_group_cap_and_cumulative_exposure_logged(self):
        for cohort in ("ordinary","stress"):
            with (HERE/f"{cohort}_group_guard_decisions.jsonl").open(encoding="utf-8") as stream:
                for record in (json.loads(x) for x in stream):
                    for decision in record["records"]:
                        if decision["decision"]=="accept":
                            self.assertLessEqual(decision["proposed_fragment_count"],2)
                            self.assertLessEqual(decision["proposed_cumulative_exposure"],250)
                            self.assertTrue(decision["source_root_independence"])

    def test_locked_cohort_remains_unopened(self):
        p19=HERE.parent/"PHASE19_DEV_RECONSTRUCTION"
        freeze=json.loads((p19/"experiments/development_freeze.json").read_text())
        self.assertFalse(freeze["locked_truth_read"])
        self.assertFalse(freeze["locked_predictions_created"])
        self.assertFalse(list(p19.rglob("locked_test_*evaluation*.json")))
        self.assertFalse(list(HERE.rglob("locked_test_*")))

if __name__=="__main__":unittest.main()
