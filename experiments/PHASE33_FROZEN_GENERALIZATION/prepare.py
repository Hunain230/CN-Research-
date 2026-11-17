"""Verify Phase 32 freeze and copy the exact Phase 31 v2 generator inputs."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    frozen = json.loads((P32 / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in frozen["sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    for name in ("generator.py", "config.json", "validate_generator.py"):
        source = P31 / name
        target = HERE / name
        if target.exists(): raise FileExistsError(target)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
    files = [P31 / "model.py", P32 / "model.py", P31 / "generator.py", P31 / "config.json",
        P31 / "validate_generator.py", P31 / "artifacts/development_evidence_aware_ranked_predictions.jsonl",
        P31 / "artifacts/development_evidence_aware_ranked_evaluation.json",
        P32 / "artifacts/development_endpoint_fallback_bonus1_predictions.jsonl",
        P32 / "artifacts/development_endpoint_fallback_bonus1_evaluation.json",
        P32 / "artifacts/development_pre_evaluation_seal.json",
        ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py",
        HERE / "PHASE33_PLAN.md", HERE / "generator.py", HERE / "config.json", HERE / "validate_generator.py"]
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()
    result = {"candidate": "endpoint_fallback_bonus1", "baseline": "evidence_aware_ranked",
        "phase32_development": {"recall": "169/200", "recoverability": "177/200", "p10": "73/100",
            "false_pairs": 0, "mixed_groups": 0, "phase32_go": False},
        "locked_test": {"seed": 31103, "queues": 15, "template_variant": 2, "generated": False},
        "historical_hash_verification": "pass", "sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
        "working_tree_before_generation": status}
    (HERE / "PHASE33_FREEZE.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"hash_verification": "pass", "frozen_files": len(files), "locked_test_generated": False}))


if __name__ == "__main__": main()
