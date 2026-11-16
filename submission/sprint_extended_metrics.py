"""Extended tie-aware metrics and paired uncertainty for the selected frozen fusion."""

from __future__ import annotations

import json
import math
import pickle
from collections import Counter

import numpy as np

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, tie_aware_ranking, write_json
from src.sprint_rank_fusion_v1 import RUN, V2, V7


def extended(groups, scores, truth, ranks):
    sizes = Counter(truth[a] for group in groups for a in group)
    labels_by_group = {}
    for index, group in enumerate(groups):
        members = Counter(truth[a] for a in group)
        gold, overlap = max(members.items(), key=lambda pair: (pair[1], pair[0]))
        if gold in ranks and overlap/sizes[gold] >= .8 and overlap/len(group) >= .8:
            labels_by_group[index] = ranks[gold]
    order = sorted(range(len(groups)), key=lambda i: (-scores[i], groups[i][0]))
    relevant = {5: 0.0, 10: 0.0, 20: 0.0}
    dcg10 = 0.0
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and scores[order[end]] == scores[order[start]]:
            end += 1
        block = order[start:end]
        count = sum(i in labels_by_group for i in block)
        for cutoff in relevant:
            take = max(0, min(end, cutoff)-start)
            relevant[cutoff] += take*count/len(block)
        take = max(0, min(end, 10)-start)
        if take:
            mean_gain = sum(2**(21-labels_by_group[i])-1 for i in block if i in labels_by_group)/len(block)
            dcg10 += mean_gain*sum(1/math.log2(pos+2) for pos in range(start,start+take))
        start = end
    ideal = sorted((2**(21-rank)-1 for rank in ranks.values()), reverse=True)
    idcg10 = sum(g/math.log2(i+2) for i,g in enumerate(ideal[:10]))
    result = {"p5": relevant[5]/5, "p10": relevant[10]/10,
              "incident_recall10": relevant[10]/len(ranks),
              "incident_recall20": relevant[20]/len(ranks),
              "ndcg10": dcg10/idcg10 if idcg10 else 0.0}
    original = tie_aware_ranking(groups, scores, truth, ranks)
    assert abs(result["p10"]-original["precision_at_10"]) < 1e-10
    assert abs(result["incident_recall20"]-original["recall_at_20"]) < 1e-10
    result["ndcg20"] = original["ndcg_at_20_rank1_highest"]
    return result


def main():
    public = ROOT / "outputs" / RUN
    out = public / "extended_metrics.json"
    if out.exists():
        raise FileExistsError("Extended metrics already frozen")
    metrics_path = public / "metrics.json"
    metrics = json.loads(metrics_path.read_text())
    if metrics["selected_on_validation"] != "0.75":
        raise ValueError("Selected method changed")
    freeze = json.loads((public / "prediction_freeze.json").read_text())
    v2f = json.loads((ROOT / "outputs" / V2 / "prediction_freeze.json").read_text())
    v7f = json.loads((ROOT / "outputs" / V7 / "prediction_freeze.json").read_text())
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    rows = {}
    for org in orgs:
        name = key(org)
        paths = ((ROOT / "data/derived" / V2 / f"v2_{name}.pkl", v2f["prediction_sha256"][name]),
                 (ROOT / "data/derived" / V7 / f"scores_{name}.pkl", v7f["score_sha256"][name]),
                 (ROOT / "data/derived" / RUN / f"scores_{name}.pkl", freeze["score_sha256"][name]))
        if any(sha256_file(path) != digest for path,digest in paths):
            raise ValueError("Frozen prediction changed")
        with paths[0][0].open("rb") as stream: group = pickle.load(stream)["groups"]
        with paths[1][0].open("rb") as stream: base = pickle.load(stream)
        with paths[2][0].open("rb") as stream: selected = pickle.load(stream)["0.75"]
        rows[name] = {"split": split.get(org,"unassigned"),
                      "v7": extended(group, base, truth, ranks[org]),
                      "selected": extended(group, selected, truth, ranks[org])}
    def cohort(chosen):
        fields = ("p5", "p10", "incident_recall10", "incident_recall20", "ndcg10", "ndcg20")
        rng = np.random.default_rng(20261116)
        result = {}
        for field in fields:
            a = np.array([rows[key(o)]["v7"][field] for o in chosen])
            b = np.array([rows[key(o)]["selected"][field] for o in chosen])
            indices = rng.integers(0,len(chosen),size=(5000,len(chosen)))
            change = b-a
            result[field] = {"v7": float(a.mean()), "selected": float(b.mean()),
                             "paired_change": float(change.mean()),
                             "paired_ci95": np.quantile(change[indices].mean(axis=1),[.025,.975]).tolist()}
        return {"organizations": len(chosen), "expert_top20_denominator": 20*len(chosen), "metrics": result}
    cohorts = {"validation_67": cohort([o for o in orgs if split.get(o)=="validation"]),
               "holdout_68_previously_exposed": cohort([o for o in orgs if split.get(o)=="holdout"]),
               "outside_fitting_135": cohort([o for o in orgs if split.get(o) in ("validation","holdout")]),
               "all_499": cohort(orgs)}
    for cohort_name, source_name in (("all_499","all_499_descriptive"),
                                     ("outside_fitting_135","outside_fitting_135_exploratory")):
        for method, row_name in (("v7","v7"),("selected","0.75")):
            for field, source_field in (("p10","p10"),("incident_recall20","recall20"),("ndcg20","ndcg20")):
                observed = cohorts[cohort_name]["metrics"][field][method]
                prior = metrics["cohorts"][source_name][row_name][source_field]
                assert abs(observed-prior) < 1e-10
    write_json(out,{"run": RUN, "classification": "retrospective_exploratory_extended_metrics",
                    "selected_method": "0.75", "cohorts": cohorts,
                    "bootstrap_seed": 20261116, "bootstrap_resamples": 5000,
                    "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
                    "metrics_sha256": sha256_file(metrics_path),
                    "per_organization_pseudonymous": rows})
    print(json.dumps({"status":"extended_metrics_frozen", "all499":cohorts["all_499"],
                      "outside_fitting_135":cohorts["outside_fitting_135"]}))


if __name__ == "__main__":
    main()
