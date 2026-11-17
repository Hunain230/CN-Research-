"""Verify old freezes and record Phase 31 split/code inventory."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"
P30 = ROOT / "experiments/PHASE30_SAFE_RECALL_IMPROVEMENT"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    prior = json.loads((PREV / "BASELINE_METRICS.json").read_text(encoding="utf-8"))
    for rel, digest in prior["frozen_file_sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    phase30 = json.loads((P30 / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in phase30["sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    references = [PREV / "FINAL_REPORT.md", PREV / "GO_NO_GO.md", PREV / "BASELINE_METRICS.json",
        PREV / "artifacts/fresh_candidate_evaluation.json", P30 / "PHASE30_FINAL_REPORT.md",
        P30 / "PHASE30_GO_NO_GO.md", P30 / "BASELINE_FREEZE.json",
        ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/experiments/locked_test_result.json",
        ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"]
    git_status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()
    frozen = {"historical_reference": {"phase16": "407/600", "source_depth_holdout": "444/600",
        "phase30_development": "220/300", "phase30_safe_new_unions": 0},
        "working_tree_at_phase31_start": "clean (recorded before implementation)",
        "working_tree_now": git_status,
        "prior_hash_verification": "pass", "historical_files_sha256": {
            p.relative_to(ROOT).as_posix(): sha(p) for p in references},
        "official_evaluator": "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"}
    (HERE / "BASELINE_FREEZE.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    manifest = {"schema": config["schema"], "config_sha256": sha(HERE / "config.json"),
        "generator_sha256": sha(HERE / "generator.py"),
        "splits": {s: json.loads((HERE / "dataset" / f"{s}_manifest.json").read_text(encoding="utf-8"))
                   if (HERE / "dataset" / f"{s}_manifest.json").exists() else
                   {"status": "not generated", **spec} for s, spec in config["splits"].items()},
        "pilot_v1": "archived after enhanced generator validation exposed weak false-context challenge and timestamp disorder"}
    (HERE / "SPLIT_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"prior_hash_verification": "pass", "historical_files": len(references),
                      "locked_test_generated": (HERE / "dataset/locked_test_manifest.json").exists()}))


if __name__ == "__main__": main()
