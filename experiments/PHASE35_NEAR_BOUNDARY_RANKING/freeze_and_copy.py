"""Inventory all Phase 34 files and copy its unchanged generator/validator."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P34 = ROOT / "experiments/PHASE34_FROZEN_RANK_GENERALIZATION"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    old = json.loads((P34 / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    assert sha(P34 / "PHASE33_HASH_INVENTORY.json") == old["phase33_inventory_sha256"]
    inventory = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(P34.rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts}
    (HERE / "PHASE34_HASH_INVENTORY.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    for name in ("generator.py", "validate_generator.py"):
        source = P34 / name; target = HERE / name
        if target.exists(): raise FileExistsError(target)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
    snapshot = {"phase34_files": len(inventory), "phase34_inventory_sha256": sha(HERE / "PHASE34_HASH_INVENTORY.json"),
        "confirmed_phase33_holdout_recall": "260/300", "phase34_development_recall": "267/300",
        "phase34_development_only": True,
        "generator_sha256": sha(HERE / "generator.py"), "config_sha256": sha(HERE / "config.json"),
        "validator_sha256": sha(HERE / "validate_generator.py"),
        "phase32_model_sha256": sha(P32 / "model.py"),
        "official_evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (HERE / "BASELINE_FREEZE.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps({"phase34_files_hashed": len(inventory), "generator_copy_matches": True}))


if __name__ == "__main__": main()
