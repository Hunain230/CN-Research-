"""Development search, pre-test freeze, then one locked synthetic test evaluation."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
PY=sys.executable
CONFIGS=[("exact","simple"),("exact","progression"),("multi","simple"),
         ("multi","progression"),("multi_v","simple"),("multi_v","progression")]


def call(*args):
    result=subprocess.run([PY,*map(str,args)],cwd=HERE.parents[1],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def evaluate_one(split,method,ranker):
    stem=f"{split}_{method}_{ranker}"
    pred=HERE/"experiments"/"predictions"/f"{stem}.jsonl"
    ev=HERE/"experiments"/"evaluations"/f"{stem}.json"
    if not pred.exists():
        call(HERE/"pipeline.py","--split",split,"--method",method,"--ranker",ranker,"--out",pred)
    if not ev.exists():
        call(HERE/"evaluation/evaluate.py","--predictions",pred,"--truth-root",HERE/"datasets"/split/"ground_truth_private","--out",ev)
    return json.loads(ev.read_text())["summary"]


def write_csv(name,rows):
    rows=list(rows)
    if not rows:raise ValueError(name)
    path=HERE/name
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)


def run():
    results=[evaluate_one("development",m,r) for m,r in CONFIGS]
    baseline=results[0]
    for row in results:
        row["safety_vs_exact_baseline"]=(row["grouped_pair_precision"]>=.9 and
             row["false_grouped_pairs"]<=baseline["false_grouped_pairs"] and
             row["mixed_predicted_groups"]<=baseline["mixed_predicted_groups"])
        row["all_targets"]=(row["safety_vs_exact_baseline"] and row["incident_recall20"]>=.8
             and row["group_recoverability"]>=.85 and row["p10"]>=.6388)
    candidates=[x for x in results if x["safety_vs_exact_baseline"]]
    winners=[x for x in candidates if x["all_targets"]] or candidates
    if winners:
        selected=max(winners,key=lambda x:(x["incident_recall20"] if any(y["all_targets"] for y in winners) else x["group_recoverability"],
                                    x["group_recoverability"],x["incident_recall20"],x["p10"],
                                    -CONFIGS.index((x["method"],x["ranker"]))))
    else:
        selected=baseline
    write_csv("PHASE15_BASELINE_RESULTS.csv",[baseline])
    write_csv("PHASE15_C_STAGE_RESULTS.csv",[x for x in results if x["ranker"]=="simple"])
    write_csv("PHASE15_P_STAGE_RESULTS.csv",[x for x in results if x["method"]=="exact"])
    write_csv("PHASE15_V_STAGE_RESULTS.csv",[x for x in results if x["method"].startswith("multi")])
    write_csv("PHASE15_ABLATION_RESULTS.csv",results)
    frontier=[]
    for x in results:
        dominated=any(y is not x and y["incident_recall20"]>=x["incident_recall20"] and
           y["group_recoverability"]>=x["group_recoverability"] and y["p10"]>=x["p10"] and
           y["grouped_pair_precision"]>=x["grouped_pair_precision"] and
           y["false_grouped_pairs"]<=x["false_grouped_pairs"] and
           y["mixed_predicted_groups"]<=x["mixed_predicted_groups"] and
           (y["incident_recall20"],y["group_recoverability"],y["p10"],y["grouped_pair_precision"],
            y["false_grouped_pairs"],y["mixed_predicted_groups"])!=(x["incident_recall20"],x["group_recoverability"],x["p10"],x["grouped_pair_precision"],x["false_grouped_pairs"],x["mixed_predicted_groups"])
           for y in results)
        if not dominated:frontier.append(x)
    write_csv("PHASE15_PARETO_FRONTIER.csv",frontier)
    freeze=HERE/"experiments"/"selection_freeze.json"
    if not freeze.exists():
        hashes={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
               [HERE/"pipeline.py",HERE/"evaluation/evaluate.py",HERE/"simulator/generate.py",
                HERE/"configs/study.json",HERE/"PHASE15_SIMULATION_DESIGN.md",HERE/"datasets/manifest.json"]}
        freeze.write_text(json.dumps({"selected":{"method":selected["method"],"ranker":selected["ranker"]},
            "development_results":results,"source_sha256":hashes,"locked_test_truth_opened":False},indent=2))
    frozen=json.loads(freeze.read_text())
    if frozen["selected"]!={"method":selected["method"],"ranker":selected["ranker"]}:
        raise ValueError("Development selection changed after freeze")
    # This is the only locked-test truth evaluation for the selected pipeline.
    test_base=evaluate_one("locked_test","exact","simple")
    chosen=frozen["selected"]
    test_selected=test_base if chosen=={"method":"exact","ranker":"simple"} else evaluate_one("locked_test",chosen["method"],chosen["ranker"])
    write_csv("PHASE15_END_TO_END_RESULTS.csv",[test_base,test_selected] if test_selected is not test_base else [test_base])
    # Per-queue, not cherry-picked: gives observed variation across all locked queues.
    ev=HERE/"experiments"/"evaluations"/f"locked_test_{chosen['method']}_{chosen['ranker']}.json"
    qrows=json.loads(ev.read_text())["queues"]
    write_csv("PHASE15_ROBUSTNESS_RESULTS.csv",[{**q,"split":"locked_test",
         "recoverability":q["recoverable"]/20,"recall20":q["recall20_count"]/20,
         "p10":q["p10_count"]/10,
         "pair_precision":q["pair_tp"]/(q["pair_tp"]+q["false_grouped_pairs"]) if q["pair_tp"]+q["false_grouped_pairs"] else 1} for q in qrows])
    print(json.dumps({"development":results,"selected":frozen["selected"],"locked_test_baseline":test_base,"locked_test_selected":test_selected},indent=2))


if __name__=="__main__":run()
