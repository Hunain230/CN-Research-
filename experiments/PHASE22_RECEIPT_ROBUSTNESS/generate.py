"""Fresh receipt-robustness fixture; locked partition generated but never evaluated."""
import hashlib
import json
import random
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/"datasets"
SENSORS=("auth","endpoint","network","identity")
SPLITS={"train":(4,2201),"development":(10,2202),"locked_test":(20,2203)}

def token(*parts):
    return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()[:20]

def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")

def generate():
    if OUT.exists():raise FileExistsError("Phase 22 dataset already frozen")
    manifest={"schema":"phase22-receipt-robustness-v1","namespace":"phase22a",
              "splits":{},"decision_minute":100,"sensor_processes":list(SENSORS),
              "classification":"controlled_synthetic_development_not_independent_validation",
              "locked_test_policy":"generated_and_sealed_no_predictions_or_truth_reads"}
    for split,(queue_count,seed) in SPLITS.items():
        manifest["splits"][split]=[]
        for qi in range(queue_count):
            q=f"phase22a_{split}_q{qi:03d}"
            world=random.Random(seed+qi*7919)
            rngs={s:random.Random(seed+qi*7919+(i+1)*100003) for i,s in enumerate(SENSORS)}
            events=[];priority=[];collision_pairs=[]
            graph_shape=("fork_merge","three_fragment","chain_cross")[qi%3]
            failure_mode=("missing_delayed","duplicate_sources","incorrect_claims",
                          "single_compromise","shared_upstream")[qi%5]
            for inc in range(12):
                incident=f"{q}_incident_{inc:03d}"
                pair=inc//2
                host=f"host_{pair}";account=f"acct_{pair}"
                priority.append({"incident_id":incident,"priority_rank":inc+1})
                start=10+world.randrange(30)
                for j in range(6):
                    eid=f"{q}_event_{inc:03d}_{j}"
                    if graph_shape=="three_fragment":
                        parent_indexes={1:[0],2:[1],3:[0],4:[3],5:[2]}.get(j,[])
                        fragment=j//2
                    else:
                        parent_indexes={1:[0],2:[1],3:[1 if graph_shape=="fork_merge" else 2],
                                        4:[3,2 if graph_shape=="fork_merge" else 1],5:[4]}.get(j,[])
                        fragment=j//3
                    parents=[f"{q}_event_{inc:03d}_{k}" for k in parent_indexes]
                    events.append({"event_id":eid,"incident_id":incident,"minute":start+3*j,
                                   "parent_event_ids":parents,"fragment_ref":token(q,inc,fragment,"session"),
                                   "host":host,"account":account,
                                   "auth_ref":token(q,pair,"shared_auth"),
                                   "flow_ref":token(q,pair,"shared_network"),"malicious":True})
            for pair in range(6):
                collision_pairs.append({"left_incident":f"{q}_incident_{2*pair:03d}",
                                        "right_incident":f"{q}_incident_{2*pair+1:03d}",
                                        "shared_host":f"host_{pair}","shared_account":f"acct_{pair}"})
            for j in range(20):
                events.append({"event_id":f"{q}_benign_event_{j:03d}","incident_id":f"{q}_benign_{j:03d}",
                               "minute":10+world.randrange(60),"parent_event_ids":[],
                               "fragment_ref":token(q,"benign",j,"session"),
                               "host":f"host_{j%6}","account":f"acct_{j%6}",
                               "auth_ref":token(q,j%6,"shared_auth"),
                               "flow_ref":token(q,j%6,"shared_network"),"malicious":False})
            for pair in range(6):
                events.append({"event_id":f"{q}_shared_resource_{pair}","incident_id":None,
                               "minute":40,"parent_event_ids":[],"fragment_ref":None,
                               "host":f"host_{pair}","account":f"acct_{pair}",
                               "auth_ref":token(q,pair,"shared_auth"),
                               "flow_ref":token(q,pair,"shared_network"),"malicious":False,
                               "infrastructure_only":True})
            by_id={e["event_id"]:e for e in events}
            sensor_records=[];receipts=[];alerts=[];alert_lineage=[];field_ledger=[];truth=[];claims=[];claim_lineage=[];faults=[]
            alert_seq=claim_seq=0
            for sensor in SENSORS:
                rng=rngs[sensor]
                for event in events:
                    if event.get("infrastructure_only"):continue
                    if rng.random()<(.13 if event["malicious"] else .25):continue
                    source=f"{q}_{sensor}_record_{len(sensor_records):04d}"
                    available=event["minute"]+rng.randrange(1,9)
                    record={"source_record_id":source,"sensor_process":sensor,
                            "observed_event_id":event["event_id"],"origin_event_id":event["event_id"],
                            "collection_minute":event["minute"]+rng.randrange(0,3),
                            "receiver_available_minute":available}
                    sensor_records.append(record)
                    receipts.append({"source_record_id":source,"sensor":sensor,
                                     "origin_event_id":event["event_id"],
                                     "observed_parent_event_ids":event["parent_event_ids"],
                                     "observed_fragment_ref":event["fragment_ref"],
                                     "receiver_available_minute":available})
                    for duplicate in range(2 if rng.random()<.16 else 1):
                        aid=f"{source}_alert_{duplicate}"
                        alerts.append({"alert_id":aid,"source_id":source,"sensor":sensor,"queue_id":q,
                                       "event_minute":event["minute"],"evidence_available_minute":available,
                                       "fragment_ref":event["fragment_ref"],"host":event["host"],
                                       "account":event["account"],"auth_ref":event["auth_ref"],
                                       "flow_ref":event["flow_ref"],"severity":3 if event["malicious"] else 1,
                                       "asset_criticality":2})
                        alert_lineage.append({"alert_id":aid,"source_record_id":source,
                                              "transformation_id":f"{source}_transform_{duplicate}"})
                        truth.append({"alert_id":aid,"source_id":source,"incident_id":event["incident_id"],
                                      "malicious":event["malicious"]})
                        for field in ("fragment_ref","host","account","auth_ref","flow_ref"):
                            alert_seq+=1
                            field_ledger.append({"sequence":alert_seq,"artifact_id":aid,"field":field,
                                                 "available_minute":available+(rng.randrange(25,65) if rng.random()<.08 else 0),
                                                 "permitted":True})
                    # Distinct child events support each physical cross-fragment link.
                    j=int(event["event_id"].rsplit("_",1)[-1]) if event["malicious"] else -1
                    if graph_shape=="three_fragment":
                        cross={(2,"auth"):1,(3,"endpoint"):0,(4,"auth"):3,(5,"endpoint"):2}
                    else:
                        cross={(3,"auth"):1 if graph_shape=="fork_merge" else 2,
                               (4,"endpoint"):2 if graph_shape=="fork_merge" else 1}
                    parent_index=cross.get((j,sensor))
                    parent=f"{q}_event_{event['incident_id'].rsplit('_',1)[-1]}_{parent_index}" if parent_index is not None else None
                    if parent:
                        claim_seq+=1
                        claims.append({"claim_id":f"{q}_claim_{claim_seq:04d}","sensor":sensor,
                                       "source_record_id":source,"origin_event_id":event["event_id"],
                                       "parent_event_id":parent,
                                       "left_fragment_ref":by_id[parent]["fragment_ref"],
                                       "right_fragment_ref":event["fragment_ref"],
                                       "receiver_available_minute":available+(rng.randrange(65,95) if rng.random()<.22 else rng.randrange(0,7))})
                        claim_lineage.append({"claim_id":claims[-1]["claim_id"],"physical_parent_event_id":parent,
                                              "physical_child_event_id":event["event_id"],"source_record_id":source})
            # Each pair has two misleading labels from distinct sensors but one shared
            # infrastructure event root. They are not independent causal support.
            for pair in range(6):
                left=by_id[f"{q}_event_{2*pair:03d}_2"]
                right=by_id[f"{q}_event_{2*pair+1:03d}_3"]
                common_root=f"{q}_shared_resource_{pair}"
                for sensor in ("auth","network"):
                    source=f"{q}_{sensor}_context_{pair}"
                    sensor_records.append({"source_record_id":source,"sensor_process":sensor,
                                           "observed_event_id":common_root,"origin_event_id":common_root,
                                           "collection_minute":40,"receiver_available_minute":45})
                    receipts.append({"source_record_id":source,"sensor":sensor,
                                     "origin_event_id":common_root,"observed_parent_event_ids":[],
                                     "observed_fragment_ref":None,"receiver_available_minute":45})
                    claim_seq+=1
                    claims.append({"claim_id":f"{q}_claim_{claim_seq:04d}","sensor":sensor,
                                   "source_record_id":source,"origin_event_id":common_root,
                                   "parent_event_id":left["event_id"],
                                   "left_fragment_ref":left["fragment_ref"],
                                   "right_fragment_ref":right["fragment_ref"],
                                   "receiver_available_minute":48})
                    claim_lineage.append({"claim_id":claims[-1]["claim_id"],
                                          "physical_parent_event_id":None,
                                          "physical_child_event_id":common_root,"source_record_id":source})
                if pair==0:
                    # Independent sensor-local error: a different resource event is
                    # incorrectly associated with the same unrelated fragments.
                    other_root=f"{q}_shared_resource_1"
                    source=f"{q}_network_independent_error_0"
                    sensor_records.append({"source_record_id":source,"sensor_process":"network",
                                           "observed_event_id":other_root,"origin_event_id":other_root,
                                           "collection_minute":41,"receiver_available_minute":46})
                    receipts.append({"source_record_id":source,"sensor":"network",
                                     "origin_event_id":other_root,"observed_parent_event_ids":[],
                                     "observed_fragment_ref":None,"receiver_available_minute":46})
                    claim_seq+=1
                    claims.append({"claim_id":f"{q}_claim_{claim_seq:04d}","sensor":"network",
                                   "source_record_id":source,"origin_event_id":other_root,
                                   "parent_event_id":left["event_id"],
                                   "left_fragment_ref":left["fragment_ref"],
                                   "right_fragment_ref":right["fragment_ref"],
                                   "receiver_available_minute":49})
                    claim_lineage.append({"claim_id":claims[-1]["claim_id"],
                                          "physical_parent_event_id":None,
                                          "physical_child_event_id":other_root,"source_record_id":source})
            if failure_mode=="missing_delayed":
                real={x["claim_id"] for x in claim_lineage if x["physical_parent_event_id"]}
                for claim in claims:
                    if claim["claim_id"] not in real:continue
                    incident=int(claim["origin_event_id"].split("_event_")[1].split("_")[0])
                    if incident%3==0 and claim["sensor"]=="auth":
                        receipts=[r for r in receipts if r["source_record_id"]!=claim["source_record_id"]]
                        faults.append({"type":"missing_receipt","claim_id":claim["claim_id"]})
                    elif incident%3==1 and claim["sensor"]=="endpoint":
                        for receipt in receipts:
                            if receipt["source_record_id"]==claim["source_record_id"]:
                                receipt["receiver_available_minute"]=140
                        faults.append({"type":"delayed_receipt","claim_id":claim["claim_id"]})
            elif failure_mode=="duplicate_sources":
                true_ids={x["claim_id"] for x in claim_lineage if x["physical_parent_event_id"]}
                chosen=next(c for c in claims if c["claim_id"] in true_ids)
                old=chosen["source_record_id"];new=old+"_duplicate_observation"
                old_record=next(r for r in sensor_records if r["source_record_id"]==old)
                old_receipt=next(r for r in receipts if r["source_record_id"]==old)
                sensor_records.append({**old_record,"source_record_id":new})
                receipts.append({**old_receipt,"source_record_id":new})
                claim_seq+=1
                new_claim={**chosen,"claim_id":f"{q}_claim_{claim_seq:04d}","source_record_id":new}
                claims.append(new_claim)
                old_link=next(x for x in claim_lineage if x["claim_id"]==chosen["claim_id"])
                claim_lineage.append({**old_link,"claim_id":new_claim["claim_id"],"source_record_id":new})
                original_alert=next(a for a in alerts if a["source_id"]==old)
                aid=new+"_alert_0"
                alerts.append({**original_alert,"alert_id":aid,"source_id":new})
                alert_lineage.append({"alert_id":aid,"source_record_id":new,
                                      "transformation_id":new+"_transform_0"})
                original_truth=next(x for x in truth if x["source_id"]==old)
                truth.append({**original_truth,"alert_id":aid,"source_id":new})
                for field in ("fragment_ref","host","account","auth_ref","flow_ref"):
                    alert_seq+=1
                    field_ledger.append({"sequence":alert_seq,"artifact_id":aid,"field":field,
                                         "available_minute":original_alert["evidence_available_minute"],"permitted":True})
                faults.append({"type":"duplicate_source_observation","claim_id":new_claim["claim_id"]})
            elif failure_mode in ("single_compromise","shared_upstream"):
                left=by_id[f"{q}_event_000_2"]
                right=by_id[f"{q}_event_001_3"]
                targets=[f"{q}_auth_context_0"]
                if failure_mode=="shared_upstream":targets.append(f"{q}_network_independent_error_0")
                for receipt in receipts:
                    if receipt["source_record_id"] in targets:
                        receipt["observed_parent_event_ids"]=[left["event_id"]]
                        receipt["observed_fragment_ref"]=right["fragment_ref"]
                        faults.append({"type":"corrupt_receipt","source_record_id":receipt["source_record_id"],
                                       "upstream_failure_id":"shared_controller_fault_0" if failure_mode=="shared_upstream" else None})
            world.shuffle(alerts);world.shuffle(claims)
            claim_field_ledger=[]
            for claim in claims:
                for field in ("origin_event_id","parent_event_id","left_fragment_ref","right_fragment_ref"):
                    claim_field_ledger.append({"sequence":len(claim_field_ledger)+1,
                                               "artifact_id":claim["claim_id"],"field":field,
                                               "available_minute":claim["receiver_available_minute"],
                                               "permitted":True})
            receipt_field_ledger=[]
            for receipt in receipts:
                for field in ("origin_event_id","observed_parent_event_ids","observed_fragment_ref"):
                    receipt_field_ledger.append({"sequence":len(receipt_field_ledger)+1,
                                                 "artifact_id":receipt["source_record_id"],"field":field,
                                                 "available_minute":receipt["receiver_available_minute"],
                                                 "permitted":True})
            folder=OUT/split
            for name,rows in (("physical_events_private",events),("sensor_records_private",sensor_records),
                              ("alert_lineage_private",alert_lineage),("claim_lineage_private",claim_lineage),
                              ("generated_alerts",alerts),("field_ledger",field_ledger),
                              ("receiver_receipts",receipts),("receipt_field_ledger",receipt_field_ledger),
                              ("causal_claims",claims),("claim_field_ledger",claim_field_ledger),
                              ("ground_truth_private",truth),
                              ("collision_pairs_private",collision_pairs),("faults_private",faults)):
                write(folder/name/f"{q}.jsonl",rows)
            for sensor in SENSORS:
                write(folder/"sensor_process_records_private"/sensor/f"{q}.jsonl",
                      [r for r in sensor_records if r["sensor_process"]==sensor])
            write(folder/"ground_truth_private"/f"{q}_priority.jsonl",priority)
            manifest["splits"][split].append({"queue_id":q,"alerts":len(alerts),"claims":len(claims),
                                                "incidents":12,"collision_pairs":6,
                                                "graph_shape":graph_shape,"failure_mode":failure_mode})
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({s:len(v) for s,v in manifest["splits"].items()}))

if __name__=="__main__":generate()
