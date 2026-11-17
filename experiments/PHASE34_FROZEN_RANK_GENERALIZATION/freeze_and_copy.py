"""Hash every Phase 33 artifact; copy its frozen generator and validator."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    frozen = json.loads((P33 / "PHASE33_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in frozen["sha256"].items(): assert sha(ROOT / rel) == digest, rel
    seal = json.loads((P33 / "artifacts/pre_evaluation_seal.json").read_text(encoding="utf-8"))
    for name in ("baseline", "candidate"):
        assert sha(P33 / f"artifacts/{name}_predictions.jsonl") == seal["predictions_sha256"][name]
        assert sha(P33 / f"artifacts/{name}_decisions.jsonl") == seal["decisions_sha256"][name]
    assert sha(P31 / "model.py") == seal["baseline_model_sha256"]
    assert sha(P32 / "model.py") == seal["candidate_model_sha256"]
    historical = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(P33.rglob("*"))
                  if p.is_file() and "__pycache__" not in p.parts}
    (HERE / "PHASE33_HASH_INVENTORY.json").write_text(json.dumps(historical, indent=2), encoding="utf-8")
    for name in ("generator.py", "validate_generator.py"):
        source = P33 / name
        target = HERE / name
        if target.exists(): raise FileExistsError(target)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
    result = {"phase33_artifact_files": len(historical),
        "phase33_inventory_sha256": sha(HERE / "PHASE33_HASH_INVENTORY.json"),
        "phase33_result": "260/300 recall, 281/300 recoverability, 113/150 P@10, zero false pairs/mixed groups",
        "source_generator_sha256": sha(P33 / "generator.py"),
        "copied_generator_sha256": sha(HERE / "generator.py"),
        "validator_sha256": sha(HERE / "validate_generator.py"),
        "config_sha256": sha(HERE / "config.json"),
        "phase31_model_sha256": sha(P31 / "model.py"),
        "phase32_model_sha256": sha(P32 / "model.py"),
        "official_evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (HERE / "BASELINE_FREEZE.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"phase33_files_hashed": len(historical), "generator_copy_matches": True}))


if __name__ == "__main__": main()
