"""Development selection and a single fresh locked-test evaluation."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from model import HERE,predict

ROOT=HERE.parents[1]
EVALUATOR=ROOT/"experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def run_one(split,threshold,ranker,probabilities):
    label="baseline" if threshold==2 else f"t{str(threshold).replace('.','p')}_{ranker}"
    pred=HERE/"experiments/predictions"/f"{split}_{label}.jsonl"
    audit=HERE/"experiments/decisions"/f"{split}_{label}.jsonl"
    ev=HERE/"experiments/evaluations"/f"{split}_{label}.json"
    if not pred.exists():
        cfg=json.loads((HERE/"configs/study.json").read_text())
        manifest=json.loads((HERE/"datasets/manifest.json").read_text())
        pred.parent.mkdir(parents=True,exist_ok=True);audit.parent.mkdir(parents=True,exist_ok=True)
        with pred.open("w",encoding="utf-8") as output,audit.open("w",encoding="utf-8") as decisions:
            for item in manifest["queues"][split]:
                row,reasons,_,_=predict(HERE/"datasets",split,item["queue_id"],threshold,ranker,
                                        probabilities,cfg["decision_minute"],cfg["component_cap"])
                output.write(json.dumps(row,sort_keys=True)+"\n")
                decisions.write(json.dumps({"queue_id":item["queue_id"],"records":reasons},sort_keys=True)+"\n")
    if not ev.exists():
        result=subprocess.run([sys.executable,str(EVALUATOR),"--predictions",str(pred),
             "--truth-root",str(HERE/"datasets"/split/"ground_truth_private"),"--out",str(ev)],
             cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return json.loads(ev.read_text())["summary"]


def write_csv(path,rows):
    rows=list(rows)
    with (HERE/path).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run():
    cfg=json.loads((HERE/"configs/study.json").read_text())
    trained=json.loads((HERE/"models/reliability.json").read_text())
    probs=trained["probabilities"]
    baseline=run_one("development",2,"progression",probs)
    dev=[baseline]
    for threshold in cfg["thresholds"]:
        for ranker in ("progression","sensor_priority"):
            dev.append(run_one("development",threshold,ranker,probs))
    for row in dev:
        row["safety_pass"]=(row["grouped_pair_precision"]>=.9 and
            row["false_grouped_pairs"]<=baseline["false_grouped_pairs"] and
            row["mixed_predicted_groups"]<=baseline["mixed_predicted_groups"])
    eligible=[x for x in dev if x["safety_pass"]]
    selected=max(eligible,key=lambda x:(x["group_recoverability"],x["incident_recall20"],x["p10"],
                                  x["grouped_pair_precision"])) if eligible else baseline
    write_csv("PHASE17_DEVELOPMENT_RESULTS.csv",dev)
    freeze=HERE/"experiments/selection_freeze.json"
    if freeze.exists():raise FileExistsError(freeze)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (HERE/"generate.py",HERE/"model.py",HERE/"train.py",HERE/"run_study.py",
         HERE/"configs/study.json",HERE/"METRIC_AND_SELECTION_CONTRACT.md",
         HERE/"models/reliability.json",HERE/"datasets/manifest.json",EVALUATOR)}
    freeze.write_text(json.dumps({"selected":{"method":selected["method"],"ranker":selected["ranker"]},
        "development_results":dev,"source_sha256":hashes,"locked_truth_opened_at_freeze":False},indent=2))
    test_baseline=run_one("locked_test",2,"progression",probs)
    if selected is baseline:test_selected=test_baseline
    else:
        threshold=float(selected["method"].split("_")[1])
        test_selected=run_one("locked_test",threshold,selected["ranker"],probs)
    write_csv("PHASE17_LOCKED_TEST_RESULTS.csv",[test_baseline] if test_selected is test_baseline else [test_baseline,test_selected])
    result={"selected":selected,"test_baseline":test_baseline,"test_selected":test_selected}
    (HERE/"experiments/locked_test_result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":run()
