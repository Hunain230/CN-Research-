"""Post-freeze evaluator diagnostics and report generation."""
import csv
import hashlib
import json
import math
import random
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/"datasets"
EXP=HERE/"experiments"


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(x) for x in stream if x.strip()]


def metrics(stem):
    return json.loads((EXP/"evaluations"/f"{stem}.json").read_text())


def write_csv(path,rows):
    rows=list(rows)
    if not rows:raise ValueError(path)
    with (HERE/path).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def main():
    manifest=json.loads((DATA/"manifest.json").read_text())
    freeze=json.loads((EXP/"selection_freeze.json").read_text())
    selected=freeze["selected"]
    base=metrics("locked_test_exact_simple")
    chosen=metrics(f"locked_test_{selected['method']}_{selected['ranker']}")
    dev=[json.loads(p.read_text())["summary"] for p in sorted((EXP/"evaluations").glob("development_*.json"))]
    observations=alerts=degraded=late=duplicates=0
    hashes={}
    families=Counter()
    for split,queues in manifest["splits"].items():
        for q in queues:
            queue=q["queue_id"]
            folder=DATA/split
            source=lines(folder/"source_observations"/f"{queue}.jsonl")
            visible=lines(folder/"generated_alerts"/f"{queue}.jsonl")
            ledger=lines(folder/"evidence_ledger"/f"{queue}.jsonl")
            issues=lines(folder/"degradation"/f"{queue}.jsonl")
            oracle=lines(folder/"ground_truth_private"/f"{queue}_priority.jsonl")
            observations+=len(source);alerts+=len(visible);degraded+=sum(x["reason"]=="missing_source_observation" for x in issues)
            late+=sum(x["evidence_available_minute"]>90 for x in visible)
            duplicates+=len(visible)-len({x["source_id"] for x in visible})
            for row in oracle:families[(split,row["family"])]+=1
            assert len(ledger)==len(visible)
            for p in (folder/"generated_alerts"/f"{queue}.jsonl",folder/"source_observations"/f"{queue}.jsonl",
                      folder/"evidence_ledger"/f"{queue}.jsonl",folder/"ground_truth_private"/f"{queue}.jsonl",
                      folder/"ground_truth_private"/f"{queue}_priority.jsonl"):
                hashes[str(p.relative_to(HERE))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE/"dataset_hashes.json").write_text(json.dumps(hashes,indent=2))
    # Candidate-pair diagnostic: recreate the documented multi route after prediction freeze.
    edge_rows=[]
    for split in ("development",):
        for q in manifest["splits"][split]:
            queue=q["queue_id"]
            a=[x for x in lines(DATA/split/"generated_alerts"/f"{queue}.jsonl") if x["evidence_available_minute"]<=90]
            a.sort(key=lambda x:x["alert_id"])
            truth={x["alert_id"]:x["incident_id"] for x in lines(DATA/split/"ground_truth_private"/f"{queue}.jsonl")}
            buckets=defaultdict(list)
            for i,x in enumerate(a):
                if x["host"] and x["account"]:buckets[(x["host"],x["account"])].append(i)
            cand=set()
            for values in buckets.values():
                values.sort(key=lambda i:a[i]["event_minute"])
                for pos,i in enumerate(values):
                    for j in values[pos+1:]:
                        if a[j]["event_minute"]-a[i]["event_minute"]>18:break
                        if a[i]["source_id"]==a[j]["source_id"]:continue
                        if (a[i]["indicator"] and a[i]["indicator"]==a[j]["indicator"]) or a[i]["event_type"]!=a[j]["event_type"]:
                            cand.add((i,j))
            target=metrics(f"{split}_multi_simple") if split=="development" else None
            if target:
                expected=next(x["candidate_pairs"] for x in target["queues"] if x["queue_id"]==queue)
                assert len(cand)==expected
            tp=sum(truth[a[i]["alert_id"]]==truth[a[j]["alert_id"]] for i,j in cand)
            true_total=sum(v*(v-1)//2 for v in Counter(truth[x["alert_id"]] for x in a).values())
            edge_rows.append({"split":split,"queue_id":queue,"candidate_pairs":len(cand),
                              "true_candidate_pairs":tp,"false_candidate_pairs":len(cand)-tp,
                              "candidate_pair_precision":tp/len(cand) if cand else 1,
                              "candidate_pair_recall":tp/true_total if true_total else 1,
                              "true_pair_denominator":true_total,
                              "status":"evaluator_only_retrospective_diagnostic"})
    write_csv("PHASE15_CANDIDATE_EDGE_DIAGNOSTICS.csv",edge_rows)
    s=chosen["summary"];b=base["summary"]
    # Queue-cluster bootstrap respects within-queue dependence; only 3 queues.
    rng=random.Random(1515)
    q=chosen["queues"]
    bootstrap=[]
    for _ in range(2000):
        sample=[rng.choice(q) for _ in q]
        bootstrap.append((sum(x["recall20_count"] for x in sample)/(20*len(sample)),
                          sum(x["recoverable"] for x in sample)/(20*len(sample)),
                          sum(x["p10_count"] for x in sample)/(10*len(sample))))
    ci=[]
    for col in range(3):
        values=sorted(x[col] for x in bootstrap)
        ci.append((values[49],values[1949]))
    summary={"observations":observations,"alerts":alerts,"missing_observations":degraded,
             "late_alerts":late,"duplicate_alerts":duplicates,
             "families":{f"{k[0]}:{k[1]}":v for k,v in families.items()},
             "selected":selected,"test_baseline":b,"test_selected":s,
             "queue_bootstrap_95pct":{"recall20":ci[0],"recoverability":ci[1],"p10":ci[2]}}
    failure=Counter()
    family_count=defaultdict(Counter)
    selected_pred=EXP/"predictions"/f"locked_test_{selected['method']}_{selected['ranker']}.jsonl"
    for pred in lines(selected_pred):
        queue=pred["queue_id"]
        truth={x["alert_id"]:x["incident_id"] for x in lines(DATA/"locked_test"/"ground_truth_private"/f"{queue}.jsonl")}
        oracle=lines(DATA/"locked_test"/"ground_truth_private"/f"{queue}_priority.jsonl")
        sizes=Counter(truth[a] for a in pred["eligible_alert_ids"])
        parts=defaultdict(list)
        for pos,group in enumerate(pred["groups_ranked"],1):
            counts=Counter(truth[a] for a in group)
            for incident,hits in counts.items():parts[incident].append((pos,hits,len(group)))
        for incident in oracle:
            if incident["priority_rank"]>20:continue
            ident=incident["incident_id"]
            candidates=[x for x in parts[ident] if x[1]/sizes[ident]>=.8]
            pure=[x for x in candidates if x[1]/x[2]>=.8]
            category="incomplete" if not candidates else "impure" if not pure else "ranking_only" if min(x[0] for x in pure)>20 else "success"
            failure[category]+=1
            family_count[incident["family"]][category]+=1
    assert sum(failure.values())==s["expert_top20"]
    assert failure["success"]==s["recall20_count"]
    assert failure["success"]+failure["ranking_only"]==s["recoverable"]
    write_csv("PHASE15_FAILURE_CASCADE.csv",[{"category":k,"count":v,"denominator":s["expert_top20"],
        "fraction":v/s["expert_top20"],"cohort":"controlled_synthetic_locked_test"} for k,v in sorted(failure.items())])
    write_csv("PHASE15_FAMILY_RESULTS.csv",[{"family":family,"top20_labels":sum(counts.values()),
        "recovered_top20":counts["success"],"recoverable":counts["success"]+counts["ranking_only"],
        "incomplete":counts["incomplete"],"impure":counts["impure"]} for family,counts in sorted(family_count.items())])
    summary["failure_cascade"]=dict(failure)
    (HERE/"analysis_summary.json").write_text(json.dumps(summary,indent=2))
    target={"Incident Recall@20":(s["incident_recall20"],.8),
            "Group recoverability":(s["group_recoverability"],.85),
            "P@10":(s["p10"],.6388),
            "Grouped-pair precision":(s["grouped_pair_precision"],.9)}
    status=[{"metric":name,"target":threshold,"observed":observed,
             "gap":max(0,threshold-observed),"pass":observed>=threshold,
             "cohort":"controlled_synthetic_locked_test"} for name,(observed,threshold) in target.items()]
    status.extend([{"metric":"False grouped pairs","target":b["false_grouped_pairs"],
                    "observed":s["false_grouped_pairs"],"gap":max(0,s["false_grouped_pairs"]-b["false_grouped_pairs"]),
                    "pass":s["false_grouped_pairs"]<=b["false_grouped_pairs"],"cohort":"controlled_synthetic_locked_test"},
                   {"metric":"Mixed predicted groups","target":b["mixed_predicted_groups"],
                    "observed":s["mixed_predicted_groups"],"gap":max(0,s["mixed_predicted_groups"]-b["mixed_predicted_groups"]),
                    "pass":s["mixed_predicted_groups"]<=b["mixed_predicted_groups"],"cohort":"controlled_synthetic_locked_test"}])
    write_csv("PHASE15_TARGET_STATUS.csv",status)
    print(json.dumps({"dataset":{k:summary[k] for k in ("observations","alerts","missing_observations","late_alerts","duplicate_alerts")},
                      "ci":summary["queue_bootstrap_95pct"],"target_passes":sum(x["pass"] for x in status)}))


if __name__=="__main__":main()
