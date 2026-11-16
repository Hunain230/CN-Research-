import ast
import csv
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run_study import read,visible

class Phase22RobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=json.loads((HERE/"summary.json").read_text())
        cls.rows=read(HERE/"queue_audit.jsonl")
        with (HERE/"union_pair_increments.csv").open(newline="",encoding="utf-8") as stream:
            cls.increments=list(csv.DictReader(stream))
        cls.manifest=json.loads((HERE/"datasets/manifest.json").read_text())

    def test_phase21_verifier_is_frozen(self):
        previous=(HERE.parent/"PHASE21_CAUSAL_PROVENANCE/run_study.py").read_text()
        current=(HERE/"run_study.py").read_text()
        get=lambda s:next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=="decide")
        self.assertEqual(ast.dump(get(previous),include_attributes=False),
                         ast.dump(get(current),include_attributes=False))

    def test_new_cohort_coverage(self):
        self.assertEqual({k:len(v) for k,v in self.manifest["splits"].items()},
                         {"train":4,"development":10,"locked_test":20})
        development=self.manifest["splits"]["development"]
        self.assertEqual(set(x["failure_mode"] for x in development),
                         {"missing_delayed","duplicate_sources","incorrect_claims",
                          "single_compromise","shared_upstream"})
        self.assertEqual(set(x["graph_shape"] for x in development),
                         {"fork_merge","three_fragment","chain_cross"})
        self.assertEqual(sum(x["collision_pairs"] for x in development),60)

    def test_every_union_reconciles_to_final_pairs(self):
        for rule,partition in self.summary.items():
            for split,result in partition.items():
                rows=[x for x in self.increments if x["rule"]==rule and x["split"]==split]
                self.assertEqual(len(rows),result["accepted_unions"])
                self.assertEqual(sum(int(x["new_false_pairs"]) for x in rows),result["false_pairs"])
                self.assertEqual(sum(x["all_claims_physically_valid"]=="False" for x in rows),
                                 result["accepted_invalid_unions"])

    def test_frozen_verifier_fails_only_shared_upstream(self):
        rows=[x for x in self.rows if x["rule"]=="verified_edges" and x["split"]=="development"]
        self.assertEqual(sum(x["false_pairs"] for x in rows),300)
        self.assertEqual(sum(x["accepted_invalid_unions"] for x in rows),2)
        self.assertEqual({x["failure_mode"] for x in rows if x["false_pairs"]}, {"shared_upstream"})
        self.assertEqual(sum(x["corrupt_receipts"] for x in rows),6)

    def test_partial_evidence_is_not_safe(self):
        verified=self.summary["verified_edges"]["development"]
        partial=self.summary["partial_verified"]["development"]
        self.assertGreater(partial["recoverable"],verified["recoverable"])
        self.assertGreater(partial["false_pairs"],verified["false_pairs"])
        self.assertGreater(partial["accepted_invalid_unions"],verified["accepted_invalid_unions"])
        self.assertTrue(any(x["failure_mode"]=="single_compromise" and x["false_pairs"]>0
                            for x in self.rows if x["rule"]=="partial_verified" and x["split"]=="development"))

    def test_duplicate_observations_share_causal_root(self):
        for item in self.manifest["splits"]["development"]:
            if item["failure_mode"]!="duplicate_sources":continue
            q=item["queue_id"]
            claims=read(HERE/"datasets/development/causal_claims"/f"{q}.jsonl")
            counts=Counter(x["origin_event_id"] for x in claims)
            self.assertTrue(any(v>=2 for v in counts.values()))
            faults=read(HERE/"datasets/development/faults_private"/f"{q}.jsonl")
            self.assertEqual(sum(x["type"]=="duplicate_source_observation" for x in faults),1)

    def test_unavailable_receipts_are_excluded(self):
        for q in ("phase22a_development_q000","phase22a_development_q005"):
            _,_,receipts=visible("development",q)
            visible_ids={x["source_record_id"] for x in receipts}
            raw=read(HERE/"datasets/development/receiver_receipts"/f"{q}.jsonl")
            delayed={x["source_record_id"] for x in raw if x["receiver_available_minute"]>100}
            self.assertFalse(visible_ids&delayed)
            faults=read(HERE/"datasets/development/faults_private"/f"{q}.jsonl")
            self.assertTrue(any(x["type"]=="missing_receipt" for x in faults))
            self.assertTrue(any(x["type"]=="delayed_receipt" for x in faults))

    def test_both_locked_cohorts_sealed(self):
        freeze=json.loads((HERE/"freeze_manifest.json").read_text())
        self.assertFalse(freeze["phase19_locked_truth_read"])
        self.assertFalse(freeze["phase22_locked_truth_read"])
        self.assertFalse(freeze["phase22_locked_predictions_created"])
        self.assertFalse(any(x["split"]=="locked_test" for x in self.rows))
        self.assertEqual(hashlib.sha256((HERE/"datasets/manifest.json").read_bytes()).hexdigest(),
                         freeze["dataset_manifest_sha256"])
        for rule,digest in freeze["prediction_sha256"].items():
            self.assertEqual(hashlib.sha256((HERE/f"{rule}_predictions.jsonl").read_bytes()).hexdigest(),digest)

if __name__=="__main__":unittest.main()
