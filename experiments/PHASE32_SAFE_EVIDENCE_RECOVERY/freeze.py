"""Verify historical hashes and snapshot exact Phase 32 inputs."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P30 = ROOT / "experiments/PHASE30_SAFE_RECALL_IMPROVEMENT"
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    historical = json.loads((PREV / "BASELINE_METRICS.json").read_text(encoding="utf-8"))
    for rel, digest in historical["frozen_file_sha256"].items(): assert sha(ROOT / rel) == digest, rel
    phase30 = json.loads((P30 / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in phase30["sha256"].items(): assert sha(ROOT / rel) == digest, rel
    phase31 = json.loads((P31 / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in phase31["historical_files_sha256"].items(): assert sha(ROOT / rel) == digest, rel
    paths = [P31 / "config.json", P31 / "generator.py", P31 / "model.py",
        P31 / "dataset/development_manifest.json",
        P31 / "artifacts/development_evidence_aware_ranked_predictions.jsonl",
        P31 / "artifacts/development_evidence_aware_ranked_evaluation.json",
        P31 / "artifacts/development_evidence_aware_ranked_decisions.jsonl",
        P31 / "PHASE31_FINAL_REPORT.md", HERE / "model.py", HERE / "PHASE32_PLAN.md",
        ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"]
    snapshot = {"historical_references": {"phase16_recall": "407/600", "later_source_depth_holdout": "444/600",
        "phase31_v2_development_recall": "158/200", "phase31_v2_development_recoverability": "166/200",
        "phase31_v2_development_p10": "73/100", "phase31_v2_false_pairs": 0, "phase31_v2_mixed_groups": 0},
        "historical_hash_verification": "pass", "phase31_locked_test_generated": (P31 / "dataset/locked_test_manifest.json").exists(),
        "sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "working_tree": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()}
    (HERE / "BASELINE_FREEZE.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps({"hash_verification": "pass", "input_files": len(paths),
                      "locked_test_generated": snapshot["phase31_locked_test_generated"]}))


if __name__ == "__main__": main()
