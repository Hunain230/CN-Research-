"""Controlled causal-provenance fixture. No attack execution or locked cohort."""
import hashlib
import json
import random
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/"datasets_v3"
SENSORS=("auth","endpoint","network","identity")
SPLITS={"train":(3,2101),"development":(8,2102)}

def token(*parts):
    return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()[:20]

def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")

def generate():
    if OUT.exists():raise FileExistsError("Phase 21 dataset already frozen")
    manifest={"schema":"phase21-causal-provenance-v1","namespace":"phase21a",
              "splits":{},"decision_minute":100,"sensor_processes":list(SENSORS),
              "classification":"controlled_synthetic_development_not_independent_validation"}
    for split,(queue_count,seed) in SPLITS.items():
        manifest["splits"][split]=[]
        for qi in range(queue_count):
            q=f"phase21a_{split}_q{qi:03d}"
            world=random.Random(seed+qi*7919)
            rngs={s:random.Random(seed+qi*7919+(i+1)*100003) for i,s in enumerate(SENSORS)}
            events=[];priority=[];collision_pairs=[]
            for inc in range(12):
                incident=f"{q}_incident_{inc:03d}"
                pair=inc//2
                host=f"host_{pair}";account=f"acct_{pair}"
                priority.append({"incident_id":incident,"priority_rank":inc+1})
                start=10+world.randrange(30)
                for j in range(6):
                    eid=f"{q}_event_{inc:03d}_{j}"
                    parents=([f"{q}_event_{inc:03d}_{j-1}"] if j in (1,2,4,5) else
                             [f"{q}_event_{inc:03d}_1"] if j==3 else [])
                    if j==4:parents.append(f"{q}_event_{inc:03d}_2")
                    events.append({"event_id":eid,"incident_id":incident,"minute":start+3*j,
                                   "parent_event_ids":parents,"fragment_ref":token(q,inc,j//3,"session"),
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
            sensor_records=[];receipts=[];alerts=[];alert_lineage=[];field_ledger=[];truth=[];claims=[];claim_lineage=[]
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
                    # Cross-fragment real causal edges, witnessed on distinct child events.
                    if event["malicious"] and event["event_id"].endswith("_3") and sensor=="auth":
                        parent=event["parent_event_ids"][0]
                    elif event["malicious"] and event["event_id"].endswith("_4") and sensor=="endpoint":
                        parent=event["parent_event_ids"][1]
                    else:parent=None
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
                              ("collision_pairs_private",collision_pairs)):
                write(folder/name/f"{q}.jsonl",rows)
            for sensor in SENSORS:
                write(folder/"sensor_process_records_private"/sensor/f"{q}.jsonl",
                      [r for r in sensor_records if r["sensor_process"]==sensor])
            write(folder/"ground_truth_private"/f"{q}_priority.jsonl",priority)
            manifest["splits"][split].append({"queue_id":q,"alerts":len(alerts),"claims":len(claims),
                                                "incidents":12,"collision_pairs":6})
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({s:len(v) for s,v in manifest["splits"].items()}))

if __name__=="__main__":generate()
