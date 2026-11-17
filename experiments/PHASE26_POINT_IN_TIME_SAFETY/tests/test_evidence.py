import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from evidence import FIELDS,build_snapshot  # noqa: E402


def fixture(arrival, value="host_a", correction=None, derived=False, event=10):
    aid="a1" if derived else "a0"
    header={"alert_id":aid,"source_id":"source_1","queue_id":"q","event_minute":event,
            "evidence_available_minute":10 if not derived else 101}
    expectations=[];atoms=[]
    for field in FIELDS:
        expectations.append({"artifact_id":aid,"field":field,"declared_minute":10,
                             "availability_claim":"pending","source_event_id":"source_1"})
        atoms.append({"artifact_id":aid,"field":field,"value":value if field=="host" else "v",
                      "original_source_observation_id":"source_1","source_event_id":"source_1",
                      "source_system":"endpoint","sensor_identity":"endpoint","evidence_type":field,
                      "event_timestamp":event,"receiver_arrival_timestamp":arrival,
                      "first_observable_timestamp":arrival,"last_update_timestamp":arrival,
                      "observation_kind":"derived" if derived else "original",
                      "parent_observation_ids":["a0"] if derived else [],"duplicated":derived,
                      "independence_verified":not derived,"contradictory_information":False,"version":0})
    if correction is not None:
        host=next(x for x in atoms if x["field"]=="host")
        atoms.append({**host,"value":correction,"receiver_arrival_timestamp":105,
                      "first_observable_timestamp":105,"last_update_timestamp":105,
                      "contradictory_information":True,"version":1})
    return [header],atoms,expectations


class TemporalEvidenceTests(unittest.TestCase):
    def test_before_exact_after_late_never(self):
        for arrival,expected in ((99,"SUPPORTED"),(100,"SUPPORTED"),(101,"NOT_YET_AVAILABLE"),
                                 (140,"NOT_YET_AVAILABLE"),(10**9,"NOT_YET_AVAILABLE")):
            headers,atoms,expectations=fixture(arrival)
            snap=build_snapshot(headers,atoms,expectations,100)
            self.assertEqual(snap.states[headers[0]["alert_id"],"host"],expected)
            self.assertEqual(snap.alerts[0]["host"],"host_a" if arrival<=100 else None)

    def test_out_of_event_order_uses_receiver_time(self):
        h1,a1,e1=fixture(100,event=5)
        h2,a2,e2=fixture(90,event=50)
        h2[0]["alert_id"]="b0"
        for x in a2:x["artifact_id"]="b0"
        for x in e2:x["artifact_id"]="b0"
        snap=build_snapshot(h1+h2,a1+a2,e1+e2,100)
        self.assertEqual(len(snap.alerts),2)
        self.assertEqual(snap.alerts[0]["event_minute"],5)

    def test_future_correction_cannot_change_prior_hash(self):
        h,a,e=fixture(90,correction="host_b")
        past=build_snapshot(h,a,e,100)
        mutated=[{**x,"value":"arbitrary_future_value"} if x["version"]==1 else x for x in a]
        self.assertEqual(past.sha256,build_snapshot(h,mutated,e,100).sha256)
        self.assertEqual(past.alerts[0]["host"],"host_a")
        future=build_snapshot(h,a,e,106)
        self.assertEqual(future.alerts[0]["host"],"host_b")
        self.assertEqual(future.states["a0","host"],"CONTRADICTED")

    def test_late_duplicate_and_late_contradiction(self):
        h,a,e=fixture(90)
        hd,ad,ed=fixture(101,value="host_b",derived=True)
        snap=build_snapshot(h+hd,a+ad,e+ed,100)
        self.assertEqual(len(snap.alerts),1)
        self.assertEqual(snap.alerts[0]["host"],"host_a")
        h2,a2,e2=fixture(101,value="contradictory_host")
        self.assertIsNone(build_snapshot(h2,a2,e2,100).alerts[0]["host"])

    def test_unknown_and_unavailable(self):
        h,a,e=fixture(101)
        for x in e:
            if x["field"]=="host":x["availability_claim"]="unavailable"
        self.assertEqual(build_snapshot(h,a,e,100).states["a0","host"],"UNAVAILABLE")
        e=[x for x in e if x["field"]!="host"]
        self.assertEqual(build_snapshot(h,a,e,100).states["a0","host"],"UNKNOWN")


if __name__=="__main__":unittest.main()
