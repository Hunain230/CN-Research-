import csv
import hashlib
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "v3"
sys.path.insert(0, str(V))
from evidence import build_snapshot, read  # noqa: E402
from graph import build_edges, components, disjoint_root_witness_count, hypotheses, load  # noqa: E402


def table(name):
    with (V / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def records(name):
    with (V / name).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


class Phase27Tests(unittest.TestCase):
    def test_disjoint_cohorts(self):
        manifest = json.loads((V / "datasets/manifest.json").read_text())
        holdout = json.loads((V / "datasets/locked_test/manifest.json").read_text())
        self.assertEqual((len(manifest["queues"]["train"]),
                          len(manifest["queues"]["development"]),
                          len(holdout["queues"])), (12, 20, 30))
        self.assertEqual(holdout["namespace"], "phase27k")
        self.assertTrue(all(x["queue_id"].startswith("phase27c_") for split in manifest["queues"]
                            for x in manifest["queues"][split]))
        self.assertTrue({x["variant"] for x in manifest["queues"]["train"]}.isdisjoint(
                        {x["variant"] for x in manifest["queues"]["development"]}))

    def test_frozen_artifacts_and_prediction_cutoff(self):
        for name in ("freeze_manifest.json", "pre_evaluation_protocol.json"):
            manifest = json.loads((V / name).read_text())
            for filename, digest in manifest["hashes"].items():
                self.assertEqual(hashlib.sha256((V / filename).read_bytes()).hexdigest(), digest)
        manifest = json.loads((V / "locked_prediction_freeze.json").read_text())
        for mapping in (manifest["prediction_hashes"], manifest["public_input_hashes"]):
            for filename, digest in mapping.items():
                self.assertEqual(hashlib.sha256((V / filename).read_bytes()).hexdigest(), digest)
        for name in ("development_predictions.jsonl", "locked_predictions.jsonl"):
            for prediction in records(name):
                self.assertEqual(prediction["decision_minute"], 100)
                self.assertEqual(len(prediction["snapshot_sha256"]), 64)

    def test_future_correction_and_late_evidence_do_not_change_past_snapshot(self):
        q = "phase27c_development_q000"
        folder = V / "datasets/development"
        headers = read(folder / "alert_headers" / f"{q}.jsonl")
        atoms = read(folder / "evidence_atoms" / f"{q}.jsonl")
        expectations = read(folder / "evidence_expectations" / f"{q}.jsonl")
        past = build_snapshot(headers, atoms, expectations, 100)
        future = [x for x in atoms if x["receiver_arrival_timestamp"] > 100]
        self.assertTrue(future)
        changed = [{**x, "value": "mutated_future"} if x["receiver_arrival_timestamp"] > 100 else x
                   for x in atoms]
        self.assertEqual(past.sha256, build_snapshot(headers, changed, expectations, 100).sha256)
        self.assertTrue(all(x["receiver_arrival_timestamp"] > 100 for x in future))

    def test_candidate_edges_never_implicitly_commit(self):
        q = "phase27c_development_q000"
        snap, source = load("development", q)
        edges = build_edges(snap, source)
        self.assertTrue(any(x["outcome"] == "CANDIDATE" for x in edges))
        self.assertTrue(all(x["receiver_visible_minute"] <= 100 for x in edges))
        groups, decisions = components(snap.alerts, edges, "graph_no_uncertain", snap)
        self.assertTrue(all(d["edge"]["outcome"] == "VERIFIED" for d in decisions
                            if d["decision"] == "ACCEPT"))
        original = [tuple(x) for x in groups]
        candidates = hypotheses(groups, edges)
        self.assertTrue(candidates)
        self.assertEqual(original, [tuple(x) for x in groups])
        self.assertTrue(all(not x["committed"] for x in candidates))

    def test_hypothesis_discovery_is_distinct_from_official_recovery(self):
        summary = json.loads((ROOT / "analysis_summary.json").read_text())
        self.assertEqual(summary["development"]["hypotheses"]["top20_incidents_new_beyond_groups"], 179)
        self.assertEqual(summary["locked_test"]["hypotheses"]["top20_incidents_new_beyond_groups"], 231)
        self.assertEqual(summary["locked_result"]["selected"]["recoverable"], 171)
        self.assertLess(summary["locked_test"]["hypotheses"]["hypothesis_precision"], 1)

    def test_duplicate_and_shared_root_are_not_independent_witnesses(self):
        edge = {"source_provenance": ["a", "b"], "controller_roots": ["r1", "r2"]}
        copied = {"source_provenance": ["a", "b"], "controller_roots": ["r1", "r2"]}
        common = {"source_provenance": ["c", "d"], "controller_roots": ["r1", "r3"]}
        independent = {"source_provenance": ["e", "f"], "controller_roots": ["r4", "r5"]}
        self.assertEqual(disjoint_root_witness_count([edge, copied, common]), 1)
        self.assertEqual(disjoint_root_witness_count([edge, copied, common, independent]), 2)

    def test_group_and_union_reconciliation(self):
        union = defaultdict(int)
        for row in table("PHASE27_UNION_PAIR_AUDIT.csv"):
            union[row["queue_id"], row["mode"]] += int(row["new_false_pairs"])
        for row in table("PHASE27_FAILURE_CASCADE.csv"):
            self.assertEqual(union[row["queue_id"], row["mode"]], int(row["false_pairs"]))
        for row in table("PHASE27_LOCKED_QUEUE_METRICS.csv"):
            self.assertEqual(int(row["false_grouped_pairs"]), 0)
            self.assertEqual(int(row["mixed_groups"]), 0)


if __name__ == "__main__":
    unittest.main()
