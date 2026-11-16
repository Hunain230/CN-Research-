"""Development diagnostic: one verified edge when corroborating receipts are missing."""
from collections import defaultdict

def decide_partial(alerts,claims,receipts):
    by_source={r["source_record_id"]:r for r in receipts}
    parent_fragments=defaultdict(set)
    for r in receipts:
        if r["origin_event_id"] and r["observed_fragment_ref"]:
            parent_fragments[r["origin_event_id"]].add(r["observed_fragment_ref"])
    groups=defaultdict(list)
    for alert in alerts:groups[alert["fragment_ref"] or alert["alert_id"]].append(alert)
    parent={k:k for k in groups};members={k:list(v) for k,v in groups.items()}
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    proposed=defaultdict(list);decisions=[]
    for claim in claims:
        left,right=claim["left_fragment_ref"],claim["right_fragment_ref"]
        if not left or not right or left not in groups or right not in groups or left==right:
            decisions.append({"decision":"reject","reason":"unavailable_or_same_fragment",
                              "claim_ids":[claim["claim_id"]],"left":left,"right":right,
                              "premerge_pair_exposure":0})
            continue
        r=by_source.get(claim["source_record_id"])
        valid=bool(r and r["sensor"]==claim["sensor"] and
                   r["origin_event_id"]==claim["origin_event_id"] and
                   r["observed_fragment_ref"]==right and
                   claim["parent_event_id"] in (r["observed_parent_event_ids"] or []) and
                   left in parent_fragments[claim["parent_event_id"]])
        if not valid:
            decisions.append({"decision":"reject","reason":"source_receipt_does_not_verify_edge",
                              "claim_ids":[claim["claim_id"]],"left":left,"right":right,
                              "premerge_pair_exposure":0})
        else:proposed[tuple(sorted((left,right)))].append(claim)
    for (left,right),rows in sorted(proposed.items()):
        a,b=root(left),root(right)
        if a==b:continue
        roots={x["origin_event_id"] for x in rows}
        sensors={x["sensor"] for x in rows}
        exposure=len(members[a])*len(members[b])
        decisions.append({"decision":"accept","reason":"single_verified_edge_diagnostic",
                          "claim_ids":[x["claim_id"] for x in rows],"left":left,"right":right,
                          "distinct_roots":len(roots),"sensor_processes":len(sensors),
                          "premerge_pair_exposure":exposure})
        parent[b]=a;members[a]+=members[b]
    final=defaultdict(list)
    for key,group in groups.items():final[root(key)].extend(group)
    ranked=sorted(final.values(),key=lambda g:(-max(x["severity"]+x["asset_criticality"] for x in g),
                                               -len(g),min(x["alert_id"] for x in g)))
    assert sum(map(len,ranked))==len(alerts) and max(map(len,ranked),default=0)<=100
    return [[x["alert_id"] for x in group] for group in ranked],decisions,groups
