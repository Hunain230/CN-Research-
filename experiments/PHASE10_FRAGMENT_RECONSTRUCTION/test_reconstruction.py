"""Synthetic-only unit and integration checks. No GUIDE labels are imported."""
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("phase10_reconstruct", HERE / "reconstruct.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CFG = json.loads((HERE / "PHASE10_EXPERIMENT_CONFIG.json").read_text())


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.keys = ["a", "b", "c", "d", "e"]
        self.groups = [["a", "b"], ["c", "d"], ["e"]]
        self.docs = {a: {"entities": {("DeviceId", "one" if a != "e" else "other")},
                         "fields": {"Category": {"cat" if a != "e" else "other"},
                                    "MitreTechniques": {"t" if a != "e" else "other"}},
                         "stamp": 100} for a in self.keys}

    def test_fragments_preserve_scope(self):
        membership, summaries = module.fragments(self.keys, self.groups, self.docs)
        self.assertEqual(membership.tolist(), [0, 0, 1, 1, 2])
        self.assertEqual([s["size"] for s in summaries], [2, 2, 1])
        with self.assertRaises(ValueError):
            module.fragments(self.keys, [["a", "b"], ["b", "c"], ["d", "e"]], self.docs)

    def test_boundary_and_score(self):
        import numpy as np
        summaries, boundaries = module.boundaries(self.keys, self.groups, self.docs,
            np.asarray([2, 3, 7, 8]), np.asarray([.8, .7, .8, .6]), 20)
        row = boundaries[(0, 1)]
        self.assertEqual(row["edges"], 4)
        self.assertEqual(row["coverage_left"], 1)
        self.assertGreater(module.score_boundary(row, CFG["scoring"]), .68)
        self.assertEqual(summaries[0]["size"], 2)

    def test_merge_and_verification(self):
        import numpy as np
        summaries, boundaries = module.boundaries(self.keys, self.groups, self.docs,
            np.asarray([2, 3, 7, 8]), np.asarray([.8, .7, .8, .6]), 20)
        groups, decisions = module.reconstruct(self.keys, self.groups, summaries, boundaries, CFG["policies"]["E2"], CFG)
        self.assertEqual(groups, [["a", "b", "c", "d"], ["e"]])
        self.assertEqual(sum(d["decision"] == "accepted" for d in decisions), 1)
        bad = dict(boundaries[(0, 1)], gap_hours=100)
        self.assertEqual(module.verify_boundary(bad, CFG["verification"]), "verification_temporal_uncertainty")

    def test_integration_cap_and_rejection(self):
        import numpy as np
        summaries, boundaries = module.boundaries(self.keys, self.groups, self.docs,
            np.asarray([2, 3, 7, 8]), np.asarray([.8, .7, .8, .6]), 20)
        config = dict(CFG, cap=3)
        groups, decisions = module.reconstruct(self.keys, self.groups, summaries, boundaries, CFG["policies"]["E3"], config)
        self.assertEqual(groups, self.groups)
        self.assertEqual(decisions[0]["reason"], "component_cap")
        self.assertEqual(sum(map(len, groups)), len(self.keys))


if __name__ == "__main__":
    unittest.main()
