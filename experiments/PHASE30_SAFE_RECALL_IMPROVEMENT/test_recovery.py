"""Focused negative and positive tests for direct-evidence union behavior."""
import unittest

from run_development import strict_union


def alert(aid, source, auth, flow, host="h", account="a", minute=10):
    return {"alert_id": aid, "source_id": source, "auth_session_ref": auth,
            "network_flow_ref": flow, "host": host, "account": account,
            "event_minute": minute}


class StrictUnionTests(unittest.TestCase):
    def test_direct_distinct_witnesses(self):
        groups = [["a1", "a2"], ["b1", "b2"]]
        lookup = {x["alert_id"]: x for x in [alert("a1", "s1", "auth", None),
            alert("a2", "s2", None, "flow"), alert("b1", "s3", "auth", None),
            alert("b2", "s4", None, "flow")]}
        merged, d = strict_union(groups, lookup)
        self.assertEqual(d["accepted_unions"], 1)
        self.assertEqual(len(merged), 1)

    def test_shared_reference_reuse_abstains(self):
        groups = [["a1", "a2"], ["b1", "b2"], ["c1"]]
        lookup = {x["alert_id"]: x for x in [alert("a1", "s1", "auth", None),
            alert("a2", "s2", None, "flow"), alert("b1", "s3", "auth", None),
            alert("b2", "s4", None, "flow"), alert("c1", "s5", "auth", None)]}
        merged, d = strict_union(groups, lookup)
        self.assertEqual(d["accepted_unions"], 0)
        self.assertEqual(len(merged), 3)

    def test_future_gap_abstains(self):
        groups = [["a1", "a2"], ["b1", "b2"]]
        lookup = {x["alert_id"]: x for x in [alert("a1", "s1", "auth", None),
            alert("a2", "s2", None, "flow"), alert("b1", "s3", "auth", None, minute=70),
            alert("b2", "s4", None, "flow", minute=70)]}
        merged, d = strict_union(groups, lookup)
        self.assertEqual(d["accepted_unions"], 0)
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
