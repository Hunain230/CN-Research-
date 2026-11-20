"""Recreate the frozen synthetic cohort in temporary space and compare both arms.

Run from the repository root with Python 3.12. This never overwrites the
archived experiment. The rerun uses the same seed and is a reproducibility
check, not an independent new test set.
"""
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/model.py"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py"
EVALUATOR = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
ARCHIVED = json.loads((STUDY / "HOLDOUT_SUMMARY.json").read_text(encoding="utf-8"))
FREEZE = json.loads((STUDY / "PHASE33_FREEZE.json").read_text(encoding="utf-8"))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for rel, digest in FREEZE["sha256"].items():
        assert sha(ROOT / rel) == digest, f"Frozen source changed: {rel}"
    with tempfile.TemporaryDirectory(prefix="soc_frozen_replay_") as temporary:
        here = Path(temporary)
        for name in ("generator.py", "config.json"):
            shutil.copyfile(STUDY / name, here / name)
        subprocess.run([sys.executable, str(here / "generator.py"), "--split", "locked_test"],
                       check=True, stdout=subprocess.DEVNULL)
        manifest = json.loads((here / "dataset/locked_test_manifest.json").read_text(encoding="utf-8"))
        assert sha(here / "dataset/locked_test_manifest.json") == sha(STUDY / "dataset/locked_test_manifest.json")
        visible = here / "dataset/receiver_visible/locked_test"
        truth = here / "dataset/evaluator_only/locked_test/ground_truth_private"
        models = {"baseline": module("replay_baseline", P31), "candidate": module("replay_candidate", P32)}
        results = {}
        for name, model in models.items():
            prediction = here / f"{name}.jsonl"
            with prediction.open("w", encoding="utf-8", newline="\n") as stream:
                for entry in manifest["queues"]:
                    q = entry["queue_id"]
                    if name == "baseline":
                        row, _ = model.predict_queue(visible, "locked_test", q, "evidence_aware_ranked", 100, 100)
                    else:
                        row, _ = model.predict_queue(visible, "locked_test", q, 1)
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
            output = here / f"{name}_evaluation.json"
            subprocess.run([sys.executable, str(EVALUATOR), "--predictions", str(prediction),
                            "--truth-root", str(truth), "--out", str(output)],
                           check=True, stdout=subprocess.DEVNULL)
            rerun = json.loads(output.read_text(encoding="utf-8"))
            for key in ("eligible_alerts", "expert_top20", "recoverable", "recall20_count", "p10_count",
                        "pair_tp", "false_grouped_pairs", "mixed_predicted_groups", "predicted_groups",
                        "candidate_pairs", "accepted_merges"):
                assert rerun["summary"][key] == ARCHIVED[name][key], (name, key)
            results[name] = rerun
        with (STUDY / "HOLDOUT_RESULTS.csv").open(newline="", encoding="utf-8") as stream:
            archived_rows = list(csv.DictReader(stream))
        for i, archived in enumerate(archived_rows):
            baseline, candidate = results["baseline"]["queues"][i], results["candidate"]["queues"][i]
            assert archived["queue_id"] == baseline["queue_id"] == candidate["queue_id"]
            for key, bkey, ckey in (("recall", "recall20_count", "recall20_count"),
                                    ("recoverable", "recoverable", "recoverable"),
                                    ("p10", "p10_count", "p10_count")):
                assert int(archived["baseline_" + key]) == baseline[bkey]
                assert int(archived["candidate_" + key]) == candidate[ckey]
        summary = {name: {k: results[name]["summary"][k] for k in
                 ("queues", "eligible_alerts", "recall20_count", "recoverable", "p10_count",
                  "false_grouped_pairs", "mixed_predicted_groups")} for name in results}
        print(json.dumps({"type": "same-seed reproducibility replay", "frozen_sources_verified": True,
                          "manifest_identical": True, "all_15_queue_counts_identical": True,
                          "result": summary}, indent=2))


if __name__ == "__main__":
    main()
