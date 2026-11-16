"""Label-blind source-lineage fragment reconstruction with accept/reject/abstain."""
import argparse
import json
import time
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ALLOWED={"alert_id","source_id","queue_id","event_minute","host","account","indicator",
         "process_tree_ref","auth_session_ref","network_flow_ref","event_type","severity",
         "asset_criticality","evidence_available_minute"}
PRIVATE={"incident_id","scenario_id","template_id","attack_stage","malicious","priority_score","priority_rank"}


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def visible(data,split,queue,cutoff):
    folder=Path(data)/split
    alerts=lines(folder/"generated_alerts"/f"{queue}.jsonl")
    ledger=lines(folder/"evidence_ledger"/f"{queue}.jsonl")
    if any(set(a)-ALLOWED or set(a)&PRIVATE for a in alerts):raise ValueError("Unapproved model input")
    if [x["sequence"] for x in ledger]!=list(range(1,len(ledger)+1)):raise ValueError("Ledger sequence")
    availability={x["artifact_id"]:x["evidence_available_minute"] for x in ledger}
    if len(alerts)!=len(ledger) or len(availability)!=len(ledger):raise ValueError("Ledger coverage")
    if any(a["evidence_available_minute"]!=availability[a["alert_id"]] for a in alerts):raise ValueError("Availability mismatch")
    return sorted((a for a in alerts if availability[a["alert_id"]]<=cutoff),key=lambda a:a["alert_id"])


def correlate(alerts,method,cap):
    n=len(alerts);parent=list(range(n));sizes=[1]*n;decisions=Counter();reason_rows=[]
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def members(r):return [i for i in range(n) if root(i)==r]
    def merge(i,j,kind):
        a,b=root(i),root(j)
        if a==b:return
        if sizes[a]+sizes[b]>cap:
            decisions["cap_reject"]+=1;return
        if method.endswith("_v"):
            ma,mb=members(a),members(b)
            hosts_a={alerts[k]["host"] for k in ma if alerts[k]["host"]}
            hosts_b={alerts[k]["host"] for k in mb if alerts[k]["host"]}
            accounts_a={alerts[k]["account"] for k in ma if alerts[k]["account"]}
            accounts_b={alerts[k]["account"] for k in mb if alerts[k]["account"]}
            if method=="lineage_one_context_v" and kind=="lineage" and not (
                hosts_a and hosts_b and hosts_a&hosts_b and accounts_a and accounts_b and accounts_a&accounts_b):
                decisions["context_abstain"]+=1
                reason_rows.append({"decision":"abstain","reason":"lineage_without_host_and_account_agreement",
                                    "left":alerts[i]["alert_id"],"right":alerts[j]["alert_id"]})
                return
            if hosts_a and hosts_b and not hosts_a&hosts_b and accounts_a and accounts_b and not accounts_a&accounts_b:
                decisions["contradiction_reject"]+=1
                reason_rows.append({"decision":"reject","reason":"host_and_account_conflict","left":alerts[i]["alert_id"],"right":alerts[j]["alert_id"]})
                return
        parent[b]=a;sizes[a]+=sizes[b]
        decisions[kind+"_accept"]+=1
        reason_rows.append({"decision":"accept","reason":kind,"left":alerts[i]["alert_id"],"right":alerts[j]["alert_id"]})
    by_source=defaultdict(list)
    for i,a in enumerate(alerts):by_source[a["source_id"]].append(i)
    for indices in by_source.values():
        for i in indices[1:]:merge(indices[0],i,"same_source")
    if method!="source_only":
        by_tree=defaultdict(list)
        for i,a in enumerate(alerts):
            if a["process_tree_ref"]:by_tree[a["process_tree_ref"]].append(i)
        for indices in by_tree.values():
            for i in indices[1:]:merge(indices[0],i,"process_tree")
    edge_count=0
    if method.startswith("lineage"):
        supports=defaultdict(lambda:defaultdict(set))
        for field in ("auth_session_ref","network_flow_ref"):
            by_ref=defaultdict(list)
            for i,a in enumerate(alerts):
                if a[field]:by_ref[a[field]].append(i)
            for indices in by_ref.values():
                for pos,i in enumerate(indices):
                    for j in indices[pos+1:]:
                        if alerts[i]["source_id"]==alerts[j]["source_id"] or root(i)==root(j):continue
                        if abs(alerts[i]["event_minute"]-alerts[j]["event_minute"])>25:continue
                        pair=tuple(sorted((root(i),root(j))))
                        supports[pair][field].add((alerts[i]["source_id"],alerts[j]["source_id"]))
                        edge_count+=1
        proposals=[]
        for (a,b),fields in supports.items():
            source_ids={x for pairs in fields.values() for pair in pairs for x in pair}
            valid=(len(fields)>=1 and len(source_ids)>=2) if method in ("lineage_one","lineage_one_context_v") else (len(fields)==2 and len(source_ids)>=4)
            if valid:proposals.append((len(fields),len(source_ids),a,b))
            else:
                decisions["abstain_insufficient_independent_sources"]+=1
                reason_rows.append({"decision":"abstain","reason":"insufficient_independent_lineage","left":alerts[a]["alert_id"],"right":alerts[b]["alert_id"]})
        for _,__,a,b in sorted(proposals,reverse=True):merge(a,b,"lineage")
    groups=defaultdict(list)
    for i,a in enumerate(alerts):groups[root(i)].append(a["alert_id"])
    result=sorted((sorted(g) for g in groups.values()),key=lambda g:g[0])
    if sum(map(len,result))!=n or max(map(len,result),default=0)>cap:raise AssertionError("invalid partition")
    return result,edge_count,dict(decisions),reason_rows


