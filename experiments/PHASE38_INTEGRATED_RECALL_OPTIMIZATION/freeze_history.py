"""Freeze and recheck Phase 32–37 historical artifacts."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHASES = ("PHASE32_SAFE_EVIDENCE_RECOVERY", "PHASE33_FROZEN_GENERALIZATION",
          "PHASE34_FROZEN_RANK_GENERALIZATION", "PHASE35_NEAR_BOUNDARY_RANKING",
          "PHASE36_EVIDENCE_AWARE_RECALL", "PHASE37_EVIDENCE_AVAILABILITY_RESEARCH")


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inventory = {p.relative_to(ROOT).as_posix(): sha(p) for phase in PHASES
                 for p in sorted((ROOT / "experiments" / phase).rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    path = HERE / "HISTORICAL_HASH_INVENTORY.json"
    if path.exists(): assert json.loads(path.read_text(encoding="utf-8")) == inventory
    else: path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    freeze = {"files": len(inventory), "inventory_sha256": sha(path),
              "phase32_model_sha256": sha(ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py"),
              "phase15_evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"),
              "generator_sha256": sha(HERE / "generator.py"),
              "historical_phase33_holdout_recall": "260/300",
              "historical_phase36_development_recall": "262/300",
              "phase37_reconstruction_decision": "NO-GO"}
    out = HERE / "BASELINE_FREEZE.json"
    if out.exists(): assert json.loads(out.read_text(encoding="utf-8")) == freeze
    else: out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps(freeze))


if __name__ == "__main__": main()
