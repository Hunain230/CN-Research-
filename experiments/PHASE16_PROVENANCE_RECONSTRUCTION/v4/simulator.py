"""Generate non-executing, independently labelled source-lineage telemetry."""
import hashlib
import json
import random
from pathlib import Path

HERE=Path(__file__).resolve().parent
FAMILIES=["initial_access","credential_compromise","suspicious_authentication",
          "lateral_movement","privilege_escalation","persistence","command_control",
          "data_staging","exfiltration","multi_stage_chain"]
BENIGN=["normal_authentication","routine_administration","scheduled_task","software_update",
        "network_connection","service_activity","file_access","process_creation","legitimate_privilege_use"]
EVENTS=["auth","process","network","file","service","privilege"]


def tok(*parts):return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()[:16]
def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")


def generate():
    config=json.loads((HERE/"configs/study.json").read_text())
    data=HERE/"datasets"
    if data.exists():raise FileExistsError("Sealed dataset exists")
    manifest={"schema":config["schema"],"split_templates":{},"queues":{}}
    for split,variants in (("train",(0,1,2,3)),("development",(4,)),("locked_test",(5,))):
        rng=random.Random(config["seeds"][split])
        templates=[f"{f}:v{v}" for f in FAMILIES for v in variants]
        manifest["split_templates"][split]=templates
        manifest["queues"][split]=[]
        for qi in range(config["queues"][split]):
            queue=f"phase16v4_{split}_q{qi:03d}"
            alerts=[];source=[];ledger=[];truth=[];priority=[];degradation=[]
            for ii in range(config["incidents_per_queue"]):
                family,variant=templates[(ii+qi*3)%len(templates)].split(":")
                incident=f"{queue}_incident_{ii:03d}"
                scenario=f"{queue}_scenario_{ii:03d}"
                host=f"host_{rng.randrange(10)}"
                account=f"acct_{rng.randrange(14)}"
                service=f"service_{rng.randrange(8)}"
                criticality=rng.randrange(1,5);impact=rng.randrange(1,5);urgency=rng.randrange(1,5)
                score=4*impact+3*criticality+2*urgency+rng.randrange(1,5)
                priority.append({"incident_id":incident,"scenario_id":scenario,"template_id":f"{family}:{variant}",
                                 "family":family,"impact":impact,"urgency":urgency,
                                 "criticality":criticality,"priority_score":score})
                count=rng.randrange(9,13)
                start=rng.randrange(5,58)
                # Partial lineage references span adjacent three-event fragments.
                # Some unrelated incidents deliberately reuse a pool token.
                shared_auth=tok(queue,"shared-auth",rng.randrange(5)) if rng.random()<.12 else None
                shared_flow=tok(queue,"shared-flow",rng.randrange(5)) if rng.random()<.12 else None
                for j in range(count):
                    obs=f"{queue}_src_{ii:03d}_{j:02d}"
                    if j>0 and rng.random()<.08:
                        degradation.append({"source_id":obs,"reason":"missing_observation"});continue
                    segment=j//3
                    boundary=(j-2)//3 if j%3==2 else (j-3)//3 if j%3==0 and j else None
                    # Two independent boundary witnesses use distinct source events:
                    # auth 2/3 and flow 0/4 for boundary 0; auth 5/6 and
                    # flow 3/7 for boundary 1; auth 8/9 and flow 6/10 for 2.
                    flow_boundary={0:0,4:0,3:1,7:1,6:2,10:2}.get(j)
                    if j in (2,3,5,6,8,9,11):
                        auth_boundary=(j-2)//3 if j%3==2 else (j-3)//3
                    else:auth_boundary=None
                    # A small fraction of references are unavailable/noisy.
                    auth=(shared_auth or tok(scenario,"auth",auth_boundary)) if auth_boundary is not None and rng.random()>.10 else None
                    flow=(shared_flow or tok(scenario,"flow",flow_boundary)) if flow_boundary is not None and rng.random()>.10 else None
                    tree=tok(scenario,"tree",segment) if rng.random()>.06 else None
                    event=min(95,start+2*j+rng.randrange(0,3))
                    collection=event+rng.randrange(0,3)
                    detector=collection+rng.randrange(0,3)
                    available=detector+(rng.randrange(20,42) if j and rng.random()<.13 else rng.randrange(0,4))
                    processing=available+rng.randrange(0,3)
                    record={"source_id":obs,"event_minute":event,"collection_minute":collection,
                            "detector_minute":detector,"evidence_available_minute":available,
                            "processing_minute":processing,"host":host if rng.random()>.07 else None,
                            "account":account if rng.random()>.07 else None,"indicator":service,
                            "process_tree_ref":tree,"auth_session_ref":auth,"network_flow_ref":flow,
                            "event_type":EVENTS[(j+ii)%len(EVENTS)],"severity":max(1,min(5,impact+rng.choice((-1,0,0,1)))),
                            "asset_criticality":criticality}
                    source.append(record)
                    copies=2 if rng.random()<.08 else 1
                    for copy in range(copies):
                        alert_id=f"{obs}_a{copy}"
                        alert={k:record[k] for k in ("source_id","event_minute","host","account","indicator",
                          "process_tree_ref","auth_session_ref","network_flow_ref","event_type","severity","asset_criticality")}
                        alert.update({"alert_id":alert_id,"queue_id":queue,"evidence_available_minute":available+copy})
                        alerts.append(alert)
                        ledger.append({"sequence":len(ledger)+1,"artifact_id":alert_id,"source_id":obs,
                            "event_minute":event,"collection_minute":collection,"detector_minute":detector,
                            "evidence_available_minute":available+copy,"processing_minute":processing+copy,
                            "analyst_decision_minute":config["decision_minute"]})
                        truth.append({"alert_id":alert_id,"source_id":obs,"incident_id":incident,
                            "scenario_id":scenario,"attack_stage":family,"malicious":True})
                    if available>config["decision_minute"]:degradation.append({"source_id":obs,"reason":"late_evidence"})
            for j in range(config["benign_observations_per_queue"]):
                obs=f"{queue}_benign_{j:03d}";event=rng.randrange(0,95)
                collection=event+rng.randrange(0,3);detector=collection+rng.randrange(0,3);available=detector+rng.randrange(0,5)
                record={"source_id":obs,"event_minute":event,"collection_minute":collection,
                    "detector_minute":detector,"evidence_available_minute":available,"processing_minute":available+1,
                    "host":f"host_{rng.randrange(10)}","account":f"acct_{rng.randrange(14)}",
                    "indicator":f"service_{rng.randrange(8)}","process_tree_ref":tok(queue,"benign-tree",j//3) if rng.random()>.1 else None,
                    "auth_session_ref":tok(queue,"shared-auth",rng.randrange(5)) if rng.random()<.08 else None,
                    "network_flow_ref":tok(queue,"shared-flow",rng.randrange(5)) if rng.random()<.08 else None,
                    "event_type":EVENTS[j%len(EVENTS)],"severity":rng.randrange(1,5),"asset_criticality":rng.randrange(1,5)}
                source.append(record);alert_id=obs+"_a0"
                alerts.append({**{k:record[k] for k in ("source_id","event_minute","host","account","indicator",
                    "process_tree_ref","auth_session_ref","network_flow_ref","event_type","severity","asset_criticality")},
                    "alert_id":alert_id,"queue_id":queue,"evidence_available_minute":available})
                ledger.append({"sequence":len(ledger)+1,"artifact_id":alert_id,"source_id":obs,
                    "event_minute":event,"collection_minute":collection,"detector_minute":detector,
                    "evidence_available_minute":available,"processing_minute":available+1,
                    "analyst_decision_minute":config["decision_minute"],"reason":BENIGN[j%len(BENIGN)]})
                truth.append({"alert_id":alert_id,"source_id":obs,"incident_id":f"{queue}_benign_{j:03d}",
                    "scenario_id":None,"attack_stage":None,"malicious":False})
            priority.sort(key=lambda x:(-x["priority_score"],x["incident_id"]))
            for rank,row in enumerate(priority,1):row["priority_rank"]=rank
            rng.shuffle(alerts);rng.shuffle(source)
            for name,rows in (("generated_alerts",alerts),("source_observations",source),("evidence_ledger",ledger),
                              ("ground_truth_private",truth),("degradation",degradation)):
                write(data/split/name/f"{queue}.jsonl",rows)
            write(data/split/"ground_truth_private"/f"{queue}_priority.jsonl",priority)
            manifest["queues"][split].append({"queue_id":queue,"alerts":len(alerts),"incidents":len(priority)})
    (data/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:len(v) for k,v in manifest["queues"].items()}))


if __name__=="__main__":generate()
