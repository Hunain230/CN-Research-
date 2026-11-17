"""Read-only, post-freeze Phase 25 development and holdout reporting."""
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from predict import HERE, features, ranking_score, rows, visible, visible_receipts


def read_csv(name):
    with (HERE/name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(name, values):
    values=list(values)
    with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bootstrap(queue_rows,rule,ranker,rounds=2000):
    sample=[x for x in queue_rows if x["rule"]==rule and x["ranker"]==ranker]
    rng=random.Random(250425)
    result={}
    for field,denom in (("recoverable",20),("recall20_count",20),("p10_count",10)):
        values=sorted(sum(int(x[field]) for x in rng.choices(sample,k=len(sample)))/(denom*len(sample))
                      for _ in range(rounds))
        result[field]=[values[49],values[1949]]
    return result


def incident_audit(predictions,split):
    output=[]
    for pred in predictions:
        q=pred["queue_id"]
        truth={x["alert_id"]:x["incident_id"] for x in rows(
            HERE/"datasets"/split/"ground_truth_private"/f"{q}.jsonl")}
        priorities={x["incident_id"]:x for x in rows(
            HERE/"datasets"/split/"ground_truth_private"/f"{q}_priority.jsonl")}
        eligible=Counter(truth[a] for a in pred["eligible_alert_ids"])
        qualifiers=defaultdict(list)
        best=Counter()
        for pos,group in enumerate(pred["groups_ranked"],1):
            counts=Counter(truth[a] for a in group)
            for inc,hits in counts.items():
                best[inc]=max(best[inc],hits)
                if inc in priorities and hits/eligible[inc]>=.8 and hits/len(group)>=.8:
                    qualifiers[inc].append(pos)
        faults={x["incident_id"]:x["failure_mode"] for x in rows(
            HERE/"datasets"/split/"faults_private"/f"{q}.jsonl")}
        for inc,oracle in priorities.items():
            if oracle["priority_rank"]>20:continue
            positions=qualifiers.get(inc,[])
            if positions:status="recalled" if min(positions)<=20 else "ranking_only"
            elif best[inc]/eligible[inc]<.8:status="incomplete"
            else:status="impure"
            output.append({"split":split,"queue_id":q,"rule":pred.get("rule",pred.get("method")),
                           "ranker":pred["ranker"],"incident_id":inc,"family":oracle["family"],
                           "failure_mode":faults[inc],"eligible_alerts":eligible[inc],
                           "best_overlap":best[inc],"qualifying_position":min(positions) if positions else "",
                           "status":status})
    return output


def main():
    dev_freeze=json.loads((HERE/"freeze_manifest.json").read_text())
    selection=json.loads((HERE/"selection_freeze.json").read_text())
    holdout_freeze=json.loads((HERE/"locked_prediction_freeze.json").read_text())
    for name,expected in dev_freeze["hashes"].items():assert digest(HERE/name)==expected
    for name,expected in selection["hashes"].items():assert digest(HERE/name)==expected
    assert holdout_freeze["prediction_sha256"]==digest(HERE/"locked_predictions.jsonl")
    assert holdout_freeze["decision_sha256"]==digest(HERE/"locked_decisions.jsonl")
    cfg=json.loads((HERE/"config.json").read_text())
    dev_queues=read_csv("PHASE25_QUEUE_METRICS.csv")
    locked_queues=read_csv("locked_queue_metrics.csv")
    locked_base={x["queue_id"]:x for x in locked_queues if x["rule"]=="context" and x["ranker"]=="progression"}
    locked_selected=[x for x in locked_queues if x["rule"]==selection["selected"]["rule"]
                     and x["ranker"]==selection["selected"]["ranker"]]
    queue_violations=[{"queue_id":x["queue_id"],"selected_false_pairs":int(x["false_grouped_pairs"]),
                       "baseline_false_pairs":int(locked_base[x["queue_id"]]["false_grouped_pairs"]),
                       "selected_mixed_groups":int(x["mixed_predicted_groups"]),
                       "baseline_mixed_groups":int(locked_base[x["queue_id"]]["mixed_predicted_groups"])}
                      for x in locked_selected if
                      int(x["false_grouped_pairs"])>int(locked_base[x["queue_id"]]["false_grouped_pairs"]) or
                      int(x["mixed_predicted_groups"])>int(locked_base[x["queue_id"]]["mixed_predicted_groups"])]
    (HERE/"holdout_gate.json").write_text(json.dumps({"queue_safety_pass":not queue_violations,
        "queue_violations":queue_violations,"decision":"NO-GO" if queue_violations else "queue_gate_pass"},indent=2)+"\n")
    dev_incidents=read_csv("PHASE25_RECONSTRUCTION_AUDIT.csv")
    dev_meta={}
    for q in {x["queue_id"] for x in dev_incidents}:
        priority={x["incident_id"]:x["family"] for x in rows(
            HERE/"datasets/development/ground_truth_private"/f"{q}_priority.jsonl")}
        faults={x["incident_id"]:x["failure_mode"] for x in rows(
            HERE/"datasets/development/faults_private"/f"{q}.jsonl")}
        dev_meta[q]=(priority,faults)
    for x in dev_incidents:
        x["family"]=dev_meta[x["queue_id"]][0][x["incident_id"]]
        x["failure_mode"]=dev_meta[x["queue_id"]][1][x["incident_id"]]
    locked_predictions=rows(HERE/"locked_predictions.jsonl")
    locked_incidents=incident_audit(locked_predictions,"locked_test")
    write_csv("PHASE25_HOLDOUT_RECALL_AUDIT.csv",locked_incidents)
    methods=(("context","progression"),(selection["selected"]["rule"],selection["selected"]["ranker"]))
    grouped=[]
    for split,items in (("development",dev_incidents),("locked_test",locked_incidents)):
        for rule,ranker in methods:
            subset=[x for x in items if x["rule"]==rule and x["ranker"]==ranker]
            for category in ("family","failure_mode"):
                keys=sorted({x[category] for x in subset})
                for key in keys:
                    rows_here=[x for x in subset if x[category]==key]
                    grouped.append({"split":split,"rule":rule,"ranker":ranker,"category":category,
                                    "value":key,"incidents":len(rows_here),
                                    "recovered":sum(x["status"] in ("recalled","ranking_only") for x in rows_here),
                                    "recalled":sum(x["status"]=="recalled" for x in rows_here)})
    write_csv("PHASE25_FAMILY_FAILURE_METRICS.csv",grouped)

    availability=[]
    manifests={"train":json.loads((HERE/"datasets/manifest.json").read_text()),
               "development":json.loads((HERE/"datasets/manifest.json").read_text()),
               "locked_test":json.loads((HERE/"datasets/locked_manifest.json").read_text())}
    for split,manifest in manifests.items():
        for item in manifest["queues"][split]:
            q=item["queue_id"]
            raw=rows(HERE/"datasets"/split/"generated_alerts"/f"{q}.jsonl")
            ledger=rows(HERE/"datasets"/split/"field_ledger"/f"{q}.jsonl")
            alert_view=visible(split,q)
            ids={a["alert_id"] for a in alert_view}
            all_receipts=rows(HERE/"datasets"/split/"receiver_receipts"/f"{q}.jsonl")
            receipt_view=visible_receipts(split,q)
            availability.append({"split":split,"queue_id":q,"raw_alerts":len(raw),
                                 "visible_alerts":len(alert_view),"late_alerts":len(raw)-len(alert_view),
                                 "late_fields_on_visible_alerts":sum(x["artifact_id"] in ids and
                                    x["available_minute"]>100 for x in ledger),
                                 "raw_receipts":len(all_receipts),"visible_receipts":len(receipt_view),
                                 "late_receipts":len(all_receipts)-len(receipt_view)})
    write_csv("PHASE25_FEATURE_AVAILABILITY_AUDIT.csv",availability)

    model=json.loads((HERE/"ranker_model.json").read_text())
    rank_rows=[]
    for split,preds in (("development",rows(HERE/"development_predictions.jsonl")),
                        ("locked_test",locked_predictions)):
        for pred in preds:
            rule=pred.get("rule",pred.get("method"))
            if (rule,pred["ranker"]) not in methods:continue
            q=pred["queue_id"]
            lookup={a["alert_id"]:a for a in visible(split,q)}
            truth={x["alert_id"]:x["incident_id"] for x in rows(
                HERE/"datasets"/split/"ground_truth_private"/f"{q}.jsonl")}
            weights=model["linear_weights"] if pred["ranker"]=="linear" else None
            for pos,group in enumerate(pred["groups_ranked"],1):
                v=features(group,lookup)
                rank_rows.append({"split":split,"queue_id":q,"rule":rule,"ranker":pred["ranker"],
                                  "position":pos,"group_size":len(group),
                                  "source_events":len({lookup[a]["source_id"] for a in group}),
                                  "score":round(ranking_score(v,pred["ranker"],weights),6),
                                  "max_severity":v[0],"max_criticality":v[1],
                                  "mean_severity":round(v[2],4),"event_type_count":v[3],
                                  "relation_types":v[5],"time_span_tens":v[6],
                                  "duplicate_fraction":round(v[7],4),
                                  "context_available_fraction":round(v[8],4),
                                  "incident_membership_evaluator_only":json.dumps(Counter(truth[a] for a in group))})
    write_csv("PHASE25_RANKING_AUDIT.csv",rank_rows)

    ci={split:{f"{rule}/{ranker}":bootstrap(queue_data,rule,ranker) for rule,ranker in methods}
        for split,queue_data in (("development",dev_queues),("locked_test",locked_queues))}
    (HERE/"PHASE25_BOOTSTRAP_CI.json").write_text(json.dumps(ci,indent=2)+"\n")
    dataset_hashes={str(path.relative_to(HERE)):digest(path) for path in
                    sorted((HERE/"datasets").rglob("*.jsonl"))}
    dataset_hashes["datasets/manifest.json"]=digest(HERE/"datasets/manifest.json")
    dataset_hashes["datasets/locked_manifest.json"]=digest(HERE/"datasets/locked_manifest.json")
    (HERE/"dataset_hashes.json").write_text(json.dumps(dataset_hashes,indent=2)+"\n")
    dev_summary={str((x["rule"],x["ranker"])):dict(Counter(y["status"] for y in dev_incidents
                  if y["rule"]==x["rule"] and y["ranker"]==x["ranker"])) for x in
                 ({"rule":r,"ranker":k} for r,k in methods)}
    locked_summary={str((r,k)):dict(Counter(y["status"] for y in locked_incidents
                    if y["rule"]==r and y["ranker"]==k)) for r,k in methods}
    (HERE/"analysis_summary.json").write_text(json.dumps({
        "development_cascade":dev_summary,"locked_cascade":locked_summary,
        "bootstrap_ci":ci,"locked_summary":json.loads((HERE/"locked_results.json").read_text())["summary"]},
        indent=2)+"\n")
    print(json.dumps({"development_cascade":dev_summary,"locked_cascade":locked_summary},indent=2))


if __name__=="__main__":main()
