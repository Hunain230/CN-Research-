"""Complete reporting from already frozen holdout predictions after a summary bug."""
import csv
import hashlib
import json
from pathlib import Path

from evaluate_locked import HERE, historical, union_audit
from predict import rows


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if (HERE/"locked_results.json").exists():raise FileExistsError("Holdout result exists")
    freeze=json.loads((HERE/"locked_prediction_freeze.json").read_text())
    assert freeze["status"]=="locked_predictions_hashed_before_truth_audit"
    assert freeze["prediction_sha256"]==digest(HERE/"locked_predictions.jsonl")
    assert freeze["decision_sha256"]==digest(HERE/"locked_decisions.jsonl")
    assert freeze["selection_sha256"]==digest(HERE/"selection_freeze.json")
    assert freeze["locked_manifest_sha256"]==digest(HERE/"datasets/locked_manifest.json")
    selection=json.loads((HERE/"selection_freeze.json").read_text())
    predictions=rows(HERE/"locked_predictions.jsonl")
    decisions=rows(HERE/"locked_decisions.jsonl")
    assert len(predictions)==len(decisions)==60
    truth_root=HERE/"datasets/locked_test/ground_truth_private"
    queue_rows=[];union_rows=[]
    for pred,drow in zip(predictions,decisions):
        assert (pred["queue_id"],pred["method"],pred["ranker"])==(
            drow["queue_id"],drow["rule"],drow["ranker"])
        metric=historical.evaluate_queue(pred,truth_root)
        metric["rule"]=drow["rule"]
        metric["ranker"]=drow["ranker"]
        queue_rows.append(metric)
        truth={x["alert_id"]:x["incident_id"] for x in rows(truth_root/f"{pred['queue_id']}.jsonl")}
        union_rows.extend(union_audit(pred["queue_id"],drow["rule"],drow["decisions"],pred,truth))
    summary={}
    for method in (selection["baseline"],selection["selected"]):
        key=method["rule"]+"/"+method["ranker"]
        subset=[x for x in queue_rows if x["rule"]==method["rule"] and x["ranker"]==method["ranker"]]
        tp=sum(x["pair_tp"] for x in subset);fp=sum(x["false_grouped_pairs"] for x in subset)
        summary[key]={"queues":len(subset),"recoverable":sum(x["recoverable"] for x in subset),
                      "recall20_count":sum(x["recall20_count"] for x in subset),
                      "p10_count":sum(x["p10_count"] for x in subset),
                      "ndcg20":sum(x["ndcg20"] for x in subset)/len(subset),
                      "pair_precision":tp/(tp+fp),"false_grouped_pairs":fp,
                      "mixed_predicted_groups":sum(x["mixed_predicted_groups"] for x in subset)}
    with (HERE/"locked_queue_metrics.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(queue_rows[0]));writer.writeheader();writer.writerows(queue_rows)
    with (HERE/"locked_union_pair_audit.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(union_rows[0]));writer.writeheader();writer.writerows(union_rows)
    result={"selected":selection["selected"],"summary":summary,
            "prediction_freeze_sha256":digest(HERE/"locked_prediction_freeze.json"),
            "audit_completion_note":"same frozen predictions; initial summary failed on missing ranker field"}
    (HERE/"locked_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
