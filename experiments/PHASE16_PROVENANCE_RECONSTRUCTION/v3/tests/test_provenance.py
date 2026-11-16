import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from predict import ALLOWED,PRIVATE,correlate,lines,visible


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((HERE/"datasets/manifest.json").read_text())

    def test_split_and_schema(self):
        templates=[set(x) for x in self.manifest["split_templates"].values()]
        self.assertFalse(templates[0]&templates[1] or templates[0]&templates[2] or templates[1]&templates[2])
        for split,queues in self.manifest["queues"].items():
            q=queues[0]["queue_id"]
            a=lines(HERE/"datasets"/split/"generated_alerts"/f"{q}.jsonl")
            self.assertTrue(all(set(x)<=ALLOWED and not set(x)&PRIVATE for x in a))
            self.assertTrue(all(x["queue_id"]==q for x in a))
        self.assertNotIn("ground_truth_private",(HERE/"predict.py").read_text())

    def test_availability(self):
        q=self.manifest["queues"]["locked_test"][0]["queue_id"]
        all_alerts=lines(HERE/"datasets/locked_test/generated_alerts"/f"{q}.jsonl")
        seen=visible(HERE/"datasets","locked_test",q,100)
        self.assertLess(len(seen),len(all_alerts))
        self.assertTrue(all(x["evidence_available_minute"]<=100 for x in seen))

    def test_two_independent_witnesses_and_duplicate_suppression(self):
        a=[]
        for i,(tree,auth,flow) in enumerate((("p1","auth",None),("p1",None,"flow"),
                                              ("p2","auth",None),("p2",None,"flow"))):
            a.append({"alert_id":f"a{i}","source_id":f"s{i}","event_minute":i,
                      "host":"h","account":"u","process_tree_ref":tree,
                      "auth_session_ref":auth,"network_flow_ref":flow})
        groups,_,_,_=correlate(a,"lineage_two_v",100)
        self.assertEqual(len(groups),1)
        b=[dict(x) for x in a]
        b[3]["network_flow_ref"]=None
        groups,_,_,_=correlate(b,"lineage_two_v",100)
        self.assertEqual(len(groups),2)
        c=[dict(x) for x in a]
        c[3]["source_id"]="s2"  # duplicate source cannot create a fourth witness
        groups,_,_,_=correlate(c,"lineage_two_v",100)
        self.assertEqual(len(groups),2)  # duplicate source does not provide a fourth witness

    def test_context_veto_and_cap(self):
        a=[]
        for i,(tree,auth,host,account) in enumerate((("p1","x","h1","u1"),("p1",None,"h1","u1"),
                                                      ("p2","x","h2","u2"),("p2",None,"h2","u2"))):
            a.append({"alert_id":f"a{i}","source_id":f"s{i}","event_minute":i,
                      "host":host,"account":account,"process_tree_ref":tree,
                      "auth_session_ref":auth,"network_flow_ref":None})
        groups,_,decisions,_=correlate(a,"lineage_one_context_v",100)
        self.assertEqual(len(groups),2)
        self.assertGreater(decisions.get("context_abstain",0),0)
        b=[dict(x,host="h1",account="u1") for x in a]
        groups,_,_,_=correlate(b,"lineage_one_context_v",2)
        self.assertTrue(all(len(g)<=2 for g in groups))

    def test_freeze_and_metrics(self):
        freeze=json.loads((HERE/"experiments/selection_freeze.json").read_text())
        for path,digest in freeze["sha256"].items():
            self.assertEqual(hashlib.sha256((HERE.parents[2]/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(freeze["selected_method"],"lineage_one_context_v")
        result=json.loads((HERE/"experiments/locked_test_result.json").read_text())
        s=result["selected"];b=result["baseline"]
        self.assertEqual((s["queues"],s["expert_top20"],s["recoverable"],s["recall20_count"]),(24,480,361,306))
        self.assertGreaterEqual(s["grouped_pair_precision"],.9)
        self.assertLessEqual(s["false_grouped_pairs"],b["false_grouped_pairs"])
        self.assertLessEqual(s["mixed_predicted_groups"],b["mixed_predicted_groups"])


if __name__=="__main__":unittest.main()
