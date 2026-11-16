import unittest

from run_bridge_split import split_bridges
from evaluate_c_sensitivity import group_counts
from compare_c_status import recoverable


class GraphTests(unittest.TestCase):
    def test_weak_bridge_split_preserves_scope(self):
        keys = ["a", "b", "c", "d"]
        groups = [keys]
        edges = [1, 2, 1 * 4 + 2, 2 * 4 + 3]
        scores = [.9, .9, .9, .78]
        output, cuts = split_bridges(keys, groups, edges, scores)
        self.assertEqual(output, [["a", "b", "c"], ["d"]])
        self.assertEqual(cuts, 1)

    def test_nonbridge_weak_edge_retained(self):
        keys = ["a", "b", "c"]
        groups = [keys]
        edges = [1, 2, 1 * 3 + 2]
        output, cuts = split_bridges(keys, groups, edges, [.78, .9, .9])
        self.assertEqual(output, [keys])
        self.assertEqual(cuts, 0)

    def test_pair_and_recovery_counts(self):
        truth = {"a": "i", "b": "i", "c": "j"}
        self.assertEqual(group_counts([["a", "b"], ["c"]], truth), (1, 0, 0))
        self.assertEqual(group_counts([["a", "c"], ["b"]], truth), (0, 1, 1))
        self.assertEqual(recoverable([["a", "b"], ["c"]], list(truth), truth, {"i": 1}), {"i"})


if __name__ == "__main__":
    unittest.main()
