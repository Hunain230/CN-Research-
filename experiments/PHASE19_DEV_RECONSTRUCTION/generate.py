"""Four isolated sensor simulators observe controller actions; no attack execution."""
import hashlib
import json
import random
from pathlib import Path

HERE=Path(__file__).resolve().parent
SENSORS=("auth","endpoint","network","identity")
FAMILIES=("initial_access","credential_compromise","suspicious_authentication","lateral_movement",
          "privilege_escalation","persistence","command_control","data_staging","exfiltration","multi_stage_chain")
EVENTS=("auth","process","network","file","service","privilege")
FIELDS=("transaction_ref","process_ref","auth_ref","flow_ref","host","account","indicator",
        "event_type","severity","asset_criticality")


def tok(*parts):return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()[:18]
def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")


def generate():
    cfg=json.loads((HERE/"configs/study.json").read_text())
    out=HERE/"datasets"
    if out.exists():raise FileExistsError("Dataset already sealed")
    manifest={"schema":cfg["schema"],"templates":{},"queues":{},"sensor_process_seeds":{}}
    for split,variants in (("train",(0,1,2,3)),("development",(4,)),("locked_test",(5,))):
        controller=random.Random(cfg["seeds"][split])
        templates=[f"{f}:v{v}" for f in FAMILIES for v in variants]
        manifest["templates"][split]=templates;manifest["queues"][split]=[]
        for qi in range(cfg["queues"][split]):
            queue=f"{cfg['namespace']}_{split}_q{qi:03d}"
            sensor_rng={s:random.Random(cfg["seeds"][split]+(k+1)*100000+qi*1009) for k,s in enumerate(SENSORS)}
            manifest["sensor_process_seeds"][queue]={s:cfg["seeds"][split]+(k+1)*100000+qi*1009 for k,s in enumerate(SENSORS)}
            actions=[];priority=[]
            for i in range(cfg["incidents_per_queue"]):
                family,variant=templates[(i+qi*7)%len(templates)].split(":")
                incident=f"{queue}_incident_{i:03d}"
                host=f"host_{controller.randrange(12)}"
                account=f"acct_{controller.randrange(16)}"
                if i and controller.random()<.12:  # common-mode infrastructure collision
                    host=f"host_{i%4}";account=f"acct_{i%4}"
                impact=controller.randrange(1,5);criticality=controller.randrange(1,5);urgency=controller.randrange(1,5)
                priority.append({"incident_id":incident,"scenario_id":f"{queue}_scenario_{i:03d}",
                    "template_id":f"{family}:{variant}","family":family,"impact":impact,
                    "criticality":criticality,"urgency":urgency,
                    "priority_score":4*impact+3*criticality+2*urgency+controller.randrange(1,5)})
                shared=(controller.random()<.14)
                start=controller.randrange(4,57)
                for j in range(9):
                    segment=j//3
                    auth_b={2:0,3:0,5:1,6:1,8:2}.get(j)
                    flow_b={0:0,4:0,3:1,7:1,6:2}.get(j)
                    action={"action_id":f"{queue}_action_{i:03d}_{j:02d}","incident_id":incident,
                        "family":family,"event_minute":min(92,start+2*j),
                        "host":host,"account":account,"indicator":f"service_{controller.randrange(10)}",
                        "event_type":EVENTS[(j+i)%len(EVENTS)],"severity":max(1,min(5,impact+controller.choice((-1,0,1)))),
                        "asset_criticality":criticality,"transaction_ref":tok(queue,i,j,"transaction"),
                        "process_ref":tok(queue,i,segment,"process"),
                        "auth_ref":(tok(queue,"shared",i%4,"auth",auth_b) if shared else tok(queue,i,"auth",auth_b)) if auth_b is not None else None,
                        "flow_ref":(tok(queue,"shared",i%4,"flow",flow_b) if shared else tok(queue,i,"flow",flow_b)) if flow_b is not None else None,
                        "malicious":True}
                    actions.append(action)
            for j in range(cfg["benign_actions_per_queue"]):
                actions.append({"action_id":f"{queue}_benign_action_{j:03d}","incident_id":f"{queue}_benign_{j:03d}",
                    "family":None,"event_minute":controller.randrange(3,93),"host":f"host_{controller.randrange(12)}",
                    "account":f"acct_{controller.randrange(16)}","indicator":f"service_{controller.randrange(10)}",
                    "event_type":EVENTS[j%len(EVENTS)],"severity":controller.randrange(1,5),
                    "asset_criticality":controller.randrange(1,5),"transaction_ref":tok(queue,"benign",j,"transaction"),
                    "process_ref":tok(queue,"benign",j//3,"process"),
                    "auth_ref":tok(queue,"shared",j%4,"auth",j%2) if controller.random()<.16 else None,
                    "flow_ref":tok(queue,"shared",j%4,"flow",j%2) if controller.random()<.16 else None,
                    "malicious":False})
            actions.sort(key=lambda x:(x["event_minute"],x["action_id"]))
            source=[];alerts=[];ledger=[];field_ledger=[];truth=[];degradation=[]
            for action in actions:
                for sensor in SENSORS:
                    rng=sensor_rng[sensor]
                    if rng.random()<(.21 if action["malicious"] else .35):
                        degradation.append({"action_id":action["action_id"],"sensor":sensor,"reason":"sensor_missed"})
                        continue
                    obs=f"{action['action_id']}_{sensor}_obs"
                    event=action["event_minute"]
                    collection=event+rng.randrange(0,4);detector=collection+rng.randrange(0,4)
                    base_available=detector+rng.randrange(0,5)+(rng.randrange(15,35) if rng.random()<.08 else 0)
                    raw={"source_id":obs,"sensor":sensor,"action_ref_private":action["action_id"],
                         "event_minute":event,"collection_minute":collection,"detector_minute":detector,
                         "evidence_available_minute":base_available,"processing_minute":base_available+rng.randrange(0,3)}
                    visible_fields={}
                    for field in FIELDS:
                        value=action[field]
                        if field=="process_ref" and sensor not in ("endpoint","network"):value=None
                        if field=="auth_ref" and sensor not in ("auth","identity"):value=None
                        if field=="flow_ref" and sensor not in ("endpoint","network"):value=None
                        if field=="account" and sensor=="network" and rng.random()<.4:value=None
                        if field=="host" and sensor=="identity" and rng.random()<.4:value=None
                        if rng.random()<.07:value=None
                        visible_fields[field]=value
                    raw.update(visible_fields);source.append(raw)
                    alert_id=obs+"_alert"
                    alert={"alert_id":alert_id,"source_id":obs,"sensor":sensor,"queue_id":queue,
                           "event_minute":event,"evidence_available_minute":base_available,**visible_fields}
                    alerts.append(alert)
                    ledger.append({"sequence":len(ledger)+1,"artifact_id":alert_id,"source_id":obs,"sensor":sensor,
                        "event_minute":event,"collection_minute":collection,"detector_minute":detector,
                        "evidence_available_minute":base_available,"processing_minute":raw["processing_minute"],
                        "analyst_decision_minute":cfg["decision_minute"]})
                    for field in FIELDS:
                        field_ledger.append({"sequence":len(field_ledger)+1,"artifact_id":alert_id,"field":field,
                            "source_id":obs,"sensor":sensor,
                            "available_minute":base_available+(rng.randrange(8,25) if rng.random()<.12 else 0),
                            "permitted":True,"derivation":"sensor_observation"})
                    truth.append({"alert_id":alert_id,"source_id":obs,"incident_id":action["incident_id"],
                        "scenario_id":action["incident_id"] if action["malicious"] else None,
                        "attack_stage":action["family"],"malicious":action["malicious"]})
            priority.sort(key=lambda x:(-x["priority_score"],x["incident_id"]))
            for rank,row in enumerate(priority,1):row["priority_rank"]=rank
            controller.shuffle(alerts)
            for name,rows in (("source_observations",source),("generated_alerts",alerts),("evidence_ledger",ledger),
                              ("field_ledger",field_ledger),("ground_truth_private",truth),("degradation",degradation)):
                write(out/split/name/f"{queue}.jsonl",rows)
            write(out/split/"ground_truth_private"/f"{queue}_priority.jsonl",priority)
            write(out/split/"ground_truth_private"/f"{queue}_controller_actions.jsonl",actions)
            manifest["queues"][split].append({"queue_id":queue,"alerts":len(alerts),"source_observations":len(source),
                                               "field_ledger_rows":len(field_ledger),"incidents":len(priority)})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:len(v) for k,v in manifest["queues"].items()}))


if __name__=="__main__":generate()
