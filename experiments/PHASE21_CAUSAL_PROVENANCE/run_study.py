"""Freeze label-blind decisions, then audit causal and pair outcomes separately."""
import csv
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/"datasets_v3"
CUTOFF=100

def read(path):
    with path.open(encoding="utf-8") as stream:return [json.loads(line) for line in stream if line.strip()]

def write(path,rows):
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")

def visible(split,q):
    folder=DATA/split
    alerts=read(folder/"generated_alerts"/f"{q}.jsonl")
    fields={(x["artifact_id"],x["field"]):x for x in read(folder/"field_ledger"/f"{q}.jsonl")}
    result=[]
    for raw in alerts:
        if raw["evidence_available_minute"]>CUTOFF:continue
        row=dict(raw)
        for field in ("fragment_ref","host","account","auth_ref","flow_ref"):
            ledger=fields[(raw["alert_id"],field)]
            if not ledger["permitted"] or ledger["available_minute"]>CUTOFF:row[field]=None
        result.append(row)
    claims=read(folder/"causal_claims"/f"{q}.jsonl")
    claim_fields={(x["artifact_id"],x["field"]):x for x in read(folder/"claim_field_ledger"/f"{q}.jsonl")}
    available=[]
    for raw in claims:
        if raw["receiver_available_minute"]>CUTOFF:continue
        row=dict(raw)
        for field in ("origin_event_id","parent_event_id","left_fragment_ref","right_fragment_ref"):
            ledger=claim_fields[(raw["claim_id"],field)]
            if not ledger["permitted"] or ledger["available_minute"]>CUTOFF:row[field]=None
        available.append(row)
    receipts=read(folder/"receiver_receipts"/f"{q}.jsonl")
    receipt_fields={(x["artifact_id"],x["field"]):x for x in read(folder/"receipt_field_ledger"/f"{q}.jsonl")}
    available_receipts=[]
    for raw in receipts:
        if raw["receiver_available_minute"]>CUTOFF:continue
        row=dict(raw)
        for field in ("origin_event_id","observed_parent_event_ids","observed_fragment_ref"):
            ledger=receipt_fields[(raw["source_record_id"],field)]
            if not ledger["permitted"] or ledger["available_minute"]>CUTOFF:row[field]=None
        available_receipts.append(row)
    return (sorted(result,key=lambda x:x["alert_id"]),
            sorted(available,key=lambda x:x["claim_id"]),available_receipts)

def decide(alerts,claims,rule="causal_roots",receipts=None):
    """Compare causal-root support with a diagnostic sensor-label-only rule."""
    if rule not in ("causal_roots","sensor_labels_only","verified_edges"):raise ValueError(rule)
    receipts=receipts or []
    by_source={r["source_record_id"]:r for r in receipts}
    parent_fragments=defaultdict(set)
    for receipt in receipts:
        if receipt["origin_event_id"] and receipt["observed_fragment_ref"]:
            parent_fragments[receipt["origin_event_id"]].add(receipt["observed_fragment_ref"])
    groups=defaultdict(list)
    for a in alerts:groups[a["fragment_ref"] or a["alert_id"]].append(a)
    keys=sorted(groups);index={k:i for i,k in enumerate(keys)}
    parent=list(range(len(keys)));members=[list(groups[k]) for k in keys]
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    proposed=defaultdict(list);decisions=[]
    for claim in claims:
        l,r=claim["left_fragment_ref"],claim["right_fragment_ref"]
        if not l or not r or l not in index or r not in index:
            decisions.append({"decision":"reject","reason":"unavailable_fragment_or_claim_field",
                              "claim_ids":[claim["claim_id"]],"left":l,"right":r,
                              "premerge_pair_exposure":0})
        elif l==r:
            decisions.append({"decision":"reject","reason":"same_fragment",
                              "claim_ids":[claim["claim_id"]],"left":l,"right":r,
                              "premerge_pair_exposure":0})
        elif rule=="verified_edges" and not (
            claim["source_record_id"] in by_source and
            by_source[claim["source_record_id"]]["sensor"]==claim["sensor"] and
            by_source[claim["source_record_id"]]["origin_event_id"]==claim["origin_event_id"] and
            by_source[claim["source_record_id"]]["observed_fragment_ref"]==r and
            claim["parent_event_id"] in (by_source[claim["source_record_id"]]["observed_parent_event_ids"] or []) and
            l in parent_fragments[claim["parent_event_id"]]):
            decisions.append({"decision":"reject","reason":"source_receipt_does_not_verify_edge",
                              "claim_ids":[claim["claim_id"]],"left":l,"right":r,
                              "premerge_pair_exposure":0})
        else:proposed[tuple(sorted((l,r)))].append(claim)
    for (l,r),rows in sorted(proposed.items()):
        a,b=root(index[l]),root(index[r])
        if a==b:
            decisions.append({"decision":"reject","reason":"already_joined","claim_ids":[x["claim_id"] for x in rows],
                              "left":l,"right":r,"premerge_pair_exposure":0})
            continue
        roots={x["origin_event_id"] for x in rows if x["origin_event_id"]}
        sensors={x["sensor"] for x in rows if x["origin_event_id"]}
        exposure=len(members[a])*len(members[b])
        if len(sensors)>=2 and (rule=="sensor_labels_only" or len(roots)>=2):
            state,reason="accept",("two_sensor_labels" if rule=="sensor_labels_only" else
                                   "verified_distinct_edges" if rule=="verified_edges" else
                                   "distinct_causal_roots_and_sensors")
        else:state,reason="abstain","common_or_single_causal_root"
        decisions.append({"decision":state,"reason":reason,"claim_ids":[x["claim_id"] for x in rows],
                          "left":l,"right":r,"distinct_roots":len(roots),"sensor_processes":len(sensors),
                          "premerge_pair_exposure":exposure})
        if state=="accept":parent[b]=a;members[a]+=members[b]
    final=defaultdict(list)
    for i,k in enumerate(keys):final[root(i)].extend(groups[k])
    ranked=sorted(final.values(),key=lambda g:(-max(x["severity"]+x["asset_criticality"] for x in g),
                                                -len(g),min(x["alert_id"] for x in g)))
    assert sum(map(len,ranked))==len(alerts) and max(map(len,ranked),default=0)<=100
    return [[a["alert_id"] for a in g] for g in ranked],decisions,groups

