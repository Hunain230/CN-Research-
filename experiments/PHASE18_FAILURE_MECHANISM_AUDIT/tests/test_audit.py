import csv
import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
P17=ROOT/"experiments/PHASE17_INDEPENDENT_PROVENANCE"


def rows(name):
    with (HERE/name).open(newline="",encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class MechanismAuditTests(unittest.TestCase):
    def test_frozen_sources_unchanged(self):
        summary=json.loads((HERE/"PHASE18_AUDIT_SUMMARY.json").read_text())
        for rel,digest in summary["input_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest)

    def test_baseline_zero_is_structural_across_splits(self):
        incident=rows("PHASE18_BASELINE_INCIDENT_AUDIT.csv")
        self.assertEqual(Counter(x["split"] for x in incident),{"train":300,"development":300,"locked_test":600})
        self.assertTrue(all(x["recoverable"]=="0" and x["has_80pct_complete_group"]=="0"
                            and x["raw_all_fields_complete"]=="0" for x in incident))
        self.assertLess(max(float(x["largest_overlap_fraction"]) for x in incident),.8)

    def test_merge_pair_reconciliation(self):
        merges=rows("PHASE18_ACCEPTED_MERGE_PAIR_INCREMENTS.csv")
        self.assertEqual(len(merges),953)
        self.assertEqual(sum(int(x["new_false_pairs"]) for x in merges),986)
        self.assertEqual(sum(int(x["new_true_pairs"]) for x in merges),82646)
        self.assertEqual(sum(int(x["was_false_merge"]) for x in merges),12)
        baseline=json.loads((P17/"experiments/evaluations/development_baseline.json").read_text())["summary"]
        candidate=json.loads((P17/"experiments/evaluations/development_t0p8_progression.json").read_text())["summary"]
        self.assertEqual(candidate["false_grouped_pairs"]-baseline["false_grouped_pairs"],986)

    def test_field_provenance_and_availability_population(self):
        fields=rows("PHASE18_FIELD_AVAILABILITY.csv")
        self.assertEqual(len(fields),60*10)
        self.assertTrue(all(int(x["visible_nonnull"])<=int(x["raw_nonnull"]) for x in fields))
        queue=rows("PHASE18_QUEUE_DISTRIBUTION.csv")
        self.assertEqual(len(queue),60)
        self.assertTrue(all(int(x["actions_with_2plus_sensors"])>0 for x in queue))

    def test_locked_test_baseline_only(self):
        freeze=json.loads((P17/"experiments/selection_freeze.json").read_text())
        self.assertEqual(freeze["selected"],{"method":"calibrated_2","ranker":"progression"})
        files=list((P17/"experiments/evaluations").glob("locked_test_*.json"))
        self.assertEqual([x.name for x in files],["locked_test_baseline.json"])
        self.assertEqual(len(rows("PHASE18_FALSE_PAIR_QUEUE_RECONCILIATION.csv")),15)


if __name__=="__main__":unittest.main()
