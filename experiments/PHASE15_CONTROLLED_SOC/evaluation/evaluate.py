"""Evaluator-only process. Open truth only after prediction file is frozen."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]


def read_lines(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def evaluate_queue(pred, truth_root):
    queue=pred["queue_id"]
    truth={x["alert_id"]:x for x in read_lines(Path(truth_root)/f"{queue}.jsonl")}
    oracle=read_lines(Path(truth_root)/f"{queue}_priority.jsonl")
    assert len(oracle)==25
    rank={x["incident_id"]:x["priority_rank"] for x in oracle}
    eligible=set(pred["eligible_alert_ids"])
    assert eligible <= set(truth)
    groups=pred["groups_ranked"]
    assert {a for g in groups for a in g}==eligible
    assert sum(map(len,groups))==len(eligible)
    assert max(map(len,groups),default=0)<=100
    sizes=Counter(truth[a]["incident_id"] for a in eligible)
    assert all(sizes[i]>0 for i in rank)
    qualifies=defaultdict(list)
    tp=fp=mixed=0
    for pos,group in enumerate(groups,1):
        counts=Counter(truth[a]["incident_id"] for a in group)
        if len(counts)>1: mixed+=1
        for count in counts.values(): tp+=count*(count-1)//2
        fp+=len(group)*(len(group)-1)//2-sum(c*(c-1)//2 for c in counts.values())
        for incident,hits in counts.items():
            if incident in rank and hits/sizes[incident]>=.8 and hits/len(group)>=.8:
                qualifies[incident].append(pos)
    top20={i for i,r in rank.items() if r<=20}
    recovered={i for i in top20 if i in qualifies}
    recalled={i for i in recovered if min(qualifies[i])<=20}
    top10={i for i,r in rank.items() if r<=10}
    credited=set()
    p10=0
    dcg=0.0
    first=None
    for pos,group in enumerate(groups[:20],1):
        candidates=[i for i,positions in qualifies.items() if pos in positions and i not in credited]
        if candidates:
            incident=min(candidates,key=lambda i:rank[i])
            credited.add(incident)
            if first is None and incident in top20:first=pos
            if pos<=10 and incident in top10:p10+=1
            dcg+=(26-rank[incident])/math.log2(pos+1)
    ideal=sum((26-r)/math.log2(r+1) for r in range(1,21))
    # Candidate edge counts are model diagnostics; true candidate precision is not
    # reconstructible from the current prediction artifact, so do not fabricate it.
    return {"queue_id":queue,"eligible_alerts":len(eligible),"expert_top20":20,
            "recoverable":len(recovered),"recall20_count":len(recalled),"p10_count":p10,
            "ndcg20":dcg/ideal,"mrr":0 if first is None else 1/first,
            "pair_tp":tp,"false_grouped_pairs":fp,"mixed_predicted_groups":mixed,
            "predicted_groups":len(groups),"candidate_pairs":pred["candidate_pairs"],
            "accepted_merges":pred["decisions"].get("accepted",0),
            "rejected_merges":sum(v for k,v in pred["decisions"].items() if k.endswith("rejected")),
            "abstained":pred["decisions"].get("weak_abstained",0),
            "runtime_seconds":pred["runtime_seconds"]}


def evaluate(prediction_path,truth_root,output_path):
    prediction_path=Path(prediction_path)
    output_path=Path(output_path)
    if output_path.exists():raise FileExistsError(output_path)
    if not prediction_path.exists():raise FileNotFoundError(prediction_path)
    predictions=read_lines(prediction_path)
    if not predictions:raise ValueError("empty predictions")
    rows=[evaluate_queue(p,truth_root) for p in predictions]
    sums=Counter()
    for r in rows:
        for k in ("eligible_alerts","expert_top20","recoverable","recall20_count","p10_count",
                  "pair_tp","false_grouped_pairs","mixed_predicted_groups","predicted_groups",
                  "candidate_pairs","accepted_merges","rejected_merges","abstained"):
            sums[k]+=r[k]
    n=len(rows)
    summary={"split":predictions[0]["split"],"method":predictions[0]["method"],
             "ranker":predictions[0]["ranker"],"queues":n,**sums,
             "group_recoverability":sums["recoverable"]/sums["expert_top20"],
             "incident_recall20":sums["recall20_count"]/sums["expert_top20"],
             "p10":sums["p10_count"]/(10*n),
             "ndcg20":sum(r["ndcg20"] for r in rows)/n,
             "mrr":sum(r["mrr"] for r in rows)/n,
             "grouped_pair_precision":sums["pair_tp"]/(sums["pair_tp"]+sums["false_grouped_pairs"]) if sums["pair_tp"]+sums["false_grouped_pairs"] else 1,
             "runtime_seconds":sum(r["runtime_seconds"] for r in rows),
             "prediction_sha256":hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
             "cohort":"controlled_synthetic_not_guide"}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps({"summary":summary,"queues":rows},indent=2),encoding="utf-8")
    print(json.dumps(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--predictions",required=True)
    p.add_argument("--truth-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    evaluate(a.predictions,a.truth_root,a.out)
