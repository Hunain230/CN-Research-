"""Fresh Phase 26 point-in-time synthetic SOC fixture."""
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
    config=json.loads((HERE/"config.json").read_text())
    data=HERE/"datasets"
    if data.exists():raise FileExistsError("Sealed dataset exists")
    manifest={"schema":config["schema"],"split_templates":{},"queues":{}}
    for split,variants in (("train",(60,61,62,63)),("development",(70,71))):
        rng=random.Random(config["seeds"][split])
        templates=[f"{f}:v{v}" for f in FAMILIES for v in variants]
        manifest["split_templates"][split]=templates
        manifest["queues"][split]=[]
        for qi in range(config["queues"][split]):
            queue=f"{config['namespace']}_{split}_q{qi:03d}"
            alerts=[];source=[];ledger=[];field_ledger=[];truth=[];priority=[];degradation=[];faults=[]
            for ii in range(config["incidents_per_queue"]):
                family,variant=templates[(ii+qi*3)%len(templates)].split(":")
                incident=f"{queue}_incident_{ii:03d}"
                scenario=f"{queue}_scenario_{ii:03d}"
                host=f"host_{ii//2}" if ii < 12 else f"host_{rng.randrange(12)}"
                account=f"acct_{ii//2}" if ii < 12 else f"acct_{rng.randrange(16)}"
                service=f"service_{rng.randrange(8)}"
                criticality=rng.randrange(1,5);impact=rng.randrange(1,5);urgency=rng.randrange(1,5)
                score=4*impact+3*criticality+2*urgency+rng.randrange(1,5)
                priority.append({"incident_id":incident,"scenario_id":scenario,"template_id":f"{family}:{variant}",
                                 "family":family,"impact":impact,"urgency":urgency,
                                 "criticality":criticality,"priority_score":score})
                count=rng.randrange(8,14)
                start=rng.randrange(5,58)
                # Partial lineage references span adjacent three-event fragments.
                # Some unrelated incidents deliberately reuse a pool token.
                shared_auth=tok(queue,"shared-auth",ii//2) if ii < 12 and rng.random()<.25 else None
                shared_flow=tok(queue,"shared-flow",ii//2) if ii < 12 and rng.random()<.20 else None
                fault_mode=("clean","missing","delayed","shared_controller","independent_error",
                            "registry_error","compromised_sensor","derived_duplicate")[((ii//2)+qi)%8]
                faults.append({"incident_id":incident,"failure_mode":fault_mode,
                               "family":family,"template_id":f"{family}:v{variant}"})
                for j in range(count):
                    obs=f"{queue}_src_{ii:03d}_{j:02d}"
                    if j>0 and rng.random()<(.18 if fault_mode=="missing" else .08):
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
                    if fault_mode in ("shared_controller","independent_error","compromised_sensor") and ii < 12 and j in (2,3):
                        if rng.random()<.22:auth=tok(queue,"shared-auth",ii//2)
                    tree=tok(scenario,"tree",segment) if rng.random()>.06 else None
                    event=min(95,start+2*j+rng.randrange(0,3))
                    collection=event+rng.randrange(0,3)
                    detector=collection+rng.randrange(0,3)
                    late_chance=.27 if fault_mode=="delayed" else .13
                    available=detector+(rng.randrange(20,42) if j and rng.random()<late_chance else rng.randrange(0,4))
                    processing=available+rng.randrange(0,3)
                    record={"source_id":obs,"event_minute":event,"collection_minute":collection,
                            "detector_minute":detector,"evidence_available_minute":available,
                            "processing_minute":processing,"host":host if rng.random()>.07 else None,
                            "account":account if rng.random()>.07 else None,"indicator":service,
                            "process_tree_ref":tree,"auth_session_ref":auth,"network_flow_ref":flow,
                            "event_type":EVENTS[(j+ii)%len(EVENTS)],"severity":max(1,min(5,impact+rng.choice((-1,0,0,1)))),
                            "asset_criticality":criticality}
                    source.append(record)
                    copies=2 if rng.random()<(.18 if fault_mode=="derived_duplicate" else .08) else 1
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
                        for field in ("host","account","indicator","process_tree_ref","auth_session_ref",
                                      "network_flow_ref","event_type","severity","asset_criticality"):
                            field_ledger.append({"artifact_id":alert_id,"field":field,"permitted":True,
                                "available_minute":available+(rng.randrange(8,28) if rng.random()<.10 else 0)})
                        truth.append({"alert_id":alert_id,"source_id":obs,"incident_id":incident,
                            "scenario_id":scenario,"attack_stage":family,"malicious":True})
                    if available>config["decision_minute"]:degradation.append({"source_id":obs,"reason":"late_evidence"})
            for j in range(config["benign_observations_per_queue"]):
                obs=f"{queue}_benign_{j:03d}";event=rng.randrange(0,95)
                if j<10:event=20+2*j
                collection=event+rng.randrange(0,3);detector=collection+rng.randrange(0,3);available=detector+rng.randrange(0,5)
                record={"source_id":obs,"event_minute":event,"collection_minute":collection,
                    "detector_minute":detector,"evidence_available_minute":available,"processing_minute":available+1,
                    "host":f"host_{rng.randrange(10)}","account":f"acct_{rng.randrange(14)}",
                    "indicator":f"service_{rng.randrange(8)}","process_tree_ref":tok(queue,"benign-tree",j//3) if rng.random()>.1 else None,
                    "auth_session_ref":tok(queue,"shared-auth",rng.randrange(5)) if rng.random()<.08 else None,
                    "network_flow_ref":tok(queue,"shared-flow",rng.randrange(5)) if rng.random()<.08 else None,
                    "event_type":EVENTS[j%len(EVENTS)],"severity":rng.randrange(1,5),"asset_criticality":rng.randrange(1,5)}
                if j<10:
                    pair=j//2
                    record["host"]=f"stress_host_{pair}_{j%2}"
                    record["account"]=f"stress_acct_{pair}"
                    record["process_tree_ref"]=tok(queue,"delayed_contradiction_process",pair)
                source.append(record);alert_id=obs+"_a0"
                alerts.append({**{k:record[k] for k in ("source_id","event_minute","host","account","indicator",
                    "process_tree_ref","auth_session_ref","network_flow_ref","event_type","severity","asset_criticality")},
                    "alert_id":alert_id,"queue_id":queue,"evidence_available_minute":available})
                ledger.append({"sequence":len(ledger)+1,"artifact_id":alert_id,"source_id":obs,
                    "event_minute":event,"collection_minute":collection,"detector_minute":detector,
                    "evidence_available_minute":available,"processing_minute":available+1,
                    "analyst_decision_minute":config["decision_minute"],"reason":BENIGN[j%len(BENIGN)]})
                for field in ("host","account","indicator","process_tree_ref","auth_session_ref",
                              "network_flow_ref","event_type","severity","asset_criticality"):
                    field_available=available+(rng.randrange(8,28) if rng.random()<.10 else 0)
                    if j<10 and field=="host":
                        field_available=(99,100,101,140,10**9)[j//2] if j%2 else min(available,99)
                    field_ledger.append({"artifact_id":alert_id,"field":field,"permitted":True,
                        "available_minute":field_available})
                truth.append({"alert_id":alert_id,"source_id":obs,"incident_id":f"{queue}_benign_{j:03d}",
                    "scenario_id":None,"attack_stage":None,"malicious":False})
            # A separate receiver stream records source-to-source parent claims.
            # Private physical lineage is retained to audit corrupted claims.
            source_by_step={}
            for record in source:
                sid=record["source_id"]
                if "_src_" in sid:
                    step=sid.rsplit("_src_",1)[1].split("_")
                    source_by_step[int(step[0]),int(step[1])]=sid
            mode_by_inc={int(x["incident_id"].rsplit("_",1)[-1]):x["failure_mode"] for x in faults}
            receipt_rows=[];receipt_fields=[];physical_lineage=[]
            event_sensor={"auth":"auth","process":"endpoint","network":"network",
                          "file":"endpoint","service":"identity","privilege":"identity"}
            for record in source:
                sid=record["source_id"]
                if "_src_" not in sid:continue
                ii,j=map(int,sid.rsplit("_src_",1)[1].split("_"))
                mode=mode_by_inc[ii]
                earlier=[k for k in source_by_step if k[0]==ii and k[1]<j]
                true_parent=source_by_step[max(earlier,key=lambda x:x[1])] if earlier else None
                if j%3==1 and source_by_step.get((ii,j-2)):
                    true_parent=source_by_step[ii,j-2]
                claimed_parent=true_parent
                corrupt=False
                if mode in ("shared_controller","independent_error","compromised_sensor","registry_error") and ii<12 and j in (3,4):
                    sibling=source_by_step.get((ii^1,2))
                    fault_rng=random.Random(int(tok(config["namespace"],sid,"receipt_fault"),16))
                    if sibling and fault_rng.random()<.35:
                        claimed_parent=sibling;corrupt=True
                sensor=event_sensor[record["event_type"]]
                actual_root=(tok(queue,ii//2,"shared_controller") if mode=="shared_controller" else
                             tok(queue,ii,sensor,"controller"))
                claimed_root=(tok(queue,ii,sensor,"registry_error") if mode=="registry_error" and j%2==0
                              else actual_root)
                available=record["evidence_available_minute"]+rng.randrange(0,7)
                if mode=="delayed" and j%3==0:available+=35
                if mode=="missing" and j%4==0:
                    physical_lineage.append({"source_id":sid,"true_parent_source_id":true_parent,
                                             "claimed_parent_source_id":None,"actual_controller_root":actual_root,
                                             "corrupt":False,"missing_receipt":True})
                    continue
                receipt={"source_id":sid,"parent_source_id":claimed_parent,
                         "sensor_origin":sensor,"controller_root":claimed_root,
                         "receiver_available_minute":available}
                receipt_rows.append(receipt)
                physical_lineage.append({"source_id":sid,"true_parent_source_id":true_parent,
                                         "claimed_parent_source_id":claimed_parent,
                                         "actual_controller_root":actual_root,
                                         "corrupt":corrupt,"missing_receipt":False})
                for field in ("parent_source_id","sensor_origin","controller_root"):
                    receipt_fields.append({"source_id":sid,"field":field,"available_minute":
                                           available+(rng.randrange(8,25) if rng.random()<.08 else 0),
                                           "permitted":True})
            # A derived duplicate that arrives after the cutoff must not alter the snapshot.
            late_duplicate=next((a for a in alerts if a["alert_id"].endswith("_a1")),None)
            if late_duplicate:
                late_duplicate["evidence_available_minute"]=101
                for x in ledger:
                    if x["artifact_id"]==late_duplicate["alert_id"]:x["evidence_available_minute"]=101
                for x in field_ledger:
                    if x["artifact_id"]==late_duplicate["alert_id"]:x["available_minute"]=max(101,x["available_minute"])

            raw_by_id={a["alert_id"]:a for a in alerts}
            alert_headers=[{k:a[k] for k in ("alert_id","source_id","queue_id","event_minute",
                                             "evidence_available_minute")} for a in alerts]
            atoms=[];expectations=[]
            source_system={"auth":"identity_provider","process":"endpoint_agent",
                           "network":"network_collector","file":"endpoint_agent",
                           "service":"service_manager","privilege":"identity_provider"}
            for entry in field_ledger:
                aid,field=entry["artifact_id"],entry["field"]
                alert=raw_by_id[aid]
                value=alert[field]
                source_id=alert["source_id"]
                kind="derived" if aid.endswith("_a1") else "original"
                parent_ids=[aid[:-1]+"0"] if kind=="derived" else []
                declared=min(alert["evidence_available_minute"],config["decision_minute"])
                if rng.random()<.025:declared=config["decision_minute"]+1
                expectations.append({"artifact_id":aid,"field":field,"declared_minute":declared,
                                     "availability_claim":"unavailable" if value is None else "pending",
                                     "source_event_id":source_id})
                atom={"artifact_id":aid,"field":field,"value":value,
                      "original_source_observation_id":source_id,"source_event_id":source_id,
                      "source_system":source_system.get(alert["event_type"],"unknown_system"),
                      "sensor_identity":alert["event_type"],"evidence_type":field,
                      "event_timestamp":alert["event_minute"],
                      "receiver_arrival_timestamp":entry["available_minute"],
                      "first_observable_timestamp":entry["available_minute"],
                      "last_update_timestamp":entry["available_minute"],
                      "observation_kind":kind,"parent_observation_ids":parent_ids,
                      "duplicated":kind=="derived","independence_verified":kind=="original",
                      "contradictory_information":False,"version":0}
                atoms.append(atom)
                if aid.endswith("_benign_010_a0") and field=="host":
                    atoms.append({**atom,"value":"corrected_contradictory_host",
                                  "receiver_arrival_timestamp":105,
                                  "first_observable_timestamp":105,"last_update_timestamp":105,
                                  "contradictory_information":True,"version":1})
            priority.sort(key=lambda x:(-x["priority_score"],x["incident_id"]))
            for rank,row in enumerate(priority,1):row["priority_rank"]=rank
            rng.shuffle(alerts);rng.shuffle(source)
            for name,rows in (("generated_alerts",alerts),("source_observations",source),("evidence_ledger",ledger),
                              ("field_ledger",field_ledger),("ground_truth_private",truth),
                              ("faults_private",faults),("degradation",degradation),
                              ("receiver_receipts",receipt_rows),("receipt_field_ledger",receipt_fields),
                              ("physical_lineage_private",physical_lineage),
                              ("alert_headers",alert_headers),("evidence_atoms",atoms),
                              ("evidence_expectations",expectations)):
                write(data/split/name/f"{queue}.jsonl",rows)
            write(data/split/"ground_truth_private"/f"{queue}_priority.jsonl",priority)
            manifest["queues"][split].append({"queue_id":queue,"alerts":len(alerts),"incidents":len(priority)})
    manifest["classification"]="controlled_synthetic_development_only"
    manifest["locked_test"]="not_created"
    (data/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:len(v) for k,v in manifest["queues"].items()}))


if __name__=="__main__":generate()
