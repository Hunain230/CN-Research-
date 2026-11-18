"""Record and verify Phase 32–35 historical artifacts before Phase 36 work."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHASES = ("PHASE32_SAFE_EVIDENCE_RECOVERY", "PHASE33_FROZEN_GENERALIZATION",
          "PHASE34_FROZEN_RANK_GENERALIZATION", "PHASE35_NEAR_BOUNDARY_RANKING")


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory = {}
    for phase in PHASES:
        for path in sorted((ROOT / "experiments" / phase).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                inventory[path.relative_to(ROOT).as_posix()] = sha(path)
    path = HERE / "HISTORICAL_HASH_INVENTORY.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        assert inventory == old, "historical artifact changed"
    else:
        path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    freeze = {"files": len(inventory), "inventory_sha256": sha(path),
              "phase32_reference": "endpoint_fallback_bonus1",
              "phase33_confirmed_holdout_recall": "260/300",
              "phase34_development_recall": "267/300",
              "phase35_development_recall": "258/300",
              "phase32_model_sha256": sha(ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py"),
              "official_evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"),
              "generator_sha256": sha(HERE / "generator.py"),
              "validator_sha256": sha(HERE / "validate_generator.py")}
    out = HERE / "BASELINE_FREEZE.json"
    if out.exists(): assert json.loads(out.read_text(encoding="utf-8")) == freeze
    else: out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps(freeze))


if __name__ == "__main__": main()
