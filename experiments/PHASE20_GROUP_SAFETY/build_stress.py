"""Evaluator-designed development stress; Phase 19 locked data remain sealed."""
import csv
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"PHASE19_DEV_RECONSTRUCTION"))
from model import HERE,lines,visible
from reconstruct import predict

ROOT=HERE.parents[1]
OUT=Path(__file__).resolve().parent/"stress"
EVALUATOR=ROOT/"experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"


def write_lines(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as stream:
        for row in rows:stream.write(json.dumps(row,sort_keys=True)+"\n")


def main():
    if OUT.exists():raise FileExistsError("Stress set already frozen")
    cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((HERE/"datasets/manifest.json").read_text())
    selected=manifest["queues"]["development"]
    injection=[]
    for item in selected:
        q=item["queue_id"]
        source=HERE/"datasets/development"
        target=OUT/"datasets/development"
        for folder,suffix in (("evidence_ledger",""),("field_ledger",""),
                              ("ground_truth_private",""),("ground_truth_private","_priority")):
            src=source/folder/f"{q}{suffix}.jsonl"
            dst=target/folder/f"{q}{suffix}.jsonl"
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
        alerts=lines(source/"generated_alerts"/f"{q}.jsonl")
        observations=lines(source/"source_observations"/f"{q}.jsonl")
        truth={x["alert_id"]:x["incident_id"] for x in lines(source/"ground_truth_private"/f"{q}.jsonl")}
        priority=lines(source/"ground_truth_private"/f"{q}_priority.jsonl")
        visible_alerts=visible(HERE/"datasets","development",q,cfg["decision_minute"])
        chosen=defaultdict(list)
        for a in visible_alerts:
            if a["sensor"] in ("auth","identity") and a["auth_ref"] is not None:
                chosen[(truth[a["alert_id"]],a["transaction_ref"])].append(a)
        available={}
        for (incident,_),rows in chosen.items():
            sensors={x["sensor"] for x in rows}
            if len(sensors)>=2 and incident not in available:
                available[incident]=rows[:2]
        used=set();pairs=[]
        top=[x["incident_id"] for x in priority if x["incident_id"] in available]
        for i in range(0,len(top)-1,2):
            if len(pairs)>=8:break
            a,b=top[i],top[i+1]
            if a!=b:pairs.append((a,b))
        alert_by_id={a["alert_id"]:a for a in alerts}
        source_by_id={x["source_id"]:x for x in observations}
        for idx,(left,right) in enumerate(pairs):
            first=available[left][0]
            host,account=first["host"],first["account"]
            if not host or not account:continue
            pattern=("context_only","auth","network","auth_network")[idx%4]
            ref=f"phase20_stress_{q}_{idx}_auth"
            flow_ref=f"phase20_stress_{q}_{idx}_flow"
            changed=[]
            for incident in (left,right):
                for row in available[incident]:
                    raw=alert_by_id[row["alert_id"]]
                    if pattern in ("auth","auth_network"):
                        raw["auth_ref"]=ref
                        source_by_id[raw["source_id"]]["auth_ref"]=ref
                    changed.append(raw["alert_id"])
            if pattern in ("network","auth_network"):
                flow_rows=[r for r in visible_alerts if truth[r["alert_id"]] in (left,right) and r["flow_ref"]]
                for row in flow_rows:
                    raw=alert_by_id[row["alert_id"]]
                    raw["flow_ref"]=flow_ref
                    source_by_id[raw["source_id"]]["flow_ref"]=flow_ref
                    changed.append(raw["alert_id"])
            for raw in alerts:
                if truth[raw["alert_id"]]==right:
                    raw["host"]=host;raw["account"]=account
                    source_by_id[raw["source_id"]]["host"]=host
                    source_by_id[raw["source_id"]]["account"]=account
            injection.append({"queue_id":q,"left_incident":left,"right_incident":right,
                              "shared_host":host,"shared_account":account,
                              "pattern":pattern,"injected_auth_ref":ref if "auth" in pattern else "",
                              "injected_flow_ref":flow_ref if "network" in pattern else "",
                              "changed_alerts":len(set(changed))})
        write_lines(target/"generated_alerts"/f"{q}.jsonl",alerts)
        write_lines(target/"source_observations"/f"{q}.jsonl",observations)
    if not injection:raise ValueError("No hard negatives constructed")
    (OUT/"datasets/manifest.json").write_text(json.dumps({"queues":{"development":selected},
        "construction":"retrospective_controller-designed_shared_context_and_auth_ref"},indent=2))
    with (OUT/"injections.csv").open("w",newline="",encoding="utf-8") as stream:
        w=csv.DictWriter(stream,fieldnames=list(injection[0]));w.writeheader();w.writerows(injection)
    pred=OUT/"predictions_baseline.jsonl";audit=OUT/"decisions_baseline.jsonl"
    with pred.open("w",encoding="utf-8") as p,audit.open("w",encoding="utf-8") as d:
        for item in selected:
            row,decisions,_,_=predict(OUT/"datasets","development",item["queue_id"],cfg["baseline_method"],
                                      cfg["decision_minute"],cfg["component_cap"])
            p.write(json.dumps(row,sort_keys=True)+"\n")
            d.write(json.dumps({"queue_id":item["queue_id"],"records":decisions},sort_keys=True)+"\n")
    ev=OUT/"evaluation_baseline.json"
    result=subprocess.run([sys.executable,str(EVALUATOR),"--predictions",str(pred),
         "--truth-root",str(OUT/"datasets/development/ground_truth_private"),"--out",str(ev)],
         cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    evaluated=json.loads(ev.read_text())
    original=[]
    for item in selected:
        q=item["queue_id"]
        data=json.loads((HERE/"experiments/evaluations"/f"development_{cfg['baseline_method']}.json").read_text())
        original.append(next(x for x in data["queues"] if x["queue_id"]==q))
    base_fp=sum(x["false_grouped_pairs"] for x in original)
    summary={"classification":"adversarial_development_stress_not_validation",
             "injected_incident_pairs":len(injection),"queues":len(selected),
             "original_false_pairs":base_fp,
             "stress_false_pairs":evaluated["summary"]["false_grouped_pairs"],
             "additional_false_pairs":evaluated["summary"]["false_grouped_pairs"]-base_fp,
             "original_recoverable":sum(x["recoverable"] for x in original),
             "stress_recoverable":evaluated["summary"]["recoverable"]}
    (OUT/"summary_baseline.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=="__main__":main()
