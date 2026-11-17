"""One frozen Phase 25 holdout prediction, then one truth audit."""
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

from predict import HERE, rank, reconstruct, rows, visible, visible_receipts

EVALUATOR = HERE.parents[1] / "experiments" / "PHASE15_CONTROLLED_SOC" / "evaluation" / "evaluate.py"
spec = importlib.util.spec_from_file_location("historical_metric_evaluator", EVALUATOR)
historical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(historical)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_lines(path, values):
    with path.open("w", encoding="utf-8") as stream:
        for x in values:stream.write(json.dumps(x, sort_keys=True)+"\n")


def union_audit(queue, rule, decisions, pred, truth):
    parent={a:a for a in pred["eligible_alert_ids"]}
    counts={a:Counter([truth[a]]) for a in parent}
    def root(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    output=[]
    for order,d in enumerate(decisions):
        if d["decision"]!="accept":continue
        a,b=root(d["left"][0]),root(d["right"][0])
        assert a!=b
        x,y=counts[a],counts[b]
        tp=sum(x[k]*y[k] for k in x.keys()&y.keys())
        fp=sum(x.values())*sum(y.values())-tp
        output.append({"queue_id":queue,"rule":rule,"order":order,"reason":d["reason"],
                       "left_size":len(d["left"]),"right_size":len(d["right"]),
                       "new_true_pairs":tp,"new_false_pairs":fp,
                       "premerge_pair_exposure":d["premerge_pair_exposure"]})
        counts[a]+=counts[b];del counts[b];parent[b]=a
    final_fp=sum(len(g)*(len(g)-1)//2-sum(n*(n-1)//2 for n in
                 Counter(truth[a] for a in g).values()) for g in pred["groups_ranked"])
    assert final_fp==sum(x["new_false_pairs"] for x in output)
    return output


def main():
    if (HERE/"locked_results.json").exists() or (HERE/"locked_prediction_freeze.json").exists():
        raise FileExistsError("Holdout evaluation already started")
    selection=json.loads((HERE/"selection_freeze.json").read_text())
    assert selection["status"]=="frozen_before_locked_generation_or_truth_access"
    assert not selection["locked_cohort_existed_at_freeze"]
    for name,expected in selection["hashes"].items():
        assert digest(HERE/name)==expected
    chosen=selection["selected"]
    if not chosen:raise RuntimeError("No development-safe candidate")
    manifest=json.loads((HERE/"datasets/locked_manifest.json").read_text())
    assert set(manifest["queues"])=={"locked_test"}
    cfg=json.loads((HERE/"config.json").read_text())
    train_dev=json.loads((HERE/"datasets/manifest.json").read_text())
    assert set(manifest["split_templates"]["locked_test"]).isdisjoint(
        train_dev["split_templates"]["train"]+train_dev["split_templates"]["development"])
    ranker=json.loads((HERE/"ranker_model.json").read_text())
    predictors=(selection["baseline"],chosen)
    predictions=[];decision_rows=[]
    for item in manifest["queues"]["locked_test"]:
        q=item["queue_id"]
        alerts=visible("locked_test",q)
        receipts=visible_receipts("locked_test",q)
        for method in predictors:
            rule,ranker_name=method["rule"],method["ranker"]
            groups,decisions,candidates=reconstruct(alerts,rule,receipts=receipts)
            weights=(ranker["linear_weights"] if ranker_name=="linear" else
                     ranker["weights"] if ranker_name in ("learned","blend") else None)
            ranked=rank(groups,alerts,ranker_name,weights)
            predictions.append({"queue_id":q,"split":"locked_test","method":rule,
                                "ranker":ranker_name,"eligible_alert_ids":[a["alert_id"] for a in alerts],
                                "groups_ranked":ranked,"candidate_pairs":candidates,
                                "decisions":{},"runtime_seconds":0.0})
            decision_rows.append({"queue_id":q,"rule":rule,"ranker":ranker_name,"decisions":decisions})
    prediction_file=HERE/"locked_predictions.jsonl"
    decision_file=HERE/"locked_decisions.jsonl"
    write_lines(prediction_file,predictions)
    write_lines(decision_file,decision_rows)
    (HERE/"locked_prediction_freeze.json").write_text(json.dumps({
        "status":"locked_predictions_hashed_before_truth_audit",
        "selection_sha256":digest(HERE/"selection_freeze.json"),
        "locked_manifest_sha256":digest(HERE/"datasets/locked_manifest.json"),
        "prediction_sha256":digest(prediction_file),"decision_sha256":digest(decision_file)},indent=2)+"\n")

    # Private truth is first opened below this freeze boundary.
    truth_root=HERE/"datasets/locked_test/ground_truth_private"
    queue_rows=[];union_rows=[]
    for pred,drow in zip(predictions,decision_rows):
        metric=historical.evaluate_queue(pred,truth_root)
        metric["rule"]=drow["rule"]
        queue_rows.append(metric)
        truth={x["alert_id"]:x["incident_id"] for x in rows(truth_root/f"{pred['queue_id']}.jsonl")}
        union_rows.extend(union_audit(pred["queue_id"],drow["rule"],drow["decisions"],pred,truth))
    summary={}
    for method in predictors:
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
    result={"selected":chosen,"summary":summary,
            "prediction_freeze_sha256":digest(HERE/"locked_prediction_freeze.json")}
    (HERE/"locked_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
