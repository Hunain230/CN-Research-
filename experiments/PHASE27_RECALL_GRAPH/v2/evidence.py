"""Trusted point-in-time access layer. Inference receives only a Snapshot."""
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

FIELDS=("host","account","indicator","process_tree_ref","auth_session_ref",
        "network_flow_ref","event_type","severity","asset_criticality")
STATES={"SUPPORTED","CONTRADICTED","NOT_YET_AVAILABLE","UNAVAILABLE","UNKNOWN","UNVERIFIED"}


@dataclass(frozen=True)
class Snapshot:
    alerts: list
    states: dict
    cutoff: int
    sha256: str


def read(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def build_snapshot(headers,atoms,expectations,cutoff):
    """Select the latest receiver-visible version; future values never escape."""
    by_atom=defaultdict(list)
    by_expectation={(x["artifact_id"],x["field"]):x for x in expectations}
    if len(by_expectation)!=len(expectations):raise ValueError("duplicate expectation")
    for atom in atoms:
        if atom["field"] not in FIELDS:raise ValueError("unapproved field")
        by_atom[atom["artifact_id"],atom["field"]].append(atom)
    alerts=[];states={}
    for header in headers:
        if set(header)!={"alert_id","source_id","queue_id","event_minute","evidence_available_minute"}:
            raise ValueError("unapproved alert header")
        if header["evidence_available_minute"]>cutoff:continue
        item=dict(header)
        for field in FIELDS:
            key=(header["alert_id"],field)
            expectation=by_expectation.get(key)
            versions=by_atom.get(key,[])
            visible=[a for a in versions if a["receiver_arrival_timestamp"]<=cutoff and
                     a["first_observable_timestamp"]<=cutoff]
            if visible:
                latest=max(visible,key=lambda x:(x["receiver_arrival_timestamp"],x["version"]))
                if latest["source_event_id"]!=header["source_id"]:
                    raise ValueError("source lineage mismatch")
                value=latest["value"]
                if value is None:state="UNAVAILABLE"
                elif latest["contradictory_information"]:state="CONTRADICTED"
                elif not latest["independence_verified"]:state="UNVERIFIED"
                else:state="SUPPORTED"
                item[field]=value
            elif expectation and expectation["declared_minute"]<=cutoff:
                state="UNAVAILABLE" if expectation["availability_claim"]=="unavailable" else "NOT_YET_AVAILABLE"
                item[field]=None
            else:
                state="UNKNOWN";item[field]=None
            states[key]=state
        alerts.append(item)
    alerts.sort(key=lambda x:x["alert_id"])
    payload={"cutoff":cutoff,"alerts":alerts,
             "states":[[aid,field,state] for (aid,field),state in sorted(states.items())]}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return Snapshot(alerts,states,cutoff,digest)


def snapshot(folder,queue,cutoff=100):
    folder=Path(folder)
    return build_snapshot(
        read(folder/"alert_headers"/f"{queue}.jsonl"),
        read(folder/"evidence_atoms"/f"{queue}.jsonl"),
        read(folder/"evidence_expectations"/f"{queue}.jsonl"),cutoff)
