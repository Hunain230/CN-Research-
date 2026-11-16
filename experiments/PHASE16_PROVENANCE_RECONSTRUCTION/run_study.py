"""Development-only selection, immutable freeze, then fresh locked-test evaluation."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EVAL=ROOT/"experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"


def call(*args):
    result=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(f"{args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def one(split,method):
    pred=HERE/"experiments/predictions"/f"{split}_{method}.jsonl"
    reasons=HERE/"experiments/decisions"/f"{split}_{method}.jsonl"
    evaluated=HERE/"experiments/evaluations"/f"{split}_{method}.json"
    if not pred.exists():call(HERE/"predict.py","--split",split,"--method",method,"--out",pred,"--reasons",reasons)
    if not evaluated.exists():call(EVAL,"--predictions",pred,"--truth-root",HERE/"datasets"/split/"ground_truth_private","--out",evaluated)
    return json.loads(evaluated.read_text())["summary"]


def write_csv(path,rows):
    rows=list(rows)
    with (HERE/path).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def run():
    cfg=json.loads((HERE/"configs/study.json").read_text())
    dev=[one("development",m) for m in cfg["methods"]]
    base=next(x for x in dev if x["method"]=="process_only")
    for row in dev:
        row["safety_pass"]=(row["grouped_pair_precision"]>=.9 and
            row["false_grouped_pairs"]<=base["false_grouped_pairs"] and
            row["mixed_predicted_groups"]<=base["mixed_predicted_groups"])
        row["target_pass"]=(row["safety_pass"] and row["incident_recall20"]>=.8 and
            row["group_recoverability"]>=.85 and row["p10"]>=.6388)
    eligible=[x for x in dev if x["safety_pass"]]
    selected=max(eligible,key=lambda x:(x["group_recoverability"],x["incident_recall20"],x["p10"],
             -cfg["methods"].index(x["method"]))) if eligible else base
    write_csv("PHASE16_DEVELOPMENT_RESULTS.csv",dev)
    freeze=HERE/"experiments/selection_freeze.json"
    if freeze.exists():raise FileExistsError("Locked test selection already frozen; do not rerun selection")
    frozen={"selected_method":selected["method"],"baseline_method":"process_only",
            "development_results":dev,"locked_test_truth_opened_at_freeze":False,
            "sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
               (HERE/"simulator.py",HERE/"predict.py",HERE/"configs/study.json",
                HERE/"METRIC_AND_SELECTION_CONTRACT.md",EVAL,HERE/"datasets/manifest.json")}}
    freeze.parent.mkdir(parents=True,exist_ok=True)
    freeze.write_text(json.dumps(frozen,indent=2),encoding="utf-8")
    # Evaluate only the predeclared baseline and selected method on new locked test.
    test_base=one("locked_test","process_only")
    test_selected=test_base if selected["method"]=="process_only" else one("locked_test",selected["method"])
    write_csv("PHASE16_LOCKED_TEST_RESULTS.csv",[test_base] if test_selected is test_base else [test_base,test_selected])
    result={"selected_method":selected["method"],"baseline":test_base,"selected":test_selected}
    (HERE/"experiments/locked_test_result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":run()
