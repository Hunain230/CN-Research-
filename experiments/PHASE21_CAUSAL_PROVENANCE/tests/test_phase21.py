import csv
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run_study import decide,read,visible

class CausalProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary=json.loads((HERE/"summary.json").read_text())
        cls.queues=read(HERE/"queue_audit.jsonl")
        with (HERE/"union_pair_increments.csv").open(newline="",encoding="utf-8") as stream:
            cls.increments=list(csv.DictReader(stream))

    def test_source_root_dedup_over_sensor_labels(self):
        alerts=[{"alert_id":"a","fragment_ref":"left","severity":1,"asset_criticality":1},
                {"alert_id":"b","fragment_ref":"right","severity":1,"asset_criticality":1}]
        claims=[{"claim_id":"c1","left_fragment_ref":"left","right_fragment_ref":"right",
                 "origin_event_id":"same_event","sensor":"auth"},
                {"claim_id":"c2","left_fragment_ref":"left","right_fragment_ref":"right",
                 "origin_event_id":"same_event","sensor":"network"}]
        _,causal,_=decide(alerts,claims,"causal_roots")
        _,labels,_=decide(alerts,claims,"sensor_labels_only")
        self.assertEqual(causal[0]["decision"],"abstain")
        self.assertEqual(labels[0]["decision"],"accept")
        claims[1]["origin_event_id"]="independent_event"
        _,causal,_=decide(alerts,claims,"causal_roots")
        self.assertEqual(causal[0]["decision"],"accept")

    def test_claim_requires_matching_receiver_receipt(self):
        alerts=[{"alert_id":"a","fragment_ref":"left","severity":1,"asset_criticality":1},
                {"alert_id":"b","fragment_ref":"right","severity":1,"asset_criticality":1}]
        claims=[{"claim_id":"c1","left_fragment_ref":"left","right_fragment_ref":"right",
                 "origin_event_id":"child1","parent_event_id":"parent1","sensor":"auth","source_record_id":"s1"},
                {"claim_id":"c2","left_fragment_ref":"left","right_fragment_ref":"right",
                 "origin_event_id":"child2","parent_event_id":"parent2","sensor":"endpoint","source_record_id":"s2"}]
        receipts=[{"source_record_id":"p1","sensor":"auth","origin_event_id":"parent1",
                   "observed_fragment_ref":"left","observed_parent_event_ids":[]},
                  {"source_record_id":"p2","sensor":"endpoint","origin_event_id":"parent2",
                   "observed_fragment_ref":"left","observed_parent_event_ids":[]},
                  {"source_record_id":"s1","sensor":"auth","origin_event_id":"child1",
                   "observed_fragment_ref":"right","observed_parent_event_ids":["parent1"]},
                  {"source_record_id":"s2","sensor":"endpoint","origin_event_id":"child2",
                   "observed_fragment_ref":"right","observed_parent_event_ids":[]}]
        _,decisions,_=decide(alerts,claims,"verified_edges",receipts)
        self.assertEqual(sum(d["decision"]=="accept" for d in decisions),0)
        self.assertEqual(sum(d["decision"]=="reject" for d in decisions),1)
        receipts[-1]["observed_parent_event_ids"]=["parent2"]
        _,decisions,_=decide(alerts,claims,"verified_edges",receipts)
        self.assertEqual(sum(d["decision"]=="accept" for d in decisions),1)

    def test_private_lineage_and_pair_replay(self):
        for rule in ("causal_roots","sensor_labels_only","verified_edges"):
            for split in ("train","development"):
                rows=[r for r in self.queues if r["rule"]==rule and r["split"]==split]
                inc=[r for r in self.increments if r["rule"]==rule and r["split"]==split]
                self.assertEqual(sum(r["false_pairs"] for r in rows),sum(int(r["new_false_pairs"]) for r in inc))
                self.assertEqual(sum(r["accepted_unions"] for r in rows),len(inc))
                self.assertEqual(len(rows),self.summary[rule][split]["queues"])

    def test_common_mode_challenge_is_real(self):
        dev=self.summary["causal_roots"]["development"]
        naive=self.summary["sensor_labels_only"]["development"]
        self.assertEqual(dev["common_mode_claims"],104)
        self.assertEqual(dev["accepted_invalid_unions"],8)
        self.assertGreater(dev["false_pairs"],0)
        self.assertGreater(naive["false_pairs"],dev["false_pairs"])
        self.assertTrue(all(r["false_pairs"]>0 for r in self.queues
                            if r["rule"]=="causal_roots" and r["split"]=="development"))

    def test_invalid_union_contaminates_later_valid_union(self):
        dev=[r for r in self.increments if r["rule"]=="causal_roots" and r["split"]=="development"]
        invalid=sum(r["all_claims_physically_valid"]=="False" for r in dev)
        bad=sum(int(r["new_false_pairs"])>0 for r in dev)
        self.assertEqual(invalid,8)
        self.assertGreater(bad,invalid)

    def test_verified_receipts_reject_independent_false_claims(self):
        dev=self.summary["verified_edges"]["development"]
        self.assertEqual(dev["accepted_invalid_unions"],0)
        self.assertEqual(dev["false_pairs"],0)
        self.assertEqual(dev["recoverable"],46)
        self.assertTrue(all(r["false_pairs"]==0 and r["recoverable"]>0 for r in self.queues
                            if r["rule"]=="verified_edges" and r["split"]=="development"))

    def test_receiver_field_availability(self):
        q="phase21a_development_q000"
        alerts,claims,receipts=visible("development",q)
        root=HERE/"datasets_v3/development"
        ledger={(r["artifact_id"],r["field"]):r for r in read(root/"field_ledger"/f"{q}.jsonl")}
        raw={r["alert_id"]:r for r in read(root/"generated_alerts"/f"{q}.jsonl")}
        for alert in alerts:
            for field in ("fragment_ref","host","account","auth_ref","flow_ref"):
                if ledger[(alert["alert_id"],field)]["available_minute"]>100:
                    self.assertIsNone(alert[field])
                else:self.assertEqual(alert[field],raw[alert["alert_id"]][field])
        claim_ledger={(r["artifact_id"],r["field"]):r for r in read(root/"claim_field_ledger"/f"{q}.jsonl")}
        self.assertTrue(all(claim_ledger[(c["claim_id"],"origin_event_id")]["available_minute"]<=100 for c in claims))
        receipt_ledger={(r["artifact_id"],r["field"]):r for r in read(root/"receipt_field_ledger"/f"{q}.jsonl")}
        self.assertTrue(all(receipt_ledger[(r["source_record_id"],"origin_event_id")]["available_minute"]<=100 for r in receipts))

    def test_phase19_locked_cohort_unopened(self):
        p19=HERE.parent/"PHASE19_DEV_RECONSTRUCTION"
        freeze=json.loads((p19/"experiments/development_freeze.json").read_text())
        self.assertFalse(freeze["locked_truth_read"])
        self.assertFalse(freeze["locked_predictions_created"])
        self.assertFalse(list(HERE.rglob("locked_test_*")))

    def test_prediction_freeze_hashes(self):
        freeze=json.loads((HERE/"freeze_manifest.json").read_text())
        self.assertEqual(freeze["status"],"development_only_predictions_frozen_before_private_audit")
        self.assertFalse(freeze["phase19_locked_truth_read"])
        for rule,digest in freeze["prediction_sha256"].items():
            self.assertEqual(hashlib.sha256((HERE/f"{rule}_predictions.jsonl").read_bytes()).hexdigest(),digest)

if __name__=="__main__":unittest.main()
