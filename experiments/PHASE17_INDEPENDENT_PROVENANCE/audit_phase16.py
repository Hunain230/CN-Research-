"""Retrospective diagnostics of opened Phase 16; never used for Phase 17 selection."""
import csv
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"PHASE16_PROVENANCE_RECONSTRUCTION/v4"


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def write(name,rows):
    rows=list(rows)
    if not rows:raise ValueError(name)
    with (HERE/name).open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    method="lineage_one_context_v"
    false=[];missed=[]
    predictions=lines(OLD/"experiments/predictions"/f"locked_test_{method}.jsonl")
    for p in predictions:
        queue=p["queue_id"]
        truth={x["alert_id"]:x for x in lines(OLD/"datasets/locked_test/ground_truth_private"/f"{queue}.jsonl")}
        alerts={x["alert_id"]:x for x in lines(OLD/"datasets/locked_test/generated_alerts"/f"{queue}.jsonl")}
        oracle={x["incident_id"]:x for x in lines(OLD/"datasets/locked_test/ground_truth_private"/f"{queue}_priority.jsonl")}
        decision=next(x for x in lines(OLD/"experiments/decisions"/f"locked_test_{method}.jsonl") if x["queue_id"]==queue)
        for d in decision["decisions"]:
            if d["decision"]!="accept" or d["reason"]!="lineage":continue
            a,b=d["left"],d["right"]
            if truth[a]["incident_id"]!=truth[b]["incident_id"]:
                false.append({"queue_id":queue,"left_alert_id":a,"right_alert_id":b,
                    "left_incident":truth[a]["incident_id"],"right_incident":truth[b]["incident_id"],
                    "same_host":alerts[a]["host"]==alerts[b]["host"],
                    "same_account":alerts[a]["account"]==alerts[b]["account"],
                    "shared_auth_ref":bool(alerts[a]["auth_session_ref"] and alerts[a]["auth_session_ref"]==alerts[b]["auth_session_ref"]),
                    "shared_flow_ref":bool(alerts[a]["network_flow_ref"] and alerts[a]["network_flow_ref"]==alerts[b]["network_flow_ref"])})
        sizes=Counter(truth[a]["incident_id"] for a in p["eligible_alert_ids"])
        for incident,item in oracle.items():
            if item["priority_rank"]>20:continue
            matches=[]
            for pos,g in enumerate(p["groups_ranked"],1):
                hits=sum(truth[a]["incident_id"]==incident for a in g)
                if hits and hits/sizes[incident]>=.8 and hits/len(g)>=.8:matches.append(pos)
            if matches and min(matches)>20:
                missed.append({"queue_id":queue,"incident_id":incident,"family":item["family"],
                    "oracle_rank":item["priority_rank"],"first_qualifying_group_position":min(matches),
                    "eligible_alerts":sizes[incident]})
    assert len(false)==10 and len(missed)==44
    write("PHASE17_PHASE16_FALSE_LINK_AUDIT.csv",false)
    write("PHASE17_PHASE16_RANKING_MISSES.csv",missed)
    print(json.dumps({"false_links":len(false),"all_share_host_account":sum(x["same_host"] and x["same_account"] for x in false),
                      "ranking_misses":len(missed),"median_group_position":sorted(x["first_qualifying_group_position"] for x in missed)[len(missed)//2]}))


if __name__=="__main__":main()
