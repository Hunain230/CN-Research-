"""Label-side evaluation and validation-only selection for frozen rank fusions."""

from __future__ import annotations

import json
import pickle
import time

import psutil

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, tie_aware_ranking, write_json
from src.sprint_rank_fusion_v1 import RUN, CONFIG, V2, V7, HARD


def evaluate():
    public, private = ROOT / "outputs" / RUN, ROOT / "data/derived" / RUN
    out = public / "metrics.json"
    if out.exists():
        raise FileExistsError("Fusion metrics already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text())
    if freeze["source_sha256"] != sha256_file(ROOT / "src/sprint_rank_fusion_v1.py") or \
       freeze["config_sha256"] != sha256_file(CONFIG) or freeze["evaluation_labels_read"]:
        raise ValueError("Prediction lineage changed")
    for name, run in (("v2", V2), ("v7", V7), ("hard", HARD)):
        if freeze[name + "_prediction_freeze_sha256"] != sha256_file(ROOT / "outputs" / run / "prediction_freeze.json"):
            raise ValueError("Frozen source changed")
    v2f = json.loads((ROOT / "outputs" / V2 / "prediction_freeze.json").read_text())
    v7f = json.loads((ROOT / "outputs" / V7 / "prediction_freeze.json").read_text())
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if len(orgs) != 499 or len(freeze["score_sha256"]) != 499:
        raise ValueError("Queue scope changed")
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text())
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    process = psutil.Process()
    peak = process.memory_info().rss
    started = time.perf_counter()
    rows = {}
    methods = ("v7", "0.25", "0.5", "0.75")
    for number, org in enumerate(orgs, 1):
        name = key(org)
        paths = ((ROOT / "data/derived" / V2 / f"v2_{name}.pkl", v2f["prediction_sha256"][name]),
                 (ROOT / "data/derived" / V7 / f"scores_{name}.pkl", v7f["score_sha256"][name]),
                 (private / f"scores_{name}.pkl", freeze["score_sha256"][name]))
        if any(sha256_file(path) != digest for path,digest in paths):
            raise ValueError("Matched scores changed")
        with paths[0][0].open("rb") as stream: base = pickle.load(stream)
        with paths[1][0].open("rb") as stream: v7 = pickle.load(stream)
        with paths[2][0].open("rb") as stream: blends = pickle.load(stream)
        row = {"split": split.get(org, "unassigned")}
        for method in methods:
            scores = v7 if method == "v7" else blends[method]
            metric = tie_aware_ranking(base["groups"], scores, truth, ranks[org])
            row[method] = {"recall20": metric["recall_at_20"],
                           "p10": metric["precision_at_10"],
                           "ndcg20": metric["ndcg_at_20_rank1_highest"]}
        rows[name] = row
        peak = max(peak, process.memory_info().rss)
        if number % 100 == 0:
            print(f"Rank fusion evaluated {number}/499", flush=True)

    def cohort(chosen):
        return {method: {"organizations": len(chosen), "expert_top20_denominator": 20*len(chosen),
                         **{field: sum(rows[key(org)][method][field] for org in chosen)/len(chosen)
                            for field in ("recall20", "p10", "ndcg20")}}
                for method in methods}

    cohorts = {"validation_67_used_for_selection": cohort([o for o in orgs if split.get(o) == "validation"]),
               "holdout_68_previously_exposed": cohort([o for o in orgs if split.get(o) == "holdout"]),
               "outside_fitting_135_exploratory": cohort([o for o in orgs if split.get(o) in ("validation", "holdout")]),
               "all_499_descriptive": cohort(orgs)}
    baseline = cohorts["all_499_descriptive"]["v7"]
    if round(baseline["recall20"], 6) != round(4972/9980, 6) or round(baseline["p10"], 6) != round(.6158316633266533, 6):
        raise ValueError("Frozen rank baseline did not reproduce")
    val = cohorts["validation_67_used_for_selection"]
    eligible = [method for method in methods[1:] if val[method]["p10"] >= val["v7"]["p10"]]
    selected = max(eligible, key=lambda method: (val[method]["recall20"], -float(method))) if eligible else None
    holdout = cohorts["holdout_68_previously_exposed"]
    gates = {"validation_p10_not_lower": selected is not None,
             "validation_recall20_gain": selected is not None and val[selected]["recall20"] > val["v7"]["recall20"],
             "holdout_recall20_gain": selected is not None and holdout[selected]["recall20"] > holdout["v7"]["recall20"],
             "holdout_p10_not_lower": selected is not None and holdout[selected]["p10"] >= holdout["v7"]["p10"]}
    result = {"run": RUN, "classification": "retrospective_exploratory_GUIDE_Test_not_independent_confirmation",
              "cohorts": cohorts, "selected_on_validation": selected, "gates": gates,
              "decision": "GO_EXPLORATORY_ONLY" if all(gates.values()) else "NO_GO_RETAIN_FROZEN_V2_V7",
              "per_organization_pseudonymous": rows, "prediction_freeze_sha256": sha256_file(freeze_path),
              "resource": {"predict": freeze["resource"], "evaluation_wall_seconds": time.perf_counter()-started,
                           "evaluation_peak_process_rss_bytes": peak},
              "limits": ["Validation and holdout labels were previously accessed in earlier work",
                         "Fixed groups preserve all pair and mixed-group metrics"]}
    write_json(out, result)
    print(json.dumps({"status": "evaluated", "selected": selected, "decision": result["decision"],
                      "validation": val, "holdout": holdout, "gates": gates}))


if __name__ == "__main__":
    evaluate()
