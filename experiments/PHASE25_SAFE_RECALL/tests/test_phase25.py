import csv
import hashlib
import importlib.util
import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from predict import reconstruct, rows, visible, visible_receipts  # noqa: E402


def table(name):
    with (HERE/name).open(newline="",encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class Phase25Tests(unittest.TestCase):
    def test_frozen_selection_and_disjoint_holdout(self):
        selection=json.loads((HERE/"selection_freeze.json").read_text())
        freeze=json.loads((HERE/"locked_prediction_freeze.json").read_text())
        self.assertFalse(selection["locked_cohort_existed_at_freeze"])
        self.assertEqual(selection["selected"],{"rule":"orthogonal_veto","ranker":"linear"})
        for name,expected in selection["hashes"].items():
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).hexdigest(),expected)
        self.assertEqual(freeze["prediction_sha256"],hashlib.sha256(
            (HERE/"locked_predictions.jsonl").read_bytes()).hexdigest())
        dev=json.loads((HERE/"datasets/manifest.json").read_text())
        locked=json.loads((HERE/"datasets/locked_manifest.json").read_text())
        self.assertEqual({k:len(v) for k,v in dev["queues"].items()},
                         {"train":12,"development":20})
        self.assertEqual(len(locked["queues"]["locked_test"]),30)
        self.assertTrue(set(locked["split_templates"]["locked_test"]).isdisjoint(
            dev["split_templates"]["train"]+dev["split_templates"]["development"]))

    def test_point_in_time_masks_contradictory_host(self):
        q="phase25h_locked_test_q009"
        aid=f"{q}_benign_041_a0"
        alert=next(x for x in visible("locked_test",q) if x["alert_id"]==aid)
        self.assertIsNone(alert["host"])
        ledger=rows(HERE/"datasets/locked_test/field_ledger"/f"{q}.jsonl")
        self.assertGreater(next(x["available_minute"] for x in ledger if x["artifact_id"]==aid
                                and x["field"]=="host"),100)
        receipts=visible_receipts("locked_test",q)
        self.assertTrue(all(x["receiver_available_minute"]<=100 for x in receipts))

    def test_phase24_q014_forensic_repair_is_not_selection_data(self):
        old=HERE.parent/"PHASE24_RECALL_FIRST/v4"
        spec=importlib.util.spec_from_file_location("phase24_predict_test",old/"predict.py")
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        q="phase24d_development_q014"
        alerts=module.visible("development",q)
        truth={x["alert_id"]:x["incident_id"] for x in module.rows(
            old/"datasets/development/ground_truth_private"/f"{q}.jsonl")}
        def false_pairs(groups):
            return sum(len(g)*(len(g)-1)//2-sum(v*(v-1)//2 for v in
                       Counter(truth[a] for a in g).values()) for g in groups)
        old_groups,_,_=reconstruct(alerts,"coherent_rare")
        guarded,_,_=reconstruct(alerts,"orthogonal_veto")
        self.assertEqual(false_pairs(old_groups),120)
        self.assertEqual(false_pairs(guarded),0)

    def test_fixed_groups_for_ranking_only(self):
        predictions=rows(HERE/"development_predictions.jsonl")
        by_queue=defaultdict(list)
        for x in predictions:
            if x["rule"]=="context":by_queue[x["queue_id"]].append(x)
        for versions in by_queue.values():
            partitions=[{frozenset(g) for g in x["groups_ranked"]} for x in versions]
            self.assertTrue(all(x==partitions[0] for x in partitions))

    def test_union_accounting_and_holdout_gate(self):
        for prefix in ("PHASE25_","locked_"):
            queue_file="PHASE25_QUEUE_METRICS.csv" if prefix=="PHASE25_" else "locked_queue_metrics.csv"
            union_file="PHASE25_UNION_PAIR_AUDIT.csv" if prefix=="PHASE25_" else "locked_union_pair_audit.csv"
            queues=table(queue_file);unions=table(union_file)
            by_key=defaultdict(list)
            for x in unions:by_key[x["queue_id"],x["rule"]].append(x)
            for x in queues:
                self.assertEqual(int(x["false_grouped_pairs"]),sum(
                    int(y["new_false_pairs"]) for y in by_key[x["queue_id"],x["rule"]]))
        locked=table("locked_queue_metrics.csv")
        baseline={x["queue_id"]:x for x in locked if x["rule"]=="context"}
        failures=[x for x in locked if x["rule"]=="orthogonal_veto" and
                  int(x["false_grouped_pairs"])>int(baseline[x["queue_id"]]["false_grouped_pairs"])]
        self.assertEqual([x["queue_id"] for x in failures],["phase25h_locked_test_q009"])
        self.assertEqual(failures[0]["false_grouped_pairs"],"1")


if __name__=="__main__":unittest.main()
