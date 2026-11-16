"""Post-freeze data, decision, calibration and target audit."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from model import HERE,fragments,candidates,lines,visible


def write_csv(path,rows):
    rows=list(rows)
    if not rows:raise ValueError(path)
    with (HERE/path).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run():
    data=HERE/"datasets";cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((data/"manifest.json").read_text())
    hashes={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in data.rglob("*.jsonl")}
    (HERE/"dataset_hashes.json").write_text(json.dumps(hashes,indent=2))
    counts=Counter();split_rows=[]
    for split,queues in manifest["queues"].items():
        local=Counter()
        for item in queues:
            q=item["queue_id"]
            a=lines(data/split/"generated_alerts"/f"{q}.jsonl")
            obs=lines(data/split/"source_observations"/f"{q}.jsonl")
            field=lines(data/split/"field_ledger"/f"{q}.jsonl")
            issues=lines(data/split/"degradation"/f"{q}.jsonl")
            local["alerts"]+=len(a);local["source_observations"]+=len(obs)
            local["field_versions"]+=len(field)
            local["late_alerts"]+=sum(x["evidence_available_minute"]>100 for x in a)
            local["delayed_fields"]+=sum(x["available_minute"]>100 for x in field)
            local["sensor_misses"]+=len(issues)
        counts.update(local)
        split_rows.append({"split":split,"queues":len(queues),"oracle_top20_labels":len(queues)*20,**local})
    write_csv("PHASE17_DATASET_COUNTS.csv",split_rows)
    model=json.loads((HERE/"models/reliability.json").read_text())
    write_csv("PHASE17_CALIBRATION_BINS.csv",[{"signature":key,"positive":value.get("positive",0),
         "negative":value.get("negative",0),"posterior_mean":model["probabilities"][key],
         "split":"train"} for key,value in sorted(model["counts"].items())])
    calibration=[]
    for item in manifest["queues"]["development"]:
        q=item["queue_id"]
        a=visible(data,"development",q,100)
        groups=fragments(a,100)
        truth={x["alert_id"]:x["incident_id"] for x in lines(data/"development/ground_truth_private"/f"{q}.jsonl")}
        for row in candidates(a,groups):
            left={truth[a[i]["alert_id"]] for i in groups[row["left"]]}
            right={truth[a[i]["alert_id"]] for i in groups[row["right"]]}
            y=int(len(left)==len(right)==1 and left==right)
            p=model["probabilities"].get(row["key"],model["probabilities"]["__default__"])
            calibration.append((p,y))
    brier=sum((p-y)**2 for p,y in calibration)/len(calibration)
    ece=0.0
    for low in (0,.2,.4,.6,.8):
        bucket=[(p,y) for p,y in calibration if low<=p<(low+.2 if low<.8 else 1.0000001)]
        if bucket:ece+=len(bucket)/len(calibration)*abs(sum(p for p,y in bucket)/len(bucket)-sum(y for p,y in bucket)/len(bucket))
    # Development-only accepted-link truth audit, never a test selection input.
    decision_rows=[]
    path=HERE/"experiments/decisions/development_t0p8_progression.jsonl"
    for item in lines(path):
        q=item["queue_id"]
        a=visible(data,"development",q,100)
        groups=fragments(a,100)
        truth={x["alert_id"]:x["incident_id"] for x in lines(data/"development/ground_truth_private"/f"{q}.jsonl")}
        local=Counter()
        for d in item["records"]:
            local[d["decision"]]+=1
            if d["decision"]=="accept":
                left={truth[a[i]["alert_id"]] for i in groups[d["left"]]}
                right={truth[a[i]["alert_id"]] for i in groups[d["right"]]}
                local["accepted_pure_same_incident" if len(left)==len(right)==1 and left==right else "accepted_other"]+=1
        decision_rows.append({"queue_id":q,"accepted":local["accept"],"rejected":local["reject"],
            "abstained":local["abstain"],"accepted_pure_same_incident":local["accepted_pure_same_incident"],
            "accepted_other":local["accepted_other"]})
    write_csv("PHASE17_DEVELOPMENT_DECISION_AUDIT.csv",decision_rows)
    result=json.loads((HERE/"experiments/locked_test_result.json").read_text())
    baseline=result["test_baseline"]
    write_csv("PHASE17_TARGET_STATUS.csv",[{"metric":metric,"observed":observed,"target":target,
      "pass":observed<=target if metric in ("False grouped pairs","Mixed predicted groups") else observed>=target,
      "evaluation":"locked_test_selected_baseline"} for metric,observed,target in (
      ("Recall@20",baseline["incident_recall20"],.8),
      ("Recoverability",baseline["group_recoverability"],.85),
      ("P@10",baseline["p10"],.6388),
      ("Pair precision",baseline["grouped_pair_precision"],.9),
      ("False grouped pairs",baseline["false_grouped_pairs"],baseline["false_grouped_pairs"]),
      ("Mixed predicted groups",baseline["mixed_predicted_groups"],baseline["mixed_predicted_groups"])
    )])
    summary={"dataset":split_rows,"training_candidates":model["total"],
       "development_calibration":{"candidate_pairs":len(calibration),"brier":brier,"ece_5bins":ece},
       "development_0p8_decisions":{k:sum(x[k] for x in decision_rows) for k in
           ("accepted","rejected","abstained","accepted_pure_same_incident","accepted_other")},
       "development_selected":result["selected"],"locked_baseline":baseline,"hashes":len(hashes)}
    (HERE/"analysis_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps({"dataset":split_rows,"development_decisions":summary["development_0p8_decisions"],
                      "development_selected":summary["development_selected"]["method"]}))


if __name__=="__main__":run()
