"""Evaluate label-blind offline controls on the frozen 20-queue Qwen alert sample."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import bootstrap, read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, score_groups, write_json
from src.submission_local_qwen import groups_from_links
from src.submission_local_qwen_v2 import rank_metrics


RUN = "submission_qwen_v2_paper_20261113_v1"
FREEZE = ROOT / "outputs" / RUN / "prediction_freeze.json"
METRICS = ROOT / "outputs" / RUN / "metrics.json"
PREDICTIONS = ROOT / "data/derived" / RUN / "predictions.pkl"
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
OUT = ROOT / "outputs/submission_qwen_matched_offline_controls_20261114_v1.json"


def groups_for(item: dict, method: str) -> list[list[str]]:
    if method == "singleton":
        return [[a] for a in sorted(item["alerts"])]
    if method == "exact_pair":
        decisions = {p["id"]: {"decision": "LINK"} for p in item["pairs"]}
        return groups_from_links(item["alerts"], item["pairs"], decisions)
    if method == "qwen_c":
        return item["groups"]
    raise ValueError(method)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Matched control evaluation already frozen")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    prior = json.loads(METRICS.read_text(encoding="utf-8"))
    if sha256_file(PREDICTIONS) != freeze["prediction_sha256"]:
        raise ValueError("Frozen Qwen predictions changed")
    if sha256_file(PREPARED) != freeze["source_sha256"][str(PREPARED.relative_to(ROOT))]:
        raise ValueError("Frozen Qwen input changed")
    with PREDICTIONS.open("rb") as stream:
        predictions = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        prepared = pickle.load(stream)
    orgs = sorted(predictions)
    if len(orgs) != 20:
        raise ValueError("Qwen cohort changed")
    all_alerts = {a for a, doc in prepared["alerts"].items() if doc["org"] in orgs}
    truth = read_truth(set(orgs), all_alerts)
    ranks = labels(set(orgs))
    by_org = defaultdict(list)
    for alert in all_alerts:
        by_org[prepared["alerts"][alert]["org"]].append(alert)
    rows = defaultdict(list)
    census = Counter()
    for org in orgs:
        item = predictions[org]
        docs = {a: prepared["alerts"][a]["fields"] for a in item["alerts"]}
        full_counts = Counter(truth[a] for a in by_org[org])
        if len(item["pairs"]) != 12:
            raise ValueError("Candidate budget changed")
        census.update({"organizations": 1, "selected_pairs": len(item["pairs"]),
                       "selected_alerts": len(item["alerts"]),
                       "full_unambiguous_alerts": len(by_org[org])})
        for grouping in ("singleton", "exact_pair", "qwen_c"):
            groups = groups_for(item, grouping)
            count, bm25 = score_groups(groups, docs)
            scores_by_name = {"count": count, "bm25_like": bm25}
            if grouping == "qwen_c":
                scores_by_name["qwen_p"] = item["scores"]
            for priority, scores in scores_by_name.items():
                method = f"{grouping}_{priority}"
                metric, recovered = rank_metrics(groups, scores, truth, ranks[org], full_counts)
                rows[method].append({"recall20": metric["recall_at_20"],
                                     "p10": metric["precision_at_10"],
                                     "ndcg20": metric["ndcg_at_20_rank1_highest"],
                                     "recoverable": recovered})
    if census["selected_pairs"] != 240 or census["selected_alerts"] != 391 or census["full_unambiguous_alerts"] != 4668:
        raise ValueError("Qwen sample scope changed")
    qwen = rows["qwen_c_qwen_p"]
    observed = sum(x["recall20"] for x in qwen) / len(qwen)
    if abs(observed - prior["cpv"]["end_to_end_recall_at_20_macro"]["mean"]) > 1e-12:
        raise ValueError("Qwen C+P reproduction differs from frozen original")
    methods = {name: {metric: bootstrap([x[metric] for x in series])
                      for metric in ("recall20", "p10", "ndcg20")}
               for name, series in rows.items()}
    paired = {name: {metric: bootstrap([q[metric] - b[metric] for q, b in zip(qwen, rows[name])])
                     for metric in ("recall20", "p10", "ndcg20")}
              for name in rows if name != "qwen_c_qwen_p"}
    result = {"classification": "exploratory_20_queue_matched_offline_controls_no_new_model_calls",
              "scope": dict(census), "expert_top20_denominator": 400,
              "methods": methods, "paired_qwen_c_p_minus_control": paired,
              "v_effect_on_ranking": "none; frozen V supplied review flags only, with no score/group revision",
              "not_provided": ["B2_full_group_priority", "B3_repeated_single_model", "independent_citation_review"],
              "limits": ["Previously accessed 20-queue cohort", "Only 240 selected exact-match candidate pairs",
                         "Unselected alerts retained in full incident completeness and all 400 expert labels retained"],
              "qwen_prediction_freeze_sha256": sha256_file(FREEZE),
              "qwen_metrics_sha256": sha256_file(METRICS),
              "analysis_code_sha256": sha256_file(Path(__file__))}
    write_json(OUT, result)
    print(json.dumps({name: round(method["recall20"]["mean"], 4)
                      for name, method in methods.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
