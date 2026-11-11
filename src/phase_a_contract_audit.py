"""Aggregate Phase A contract audit; never exports row-level identifiers."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .guide_rerun_v2 import ROOT, PRIVATE, check_raw
from .phase2 import sha256_file

OUT = ROOT / "outputs/phase_a/contract_audit_v1.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    check_raw()
    rank_path = ROOT / "data/raw/GUIDE_Test_Queue_Rankings.csv"
    by = defaultdict(list)
    with rank_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if columns != ["OrgId", "IncidentId", "QueueRank"]:
            raise ValueError(f"unexpected ranking schema: {columns}")
        for row in reader:
            by[row["OrgId"]].append((row["IncidentId"], int(row["QueueRank"])))
    valid_ranks = all(len(rows) == 20 and len({i for i, _ in rows}) == 20
                      and sorted(rank for _, rank in rows) == list(range(1, 21))
                      for rows in by.values())
    if len(by) != 499 or not valid_ranks:
        raise ValueError("rank count or uniqueness drift")
    historical = read(ROOT / "data/derived/preprocessing/split_manifest.json")["assignments"]
    rerun = read(PRIVATE / "split.json")
    if len(historical) != 50 or len(rerun) != 469 or set(historical) | set(rerun) != set(by):
        raise ValueError("no-new-ranked-org accounting drift")
    if {o for o, s in historical.items() if s == "test"} & set(rerun):
        raise ValueError("historical test cohort reused in rerun")
    multi = read(ROOT / "outputs/phase_a/multimembership_sensitivity_v1.json")
    entity = read(ROOT / "outputs/phase_a/entity_retrieval_v1.json")
    title = read(ROOT / "outputs/phase_a/title_retrieval_v1.json")
    entity_manifest = read(ROOT / "data/derived/phase_a_entity_retrieval/manifest.json")
    title_manifest = read(ROOT / "data/derived/phase_a_title_retrieval/manifest.json")
    if entity["manifest_sha256"] != sha256_file(ROOT / "data/derived/phase_a_entity_retrieval/manifest.json"):
        raise ValueError("entity manifest mismatch")
    if title["manifest_sha256"] != sha256_file(ROOT / "data/derived/phase_a_title_retrieval/manifest.json"):
        raise ValueError("title manifest mismatch")
    if title_manifest["entity_manifest_sha256"] != entity["manifest_sha256"]:
        raise ValueError("candidate lineage mismatch")
    if entity["test_cohort_used"] or title["test_cohort_used"]:
        raise ValueError("holdout used in Phase A retrieval")
    et = entity["cohorts"]["validation"]["totals"]
    tt = title["cohorts"]["validation"]["totals"]
    if et["positive"] != tt["positive"] or et["possible_pairs"] != tt["possible_pairs"]:
        raise ValueError("candidate denominator changed between routes")
    if et["union_pairs"] != tt["prior_pairs"] or et["union_positive"] != tt["prior_positive"]:
        raise ValueError("candidate chaining mismatch")
    if multi["expert_label_denominator"] != 1140 or multi["current_primary_represented"] != 1066:
        raise ValueError("top20 denominator drift")
    field_policy = (ROOT / "configs/field_policy.yaml").read_text(encoding="utf-8")
    if "approved_model_fields: []" not in field_policy:
        raise ValueError("official model field policy changed")
    result = {
        "classification": "exploratory_phase_a_contract_audit",
        "raw_hashes_verified": True,
        "ranking": {"organizations": len(by), "labels": sum(map(len, by.values())),
                    "columns": columns, "each_org_has_unique_ranks_1_to_20": valid_ranks,
                    "queue_relative_top20_source_supported": True,
                    "numeric_direction_source_confirmed": False,
                    "local_active_queue_snapshot_present": False,
                    "published_schema_reconciled": False,
                    "rank1_highest": "assumption_only",
                    "non_top20_items": "unjudged_for_graded_relevance"},
        "ambiguous_alerts": {"multi_membership_source_confirmed": False,
                             "primary_top20_denominator": 1140,
                             "primary_coverage_numerator": 1066,
                             "primary_coverage_ceiling": 1066 / 1140,
                             "optimistic_all_assignment_coverage_numerator": multi["all_assignment_edges_optimistic_represented"],
                             "additional_validly_recoverable_needed_for_95_percent": 17,
                             "primary_exclusion_policy_changed": False},
        "retrieval_validation": {"organizations": 67,
                                 "positive_pairs": et["positive"],
                                 "possible_pairs": et["possible_pairs"],
                                 "baseline_pairs": et["baseline_pairs"],
                                 "baseline_positive": et["baseline_positive"],
                                 "entity_union_pairs": et["union_pairs"],
                                 "entity_union_positive": et["union_positive"],
                                 "title_union_pairs": tt["union_pairs"],
                                 "title_union_positive": tt["union_positive"],
                                 "final_micro_candidate_recall": tt["union_positive"] / tt["positive"],
                                 "final_candidate_pair_coverage": tt["union_pairs"] / tt["possible_pairs"],
                                 "target_99_percent_met": title["target_met_on_validation"]},
        "leakage_and_provenance": {"generation_label_store_read": False,
                                   "evaluator_truth_loaded_after_candidate_hash_freeze": True,
                                   "retrieval_organizations": entity_manifest["cohort_counts"],
                                   "historical_ranked_orgs": len(historical),
                                   "rerun_ranked_orgs": len(rerun),
                                   "new_confirmatory_ranked_orgs": 0,
                                   "official_approved_model_fields": [],
                                   "entity_and_title_point_in_time_confirmed": False,
                                   "external_transfer_approved": False,
                                   "public_identifier_bearing_output": False},
        "runtime": {"entity_generation_seconds": entity_manifest["seconds"],
                    "title_generation_seconds": None,
                    "full_end_to_end_latency_seconds": None,
                    "note": "Generation runtime is a local research timing, not SOC service latency."},
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                          (rank_path, ROOT / "data/raw/GUIDE_Test.csv",
                           ROOT / "data/derived/preprocessing/split_manifest.json",
                           PRIVATE / "split.json", ROOT / "configs/field_policy.yaml",
                           Path(__file__))},
        "production_ready": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ranking": result["ranking"],
                      "retrieval_validation": result["retrieval_validation"],
                      "new_confirmatory_ranked_orgs": 0}, indent=2))


if __name__ == "__main__":
    main()
