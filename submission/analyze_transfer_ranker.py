"""Additive paired analysis of the frozen 57-queue transfer experiment."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

from src.guide_rerun_v2 import ROOT, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import tie_aware_ranking
from src.submission_rank_fusion import bootstrap, write_json


RUN = "submission_transfer_ranker_20261114_v1"
PUBLIC = ROOT / "outputs" / RUN
PREDICTIONS = ROOT / "data/derived" / RUN / "scores.pkl"
PARENT = ROOT / "data/derived/offline_joint_v2/predictions.pkl"
OUT = PUBLIC / "paired_analysis.json"
COMPARE = ("B0_rule_count", "B1_rule_bm25", "offline_CPV_proxy")


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Paired analysis already exists")
    freeze = json.loads((PUBLIC / "prediction_freeze.json").read_text(encoding="utf-8"))
    if sha256_file(PREDICTIONS) != freeze["prediction_sha256"] or sha256_file(PARENT) != freeze["parent_prediction_sha256"]:
        raise ValueError("Frozen inputs changed")
    with PREDICTIONS.open("rb") as stream:
        transferred = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    if set(orgs) != set(transferred) or len(orgs) != 57:
        raise ValueError("Cohort mismatch")
    alerts = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(set(orgs), alerts)
    ranks = labels(set(orgs))
    values = {name: [] for name in ("transfer_rule", *COMPARE)}
    for org in orgs:
        parent_methods = parent[org]["methods"]
        choices = {name: (parent_methods[name]["groups"], parent_methods[name]["scores"]) for name in COMPARE}
        choices["transfer_rule"] = (parent_methods["B1_rule_bm25"]["groups"], transferred[org]["rule"])
        for name, (groups, scores) in choices.items():
            result = tie_aware_ranking(groups, scores, truth, ranks[org])
            values[name].append({"recall20": result["recall_at_20"], "p10": result["precision_at_10"], "ndcg1": result["ndcg_at_20_rank1_highest"]})
    metrics = json.loads((PUBLIC / "metrics.json").read_text(encoding="utf-8"))
    lookup = {"recall20": "end_to_end_recall_at_20_macro", "p10": "precision_at_10_macro", "ndcg1": "ndcg_at_20_rank1_high_macro"}
    for name, series in values.items():
        for key, recorded in lookup.items():
            mean = sum(row[key] for row in series) / len(series)
            if abs(mean - metrics["methods"][name][recorded]["mean"]) > 1e-12:
                raise ValueError("Recorded metric mismatch")
    comparisons = {}
    for baseline in COMPARE:
        comparisons[f"transfer_rule_minus_{baseline}"] = {
            key: bootstrap([a[key] - b[key] for a, b in zip(values["transfer_rule"], values[baseline])])
            for key in lookup
        }
    write_json(OUT, {
        "classification": "additive_exploratory_paired_organization_analysis_not_confirmatory",
        "run": RUN,
        "organizations": len(orgs),
        "expert_top20_denominator": 20 * len(orgs),
        "source_sha256": {
            "prediction_freeze": sha256_file(PUBLIC / "prediction_freeze.json"),
            "metrics": sha256_file(PUBLIC / "metrics.json"),
            "analysis_code": sha256_file(Path(__file__)),
        },
        "comparisons": comparisons,
        "limits": ["previously accessed 57-organization cohort", "method transfer and comparator choice postdate earlier project label exposure", "shared rule groups for transfer_rule, B0, and B1; offline CPV has different predicted groups", "paired bootstrap descriptive only"],
    })
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "transfer_rule_minus_B0_recall20": comparisons["transfer_rule_minus_B0_rule_count"]["recall20"]["mean"]}, sort_keys=True))


if __name__ == "__main__":
    main()
