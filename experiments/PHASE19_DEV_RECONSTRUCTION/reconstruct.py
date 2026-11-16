"""Label-blind C-stage redesign with source lineage, context, and pair exposure."""
import json
import time
from collections import Counter,defaultdict
from pathlib import Path
from model import HERE,visible,candidates


def seed_fragments(alerts,cap=100):
    n=len(alerts);parent=list(range(n));size=[1]*n;decisions=Counter()
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def context(r):
        ids=[i for i in range(n) if root(i)==r]
        return ({alerts[i]["host"] for i in ids if alerts[i]["host"]},
                {alerts[i]["account"] for i in ids if alerts[i]["account"]})
    def join(i,j,field):
        a,b=root(i),root(j)
        if a==b:return
        if size[a]+size[b]>cap:
            decisions["seed_cap_reject"]+=1;return
        if field=="process_ref":
            ha,ua=context(a);hb,ub=context(b)
            if not (ha and hb and ha&hb and ua and ub and ua&ub):
                decisions["seed_context_abstain"]+=1;return
        parent[b]=a;size[a]+=size[b];decisions[f"seed_{field}_accept"]+=1
    for field in ("source_id","transaction_ref","process_ref"):
        index=defaultdict(list)
        for i,a in enumerate(alerts):
            if a.get(field):index[a[field]].append(i)
        for indices in index.values():
            for j in indices[1:]:join(indices[0],j,field)
    groups=defaultdict(list)
    for i in range(n):groups[root(i)].append(i)
    return list(groups.values()),dict(decisions)


def group_rank(groups,alerts):
    def score(group):
        items={alerts[i]["source_id"]:alerts[i] for i in group}.values()
        values=list(items)
        return (1.2*max((x["severity"] or 1) for x in values)+
                .7*max((x["asset_criticality"] or 1) for x in values)+
                .55*len({x["event_type"] for x in values if x["event_type"]})+
                .1*min(len(values),10))
    return sorted(groups,key=lambda g:(-score(g),min(alerts[i]["alert_id"] for i in g)))


def reconstruct(alerts,method,cap=100):
    if method not in ("dual","dual_plus_rare_guarded","dual_plus_rare"):
        raise ValueError(method)
    base,seed_decisions=seed_fragments(alerts,cap)
    proposals=candidates(alerts,base)
    parent=list(range(len(base)));size=[len(g) for g in base]
    decisions=Counter(seed_decisions);audit=[]
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def context(r):
        ids=[i for g in range(len(base)) if root(g)==r for i in base[g]]
        return ({alerts[i]["host"] for i in ids if alerts[i]["host"]},
                {alerts[i]["account"] for i in ids if alerts[i]["account"]})
    ranked=sorted(proposals,key=lambda x:(-int(x["auth"] and x["flow"]),-x["source_witnesses"],
                                       x["left"],x["right"]))
    for row in ranked:
        a,b=root(row["left"]),root(row["right"])
        if a==b:continue
        exposure=size[a]*size[b]
        dual=(row["auth"] and row["flow"] and row["sensor_origins"]>=3 and
              row["source_witnesses"]>=4 and row["rare"])
        single=(row["rare"] and row["sensor_origins"]>=2 and row["source_witnesses"]>=2)
        ha,ua=context(a);hb,ub=context(b)
        context_ok=bool(ha and hb and ha&hb and ua and ub and ua&ub)
        reason="";state=""
        if size[a]+size[b]>cap:state,reason="reject","cap"
        elif not context_ok:state,reason="abstain","missing_or_conflicting_context"
        elif dual:state,reason="accept","dual_lineage"
        elif method=="dual":state,reason="abstain","dual_lineage_required"
        elif single and method=="dual_plus_rare_guarded" and exposure>250:
            state,reason="abstain","pair_exposure_over_250"
        elif single:state,reason="accept","rare_single_lineage"
        else:state,reason="abstain","insufficient_lineage"
        decisions[f"{state}_{reason}"]+=1
        audit.append({"left":row["left"],"right":row["right"],"decision":state,"reason":reason,
                      "auth":int(row["auth"]),"flow":int(row["flow"]),
                      "rare":int(row["rare"]),"sensor_origins":row["sensor_origins"],
                      "source_witnesses":row["source_witnesses"],"premerge_pair_exposure":exposure})
        if state=="accept":parent[b]=a;size[a]+=size[b]
    merged=defaultdict(list)
    for g,group in enumerate(base):merged[root(g)].extend(group)
    result=group_rank(list(merged.values()),alerts)
    assert sum(map(len,result))==len(alerts) and max(map(len,result),default=0)<=cap
    return result,len(proposals),dict(decisions),audit,base


def predict(data,split,queue,method,cutoff,cap):
    start=time.perf_counter();alerts=visible(data,split,queue,cutoff)
    groups,candidates_count,decisions,audit,base=reconstruct(alerts,method,cap)
    row={"queue_id":queue,"split":split,"method":method,"ranker":"progression",
         "cutoff":cutoff,"eligible_alert_ids":[a["alert_id"] for a in alerts],
         "groups_ranked":[[alerts[i]["alert_id"] for i in group] for group in groups],
         "candidate_pairs":candidates_count,"decisions":decisions,
         "runtime_seconds":time.perf_counter()-start}
    return row,audit,base,alerts
