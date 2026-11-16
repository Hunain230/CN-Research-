"""Evaluator-only train/development diagnostics; locked truth is never opened."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from model import HERE,visible,candidates,lines
from reconstruct import seed_fragments


def write(name,rows):
    rows=list(rows)
    if not rows:raise ValueError(name)
    with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def pair_counts(groups,alerts,truth):
    tp=fp=0
    for group in groups:
        c=Counter(truth[alerts[i]["alert_id"]] for i in group)
        tp+=sum(n*(n-1)//2 for n in c.values())
        fp+=len(group)*(len(group)-1)//2-sum(n*(n-1)//2 for n in c.values())
    return tp,fp


def run():
    cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((HERE/"datasets/manifest.json").read_text())
    freeze=json.loads((HERE/"experiments/development_freeze.json").read_text())
    assert freeze["locked_truth_read"] is False and freeze["locked_predictions_created"] is False
    merge_rows=[];queue_rows=[];hard_rows=[]
    for split in ("train","development"):
        for item in manifest["queues"][split]:
            queue=item["queue_id"]
            alerts=visible(HERE/"datasets",split,queue,cfg["decision_minute"])
            truth={x["alert_id"]:x["incident_id"] for x in lines(HERE/"datasets"/split/"ground_truth_private"/f"{queue}.jsonl")}
            base,_=seed_fragments(alerts,cfg["component_cap"])
            base_tp,base_fp=pair_counts(base,alerts,truth)
            support=candidates(alerts,base)
            negatives=0;shared_context=0;shared_context_only=0
            for row in support:
                left={truth[alerts[i]["alert_id"]] for i in base[row["left"]]}
                right={truth[alerts[i]["alert_id"]] for i in base[row["right"]]}
                different=left.isdisjoint(right)
                if different:negatives+=1
                if different and row["host_agree"] and row["account_agree"]:
                    shared_context+=1
                    if not (row["auth"] and row["flow"]):shared_context_only+=1
            hard_rows.append({"split":split,"queue_id":queue,"candidate_fragment_pairs":len(support),
                 "disjoint_truth_pairs":negatives,"disjoint_shared_host_account":shared_context,
                 "disjoint_shared_context_single_lineage":shared_context_only})
            for method in cfg["methods"]:
                decision=next(x for x in lines(HERE/"experiments/decisions"/f"{split}_{method}.jsonl") if x["queue_id"]==queue)["records"]
                result=next(x for x in json.loads((HERE/"experiments/evaluations"/f"{split}_{method}.json").read_text())["queues"] if x["queue_id"]==queue)
                parent=list(range(len(base)));membership=[Counter(truth[alerts[i]["alert_id"]] for i in g) for g in base]
                def root(x):
                    while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
                    return x
                added_tp=added_fp=accepted=0;reason_counts=Counter()
                for order,d in enumerate(decision):
                    reason_counts[d["decision"]+":"+d["reason"]]+=1
                    if d["decision"]!="accept":continue
                    a,b=root(d["left"]),root(d["right"])
                    if a==b:raise AssertionError("Recorded redundant accept")
                    ca,cb=membership[a],membership[b]
                    tp=sum(ca[i]*cb[i] for i in ca.keys()&cb.keys())
                    fp=sum(ca.values())*sum(cb.values())-tp
                    merge_rows.append({"split":split,"queue_id":queue,"method":method,"order":order,
                         "reason":d["reason"],"auth":d["auth"],"flow":d["flow"],"rare":d["rare"],
                         "sensor_origins":d["sensor_origins"],"source_witnesses":d["source_witnesses"],
                         "premerge_pair_exposure":d["premerge_pair_exposure"],
                         "new_true_pairs":tp,"new_false_pairs":fp})
                    parent[b]=a;membership[a]+=membership[b]
                    accepted+=1;added_tp+=tp;added_fp+=fp
                if base_tp+added_tp!=result["pair_tp"] or base_fp+added_fp!=result["false_grouped_pairs"]:
                    raise AssertionError(f"Pair reconciliation failed {split} {queue} {method}")
                queue_rows.append({"split":split,"queue_id":queue,"method":method,
                    "baseline_seed_true_pairs":base_tp,"baseline_seed_false_pairs":base_fp,
                    "accepted_merges":accepted,"added_true_pairs":added_tp,"added_false_pairs":added_fp,
                    "final_true_pairs":result["pair_tp"],"final_false_pairs":result["false_grouped_pairs"],
                    "recoverable_top20":result["recoverable"],
                    "abstained":sum(v for k,v in reason_counts.items() if k.startswith("abstain:")),
                    "rejected":sum(v for k,v in reason_counts.items() if k.startswith("reject:"))})
    write("PHASE19_MERGE_PAIR_AUDIT.csv",merge_rows)
    write("PHASE19_QUEUE_RECONCILIATION.csv",queue_rows)
    write("PHASE19_HARD_NEGATIVE_AUDIT.csv",hard_rows)
    baseline=cfg["baseline_method"]
    readiness={split:{"queues":len(manifest["queues"][split]),
       "queues_with_recoverable":sum(x["recoverable_top20"]>0 for x in queue_rows if x["split"]==split and x["method"]==baseline),
       "recoverable_top20":sum(x["recoverable_top20"] for x in queue_rows if x["split"]==split and x["method"]==baseline)}
       for split in ("train","development")}
    summary={"baseline_readiness":readiness,
       "development_hard_negatives":{k:sum(x[k] for x in hard_rows if x["split"]=="development") for k in
         ("candidate_fragment_pairs","disjoint_truth_pairs","disjoint_shared_host_account","disjoint_shared_context_single_lineage")},
       "baseline_dev_merge_totals":{k:sum(x[k] for x in queue_rows if x["split"]=="development" and x["method"]==baseline) for k in
         ("accepted_merges","added_true_pairs","added_false_pairs","abstained","rejected")},
       "locked_truth_opened":False,"locked_prediction_count":len(list((HERE/"experiments/predictions").glob("locked_test_*.jsonl"))),
       "source_hashes":{str(p.relative_to(HERE.parents[1])):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          (HERE/"reconstruct.py",HERE/"model.py",HERE/"configs/study.json",HERE/"METRIC_AND_ACCEPTANCE_CONTRACT.md")}}
    (HERE/"PHASE19_ANALYSIS_SUMMARY.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":run()
