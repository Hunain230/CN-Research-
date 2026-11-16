"""Post-freeze incident, provenance, resource, and safety audit."""
import csv
import hashlib
import json
import random
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/"datasets"
EXP=HERE/"experiments"


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def csv_write(name,rows):
    rows=list(rows)
    if not rows:raise ValueError(name)
    with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run():
    manifest=json.loads((DATA/"manifest.json").read_text())
    selected=json.loads((EXP/"selection_freeze.json").read_text())["selected_method"]
    result=json.loads((EXP/"locked_test_result.json").read_text())
    baseline=result["baseline"];score=result["selected"]
    assert selected=="lineage_one_context_v"
    source_hashes={}
    for path in DATA.rglob("*.jsonl"):
        source_hashes[str(path.relative_to(HERE))]=hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE/"dataset_hashes.json").write_text(json.dumps(source_hashes,indent=2))
    predictions=lines(EXP/"predictions"/f"locked_test_{selected}.jsonl")
    statuses=[];decision_rows=[];families=defaultdict(Counter);events=Counter()
    for pred in predictions:
        queue=pred["queue_id"]
        source=lines(DATA/"locked_test/source_observations"/f"{queue}.jsonl")
        alerts=lines(DATA/"locked_test/generated_alerts"/f"{queue}.jsonl")
        ledger=lines(DATA/"locked_test/evidence_ledger"/f"{queue}.jsonl")
        degradation=lines(DATA/"locked_test/degradation"/f"{queue}.jsonl")
        events.update({"source_observations":len(source),"alerts":len(alerts),
                       "late_alerts":sum(a["evidence_available_minute"]>100 for a in alerts),
                       "missing_observations":sum(x["reason"]=="missing_observation" for x in degradation),
                       "duplicate_alerts":len(alerts)-len({a["source_id"] for a in alerts})})
        assert len(ledger)==len(alerts)
        truth={x["alert_id"]:x["incident_id"] for x in lines(DATA/"locked_test/ground_truth_private"/f"{queue}.jsonl")}
        oracle=lines(DATA/"locked_test/ground_truth_private"/f"{queue}_priority.jsonl")
        eligible=set(pred["eligible_alert_ids"])
        sizes=Counter(truth[a] for a in eligible)
        groups=pred["groups_ranked"]
        parts=defaultdict(list)
        for pos,group in enumerate(groups,1):
            counts=Counter(truth[a] for a in group)
            for incident,hits in counts.items():parts[incident].append((pos,hits,len(group)))
        for item in oracle:
            if item["priority_rank"]>20:continue
            incident=item["incident_id"]
            complete=[x for x in parts[incident] if x[1]/sizes[incident]>=.8]
            pure=[x for x in complete if x[1]/x[2]>=.8]
            state="incomplete" if not complete else "impure" if not pure else "ranking_only" if min(x[0] for x in pure)>20 else "success"
            statuses.append({"queue_id":queue,"incident_id":incident,"family":item["family"],
                             "eligible_alerts":sizes[incident],"fragment_count":len(parts[incident]),
                             "best_overlap":max((x[1] for x in parts[incident]),default=0),"status":state})
            families[item["family"]][state]+=1
        decisions=lines(EXP/"decisions"/f"locked_test_{selected}.jsonl")
        record=next(x for x in decisions if x["queue_id"]==queue)
        counts=Counter(x["decision"]+":"+x["reason"] for x in record["decisions"])
        accepted=[x for x in record["decisions"] if x["decision"]=="accept" and x["reason"]=="lineage"]
        true=sum(truth[x["left"]]==truth[x["right"]] for x in accepted)
        decision_rows.append({"queue_id":queue,"lineage_accepted":len(accepted),
                              "lineage_true_endpoint":true,"lineage_false_endpoint":len(accepted)-true,
                              "context_abstain":counts["abstain:lineage_without_host_and_account_agreement"],
                              "insufficient_lineage_abstain":counts["abstain:insufficient_independent_lineage"],
                              "contradiction_reject":counts["reject:host_and_account_conflict"],
                              "all_decision_records":len(record["decisions"])})
    assert len(statuses)==480
    counts=Counter(x["status"] for x in statuses)
    assert counts["success"]==score["recall20_count"]
    assert counts["success"]+counts["ranking_only"]==score["recoverable"]
    csv_write("PHASE16_INCIDENT_FAILURES.csv",statuses)
    csv_write("PHASE16_DECISION_AUDIT.csv",decision_rows)
    csv_write("PHASE16_FAMILY_RESULTS.csv",[{"family":f,"top20":sum(c.values()),
        "success":c["success"],"ranking_only":c["ranking_only"],"incomplete":c["incomplete"],
        "impure":c["impure"]} for f,c in sorted(families.items())])
    target=[("Recall@20",score["incident_recall20"],.8),
            ("Recoverability",score["group_recoverability"],.85),
            ("P@10",score["p10"],.6388),
            ("Pair precision",score["grouped_pair_precision"],.9),
            ("False grouped pairs",score["false_grouped_pairs"],baseline["false_grouped_pairs"]),
            ("Mixed predicted groups",score["mixed_predicted_groups"],baseline["mixed_predicted_groups"])]
    csv_write("PHASE16_TARGET_STATUS.csv",[{"metric":name,"observed":value,"target":threshold,
        "pass":value<=threshold if name in ("False grouped pairs","Mixed predicted groups") else value>=threshold,
        "gap":max(0,value-threshold) if name in ("False grouped pairs","Mixed predicted groups") else max(0,threshold-value)}
        for name,value,threshold in target])
    rng=random.Random(1630)
    q=json.loads((EXP/"evaluations"/f"locked_test_{selected}.json").read_text())["queues"]
    boot=[]
    for _ in range(3000):
        sample=[rng.choice(q) for _ in q]
        boot.append((sum(x["recoverable"] for x in sample)/(20*len(sample)),
                     sum(x["recall20_count"] for x in sample)/(20*len(sample)),
                     sum(x["p10_count"] for x in sample)/(10*len(sample))))
    ci={}
    for i,name in enumerate(("recoverability","recall20","p10")):
        values=sorted(x[i] for x in boot);ci[name]=[values[74],values[2924]]
    summary={"selected":selected,"baseline":baseline,"selected_metrics":score,
             "failure_counts":dict(counts),"decision_counts":dict(Counter({k:sum(r[k] for r in decision_rows) for k in
                 ("lineage_accepted","lineage_true_endpoint","lineage_false_endpoint","context_abstain",
                  "insufficient_lineage_abstain","contradiction_reject")})),
             "data_counts":dict(events),"queue_cluster_bootstrap_95pct":ci,
             "hash_count":len(source_hashes)}
    (HERE/"analysis_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps({"failure_counts":summary["failure_counts"],"decision_counts":summary["decision_counts"],
                      "data_counts":summary["data_counts"],"ci":ci}))


if __name__=="__main__":run()
