"""Verify hashes recorded by one or more new immutable run manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args()
    for run_id in args.run_ids:
        manifest_path = ROOT / "outputs" / run_id / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for relative, expected in manifest["sha256"].items():
            if digest(ROOT / relative) != expected:
                raise ValueError(f"Hash mismatch: {run_id}: {relative}")
        metrics_path = manifest_path.parent / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics.get("prediction_freeze_sha256") != digest(manifest_path.parent / "prediction_freeze.json"):
            raise ValueError(f"Prediction freeze reference mismatch: {run_id}")
        print(f"verified {run_id}: {len(manifest['sha256'])} source/output hashes")


if __name__ == "__main__":
    main()
