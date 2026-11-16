"""Model-visible field gating, fragment candidates, calibrated inference."""
import json
import math
import time
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
FIELDS={"transaction_ref","process_ref","auth_ref","flow_ref","host","account","indicator",
        "event_type","severity","asset_criticality"}
ALLOWED=FIELDS|{"alert_id","source_id","sensor","queue_id","event_minute","evidence_available_minute"}


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def visible(data,split,queue,cutoff):
    folder=Path(data)/split
    alerts=lines(folder/"generated_alerts"/f"{queue}.jsonl")
    ledger=lines(folder/"evidence_ledger"/f"{queue}.jsonl")
    fields=lines(folder/"field_ledger"/f"{queue}.jsonl")
    if any(set(a)-ALLOWED for a in alerts):raise ValueError("Model-visible schema violation")
    if [x["sequence"] for x in ledger]!=list(range(1,len(ledger)+1)):raise ValueError("Ledger order")
    if [x["sequence"] for x in fields]!=list(range(1,len(fields)+1)):raise ValueError("Field ledger order")
    availability={x["artifact_id"]:x["evidence_available_minute"] for x in ledger}
    field_map={(x["artifact_id"],x["field"]):x for x in fields}
    if len(availability)!=len(alerts) or len(field_map)!=len(alerts)*len(FIELDS):raise ValueError("Ledger coverage")
    result=[]
    for raw in alerts:
        if raw["evidence_available_minute"]!=availability[raw["alert_id"]]:raise ValueError("Arrival mismatch")
        if availability[raw["alert_id"]]>cutoff:continue
        row={k:raw[k] for k in ALLOWED-FIELDS}
        for field in FIELDS:
            entry=field_map[(raw["alert_id"],field)]
            row[field]=raw[field] if entry["permitted"] and entry["available_minute"]<=cutoff else None
        result.append(row)
    return sorted(result,key=lambda x:x["alert_id"])


