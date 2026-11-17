"""Evaluator-only Phase 26 v2 reporting after development prediction freeze."""
import csv
import hashlib
import json
import random
import shutil
import sys
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
V=HERE/"v2"
sys.path.insert(0,str(V))
from predict import get_snapshot,reconstruct,visible_receipts,rows  # noqa: E402


def read_csv(path):
    with Path(path).open(newline="",encoding="utf-8") as stream:return list(csv.DictReader(stream))


def write_csv(path,values):
    values=list(values)
    with Path(path).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(values[0]))
        writer.writeheader();writer.writerows(values)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same_group(groups,a,b):return any(a in group and b in group for group in groups)


def delay_stress(predictions,manifest):
    lookup={(x["queue_id"],x["rule"],x["ranker"]):x for x in predictions}
    result=[]
    patterns=("before_cutoff","exact_cutoff","one_after","much_later","never",
              "correlated_false_receipts")
    for item in manifest["queues"]["development"]:
        q=item["queue_id"]
        now=get_snapshot("development",q,100)
        later=get_snapshot("development",q,150)
        later_receipts=visible_receipts("development",q)
        for rule in json.loads((V/"config.json").read_text())["rules"]:
            pred=lookup[q,rule,"progression"]
            future_groups,_,_=reconstruct(later.alerts,rule,receipts=later_receipts,
                states=later.states,snapshot_hash=later.sha256,decision_minute=150)
            for pair,pattern in enumerate(patterns):
                left=f"{q}_benign_{2*pair:03d}_a0"
                right=f"{q}_benign_{2*pair+1:03d}_a0"
                if pair==5:right=f"{q}_benign_011_a0"
                if left not in {a["alert_id"] for a in now.alerts} or right not in {a["alert_id"] for a in now.alerts}:
                    continue
                merged=same_group(pred["groups_ranked"],left,right)
                future_merged=same_group(future_groups,left,right)
                result.append({"queue_id":q,"rule":rule,"pattern":pattern,
                               "left_alert":left,"right_alert":right,
                               "left_host_state_at_100":now.states[left,"host"],
                               "right_host_state_at_100":now.states[right,"host"],
                               "right_host_state_at_150":later.states.get((right,"host"),"alert_unavailable"),
                               "merged_at_100":merged,"merged_with_later_evidence":future_merged,
                               "future_evidence_changes_decision":merged!=future_merged,
                               "new_false_pair_at_100":int(merged),
                               "decision_minute":100,"snapshot_sha256":now.sha256})
    return result


