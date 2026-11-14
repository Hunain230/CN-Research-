"""Evaluator-only aggregate ceilings for the frozen full-GUIDE rule.

The result contains counts and mathematical upper bounds, never org/alert IDs.
It is a diagnostic, not a new prediction or a measured model score.
"""

from __future__ import annotations

import json
import pickle
from collections import Counter
from pathlib import Path

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import MAX_COMPONENT, MAX_NEIGHBORS, ROOT


PARENT = "submission_full_guide_paper_20261113_v1"
PREDICTIONS = ROOT / "data/derived" / PARENT / "predictions.pkl"
PARENT_MANIFEST = ROOT / "outputs" / PARENT / "run_manifest.json"
PARENT_METRICS = ROOT / "outputs" / PARENT / "metrics.json"
OUT = ROOT / "outputs/submission_retrieval_bounds_20261114_v1.json"


def main() -> None:
    manifest = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["sha256"][str(PREDICTIONS.relative_to(ROOT))]
    if sha256_file(PREDICTIONS) != expected:
        raise ValueError("Parent prediction hash changed")
    with PREDICTIONS.open("rb") as stream:
        predictions = pickle.load(stream)
    orgs = set(predictions)
    alerts = {a for item in predictions.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alerts)
    ranks = labels(orgs)
    gold = {incident for org_ranks in ranks.values() for incident in org_ranks}
    counts = Counter(truth.values())
    parent = json.loads(PARENT_METRICS.read_text(encoding="utf-8"))
    if len(orgs) != parent["organizations"] or len(alerts) != parent["alerts"] or len(gold) != parent["expert_top20_denominator"]:
        raise ValueError("Parent denominator changed")
    available = sum(counts[incident] > 0 for incident in gold)
    too_large = sum(counts[incident] * 0.8 > MAX_COMPONENT for incident in gold if counts[incident] > 0)
    positive = parent["positive_pairs"]
    maximum_degree20_pairs = min(parent["possible_pairs"], len(alerts) * MAX_NEIGHBORS // 2)
    maximum_directed20_union = min(parent["possible_pairs"], len(alerts) * MAX_NEIGHBORS)
    result = {
        "classification": "exploratory_evaluator_only_mathematical_upper_bounds_not_measured_recall",
        "parent_run": PARENT,
        "source_sha256": {
            "parent_predictions": expected,
            "parent_metrics": sha256_file(PARENT_METRICS),
            "source_code": sha256_file(Path(__file__)),
        },
        "organizations": len(orgs),
        "unambiguous_alerts": len(alerts),
        "positive_pair_denominator": positive,
        "expert_top20_denominator": len(gold),
        "implemented_max_undirected_degree_per_alert": MAX_NEIGHBORS,
        "implemented_max_component_alerts": MAX_COMPONENT,
        "measured_candidate_positive_pairs": parent["candidate_positive_pairs"],
        "measured_candidate_recall": parent["candidate_recall_micro"],
        "mathematical_pair_capacity_degree20": maximum_degree20_pairs,
        "mathematical_candidate_recall_upper_bound_degree20": maximum_degree20_pairs / positive,
        "mathematical_pair_capacity_directed20_union_sensitivity": maximum_directed20_union,
        "mathematical_candidate_recall_upper_bound_directed20_union_sensitivity": maximum_directed20_union / positive,
        "expert_labels_with_any_unambiguous_alert": available,
        "expert_labels_with_no_unambiguous_alert": len(gold) - available,
        "expert_labels_with_more_than_125_unambiguous_alerts": too_large,
        "optimistic_recoverable_labels_under_100_alert_component_cap": available - too_large,
        "optimistic_end_to_end_recall20_ceiling_under_exclusion_and_component_cap": (available - too_large) / len(gold),
        "interpretation": [
            "The 20-degree positive-pair recall bound assumes every emitted pair is positive; actual recall is lower.",
            "The directed-union bound is sensitivity for a different 20-proposals-per-alert interpretation, not the implemented mutual degree cap.",
            "A gold incident with >125 in-scope alerts cannot meet 80% completeness in a component capped at 100.",
            "The end-to-end ceiling assumes perfect grouping and ranking for all remaining labels; purity and other errors can lower it.",
            "Sparse candidate links can still form a complete component by transitivity, so low positive-pair candidate recall alone is not an end-to-end recall bound.",
        ],
    }
    if OUT.exists():
        raise FileExistsError("Diagnostic output exists; do not overwrite")
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "degree20_candidate_upper_bound": result["mathematical_candidate_recall_upper_bound_degree20"], "end_to_end_ceiling": result["optimistic_end_to_end_recall20_ceiling_under_exclusion_and_component_cap"]}, sort_keys=True))


if __name__ == "__main__":
    main()
