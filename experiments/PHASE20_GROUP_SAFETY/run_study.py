"""Development-only comparison and evaluator-only merge reconciliation."""
import csv
import json
import subprocess
import sys
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
P19=HERE.parent/"PHASE19_DEV_RECONSTRUCTION"
ROOT=HERE.parents[1]
sys.path.insert(0,str(P19))
from model import lines,visible
from reconstruct import seed_fragments
from group_guard import predict

CFG=json.loads((P19/"configs/study.json").read_text())
MANIFEST=json.loads((P19/"datasets/manifest.json").read_text())
QUEUES=[x["queue_id"] for x in MANIFEST["queues"]["development"]]
EVALUATOR=ROOT/"experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"

def evaluate(data,predictions,out):
    if out.exists():return json.loads(out.read_text())
    args=[sys.executable,str(EVALUATOR),"--predictions",str(predictions),
          "--truth-root",str(data/"development/ground_truth_private"),"--out",str(out)]
    process=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if process.returncode:raise RuntimeError(process.stdout+process.stderr)
    return json.loads(out.read_text())

def replay(data,decision_rows,evaluation,cohort):
    all_rows=[];seed_fp=0
    for q in QUEUES:
        alerts=visible(data,"development",q,CFG["decision_minute"])
        groups,_=seed_fragments(alerts,CFG["component_cap"])
        truth={r["alert_id"]:r["incident_id"] for r in lines(data/"development/ground_truth_private"/f"{q}.jsonl")}
        parent=list(range(len(groups)))
        membership=[Counter(truth[alerts[i]["alert_id"]] for i in group) for group in groups]
        for c in membership:
            n=sum(c.values());seed_fp+=n*(n-1)//2-sum(v*(v-1)//2 for v in c.values())
        def root(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for order,d in enumerate(decision_rows[q]):
            if d["decision"]!="accept":continue
            a,b=root(d["left"]),root(d["right"])
            if a==b:raise AssertionError("Redundant accepted union")
            x,y=membership[a],membership[b]
            tp=sum(x[k]*y[k] for k in x.keys()&y.keys())
            fp=sum(x.values())*sum(y.values())-tp
            all_rows.append({"cohort":cohort,"queue_id":q,"order":order,"reason":d["reason"],
                             "new_true_pairs":tp,"new_false_pairs":fp,
                             "premerge_pair_exposure":d["premerge_pair_exposure"],
                             "proposed_cumulative_exposure":d.get("proposed_cumulative_exposure",""),
                             "proposed_fragment_count":d.get("proposed_fragment_count","")})
            parent[b]=a;membership[a]+=membership[b]
    assert seed_fp+sum(x["new_false_pairs"] for x in all_rows)==evaluation["summary"]["false_grouped_pairs"]
    return all_rows,seed_fp

def main():
    results={};merge_rows=[]
    for cohort,data in (("ordinary",P19/"datasets"),("stress",HERE/"stress/datasets")):
        predictions=HERE/f"{cohort}_group_guard_predictions.jsonl"
        decisions_path=HERE/f"{cohort}_group_guard_decisions.jsonl"
        if predictions.exists() != decisions_path.exists():raise ValueError("Partial prediction/audit artifacts")
        if predictions.exists():
            decision_rows={r["queue_id"]:r["records"] for r in lines(decisions_path)}
        else:
            decision_rows={}
            with predictions.open("w",encoding="utf-8") as p,decisions_path.open("w",encoding="utf-8") as d:
                for q in QUEUES:
                    row,audit,_,_=predict(data,"development",q,"group_guard",CFG["decision_minute"],CFG["component_cap"])
                    p.write(json.dumps(row,sort_keys=True)+"\n")
                    d.write(json.dumps({"queue_id":q,"records":audit},sort_keys=True)+"\n")
                    decision_rows[q]=audit
        evaluation=evaluate(data,predictions,HERE/f"{cohort}_group_guard_evaluation.json")
        rows,seed_fp=replay(data,decision_rows,evaluation,cohort)
        merge_rows+=rows
        queues=evaluation["queues"]
        false_by_queue={x["queue_id"]:x["false_grouped_pairs"] for x in queues}
        recovered_by_queue={x["queue_id"]:x["recoverable"] for x in queues}
        bad=sorted((x["new_false_pairs"] for x in rows if x["new_false_pairs"]),reverse=True)
        results[cohort]={"summary":evaluation["summary"],"seed_false_pairs":seed_fp,
                         "accepted_unions":len(rows),"false_pair_creating_unions":len(bad),
                         "top_1_union_false_pairs":bad[0] if bad else 0,
                         "top_5_union_false_pairs":sum(bad[:5]),
                         "worst_queue_false_pairs":max(false_by_queue.values()),
                         "queues_with_false_pairs":sum(v>0 for v in false_by_queue.values()),
                         "queues_with_zero_recovery":sum(v==0 for v in recovered_by_queue.values()),
                         "false_pairs_by_queue":false_by_queue,"recoverable_by_queue":recovered_by_queue}
    baseline_sources=(("ordinary_baseline",P19/"datasets",
                       P19/"experiments/evaluations/development_dual_plus_rare_guarded.json",
                       P19/"experiments/decisions/development_dual_plus_rare_guarded.jsonl"),
                      ("stress_baseline",HERE/"stress/datasets",
                       HERE/"stress/evaluation_baseline.json",HERE/"stress/decisions_baseline.jsonl"))
    for name,data,ev_path,dec_path in baseline_sources:
        evaluation=json.loads(ev_path.read_text())
        decisions={r["queue_id"]:r["records"] for r in lines(dec_path)}
        rows,seed_fp=replay(data,decisions,evaluation,name)
        merge_rows+=rows
        by_queue={r["queue_id"]:r["false_grouped_pairs"] for r in evaluation["queues"]}
        bad=sorted((r["new_false_pairs"] for r in rows if r["new_false_pairs"]),reverse=True)
        results[name]={"recoverable":evaluation["summary"]["recoverable"],
                       "false_grouped_pairs":evaluation["summary"]["false_grouped_pairs"],
                       "mixed_predicted_groups":evaluation["summary"]["mixed_predicted_groups"],
                       "seed_false_pairs":seed_fp,"accepted_unions":len(rows),
                       "false_pair_creating_unions":len(bad),
                       "top_1_union_false_pairs":bad[0] if bad else 0,
                       "top_5_union_false_pairs":sum(bad[:5]),
                       "worst_queue_false_pairs":max(by_queue.values()),
                       "queues_with_false_pairs":sum(v>0 for v in by_queue.values()),
                       "false_pairs_by_queue":by_queue}
    with (HERE/"merge_increments.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(merge_rows[0]));writer.writeheader();writer.writerows(merge_rows)
    (HERE/"study_summary.json").write_text(json.dumps(results,indent=2))
    print(json.dumps({k:{x:v for x,v in r.items() if x not in ("false_pairs_by_queue","recoverable_by_queue")}
                      for k,r in results.items()}))

if __name__=="__main__":main()
