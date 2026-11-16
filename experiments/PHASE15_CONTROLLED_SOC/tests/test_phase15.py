import csv
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from pipeline import ALLOWED, FORBIDDEN, groups_for, load_visible
from evaluation.evaluate import evaluate_queue, read_lines


class Phase15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((HERE/"configs/study.json").read_text())
        cls.data=HERE/"datasets"
        cls.manifest=json.loads((cls.data/"manifest.json").read_text())

    def test_template_and_scenario_disjoint(self):
        templates=[set(v) for v in self.manifest["template_assignment"].values()]
        self.assertFalse(templates[0]&templates[1] or templates[0]&templates[2] or templates[1]&templates[2])
        split_sources=[]
        for split,queues in self.manifest["splits"].items():
            ids=[]
            for q in queues:
                rows=read_lines(self.data/split/"ground_truth_private"/f"{q['queue_id']}.jsonl")
                ids.extend(x["source_id"] for x in rows)
            split_sources.append(set(ids))
            self.assertTrue(all(x.startswith(split+"_") for x in ids))
        self.assertFalse(split_sources[0]&split_sources[1] or split_sources[0]&split_sources[2] or split_sources[1]&split_sources[2])

    def test_model_schema_and_no_private_import(self):
        prediction_source=(HERE/"pipeline.py").read_text()
        self.assertNotIn('ground_truth_private',prediction_source)
        for split,queues in self.manifest["splits"].items():
            q=queues[0]["queue_id"]
            rows=read_lines(self.data/split/"generated_alerts"/f"{q}.jsonl")
            self.assertTrue(all(set(a)<=ALLOWED and not set(a)&FORBIDDEN for a in rows))

    def test_availability_and_lineage(self):
        q=self.manifest["splits"]["locked_test"][0]["queue_id"]
        all_rows=read_lines(self.data/"locked_test"/"generated_alerts"/f"{q}.jsonl")
        visible=load_visible(self.data,"locked_test",q,90)
        self.assertLess(len(visible),len(all_rows))
        self.assertTrue(all(a["evidence_available_minute"]<=90 for a in visible))
        ledger=read_lines(self.data/"locked_test"/"evidence_ledger"/f"{q}.jsonl")
        self.assertTrue(all(x["event_minute"]<=x["collection_minute"]<=x["detector_minute"]<=x["evidence_available_minute"]<=x["processing_minute"] for x in ledger))
        sources={x["source_id"] for x in read_lines(self.data/"locked_test"/"source_observations"/f"{q}.jsonl")}
        self.assertTrue(all(a["source_id"] in sources for a in all_rows))

    def test_deterministic_groups_and_cap(self):
        q=self.manifest["splits"]["development"][0]["queue_id"]
        alerts=load_visible(self.data,"development",q,90)
        a=groups_for(alerts,"multi_v",100)
        b=groups_for(alerts,"multi_v",100)
        self.assertEqual(a,b)
        self.assertLessEqual(max(map(len,a[0])),100)

    def test_metric_reconciliation(self):
        path=HERE/"experiments/evaluations/locked_test_exact_progression.json"
        data=json.loads(path.read_text())
        s=data["summary"]
        self.assertEqual(sum(x["expert_top20"] for x in data["queues"]),60)
        self.assertEqual(s["recoverable"],17)
        self.assertEqual(s["recall20_count"],13)
        self.assertAlmostEqual(s["incident_recall20"],13/60)
        self.assertAlmostEqual(s["grouped_pair_precision"],s["pair_tp"]/(s["pair_tp"]+s["false_grouped_pairs"]))

    def test_pretest_freeze_matches_code(self):
        freeze=json.loads((HERE/"experiments/selection_freeze.json").read_text())
        for rel,digest in freeze["source_sha256"].items():
            self.assertEqual(hashlib.sha256((HERE/rel).read_bytes()).hexdigest(),digest)
        self.assertEqual(freeze["selected"],{"method":"exact","ranker":"progression"})


if __name__=="__main__":unittest.main()
