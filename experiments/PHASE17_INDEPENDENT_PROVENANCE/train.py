"""Training-only reliability calibration from training-split evaluator truth."""
import json
from collections import Counter
from pathlib import Path
from model import visible,fragments,candidates,lines,HERE


def train():
    out=HERE/"models/reliability.json"
    if out.exists():raise FileExistsError(out)
    cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((HERE/"datasets/manifest.json").read_text())
    bins={}
    total=Counter()
    for item in manifest["queues"]["train"]:
        queue=item["queue_id"]
        alerts=visible(HERE/"datasets","train",queue,cfg["decision_minute"])
        groups=fragments(alerts,cfg["component_cap"])
        truth={x["alert_id"]:x["incident_id"] for x in lines(HERE/"datasets/train/ground_truth_private"/f"{queue}.jsonl")}
        for row in candidates(alerts,groups):
            left={truth[alerts[i]["alert_id"]] for i in groups[row["left"]]}
            right={truth[alerts[i]["alert_id"]] for i in groups[row["right"]]}
            positive=len(left)==len(right)==1 and left==right
            entry=bins.setdefault(row["key"],Counter())
            entry["positive" if positive else "negative"]+=1
            total["positive" if positive else "negative"]+=1
    probabilities={key:(value["positive"]+1)/(sum(value.values())+2) for key,value in bins.items()}
    probabilities["__default__"]=(total["positive"]+1)/(sum(total.values())+2)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"schema":"phase17-reliability-v1","train_queues":len(manifest["queues"]["train"]),
        "counts":{k:dict(v) for k,v in bins.items()},"probabilities":probabilities,
        "total":dict(total),"smoothing":"Beta(1,1) posterior mean"},indent=2))
    print(json.dumps({"bins":len(bins),"total":dict(total)}))


if __name__=="__main__":train()
