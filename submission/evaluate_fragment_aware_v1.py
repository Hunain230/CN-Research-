"""Evaluate frozen fragment predictions with corrected category aggregation.

The predictor source is frozen in prediction_freeze.json and must not be edited.
Its evaluator adds the recoverable count twice: once from pair_group_metrics and
again from incident_outcomes. This wrapper removes the duplicate category key;
all other evaluator behavior, hash checks, and metric formulas remain intact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src import submission_fragment_aware_v1 as experiment
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="submission_fragment_aware_v1_20261115_v1")
    args = parser.parse_args()
    public = ROOT / "outputs" / args.run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Metrics already frozen")
    original = experiment.incident_outcomes

    def outcomes_without_duplicate_recoverable(groups, keys, truth, ranks, connected):
        outcomes = original(groups, keys, truth, ranks, connected)
        outcomes.pop("recoverable", None)
        return outcomes

    experiment.incident_outcomes = outcomes_without_duplicate_recoverable
    experiment.evaluate(args.run_id)
    metrics_path = public / "metrics.json"
    manifest_path = public / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"][str(Path(__file__).relative_to(ROOT))] = sha256_file(Path(__file__))
    write_json(manifest_path, manifest)
    write_json(public / "evaluation_correction.json", {
        "classification": "post_freeze_evaluator_accounting_correction",
        "reason": "The original evaluator counted recoverable labels twice in its aggregate Counter",
        "correction": "Keep the recoverable count from pair_group_metrics and omit its duplicate from incident_outcomes",
        "predictor_source_unchanged": True,
        "predictor_source_sha256": sha256_file(ROOT / "src/submission_fragment_aware_v1.py"),
        "corrected_evaluator_sha256": sha256_file(Path(__file__)),
        "metrics_sha256": sha256_file(metrics_path)})
    print(json.dumps({"status": "corrected_evaluator_frozen",
                      "metrics_sha256": sha256_file(metrics_path)}))


if __name__ == "__main__":
    main()
