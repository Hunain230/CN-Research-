import csv
import hashlib
import json
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]


def csv_rows(name):
    with (HERE/name).open(newline="",encoding="utf-8") as stream:return list(csv.DictReader(stream))


class Phase19Tests(unittest.TestCase):
    def test_frozen_code_and_locked_separation(self):
        freeze=json.loads((HERE/"experiments/development_freeze.json").read_text())
        for rel,digest in freeze["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest)
        self.assertFalse(freeze["locked_truth_read"])
        self.assertFalse(freeze["locked_predictions_created"])
        self.assertFalse(list((HERE/"experiments/predictions").glob("locked_test_*.jsonl")))
        self.assertFalse(list((HERE/"experiments/evaluations").glob("locked_test_*.json")))
        self.assertEqual(len(json.loads((HERE/"datasets/manifest.json").read_text())["queues"]["locked_test"]),30)

    def test_baseline_readiness_and_metrics(self):
        train=csv_rows("PHASE19_TRAIN_RESULTS.csv")
        dev=csv_rows("PHASE19_DEVELOPMENT_RESULTS.csv")
        base_train=next(x for x in train if x["method"]=="dual_plus_rare_guarded")
        base_dev=next(x for x in dev if x["method"]=="dual_plus_rare_guarded")
        self.assertEqual((int(base_train["recoverable"]),int(base_dev["recoverable"])),(132,123))
        self.assertEqual((int(base_dev["false_grouped_pairs"]),int(base_dev["mixed_predicted_groups"])),(0,0))
        self.assertGreaterEqual(float(base_dev["grouped_pair_precision"]),.9)
        queues=csv_rows("PHASE19_QUEUE_RECONCILIATION.csv")
        for split in ("train","development"):
            baseline=[x for x in queues if x["split"]==split and x["method"]=="dual_plus_rare_guarded"]
            self.assertEqual(len(baseline),15)
            self.assertTrue(all(int(x["recoverable_top20"])>=1 for x in baseline))

    def test_merge_reconciliation(self):
        rows=csv_rows("PHASE19_QUEUE_RECONCILIATION.csv")
        self.assertEqual(len(rows),90)
        self.assertTrue(all(int(x["baseline_seed_true_pairs"])+int(x["added_true_pairs"])==int(x["final_true_pairs"]) for x in rows))
        self.assertTrue(all(int(x["baseline_seed_false_pairs"])+int(x["added_false_pairs"])==int(x["final_false_pairs"]) for x in rows))
        dev=[x for x in rows if x["split"]=="development" and x["method"]=="dual_plus_rare_guarded"]
        self.assertEqual(sum(int(x["accepted_merges"]) for x in dev),624)
        self.assertEqual(sum(int(x["added_false_pairs"]) for x in dev),0)

    def test_hard_negative_stress_is_not_validation(self):
        s=json.loads((HERE/"PHASE19_STRESS_SUMMARY.json").read_text())
        self.assertEqual(s["classification"],"adversarial_development_stress_not_validation")
        self.assertEqual((s["injected_incident_pairs"],s["additional_false_pairs"]),(13,1181))
        p=json.loads((HERE/"PHASE19_STRESS_PAIR_SUMMARY.json").read_text())
        self.assertEqual(p["new_false_pairs"],1181)
        self.assertEqual(p["false_pair_creating_merges"],17)
        self.assertEqual(sum(int(x["new_false_pairs"]) for x in csv_rows("PHASE19_STRESS_PAIR_INCREMENTS.csv")),1181)

    def test_no_selected_candidate(self):
        freeze=json.loads((HERE/"experiments/development_freeze.json").read_text())
        self.assertTrue(freeze["baseline_ready"])
        self.assertIsNone(freeze["selected_candidate"])
        dev=csv_rows("PHASE19_DEVELOPMENT_RESULTS.csv")
        self.assertFalse(any(x["development_acceptance"]=="True" for x in dev))


if __name__=="__main__":unittest.main()