def rank(groups,alerts):
    lookup={a["alert_id"]:a for a in alerts}
    def score(group):
        items={lookup[x]["source_id"]:lookup[x] for x in group}.values()
        items=list(items)
        return 1.2*max(a["severity"] for a in items)+.7*max(a["asset_criticality"] for a in items)+.55*len({a["event_type"] for a in items})+.1*min(len(items),10)
    return sorted(groups,key=lambda g:(-score(g),g[0]))


def predict(data,split,queue,method,cutoff,cap):
    start=time.perf_counter();alerts=visible(data,split,queue,cutoff)
    groups,edges,decisions,reasons=correlate(alerts,method,cap)
    return {"queue_id":queue,"split":split,"method":method,"ranker":"progression",
            "cutoff":cutoff,"eligible_alert_ids":[a["alert_id"] for a in alerts],
            "groups_ranked":rank(groups,alerts),"candidate_pairs":edges,"decisions":decisions,
            "runtime_seconds":time.perf_counter()-start},reasons


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--split",required=True)
    p.add_argument("--method",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--reasons",required=True)
    a=p.parse_args()
    config=json.loads((HERE/"configs/study.json").read_text())
    if a.method not in config["methods"]:raise ValueError(a.method)
    out=Path(a.out);reasons=Path(a.reasons)
    if out.exists() or reasons.exists():raise FileExistsError("Frozen predictions exist")
    manifest=json.loads((HERE/"datasets/manifest.json").read_text())
    out.parent.mkdir(parents=True,exist_ok=True);reasons.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as stream, reasons.open("w",encoding="utf-8") as audit:
        for item in manifest["queues"][a.split]:
            row,rs=predict(HERE/"datasets",a.split,item["queue_id"],a.method,config["decision_minute"],config["component_cap"])
            stream.write(json.dumps(row,sort_keys=True)+"\n")
            audit.write(json.dumps({"queue_id":item["queue_id"],"decisions":rs},sort_keys=True)+"\n")
    print(json.dumps({"split":a.split,"method":a.method,"queues":len(manifest["queues"][a.split])}))


if __name__=="__main__":main()
