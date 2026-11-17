"""Record exact Phase 16 and recall-only inputs without modifying them."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"


def main():
    relevant = [PREV / "BASELINE_METRICS.json", PREV / "BASELINE_FREEZE.md",
        PREV / "FINAL_REPORT.md", PREV / "CANDIDATE_COMPARISON.csv",
        PREV / "FALSE_MERGE_AUDIT.md", PREV / "TEMPORAL_PROVENANCE_AUDIT.md",
        PREV / "run_development.py", PREV / "artifacts/development_source_depth.jsonl",
        PREV / "artifacts/development_source_depth_evaluation.json",
        PREV / "artifacts/fresh_candidate_evaluation.json",
        PREV / "artifacts/fresh_baseline_evaluation.json",
        V4 / "predict.py", V4 / "configs/study.json",
        ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in relevant}
    snapshot = {"historical_phase16_recall": "407/600", "historical_phase16_recoverability": "451/600",
        "prior_fresh_holdout": {"baseline_recall": "410/600", "source_depth_recall": "444/600",
            "baseline_p10": "193/300", "source_depth_p10": "190/300",
            "recoverability": "463/600", "false_pairs": 306, "mixed_groups": 252},
        "source_depth_score": "1.2*max(severity)+0.7*max(asset_criticality)+0.55*distinct(event_type)+0.7*min(distinct(source_id),10)",
        "source_depth_tie_break": "group's first alert ID ascending",
        "development_p10_gate_count": 97, "development_p10_denominator": 150,
        "sha256": hashes}
    (HERE / "BASELINE_FREEZE.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps({"hashed_files": len(hashes), "source_depth_development_sha256": hashes[
        "experiments/RECALL_ONLY_IMPROVEMENT/artifacts/development_source_depth.jsonl"]}))


if __name__ == "__main__":
    main()
