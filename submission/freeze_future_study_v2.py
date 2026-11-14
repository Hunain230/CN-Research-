"""Freeze the chosen v2 entity/time pair method for a future independent cohort."""

from __future__ import annotations

import json
from pathlib import Path

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/future_cohort_study_contract_20261114_v2.json"
SOURCES = (
    "src/submission_full_entity_time.py",
    "src/submission_entity_time_pair_v2.py",
    "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl",
    "outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json",
    "outputs/submission_entity_time_pair_v2_20261114_v1/calibration.json",
    "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json",
    "configs/entity_time_sensitivity_policy.yaml",
    "configs/field_policy.yaml",
    "submission/freeze_future_study_v2.py",
)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Future study contract already frozen")
    calibration = json.loads((ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/calibration.json").read_text(encoding="utf-8"))
    if calibration["selected_threshold"] != .75:
        raise ValueError("Chosen development threshold changed")
    contract = {
        "classification": "prospective_method_freeze_not_new_cohort_evaluation_or_operational_approval",
        "chosen_method": "entity_time_pair_v2_threshold_0.75_component_cap_100",
        "reason": "Training-disjoint exploratory gain with higher pair precision and grouping ceiling than cap-v3; cap-v3 recall difference includes zero and historical holdout worsened",
        "method_source_sha256": {name: sha256_file(ROOT / name) for name in SOURCES},
        "new_cohort_available": False,
        "new_cohort_labels_opened": False,
        "primary_metric": "organization_macro_end_to_end_recall_at_20",
        "denominator": "all_20_expert_labels_per_eligible_organization",
        "recovery_rule": "predicted_top20_group_80_percent_gold_completeness_and_80_percent_group_purity",
        "baseline": "frozen_rule_grouping_plus_transferred_ranker_on_same_alert_scope",
        "candidate_route": "rare_shared_entity_within_48h_or_shared_technique_within_1h_plus_frozen_descriptor_rule",
        "ranking_ties": "uniform_expected_order_within_equal_score_blocks",
        "paired_unit": "organization",
        "secondary_metrics": ["candidate_recall_and_coverage", "pair_precision_recall_f1",
                              "false_merges_and_splits", "precision_at_10",
                              "ndcg_at_20", "review_load", "resource_use"],
        "gates": ["new_untouched_expert_ranked_cohort",
                  "alert_and_evidence_availability_timing_confirmed",
                  "operational_field_policy_approved_before_live_use",
                  "queue_snapshot_and_rank_direction_documented"],
        "claims_not_yet_supported": ["80_percent_absolute_recall_at_20",
                                     "confirmatory_superiority", "operational_soc_readiness"],
    }
    OUT.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "future_v2_method_frozen", "new_cohort_available": False,
                      "source_files": len(SOURCES)}))


if __name__ == "__main__":
    main()
