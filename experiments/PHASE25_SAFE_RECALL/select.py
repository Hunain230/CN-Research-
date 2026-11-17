"""Apply prewritten development gates and freeze one candidate for one holdout."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_csv(name):
    with (HERE/name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def digest(name):
    return hashlib.sha256((HERE/name).read_bytes()).hexdigest()


def main():
    if (HERE/"selection_freeze.json").exists():
        raise FileExistsError("Selection already frozen")
    if (HERE/"datasets/locked_test").exists():
        raise RuntimeError("Locked cohort exists before selection")
    cfg=json.loads((HERE/"config.json").read_text())
    gate=cfg["development_gates"]
    frozen=json.loads((HERE/"freeze_manifest.json").read_text())
    for name, expected in frozen["hashes"].items():
        assert digest(name)==expected
    comparisons=read_csv("PHASE25_EXPERIMENT_COMPARISON.csv")
    queues=read_csv("PHASE25_QUEUE_METRICS.csv")
    unions=read_csv("PHASE25_UNION_PAIR_AUDIT.csv")
    baseline=next(x for x in comparisons if x["rule"]=="context" and x["ranker"]=="progression")
    base_by_q={x["queue_id"]:x for x in queues if x["rule"]=="context" and x["ranker"]=="progression"}
    union_by_key=defaultdict(list)
    for row in unions:
        union_by_key[row["queue_id"],row["rule"]].append(row)
    accepted=[];gate_rows=[]
    for result in comparisons:
        subset=[q for q in queues if q["rule"]==result["rule"] and q["ranker"]==result["ranker"]]
        assert len(subset)==cfg["queues"]["development"]
        reconciled=all(int(q["false_grouped_pairs"])==sum(int(x["new_false_pairs"])
                        for x in union_by_key[q["queue_id"],q["rule"]]) for q in subset)
        queue_safe=all(
            int(q["false_grouped_pairs"])<=int(base_by_q[q["queue_id"]]["false_grouped_pairs"])
            +gate["max_false_pairs_increase_per_queue"] and
            int(q["mixed_predicted_groups"])<=int(base_by_q[q["queue_id"]]["mixed_predicted_groups"])
            +gate["max_mixed_groups_increase_per_queue"] for q in subset)
        passed=(int(result["recall20_count"])>int(baseline["recall20_count"])
                and int(result["recoverable"])>=int(baseline["recoverable"])
                and float(result["grouped_pair_precision"])>=gate["min_pair_precision"]
                and int(result["false_grouped_pairs"])<=int(baseline["false_grouped_pairs"])
                +gate["max_false_pairs_increase_total"]
                and int(result["mixed_predicted_groups"])<=int(baseline["mixed_predicted_groups"])
                +gate["max_mixed_groups_increase_total"]
                and int(result["p10_count"])>=int(baseline["p10_count"])-gate["max_p10_count_drop"]
                and queue_safe and reconciled)
        gate_rows.append({"rule":result["rule"],"ranker":result["ranker"],"passed":passed,
                          "queue_safe":queue_safe,"reconciled":reconciled})
        if passed:accepted.append(result)
    # The contradiction veto is preferred only on an otherwise exact score tie.
    order={"orthogonal_veto":1,"coherent_rare":0}
    selected=max(accepted,key=lambda x:(int(x["recall20_count"]),int(x["recoverable"]),
        int(x["p10_count"]),float(x["ndcg20"]),order.get(x["rule"],0))) if accepted else None
    selection={"status":"frozen_before_locked_generation_or_truth_access",
               "selected":{"rule":selected["rule"],"ranker":selected["ranker"]} if selected else None,
               "baseline":{"rule":"context","ranker":"progression"},
               "development_baseline":baseline,"development_selected":selected,
               "development_gate_results":gate_rows,
               "locked_cohort_existed_at_freeze":False,
               "hashes":{name:digest(name) for name in (
                   "config.json","generate.py","generate_locked.py","predict.py","run_study.py",
                   "evaluate_locked.py","datasets/manifest.json","ranker_model.json",
                   "development_predictions.jsonl","development_decisions.jsonl",
                   "PHASE25_EXPERIMENT_COMPARISON.csv","PHASE25_QUEUE_METRICS.csv",
                   "PHASE25_UNION_PAIR_AUDIT.csv")}}
    (HERE/"selection_freeze.json").write_text(json.dumps(selection,indent=2)+"\n")
    print(json.dumps({"selected":selection["selected"],"passing_candidates":len(accepted)},indent=2))


if __name__=="__main__":main()
