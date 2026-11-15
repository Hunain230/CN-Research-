"""Correct a subgroup-only accounting error in frozen Phase 7 metrics.

The predictor and original metrics remain untouched. The split manifest omits 30
organizations; their saved per-queue rows say 'unassigned', while the original
cohort selector looked for a manifest value equal to 'unassigned'. This script
uses only the already frozen per-queue metric rows to repair that aggregate.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_group_ranker_v4 import bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="submission_fragment_matching_ml_v1_20261115_v2")
    args = parser.parse_args()
    public = ROOT / "outputs" / args.run_id
    source = public / "metrics.json"
    destination = public / "metrics_corrected.json"
    correction = public / "evaluation_correction.json"
    if destination.exists() or correction.exists():
        raise FileExistsError("Correction already frozen")
    original = json.loads(source.read_text(encoding="utf-8"))
    rows = [row for row in original["per_organization_pseudonymous"].values()
            if row["split"] == "unassigned"]
    if len(rows) != 30 or original["cohorts"]["unassigned_30_exploratory"]["organizations"] != 0:
        raise ValueError("Expected subgroup-only error not found")
    corrected = copy.deepcopy(original)
    corrected["cohorts"]["unassigned_30_exploratory"] = {
        "organizations": 30, "expert_top20_denominator": 600,
        "methods": {method: {field: bootstrap([row[method][field] for row in rows])
                             for field in ("recall20", "p10", "ndcg20")}
                    for method in ("reference", "fragment_ml")},
        "paired_fragment_ml_minus_reference": {
            field: bootstrap([row["fragment_ml"][field] - row["reference"][field]
                              for row in rows])
            for field in ("recall20", "p10", "ndcg20")},
    }
    # Same-process RSS is a high-water mark shared by both legs, not a matched
    # independent baseline. Do not treat the original Boolean as a passed gate.
    corrected["descriptive_acceptance_checks"]["memory_within_25_percent_same_pass"] = None
    corrected["resource"]["prediction"]["memory_comparison_limit"] = (
        "Same-process high-water RSS cannot establish a 25% matched memory margin")
    corrected["evaluation_correction"] = (
        "30 omitted-manifest organizations aggregated from frozen per-queue rows; "
        "memory gate marked not evaluable; no prediction, label or all-499 metric changed")
    if any(corrected["cohorts"]["all_499_exploratory"]["methods"][method] !=
           original["cohorts"]["all_499_exploratory"]["methods"][method]
           for method in ("reference", "fragment_ml")):
        raise ValueError("Main result changed")
    destination.write_text(json.dumps(corrected, indent=2, sort_keys=True,
                                      allow_nan=False) + "\n", encoding="utf-8")
    write_json(correction, {
        "classification": "subgroup_accounting_correction_after_prediction_freeze",
        "run": args.run_id, "predictor_and_original_metrics_unchanged": True,
        "original_metrics_sha256": sha256_file(source),
        "corrected_metrics_sha256": sha256_file(destination),
        "correction_source_sha256": sha256_file(Path(__file__)),
        "unassigned_organizations": 30, "unassigned_label_denominator": 600,
        "all_499_metrics_unchanged": True,
    })
    print(json.dumps({"status": "corrected_aggregate_frozen",
                      "unassigned_organizations": 30,
                      "corrected_sha256": sha256_file(destination)}))


if __name__ == "__main__":
    main()
