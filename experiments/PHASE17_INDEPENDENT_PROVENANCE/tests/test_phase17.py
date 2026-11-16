import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from model import FIELDS,ALLOWED,candidates,fragments,lines,visible


class Phase17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((HERE/"datasets/manifest.json").read_text())
        cls.config=json.loads((HERE/"configs/study.json").read_text())

    def test_new_namespace_split_and_sensor_rng(self):
        templates=[set(x) for x in self.manifest["templates"].values()]
        self.assertFalse(templates[0]&templates[1] or templates[0]&templates[2] or templates[1]&templates[2])
        self.assertTrue(all(q["queue_id"].startswith("phase17a_") for rows in self.manifest["queues"].values() for q in rows))
        for values in self.manifest["sensor_process_seeds"].values():
            self.assertEqual(len(set(values.values())),4)

    def test_model_schema_and_label_separation(self):
        self.assertNotIn("ground_truth_private",(HERE/"model.py").read_text())
        q=self.manifest["queues"]["development"][0]["queue_id"]
        a=lines(HERE/"datasets/development/generated_alerts"/f"{q}.jsonl")
        self.assertTrue(all(set(x)<=ALLOWED for x in a))
        self.assertTrue(all("incident_id" not in x and "action_ref_private" not in x for x in a))

    def test_field_availability_masks_future_values(self):
        q=self.manifest["queues"]["locked_test"][0]["queue_id"]
        raw={x["alert_id"]:x for x in lines(HERE/"datasets/locked_test/generated_alerts"/f"{q}.jsonl")}
        field_rows=lines(HERE/"datasets/locked_test/field_ledger"/f"{q}.jsonl")
        delayed={(x["artifact_id"],x["field"]) for x in field_rows if x["available_minute"]>100}
        seen=visible(HERE/"datasets","locked_test",q,100)
        self.assertTrue(delayed)
        self.assertTrue(all(x["evidence_available_minute"]<=100 for x in seen))
        checked=0
        for a in seen:
            for field in FIELDS:
                if (a["alert_id"],field) in delayed and raw[a["alert_id"]][field] is not None:
                    self.assertIsNone(a[field]);checked+=1
        self.assertGreater(checked,0)

    def test_fragment_candidates_and_cap(self):
        q=self.manifest["queues"]["development"][0]["queue_id"]
        a=visible(HERE/"datasets","development",q,100)
        groups=fragments(a,100)
        self.assertEqual(sum(map(len,groups)),len(a))
        self.assertLessEqual(max(map(len,groups)),100)
        rows=candidates(a,groups)
        self.assertTrue(rows)
        self.assertTrue(all(x["source_witnesses"]>=2 for x in rows))

    def test_train_only_calibration_and_pretest_freeze(self):
        model=json.loads((HERE/"models/reliability.json").read_text())
        self.assertEqual(model["train_queues"],15)
        self.assertEqual(sum(model["total"].values()),sum(sum(x.values()) for x in model["counts"].values()))
        freeze=json.loads((HERE/"experiments/selection_freeze.json").read_text())
        for path,digest in freeze["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(freeze["selected"],{"method":"calibrated_2","ranker":"progression"})
        files=list((HERE/"experiments/predictions").glob("locked_test_*.jsonl"))
        self.assertEqual(len(files),1)

    def test_locked_metric_arithmetic(self):
        result=json.loads((HERE/"experiments/locked_test_result.json").read_text())
        b=result["test_baseline"]
        self.assertEqual((b["queues"],b["expert_top20"],b["recoverable"],b["recall20_count"]),(30,600,0,0))
        self.assertAlmostEqual(b["grouped_pair_precision"],b["pair_tp"]/(b["pair_tp"]+b["false_grouped_pairs"]))


if __name__=="__main__":unittest.main()