def audit_queue(split,q,alerts,claims,receipts,groups,decisions,ranked):
    folder=DATA/split
    events={x["event_id"]:x for x in read(folder/"physical_events_private"/f"{q}.jsonl")}
    records={x["source_record_id"]:x for x in read(folder/"sensor_records_private"/f"{q}.jsonl")}
    lineage={x["claim_id"]:x for x in read(folder/"claim_lineage_private"/f"{q}.jsonl")}
    alert_lineage={x["alert_id"]:x for x in read(folder/"alert_lineage_private"/f"{q}.jsonl")}
    truth={x["alert_id"]:x["incident_id"] for x in read(folder/"ground_truth_private"/f"{q}.jsonl")}
    all_alerts=read(folder/"generated_alerts"/f"{q}.jsonl")
    all_claims={x["claim_id"]:x for x in read(folder/"causal_claims"/f"{q}.jsonl")}
    all_receipts={x["source_record_id"]:x for x in read(folder/"receiver_receipts"/f"{q}.jsonl")}
    assert len(records)==sum(len(read(folder/"sensor_process_records_private"/s/f"{q}.jsonl"))
                             for s in ("auth","endpoint","network","identity"))
    for a in all_alerts:
        source=alert_lineage[a["alert_id"]]["source_record_id"]
        assert source==a["source_id"] and source in records
        assert records[source]["origin_event_id"] in events
    for source,receipt in all_receipts.items():
        assert receipt["origin_event_id"]==records[source]["origin_event_id"]
        event=events[receipt["origin_event_id"]]
        assert receipt["observed_parent_event_ids"]==event["parent_event_ids"]
        assert receipt["observed_fragment_ref"]==event["fragment_ref"]
    valid_claims=0;false_claims=0;valid_by_id={}
    for cid,claim in all_claims.items():
        link=lineage[cid];record=records[claim["source_record_id"]]
        assert link["source_record_id"]==record["source_record_id"]
        assert claim["origin_event_id"]==record["origin_event_id"]==link["physical_child_event_id"]
        child=events[claim["origin_event_id"]]
        parent_id=link["physical_parent_event_id"]
        valid=bool(parent_id and parent_id in child["parent_event_ids"] and
                   events[parent_id]["fragment_ref"]==claim["left_fragment_ref"] and
                   child["fragment_ref"]==claim["right_fragment_ref"] and
                   events[parent_id]["incident_id"]==child["incident_id"])
        valid_by_id[cid]=valid
        valid_claims+=valid;false_claims+=not valid
    # Evaluator-only replay. Private labels never enter decide().
    parent={k:k for k in groups};counts={k:Counter(truth[a["alert_id"]] for a in g) for k,g in groups.items()}
    def root(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    increments=[];seed_fp=0
    for c in counts.values():
        n=sum(c.values());seed_fp+=n*(n-1)//2-sum(v*(v-1)//2 for v in c.values())
    for order,d in enumerate(decisions):
        if d["decision"]!="accept":continue
        if d["reason"] in ("distinct_causal_roots_and_sensors","verified_distinct_edges"):
            assert len({all_claims[cid]["origin_event_id"] for cid in d["claim_ids"]})>=2
            assert len({all_claims[cid]["sensor"] for cid in d["claim_ids"]})>=2
        a,b=root(d["left"]),root(d["right"])
        x,y=counts[a],counts[b]
        tp=sum(x[k]*y[k] for k in x.keys()&y.keys())
        fp=sum(x.values())*sum(y.values())-tp
        increments.append({"split":split,"queue_id":q,"order":order,
                           "left":d["left"],"right":d["right"],
                           "new_true_pairs":tp,"new_false_pairs":fp,
                           "all_claims_physically_valid":all(valid_by_id[cid] for cid in d["claim_ids"]),
                           "premerge_pair_exposure":d["premerge_pair_exposure"],
                           "distinct_roots":d["distinct_roots"]})
        counts[a]+=counts[b];parent[b]=a
    final_fp=0;recovered=0
    eligible=Counter(truth[a["alert_id"]] for a in alerts)
    priority={x["incident_id"] for x in read(folder/"ground_truth_private"/f"{q}_priority.jsonl")}
    for group in ranked:
        c=Counter(truth[aid] for aid in group)
        final_fp+=len(group)*(len(group)-1)//2-sum(v*(v-1)//2 for v in c.values())
        for incident,hits in c.items():
            if incident in priority and hits/eligible[incident]>=.8 and hits/len(group)>=.8:recovered+=1
    assert seed_fp+sum(x["new_false_pairs"] for x in increments)==final_fp
    return {"split":split,"queue_id":q,"visible_alerts":len(alerts),"visible_claims":len(claims),
            "valid_causal_claims":valid_claims,"common_mode_claims":false_claims,
            "accepted_unions":len(increments),"abstained_proposals":sum(d["decision"]=="abstain" for d in decisions),
            "accepted_invalid_unions":sum(not x["all_claims_physically_valid"] for x in increments),
            "rejected_proposals":sum(d["decision"]=="reject" for d in decisions),
            "false_pairs":final_fp,"recoverable":recovered,"eligible_incidents":len(priority)},increments

def main():
    manifest=json.loads((DATA/"manifest.json").read_text())
    audit_rows=[];increments=[];frozen={}
    for rule in ("causal_roots","sensor_labels_only","verified_edges"):
        decision_rows=[];predictions=[]
        # Freeze label-blind predictions before opening private truth for this rule.
        for split,queues in manifest["splits"].items():
            for item in queues:
                q=item["queue_id"];alerts,claims,receipts=visible(split,q)
                ranked,decisions,_=decide(alerts,claims,rule,receipts)
                predictions.append({"split":split,"queue_id":q,"eligible_alert_ids":[a["alert_id"] for a in alerts],
                                    "groups_ranked":ranked})
                decision_rows.append({"split":split,"queue_id":q,"records":decisions})
        write(HERE/f"{rule}_predictions.jsonl",predictions)
        write(HERE/f"{rule}_decisions.jsonl",decision_rows)
        frozen[rule]=(predictions,decision_rows)
    freeze={"status":"development_only_predictions_frozen_before_private_audit",
            "phase19_locked_truth_read":False,"phase19_locked_predictions_created":False,
            "dataset_manifest_sha256":hashlib.sha256((DATA/"manifest.json").read_bytes()).hexdigest(),
            "study_code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "prediction_sha256":{rule:hashlib.sha256((HERE/f"{rule}_predictions.jsonl").read_bytes()).hexdigest()
                                 for rule in frozen}}
    (HERE/"freeze_manifest.json").write_text(json.dumps(freeze,indent=2))
    # All method/cohort predictions are now materialized before private lineage/truth reads.
    for rule,(predictions,decision_rows) in frozen.items():
        for pred,drow in zip(predictions,decision_rows):
            split,q=pred["split"],pred["queue_id"]
            alerts,claims,receipts=visible(split,q)
            groups=defaultdict(list)
            for a in alerts:groups[a["fragment_ref"] or a["alert_id"]].append(a)
            row,inc=audit_queue(split,q,alerts,claims,receipts,groups,drow["records"],pred["groups_ranked"])
            row["rule"]=rule
            for x in inc:x["rule"]=rule
            audit_rows.append(row);increments.extend(inc)
    write(HERE/"queue_audit.jsonl",audit_rows)
    with (HERE/"union_pair_increments.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(increments[0]));writer.writeheader();writer.writerows(increments)
    summary={rule:{split:{"queues":sum(r["split"]==split and r["rule"]==rule for r in audit_rows),
                          "incidents":sum(r["eligible_incidents"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "recoverable":sum(r["recoverable"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "false_pairs":sum(r["false_pairs"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "accepted_unions":sum(r["accepted_unions"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "accepted_invalid_unions":sum(r["accepted_invalid_unions"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "abstained_proposals":sum(r["abstained_proposals"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "valid_causal_claims":sum(r["valid_causal_claims"] for r in audit_rows if r["split"]==split and r["rule"]==rule),
                          "common_mode_claims":sum(r["common_mode_claims"] for r in audit_rows if r["split"]==split and r["rule"]==rule)}
                   for split in manifest["splits"]} for rule in ("causal_roots","sensor_labels_only","verified_edges")}
    (HERE/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))

if __name__=="__main__":main()
