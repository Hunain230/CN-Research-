"""Freeze v2 groups plus train-only v4 priority model for new cohort testing."""

from __future__ import annotations

import json
from pathlib import Path

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/future_cohort_study_contract_20261114_v3.json"
SOURCES = (
    "src/submission_full_entity_time.py",
    "src/submission_entity_time_pair_v2.py",
    "src/submission_group_ranker_v4.py",
    "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl",
    "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl",
    "outputs/submission_entity_time_pair_v2_20261114_v1/calibration.json",
    "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json",
    "outputs/submission_group_ranker_v4_20261114_v1/prediction_freeze.json",
    "configs/entity_time_sensitivity_policy.yaml",
    "configs/field_policy.yaml",
    "submission/freeze_future_study_v3.py",
)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Future study contract already frozen")
    bridge = json.loads((ROOT / "outputs/submission_bridge_group_v5_20261114_v1/metrics.json").read_text(encoding="utf-8"))
    if bridge["cohorts"]["holdout_68_previously_exposed"]["paired_v5_minus_v2"]["recall20"]["mean"] >= 0:
        raise ValueError("Bridge decision needs review")
    contract = {
        "classification": "prospective_method_freeze_not_new_cohort_evaluation_or_operational_approval",
        "chosen_method": "v2_entity_time_pair_groups_threshold_0.75_cap100_plus_v4_train_only_priority_model",
        "reason": "V4 improved matched ranking on training-disjoint historical organizations; bridge grouping gain was uncertain and historical holdout worsened",
        "method_source_sha256": {name: sha256_file(ROOT / name) for name in SOURCES},
        "new_cohort_available": False,
        "new_cohort_labels_opened": False,
        "primary_metric": "organization_macro_end_to_end_recall_at_20",
        "denominator": "all_20_expert_labels_per_eligible_organization",
        "recovery_rule": "predicted_top20_group_80_percent_gold_completeness_and_80_percent_group_purity",
        "matched_baselines": ["v2_groups_plus_prior_transferred_ranker", "frozen_rule_groups_plus_transferred_ranker"],
        "ranking_ties": "uniform_expected_order_within_equal_score_blocks",
        "paired_unit": "organization",
        "secondary_metrics": ["candidate_recall_and_coverage", "pair_precision_recall_f1",
                              "false_merges_and_splits", "precision_at_10", "ndcg_at_20",
                              "review_load", "resource_use"],
        "gates": ["new_untouched_expert_ranked_cohort", "alert_and_evidence_availability_timing_confirmed",
                  "operational_field_policy_approved_before_live_use", "queue_snapshot_and_rank_direction_documented"],
        "claims_not_yet_supported": ["80_percent_absolute_recall_at_20", "confirmatory_superiority",
                                     "operational_soc_readiness"],
    }
    OUT.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "future_v3_method_frozen", "new_cohort_available": False}))


if __name__ == "__main__":
    main()