def replay_skip_all(decision_rows,split="development"):
    output=[]
    for row in decision_rows:
        if row["rule"] not in ("orthogonal_veto","pit_direct","pit_selective"):continue
        q=row["queue_id"]
        truth={x["alert_id"]:x["incident_id"] for x in rows(
            V/"datasets"/split/"ground_truth_private"/f"{q}.jsonl")}
        actions=[(i,d) for i,d in enumerate(row["decisions"]) if d["decision"]=="accept"]
        alerts={a for _,d in actions for a in d["left"]+d["right"]}
        def replay(skip):
            parent={a:a for a in alerts}
            def root(a):
                while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
                return a
            for order,d in actions:
                if order==skip:continue
                a,b=root(d["left"][0]),root(d["right"][0])
                if a!=b:parent[b]=a
            groups=defaultdict(Counter)
            for a in alerts:groups[root(a)][truth[a]]+=1
            return sum(sum(c.values())*(sum(c.values())-1)//2-
                       sum(v*(v-1)//2 for v in c.values()) for c in groups.values())
        full=replay(None)
        for order,d in actions:
            skipped=replay(order)
            output.append({"queue_id":q,"rule":row["rule"],"order":order,
                           "reason":d["reason"],"original_final_false_pairs":full,
                           "skip_final_false_pairs":skipped,"pairs_avoided":full-skipped,
                           "premerge_pair_exposure":d["premerge_pair_exposure"]})
    return output


def bootstrap(queue_rows,rule,ranker,rounds=2000):
    data=[x for x in queue_rows if x["rule"]==rule and x["ranker"]==ranker]
    rng=random.Random(260426)
    answer={}
    for field,denom in (("recoverable",20),("recall20_count",20),("p10_count",10)):
        vals=sorted(sum(int(x[field]) for x in rng.choices(data,k=len(data)))/(denom*len(data))
                    for _ in range(rounds))
        answer[field]=[vals[49],vals[1949]]
    return answer


def main():
    freeze=json.loads((V/"freeze_manifest.json").read_text())
    for name,expected in freeze["hashes"].items():assert digest(V/name)==expected
    assert not (V/"datasets/locked_test").exists()
    manifest=json.loads((V/"datasets/manifest.json").read_text())
    cfg=json.loads((V/"config.json").read_text())
    for name in ("PHASE26_EXPERIMENT_COMPARISON.csv","PHASE26_QUEUE_METRICS.csv",
                 "PHASE26_UNION_PAIR_AUDIT.csv","PHASE26_FAILURE_CASCADE.csv",
                 "PHASE26_RECONSTRUCTION_AUDIT.csv"):
        shutil.copyfile(V/name,HERE/name)
    predictions=rows(V/"development_predictions.jsonl")
    decisions=rows(V/"development_decisions.jsonl")
    stress=delay_stress(predictions,manifest)
    write_csv(HERE/"PHASE26_DELAY_STRESS_RESULTS.csv",stress)
    counterfactual=replay_skip_all(decisions)
    write_csv(HERE/"PHASE26_COMPONENT_COUNTERFACTUAL.csv",counterfactual)

    availability=[];states=Counter()
    for split,items in manifest["queues"].items():
        for item in items:
            q=item["queue_id"]
            snap=get_snapshot(split,q)
            states.update(snap.states.values())
            raw=rows(V/"datasets"/split/"alert_headers"/f"{q}.jsonl")
            availability.append({"split":split,"queue_id":q,"raw_alerts":len(raw),
                                 "visible_alerts":len(snap.alerts),"late_alerts":len(raw)-len(snap.alerts),
                                 "visible_receipts":len(visible_receipts(split,q)),
                                 "snapshot_sha256":snap.sha256,"decision_minute":snap.cutoff,
                                 **{state:sum(x==state for x in snap.states.values()) for state in
                                    ("SUPPORTED","CONTRADICTED","NOT_YET_AVAILABLE","UNAVAILABLE","UNKNOWN","UNVERIFIED")}})
    write_csv(HERE/"PHASE26_FEATURE_AVAILABILITY_AUDIT.csv",availability)

    incidents=read_csv(V/"PHASE26_RECONSTRUCTION_AUDIT.csv")
    family=[]
    for rule,ranker in (("context","progression"),("orthogonal_veto","blend"),
                        ("pit_selective","blend"),("pit_direct","blend")):
        by_family=defaultdict(Counter);by_mode=defaultdict(Counter)
        for item in manifest["queues"]["development"]:
            q=item["queue_id"]
            pri={x["incident_id"]:x for x in rows(V/"datasets/development/ground_truth_private"/f"{q}_priority.jsonl")}
            faults={x["incident_id"]:x["failure_mode"] for x in rows(V/"datasets/development/faults_private"/f"{q}.jsonl")}
            for x in incidents:
                if x["queue_id"]!=q or x["rule"]!=rule or x["ranker"]!=ranker:continue
                for group,key in ((by_family,pri[x["incident_id"]]["family"]),(by_mode,faults[x["incident_id"]])):
                    group[key]["incidents"]+=1
                    group[key]["recovered"]+=x["status"] in ("recalled","ranking_only")
                    group[key]["recalled"]+=x["status"]=="recalled"
        for category,groups in (("family",by_family),("failure_mode",by_mode)):
            for key,value in groups.items():
                family.append({"rule":rule,"ranker":ranker,"category":category,"value":key,**value})
    write_csv(HERE/"PHASE26_FAMILY_FAILURE_METRICS.csv",family)
    comparisons=read_csv(V/"PHASE26_EXPERIMENT_COMPARISON.csv")
    queues=read_csv(V/"PHASE26_QUEUE_METRICS.csv")
    base=next(x for x in comparisons if x["rule"]=="context" and x["ranker"]=="progression")
    base_q={x["queue_id"]:x for x in queues if x["rule"]=="context" and x["ranker"]=="progression"}
    gates=[]
    for row in comparisons:
        subset=[x for x in queues if x["rule"]==row["rule"] and x["ranker"]==row["ranker"]]
        stress_bad=sum(x["new_false_pair_at_100"] for x in stress if x["rule"]==row["rule"])
        queue_safe=all(int(x["false_grouped_pairs"])<=int(base_q[x["queue_id"]]["false_grouped_pairs"])
                       and int(x["mixed_predicted_groups"])<=int(base_q[x["queue_id"]]["mixed_predicted_groups"])
                       for x in subset)
        passed=(int(row["recall20_count"])>int(base["recall20_count"])
                and int(row["recoverable"])>int(base["recoverable"])
                and float(row["grouped_pair_precision"])>=.9
                and int(row["false_grouped_pairs"])<=int(base["false_grouped_pairs"])
                and int(row["mixed_predicted_groups"])<=int(base["mixed_predicted_groups"])
                and int(row["p10_count"])>=int(base["p10_count"])-1
                and queue_safe and stress_bad==0)
        gates.append({"rule":row["rule"],"ranker":row["ranker"],"passed":passed,
                      "queue_safe":queue_safe,"stress_false_pairs":stress_bad,
                      "recoverable":row["recoverable"],"recall20_count":row["recall20_count"]})
    write_csv(HERE/"PHASE26_GATE_RESULTS.csv",gates)
    hashes={str(p.relative_to(V)):digest(p) for p in sorted((V/"datasets").rglob("*.jsonl"))}
    hashes["datasets/manifest.json"]=digest(V/"datasets/manifest.json")
    (HERE/"dataset_hashes.json").write_text(json.dumps(hashes,indent=2)+"\n")
    summary={"pilot":"v1 opened development diagnostic","authoritative":"v2",
             "eligible_candidates":sum(x["passed"] for x in gates),
             "baseline":base,"stress":{rule:sum(x["new_false_pair_at_100"] for x in stress if x["rule"]==rule)
                        for rule in cfg["rules"]},
             "state_counts":dict(states),
             "bootstrap":{f"{r}/{k}":bootstrap(queues,r,k) for r,k in
                          (("context","progression"),("context","blend"),
                           ("orthogonal_veto","blend"),("pit_selective","blend"))}}
    (HERE/"analysis_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"eligible_candidates":summary["eligible_candidates"],"stress":summary["stress"]},indent=2))


if __name__=="__main__":main()
