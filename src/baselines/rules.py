"""B0 deterministic rule clustering. No severity or label access is implemented."""
from __future__ import annotations
import datetime as dt
from collections import defaultdict

def _time(s):
    x=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None: raise ValueError("rule clustering requires timezone-aware timestamps")
    return x.astimezone(dt.timezone.utc)

def _entities(alert,common):
    result=set()
    for e in alert.get("entities",[]):
        typ=str(e.get("type","")); val=str(e.get("value","" )).strip().casefold()
        if typ and val and val not in common and len(val)>1: result.add((typ,val,e.get("evidence_id","")))
    return result

def candidate_neighbors(alerts,cap=20):
    result={a["alert_key"]:[] for a in alerts}
    for a in alerts:
        t=_time(a["timestamp_utc"])
        same=[(abs((_time(b["timestamp_utc"])-t).total_seconds()),b["alert_key"]) for b in alerts if b["alert_key"]!=a["alert_key"] and b["org_partition_key"]==a["org_partition_key"]]
        result[a["alert_key"]]=[k for _,k in sorted(same,key=lambda z:(z[0],z[1]))[:cap]]
    return result

def cluster(alerts,config):
    keys=[a["alert_key"] for a in alerts]
    if len(set(keys))!=len(keys): raise ValueError("alert keys must be unique in a synthetic snapshot")
    common={str(x).casefold() for x in config["common_entity_values"]}
    cap=config["candidate_cap_per_alert"]; neighbors=candidate_neighbors(alerts,cap)
    bykey={a["alert_key"]:a for a in alerts}; parents={k:k for k in keys}; sizes={k:1 for k in keys}
    def root(x):
        while parents[x]!=x: parents[x]=parents[parents[x]]; x=parents[x]
        return x
    candidates=[]
    for a in alerts:
        for bkey in neighbors[a["alert_key"]]:
            if config["mutual_nearest_only"] and a["alert_key"] not in neighbors[bkey]: continue
            pair=tuple(sorted((a["alert_key"],bkey)))
            if pair not in candidates: candidates.append(pair)
    candidates.sort(key=lambda pair:(abs((_time(bykey[pair[0]]["timestamp_utc"])-_time(bykey[pair[1]]["timestamp_utc"])).total_seconds()),pair))
    decisions=[]
    for ka,kb in candidates:
        a,b=bykey[ka],bykey[kb]
        delta=abs((_time(a["timestamp_utc"])-_time(b["timestamp_utc"])).total_seconds())
        shared=[]
        ea=_entities(a,common); eb=_entities(b,common)
        for ta,va,ida in ea:
            for tb,vb,idb in eb:
                if ta==tb and va==vb: shared.append({"type":ta,"evidence_ids":sorted(x for x in (ida,idb) if x)})
        tech=set(a.get("techniques",[]))&set(b.get("techniques",[]))
        rule=None
        if shared and delta<=config["entity_window_hours"]*3600: rule="shared_entity_48h"
        elif tech and delta<=config["technique_window_hours"]*3600: rule="shared_technique_1h"
        decision="NO_LINK"; reason="no configured rule matched"; refs=[]
        if rule:
            ra,rb=root(ka),root(kb)
            if ra!=rb and sizes[ra]+sizes[rb]>config["max_component_size"]:
                reason="max_component_size_guard"; rule=None
            else:
                decision="LINK"; reason=rule
                if ra!=rb:
                    parents[rb]=ra; sizes[ra]+=sizes[rb]
                refs=sorted({x for sh in shared for x in sh["evidence_ids"]})
                if rule=="shared_technique_1h":
                    chosen=sorted(tech)[0]
                    refs=sorted(set(refs)|set(a.get("technique_evidence",{}).get(chosen,[]))|set(b.get("technique_evidence",{}).get(chosen,[])))
        decisions.append({"alert_a":ka,"alert_b":kb,"decision":decision,"rule":rule or "none","reason":reason,"time_delta_seconds":int(delta),"shared_entity_types":sorted({x["type"] for x in shared}),"evidence_ids":refs,"rule_version":config["version"]})
    components=defaultdict(list)
    for key in sorted(keys): components[root(key)].append(key)
    clusters=sorted([sorted(v) for v in components.values()],key=lambda x:x[0])
    return {"method":"rules","status":"synthetic_plumbing_only","clusters":clusters,"edge_decisions":decisions,"candidate_cap_per_alert":cap,"max_component_size":config["max_component_size"],"severity_status":"unavailable_no_verified_field_or_crosswalk","ranking_runnable":False,"component_priority_scores":None}
