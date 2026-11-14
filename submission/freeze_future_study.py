"""Freeze the next independent-cohort study contract before data arrives."""

from __future__ import annotations

import json
from pathlib import Path

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/future_cohort_study_contract_20261114_v1.json"
SOURCES = (
    "src/submission_full_entity_time.py",
    "src/submission_pair_model_grouping.py",
    "src/submission_pair_group_calibrate.py",
    "data/derived/submission_pair_model_grouping_20261114_v1/pair_model.pkl",
    "data/derived/submission_trained_ranker_20261114_v1/model.pkl",
    "outputs/submission_pair_group_calibration_20261114_v1.json",
    "configs/entity_time_sensitivity_policy.yaml",
    "configs/field_policy.yaml",
    "submission/freeze_future_study.py",
)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Prospective contract already frozen")
    contract = {
        "classification": "prospective_plan_not_an_evaluation_or_field_approval",
        "objective": "independent_top20_incident_recovery_study",
        "method_source_sha256": {name: sha256_file(ROOT / name) for name in SOURCES},
        "labels_opened_for_this_contract": False,
        "new_cohort_available": False,
        "cohort_requirements": [
            "new top-20 expert ranking labels with a documented queue snapshot",
            "evidence and alert membership source independent of prior project tuning",
            "documented alert creation and evidence availability times",
            "source hashes and cohort membership frozen before evaluation labels are opened",
            "ambiguous memberships retained in denominator or handled by a predeclared adjudication rule",
        ],
        "primary_endpoint": {
            "metric": "organization_macro_end_to_end_recall_at_20",
            "denominator": "20 expert labels per eligible organization, including missing-evidence labels",
            "recovery_rule": "predicted_top20_group_contains_at_least_80_percent_of_gold_alerts_and_at_least_80_percent_group_purity",
            "comparison": "same_queue_frozen_rule_plus_transferred_ranker",
            "ranking_ties": "uniform_expected_order_within_equal_score_blocks",
        },
        "secondary_endpoints": ["precision_at_10", "ndcg_at_20_rank1_high",
                                "candidate_positive_pair_recall_and_coverage",
                                "pair_precision_recall_f1_and_false_merges",
                                "high_priority_misses", "review_load",
                                "prediction_wall_time_and_peak_rss"],
        "uncertainty": "paired_organization_bootstrap_10000_resamples_fixed_seed29",
        "claims_blocked_until_data_and_approval": ["confirmatory_superiority", "85_percent_absolute_recall_at_20",
                                                   "operational_point_in_time_validity", "live_soc_readiness"],
    }
    OUT.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "future_study_contract_frozen", "new_cohort_available": False,
                      "source_files": len(SOURCES)}))


if __name__ == "__main__":
    main()
