"""Train/development only. Never opens or evaluates locked truth."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from reconstruct import HERE,predict

ROOT=HERE.parents[1]
EVALUATOR=ROOT/"experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"


def one(split,method):
    pred=HERE/"experiments/predictions"/f"{split}_{method}.jsonl"
    decisions=HERE/"experiments/decisions"/f"{split}_{method}.jsonl"
    ev=HERE/"experiments/evaluations"/f"{split}_{method}.json"
    cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((HERE/"datasets/manifest.json").read_text())
    if not pred.exists():
        pred.parent.mkdir(parents=True,exist_ok=True);decisions.parent.mkdir(parents=True,exist_ok=True)
        with pred.open("w",encoding="utf-8") as output,decisions.open("w",encoding="utf-8") as log:
            for item in manifest["queues"][split]:
                row,audit,_,_=predict(HERE/"datasets",split,item["queue_id"],method,
                                      cfg["decision_minute"],cfg["component_cap"])
                output.write(json.dumps(row,sort_keys=True)+"\n")
                log.write(json.dumps({"queue_id":item["queue_id"],"records":audit},sort_keys=True)+"\n")
    if not ev.exists():
        command=[sys.executable,str(EVALUATOR),"--predictions",str(pred),
                 "--truth-root",str(HERE/"datasets"/split/"ground_truth_private"),"--out",str(ev)]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return json.loads(ev.read_text())["summary"],json.loads(ev.read_text())["queues"]


def write_csv(name,rows):
    rows=list(rows)
    with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)


def run():
    cfg=json.loads((HERE/"configs/study.json").read_text())
    methods=cfg["methods"]
    all_results={};queue_metrics={}
    for split in ("train","development"):
        all_results[split]=[]
        for method in methods:
            summary,queues=one(split,method)
            all_results[split].append(summary)
            queue_metrics[(split,method)]=queues
    baseline=next(x for x in all_results["development"] if x["method"]==cfg["baseline_method"])
    train_base=next(x for x in all_results["train"] if x["method"]==cfg["baseline_method"])
    readiness=(train_base["grouped_pair_precision"]>=.9 and baseline["grouped_pair_precision"]>=.9 and
               all(q["recoverable"]>=1 for q in queue_metrics[("train",cfg["baseline_method"])]) and
               all(q["recoverable"]>=1 for q in queue_metrics[("development",cfg["baseline_method"])]) )
    for split in all_results:
        for row in all_results[split]:
            ref=train_base if split=="train" else baseline
            row["baseline_ready"] = readiness
            row["development_acceptance"]=(split=="development" and readiness and
                row["method"]!=cfg["baseline_method"] and
                row["group_recoverability"]>ref["group_recoverability"] and
                row["grouped_pair_precision"]>=.9 and
                row["false_grouped_pairs"]<=ref["false_grouped_pairs"] and
                row["mixed_predicted_groups"]<=ref["mixed_predicted_groups"])
    write_csv("PHASE19_TRAIN_RESULTS.csv",all_results["train"])
    write_csv("PHASE19_DEVELOPMENT_RESULTS.csv",all_results["development"])
    accepted=[x for x in all_results["development"] if x["development_acceptance"]]
    selected=max(accepted,key=lambda x:(x["group_recoverability"],x["incident_recall20"],x["p10"])) if accepted else None
    freeze=HERE/"experiments/development_freeze.json"
    if freeze.exists():raise FileExistsError(freeze)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
       (HERE/"generate.py",HERE/"model.py",HERE/"reconstruct.py",HERE/"run_development.py",
        HERE/"configs/study.json",HERE/"METRIC_AND_ACCEPTANCE_CONTRACT.md",
        HERE/"datasets/manifest.json",EVALUATOR)}
    freeze.write_text(json.dumps({"baseline_ready":readiness,"selected_candidate":selected["method"] if selected else None,
      "train_results":all_results["train"],"development_results":all_results["development"],
      "source_sha256":hashes,"locked_truth_read":False,"locked_predictions_created":False},indent=2))
    print(json.dumps({"baseline_ready":readiness,"selected":selected["method"] if selected else None,
                      "train_baseline":train_base,"development_baseline":baseline},indent=2))


if __name__=="__main__":run()
