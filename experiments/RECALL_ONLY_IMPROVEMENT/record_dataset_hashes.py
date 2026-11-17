"""Inventory immutable historical data bytes for baseline reproducibility."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/datasets"


def main():
    paths = sorted(p for p in DATA.rglob("*") if p.is_file())
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    inventory = HERE / "artifacts/historical_dataset_hashes.json"
    inventory.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    snapshot_path = HERE / "BASELINE_METRICS.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["historical_dataset_file_count"] = len(hashes)
    snapshot["historical_dataset_hash_inventory"] = inventory.relative_to(HERE).as_posix()
    snapshot["historical_dataset_hash_inventory_sha256"] = hashlib.sha256(inventory.read_bytes()).hexdigest()
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(hashes), "inventory_sha256": snapshot["historical_dataset_hash_inventory_sha256"]}))


if __name__ == "__main__":
    main()
