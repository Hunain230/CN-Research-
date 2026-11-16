"""Evaluator-only pair increments for the adversarial development stress set."""
import csv
import json
from collections import Counter
from model import HERE,lines,visible
from reconstruct import seed_fragments


def main():
    root=HERE/"stress"
    cfg=json.loads((HERE/"configs/study.json").read_text())
    manifest=json.loads((root/"datasets/manifest.json").read_text())
    rows=[];seed_fp=0
    for item in manifest["queues"]["development"]:
        q=item["queue_id"]
        a=visible(root/"datasets","development",q,cfg["decision_minute"])
        groups,_=seed_fragments(a,cfg["component_cap"])
        truth={x["alert_id"]:x["incident_id"] for x in lines(root/"datasets/development/ground_truth_private"/f"{q}.jsonl")}
        decisions=next(x for x in lines(root/"decisions_baseline.jsonl") if x["queue_id"]==q)["records"]
        parent=list(range(len(groups)))
        membership=[Counter(truth[a[i]["alert_id"]] for i in group) for group in groups]
        for c in membership:
            n=sum(c.values());seed_fp+=n*(n-1)//2-sum(v*(v-1)//2 for v in c.values())
        def root_of(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for order,d in enumerate(decisions):
            if d["decision"]!="accept":continue
            x,y=root_of(d["left"]),root_of(d["right"])
            if x==y:raise AssertionError("redundant accept")
            cx,cy=membership[x],membership[y]
            tp=sum(cx[k]*cy[k] for k in cx.keys()&cy.keys())
            fp=sum(cx.values())*sum(cy.values())-tp
            rows.append({"queue_id":q,"order":order,"reason":d["reason"],
                "premerge_pair_exposure":d["premerge_pair_exposure"],
                "new_true_pairs":tp,"new_false_pairs":fp,
                "auth":d["auth"],"flow":d["flow"],"rare":d["rare"]})
            parent[y]=x;membership[x]+=membership[y]
    final=json.loads((root/"evaluation_baseline.json").read_text())["summary"]
    assert seed_fp+sum(x["new_false_pairs"] for x in rows)==final["false_grouped_pairs"]
    with (HERE/"PHASE19_STRESS_PAIR_INCREMENTS.csv").open("w",newline="",encoding="utf-8") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    bad=sorted((x["new_false_pairs"] for x in rows if x["new_false_pairs"]),reverse=True)
    result={"seed_false_pairs":seed_fp,"accepted_merges":len(rows),
        "false_pair_creating_merges":len(bad),"new_false_pairs":sum(bad),
        "top_1_false_pairs":bad[0] if bad else 0,"top_5_false_pairs":sum(bad[:5])}
    (HERE/"PHASE19_STRESS_PAIR_SUMMARY.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=="__main__":main()