def fragments(alerts,cap=100):
    n=len(alerts);parent=list(range(n));size=[1]*n
    def root(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def join(i,j):
        a,b=root(i),root(j)
        if a!=b and size[a]+size[b]<=cap:parent[b]=a;size[a]+=size[b]
    for field in ("source_id","transaction_ref","process_ref"):
        index=defaultdict(list)
        for i,a in enumerate(alerts):
            if a.get(field):index[a[field]].append(i)
        for ids in index.values():
            for j in ids[1:]:join(ids[0],j)
    groups=defaultdict(list)
    for i in range(n):groups[root(i)].append(i)
    return list(groups.values())


def candidates(alerts,groups):
    membership={i:g for g,group in enumerate(groups) for i in group}
    support=defaultdict(lambda:defaultdict(list));frequency={}
    for field in ("auth_ref","flow_ref"):
        index=defaultdict(list)
        for i,a in enumerate(alerts):
            if a.get(field):index[a[field]].append(i)
        for ref,ids in index.items():
            group_ids={membership[i] for i in ids}
            frequency[(field,ref)]=len(group_ids)
            for pos,i in enumerate(ids):
                for j in ids[pos+1:]:
                    ga,gb=membership[i],membership[j]
                    if ga==gb or alerts[i]["source_id"]==alerts[j]["source_id"]:continue
                    if abs(alerts[i]["event_minute"]-alerts[j]["event_minute"])>25:continue
                    support[tuple(sorted((ga,gb)))][field].append((i,j,ref))
    rows=[]
    for (ga,gb),fields in support.items():
        left=[alerts[i] for i in groups[ga]];right=[alerts[i] for i in groups[gb]]
        hosts_a={x["host"] for x in left if x["host"]};hosts_b={x["host"] for x in right if x["host"]}
        accounts_a={x["account"] for x in left if x["account"]};accounts_b={x["account"] for x in right if x["account"]}
        auth=fields.get("auth_ref",[]);flow=fields.get("flow_ref",[])
        sources=({alerts[i]["source_id"] for pairs in fields.values() for i,j,_ in pairs} |
                 {alerts[j]["source_id"] for pairs in fields.values() for i,j,_ in pairs})
        sensors=({alerts[i]["sensor"] for pairs in fields.values() for i,j,_ in pairs} |
                 {alerts[j]["sensor"] for pairs in fields.values() for i,j,_ in pairs})
        rare=all(frequency[(field,ref)]<=2 for field,pairs in fields.items() for _,_,ref in pairs)
        host_ok=bool(hosts_a&hosts_b);account_ok=bool(accounts_a&accounts_b)
        contradiction=bool(hosts_a and hosts_b and not host_ok and accounts_a and accounts_b and not account_ok)
        key=f"a{int(bool(auth))}f{int(bool(flow))}h{int(host_ok)}u{int(account_ok)}s{int(len(sensors)>=3)}r{int(rare)}"
        rows.append({"left":ga,"right":gb,"key":key,"auth":bool(auth),"flow":bool(flow),
                     "host_agree":host_ok,"account_agree":account_ok,"contradiction":contradiction,
                     "source_witnesses":len(sources),"sensor_origins":len(sensors),"rare":rare})
    return rows


def rank(groups,alerts,ranker):
    def score(group):
        unique={alerts[i]["source_id"]:alerts[i] for i in group}
        values=list(unique.values())
        maxsev=max((x["severity"] or 1) for x in values)
        critical=max((x["asset_criticality"] or 1) for x in values)
        diversity=len({x["event_type"] for x in values if x["event_type"]})
        sensor_diversity=len({x["sensor"] for x in values})
        if ranker=="progression":return 1.2*maxsev+.7*critical+.55*diversity+.1*min(len(values),10)
        if ranker=="sensor_priority":return 1.2*maxsev+.9*critical+.4*diversity+.15*sensor_diversity+.1*min(len(values),10)
        raise ValueError(ranker)
    return sorted(groups,key=lambda g:(-score(g),min(alerts[i]["alert_id"] for i in g)))


def predict(data,split,queue,threshold,ranker,model,cutoff,cap):
    start=time.perf_counter();alerts=visible(data,split,queue,cutoff)
    base=fragments(alerts,cap);rows=candidates(alerts,base)
    n=len(alerts);parent=list(range(len(base)));size=[len(g) for g in base];decisions=Counter();audit=[]
    def root(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def context(group):
        ids=[i for g in range(len(base)) if root(g)==group for i in base[g]]
        return ({alerts[i]["host"] for i in ids if alerts[i]["host"]},
                {alerts[i]["account"] for i in ids if alerts[i]["account"]})
    proposals=[]
    for row in rows:
        p=model.get(row["key"],model.get("__default__",0))
        if row["contradiction"]:
            decisions["reject_contradiction"]+=1;state="reject"
        elif row["source_witnesses"]<2 or row["sensor_origins"]<2:
            decisions["abstain_witness"]+=1;state="abstain"
        elif p<threshold:
            decisions["abstain_calibration"]+=1;state="abstain"
        else:
            proposals.append((p,row["source_witnesses"],row["left"],row["right"],row));continue
        audit.append({"left":row["left"],"right":row["right"],"decision":state,"key":row["key"],"probability":p})
    for p,_,a,b,row in sorted(proposals,key=lambda x:(-x[0],-x[1],x[2],x[3])):
        ra,rb=root(a),root(b)
        if ra==rb:continue
        if size[ra]+size[rb]>cap:
            decisions["reject_cap"]+=1;state="reject"
        else:
            ha,ua=context(ra);hb,ub=context(rb)
            if ha and hb and not ha&hb and ua and ub and not ua&ub:
                decisions["reject_group_contradiction"]+=1;state="reject"
            else:
                parent[rb]=ra;size[ra]+=size[rb];decisions["accept"]+=1;state="accept"
        audit.append({"left":a,"right":b,"decision":state,"key":row["key"],"probability":p})
    merged=defaultdict(list)
    for g,group in enumerate(base):merged[root(g)].extend(group)
    groups=rank(list(merged.values()),alerts,ranker)
    result=[[alerts[i]["alert_id"] for i in group] for group in groups]
    assert sum(map(len,result))==n and max(map(len,result),default=0)<=cap
    return {"queue_id":queue,"split":split,"method":f"calibrated_{threshold}","ranker":ranker,
            "cutoff":cutoff,"eligible_alert_ids":[a["alert_id"] for a in alerts],"groups_ranked":result,
            "candidate_pairs":len(rows),"decisions":dict(decisions),"runtime_seconds":time.perf_counter()-start},audit,base,alerts
