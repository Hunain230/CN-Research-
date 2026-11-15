"""Check local submission links and frozen aggregate artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    ROOT / "CONTEXT.md",
    ROOT / "PROJECT_ITERATIONS.md",
    ROOT / "submission/FINAL_REPORT.md",
    ROOT / "submission/REPRODUCE.md",
    ROOT / "submission/KNOWN_LIMITATIONS.md",
    ROOT / "submission/DELIVERY_CHECKLIST.md",
    ROOT / "submission/DASHBOARD_VERIFICATION.md",
    ROOT / "submission/EXPERIMENT_REGISTER.md",
    ROOT / "submission/RESULTS_AND_DISCUSSION.md",
    ROOT / "submission/FULL_SUITE_RUN_20261113.md",
    ROOT / "submission/PERFORMANCE_BASELINE_STUDY.md",
    ROOT / "submission/EXPLORATORY_PERFORMANCE_ITERATION_20261114.md",
    ROOT / "submission/METRIC_RECONCILIATION_FOR_REVIEW.md",
    ROOT / "submission/FULL_GUIDE_RANKER_AND_GROUP_CEILING_20261114.md",
    ROOT / "submission/CORRELATION_GROUPING_ITERATION_20261114.md",
    ROOT / "submission/FULL_499_ENTITY_TIME_SENSITIVITY_20261114.md",
    ROOT / "submission/FRESH_COHORT_AND_SHADOW_GATE.md",
    ROOT / "submission/ENTITY_TIME_MODEL_REEVALUATION_20261114.md",
    ROOT / "submission/INCIDENT_MISS_AND_PRIORITY_ITERATION_20261114.md",
    ROOT / "submission/POINT_IN_TIME_EVIDENCE_STATUS_20261114.md",
    ROOT / "submission/PRIORITY_GROUP_CANDIDATE_FOLLOWUP_20261114.md",
    ROOT / "submission/BASELINE_PAPER_STUDY_CONTRACT_20261114.md",
    ROOT / "submission/MATCHED_20_QUEUE_CONTROL_STUDY_20261114.md",
    ROOT / "submission/PUBLISHER_CLARIFICATION_REQUEST_20261114.md",
    ROOT / "submission/DESCRIPTOR_RANKER_ITERATION_20261114.md",
    ROOT / "submission/SPECIALIST_RANKER_NEGATIVE_CONTROL_20261114.md",
    ROOT / "submission/ADAPTIVE_LINKS_NEGATIVE_CONTROL_20261114.md",
    ROOT / "submission/GROUP_MERGE_MODEL_STUDY_20261114.md",
    ROOT / "submission/EXHIBITION_METRICS_BRIEF_20261115.md",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    links = 0
    missing = []
    for doc in DOCS:
        body = doc.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = (doc.parent / unquote(target.split("#", 1)[0])).resolve()
            links += 1
            if not path.exists():
                missing.append((str(doc.relative_to(ROOT)), target))
    if missing:
        raise ValueError(f"Broken local links: {missing}")
    for name in ("submission_full_guide_20261112_v1", "submission_qwen_20261112_v1", "submission_full_guide_paper_20261113_v1", "submission_qwen_v2_paper_20261113_v1", "submission_rank_fusion_20261114_v1", "submission_trained_ranker_20261114_v1", "submission_transfer_ranker_20261114_v1", "submission_full_ranker_transfer_20261114_v1", "submission_pair_model_grouping_20261114_v1", "submission_pair_grouping_v2_20261114_v1", "submission_full_entity_time_20261114_v1", "submission_entity_time_pair_v2_20261114_v1", "submission_entity_time_cap_v3_20261114_v1", "submission_group_ranker_v4_20261114_v1", "submission_bridge_group_v5_20261114_v1", "submission_priority_focus_v6_20261114_v1", "submission_qwen_matched_statistical_20261114_v1", "submission_descriptor_ranker_v7_20261114_v1", "submission_specialist_ranker_v8_20261114_v1", "submission_group_merge_v10_20261114_v2"):
        manifest = json.loads((ROOT / "outputs" / name / "run_manifest.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["sha256"].items():
            source = ROOT / relative
            if digest(source) != expected:
                raise ValueError(f"Run manifest mismatch: {relative}")
    correction = json.loads((ROOT / "outputs/submission_qwen_20261112_v1/correction_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in correction["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Correction manifest mismatch: {relative}")
    figure = json.loads((ROOT / "submission/figures/submission_figure_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in (figure["source_sha256"] | figure["figure_sha256"]).items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Figure manifest mismatch: {relative}")
    qwen_figure = json.loads((ROOT / "submission/figures/qwen_v2_figure_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in (qwen_figure["source_sha256"] | qwen_figure["figure_sha256"]).items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Qwen figure manifest mismatch: {relative}")
    capacity = json.loads((ROOT / "outputs/submission_retrieval_bounds_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/diagnose_retrieval_bounds.py") != capacity["source_sha256"]["source_code"]:
        raise ValueError("Capacity audit source mismatch")
    if digest(ROOT / "outputs/submission_full_guide_paper_20261113_v1/metrics.json") != capacity["source_sha256"]["parent_metrics"]:
        raise ValueError("Capacity audit parent mismatch")
    ceiling = json.loads((ROOT / "outputs/submission_full_group_ceiling_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl") != ceiling["frozen_prediction_sha256"]:
        raise ValueError("Full grouping ceiling parent mismatch")
    calibration = json.loads((ROOT / "outputs/submission_pair_group_calibration_20261114_v1.json").read_text(encoding="utf-8"))
    for relative, expected in calibration["source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Grouping calibration source mismatch: {relative}")
    comparison = json.loads((ROOT / "outputs/submission_transfer_ranker_20261114_v1/prediction_freeze.json").read_text(encoding="utf-8"))
    if digest(ROOT / "data/derived/submission_transfer_ranker_20261114_v1/scores.pkl") != comparison["prediction_sha256"]:
        raise ValueError("Grouping comparator ranking scores mismatch")
    entity_audit = json.loads((ROOT / "outputs/entity_time_field_audit_20261114_v3.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/audit_entity_time_fields_v3.py") != entity_audit["analysis_code_sha256"]:
        raise ValueError("Entity/time audit code mismatch")
    projection = json.loads((ROOT / "outputs/submission_entity_time_shards_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "src/submission_entity_time_shards.py") != projection["source_code_sha256"]:
        raise ValueError("Entity/time projection code mismatch")
    for relative, expected in projection["parquet_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Private entity/time projection mismatch: {relative}")
    full_entity = json.loads((ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json").read_text(encoding="utf-8"))
    for org_hash, expected in full_entity["prediction_sha256"].items():
        if digest(ROOT / "data/derived/submission_full_entity_time_20261114_v1" / f"{org_hash}.pkl") != expected:
            raise ValueError(f"Full entity/time prediction mismatch: {org_hash}")
    bound = json.loads((ROOT / "outputs/submission_full_candidate_bound_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/diagnose_full_candidate_bound.py") != bound["analysis_code_sha256"]:
        raise ValueError("Candidate bound analysis code mismatch")
    if digest(ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json") != bound["prediction_freeze_sha256"]:
        raise ValueError("Candidate bound parent mismatch")
    cap_calibration = json.loads((ROOT / "outputs/submission_component_cap_calibration_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/calibrate_component_cap_v3.py") != cap_calibration["analysis_code_sha256"]:
        raise ValueError("Component cap calibration code mismatch")
    if digest(ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl") != cap_calibration["pair_model_sha256"]:
        raise ValueError("Component cap calibration model mismatch")
    for run, prefix in (("submission_entity_time_pair_v2_20261114_v1", "v2"), ("submission_entity_time_cap_v3_20261114_v1", "v3")):
        freeze = json.loads((ROOT / "outputs" / run / "prediction_freeze.json").read_text(encoding="utf-8"))
        if len(freeze["prediction_sha256"]) != 499:
            raise ValueError(f"Unexpected prediction count: {run}")
        for org_hash, expected in freeze["prediction_sha256"].items():
            if digest(ROOT / "data/derived" / run / f"{prefix}_{org_hash}.pkl") != expected:
                raise ValueError(f"Prediction mismatch: {run}/{org_hash}")
    incident_audit = json.loads((ROOT / "outputs/submission_v2_incident_miss_audit_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/audit_v2_incident_misses.py") != incident_audit["analysis_code_sha256"]:
        raise ValueError("Incident miss audit code mismatch")
    if digest(ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json") != incident_audit["v2_prediction_freeze_sha256"]:
        raise ValueError("Incident miss audit parent mismatch")
    bridge_calibration = json.loads((ROOT / "outputs/submission_development_bridge_links_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/development_bridge_links.py") != bridge_calibration["analysis_code_sha256"]:
        raise ValueError("Bridge calibration code mismatch")
    for filename, script in (("submission_development_candidate_expansion_20261114_v1.json", "development_candidate_expansion.py"),
                             ("submission_development_group_merge_20261114_v1.json", "development_group_merge.py"),
                             ("submission_ambiguous_provenance_audit_20261114_v1.json", "audit_ambiguous_alert_provenance.py"),
                             ("submission_absent_rank_scope_audit_20261114_v1.json", "audit_absent_rank_scope.py"),
                             ("submission_ambiguous_provenance_audit_20261114_v2.json", "audit_ambiguous_alert_provenance_v2.py"),
                             ("submission_absent_rank_scope_audit_20261114_v2.json", "audit_absent_rank_scope_v2.py"),
                             ("submission_kaggle_queue_alignment_20261114_v1.json", "audit_kaggle_queue_alignment.py")):
        record = json.loads((ROOT / "outputs" / filename).read_text(encoding="utf-8"))
        if digest(ROOT / "submission" / script) != record["analysis_code_sha256"]:
            raise ValueError(f"Development or provenance audit mismatch: {filename}")
    corrected_scope = json.loads((ROOT / "outputs/submission_absent_rank_scope_audit_20261114_v2.json").read_text(encoding="utf-8"))
    if corrected_scope["counts"].get("absent_unambiguous_but_present_raw") != 855 or corrected_scope["counts"].get("absent_from_raw_test_incidents", 0):
        raise ValueError("Corrected rank-scope audit failed")
    published_rank = json.loads((ROOT / "outputs/submission_kaggle_queue_alignment_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "data/raw/GUIDE_Test_Queue_Rankings.csv") != published_rank["local_ranking_sha256"]:
        raise ValueError("Local ranking source changed")
    if digest(ROOT / "data/derived/publisher_queue_audit_20261114/GUIDE_Test_Queue_Rankings.csv") != published_rank["downloaded_ranking_sha256"]:
        raise ValueError("Publisher ranking download changed")
    qwen_controls = json.loads((ROOT / "outputs/submission_qwen_matched_offline_controls_20261114_v1.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/qwen_matched_offline_controls.py") != qwen_controls["analysis_code_sha256"]:
        raise ValueError("Qwen matched offline-control code mismatch")
    if digest(ROOT / "outputs/submission_qwen_v2_paper_20261113_v1/prediction_freeze.json") != qwen_controls["qwen_prediction_freeze_sha256"]:
        raise ValueError("Qwen matched offline-control parent mismatch")
    adaptive = json.loads((ROOT / "outputs/submission_development_adaptive_links_v9_20261114_v1.json").read_text(encoding="utf-8"))
    for relative, expected in adaptive["source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Adaptive-link study source mismatch: {relative}")
    if adaptive["selected_config"] != "base":
        raise ValueError("Adaptive-link development selection changed")
    for filename in ("submission_candidate_pair_classification_20261115_v1.json",
                     "submission_candidate_pair_operating_points_20261115_v1.json"):
        pair_audit = json.loads((ROOT / "outputs" / filename).read_text(encoding="utf-8"))
        for relative, expected in pair_audit["source_sha256"].items():
            if digest(ROOT / relative) != expected:
                raise ValueError(f"Candidate-pair audit source mismatch: {filename}/{relative}")
    for run, field, prefix in (("submission_group_ranker_v4_20261114_v1", "score_sha256", "scores"), ("submission_bridge_group_v5_20261114_v1", "prediction_sha256", "v5")):
        freeze = json.loads((ROOT / "outputs" / run / "prediction_freeze.json").read_text(encoding="utf-8"))
        if len(freeze[field]) != 499:
            raise ValueError(f"Unexpected frozen file count: {run}")
        for org_hash, expected in freeze[field].items():
            if digest(ROOT / "data/derived" / run / f"{prefix}_{org_hash}.pkl") != expected:
                raise ValueError(f"Frozen file mismatch: {run}/{org_hash}")
    v6 = json.loads((ROOT / "outputs/submission_priority_focus_v6_20261114_v1/prediction_freeze.json").read_text(encoding="utf-8"))
    if len(v6["score_sha256"]) != 499:
        raise ValueError("V6 score count changed")
    for org_hash, expected in v6["score_sha256"].items():
        if digest(ROOT / "data/derived/submission_priority_focus_v6_20261114_v1" / f"scores_{org_hash}.pkl") != expected:
            raise ValueError(f"V6 score mismatch: {org_hash}")
    v7 = json.loads((ROOT / "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json").read_text(encoding="utf-8"))
    if len(v7["score_sha256"]) != 499:
        raise ValueError("V7 score count changed")
    for org_hash, expected in v7["score_sha256"].items():
        if digest(ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1" / f"scores_{org_hash}.pkl") != expected:
            raise ValueError(f"V7 score mismatch: {org_hash}")
    v8 = json.loads((ROOT / "outputs/submission_specialist_ranker_v8_20261114_v1/prediction_freeze.json").read_text(encoding="utf-8"))
    if len(v8["score_sha256"]) != 499:
        raise ValueError("V8 score count changed")
    for org_hash, expected in v8["score_sha256"].items():
        if digest(ROOT / "data/derived/submission_specialist_ranker_v8_20261114_v1" / f"scores_{org_hash}.pkl") != expected:
            raise ValueError(f"V8 score mismatch: {org_hash}")
    v10 = json.loads((ROOT / "outputs/submission_group_merge_v10_20261114_v2/prediction_freeze.json").read_text(encoding="utf-8"))
    if len(v10["prediction_sha256"]) != 499:
        raise ValueError("V10 prediction count changed")
    for org_hash, expected in v10["prediction_sha256"].items():
        if digest(ROOT / "data/derived/submission_group_merge_v10_20261114_v2" / f"v10_{org_hash}.pkl") != expected:
            raise ValueError(f"V10 prediction mismatch: {org_hash}")
    future = json.loads((ROOT / "outputs/future_cohort_study_contract_20261114_v1.json").read_text(encoding="utf-8"))
    for relative, expected in future["method_source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Future study contract method mismatch: {relative}")
    future_v2 = json.loads((ROOT / "outputs/future_cohort_study_contract_20261114_v2.json").read_text(encoding="utf-8"))
    for relative, expected in future_v2["method_source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Future v2 study contract method mismatch: {relative}")
    future_v3 = json.loads((ROOT / "outputs/future_cohort_study_contract_20261114_v3.json").read_text(encoding="utf-8"))
    for relative, expected in future_v3["method_source_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Future v3 study contract method mismatch: {relative}")
    paired = json.loads((ROOT / "outputs/submission_transfer_ranker_20261114_v1/paired_analysis.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/analyze_transfer_ranker.py") != paired["source_sha256"]["analysis_code"]:
        raise ValueError("Paired analysis source mismatch")
    transfer_figure = json.loads((ROOT / "submission/figures/transfer_ranker_57_manifest.json").read_text(encoding="utf-8"))
    if digest(ROOT / "submission/figures/transfer_ranker_57.png") != transfer_figure["figure_sha256"]:
        raise ValueError("Transfer figure mismatch")
    pdf = json.loads((ROOT / "submission/PHASE3_REPORT_PDF_MANIFEST.json").read_text(encoding="utf-8"))
    for relative, expected in pdf["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Report PDF manifest mismatch: {relative}")
    dashboard = json.loads((ROOT / "dashboard/simulation_manifest.json").read_text(encoding="utf-8"))
    if digest(ROOT / "dashboard/simulation.html") != dashboard["output_sha256"]:
        raise ValueError("Dashboard output hash mismatch")
    print(f"Submission verification passed: {links} local links, twenty run manifests, 4,491 frozen entity/time group or score files, three future study contracts, report PDF, and dashboard hash")


if __name__ == "__main__":
    main()
