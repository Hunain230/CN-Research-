"""Retrospective analysis of the already-open Phase 15 test; no model inputs."""
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"PHASE15_CONTROLLED_SOC"


def lines(path):
    with Path(path).open(encoding="utf-8") as stream:return [json.loads(x) for x in stream if x.strip()]


def main():
    pred=OLD/"experiments/predictions/locked_test_exact_progression.jsonl"
    rows=[]
    for p in lines(pred):
        q=p["queue_id"]
        alerts={a["alert_id"]:a for a in lines(OLD/"datasets/locked_test/generated_alerts"/f"{q}.jsonl")}
        truth={t["alert_id"]:t["incident_id"] for t in lines(OLD/"datasets/locked_test/ground_truth_private"/f"{q}.jsonl")}
        oracle=lines(OLD/"datasets/locked_test/ground_truth_private"/f"{q}_priority.jsonl")
        eligible=set(p["eligible_alert_ids"])
        by_incident=defaultdict(list)
        for a in eligible:by_incident[truth[a]].append(a)
        groups=p["groups_ranked"]
        group_of={a:i for i,g in enumerate(groups) for a in g}
        for item in oracle:
            if item["priority_rank"]>20:continue
            ids=by_incident[item["incident_id"]]
            fragments=Counter(group_of[a] for a in ids)
            best=max(fragments.values())
            status="incomplete" if best/len(ids)<.8 else "complete"
            trace_present=sum(bool(alerts[a]["trace"]) for a in ids)
            trace_values={alerts[a]["trace"] for a in ids if alerts[a]["trace"]}
            rows.append({"queue_id":q,"incident_id":item["incident_id"],"family":item["family"],
                "eligible_alerts":len(ids),"predicted_fragments":len(fragments),
                "largest_fragment_alerts":best,"largest_fragment_fraction":best/len(ids),
                "trace_present_alerts":trace_present,"trace_coverage":trace_present/len(ids),
                "distinct_nonnull_traces":len(trace_values),"status":status})
    assert len(rows)==60
    assert sum(r["status"]=="incomplete" for r in rows)==43
    path=HERE/"PHASE16_PHASE15_FAILURE_DIAGNOSTIC.csv"
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    inc=[r for r in rows if r["status"]=="incomplete"]
    summary={"top20_labels":60,"incomplete":43,"incomplete_mean_trace_coverage":sum(r["trace_coverage"] for r in inc)/43,
             "incomplete_mean_fragments":sum(r["predicted_fragments"] for r in inc)/43,
             "incomplete_with_less_than_80pct_trace":sum(r["trace_coverage"]<.8 for r in inc),
             "incomplete_with_multiple_traces":sum(r["distinct_nonnull_traces"]>1 for r in inc)}
    (HERE/"phase15_diagnostic_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=="__main__":main()
