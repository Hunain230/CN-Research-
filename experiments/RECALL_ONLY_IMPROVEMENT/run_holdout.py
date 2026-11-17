"""Single fresh synthetic holdout, with both predictions sealed before evaluation."""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
ART = HERE / "artifacts"
FRESH = ART / "fresh_cohort"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    sys.path.insert(0, str(HERE))
    from run_development import score

    selected = json.loads((ART / "selection_freeze.json").read_text(encoding="utf-8"))
    for name, digest in selected["frozen_files"].items():
        assert sha(ROOT / name) == digest, name
    generator = FRESH / "simulator.py"
    config_path = FRESH / "configs/study.json"
    assert sha(generator) == selected["generator_sha256"]
    assert sha(config_path) == selected["holdout_config_sha256"]
    if not (FRESH / "datasets/manifest.json").exists():
        subprocess.run([sys.executable, str(generator)], check=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads((FRESH / "datasets/manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["queues"]["locked_test"]) == 30
    predict = module("frozen_predict", V4 / "predict.py")
    source = ART / "fresh_baseline_predictions.jsonl"
    candidate = ART / "fresh_candidate_predictions.jsonl"
    if source.exists() or candidate.exists():
        raise FileExistsError("One-shot predictions already exist")
    with source.open("w", encoding="utf-8", newline="\n") as a, candidate.open("w", encoding="utf-8", newline="\n") as b:
        for item in manifest["queues"]["locked_test"]:
            queue = item["queue_id"]
            baseline, _ = predict.predict(FRESH / "datasets", "locked_test", queue,
                                          "lineage_one_context_v", config["decision_minute"], config["component_cap"])
            visible = predict.visible(FRESH / "datasets", "locked_test", queue, config["decision_minute"])
            lookup = {x["alert_id"]: x for x in visible}
            ranked = sorted(baseline["groups_ranked"], key=lambda g: (-score(g, lookup, "source_depth"), g[0]))
            changed = dict(baseline, groups_ranked=ranked, ranker="source_depth")
            a.write(json.dumps(baseline, sort_keys=True) + "\n")
            b.write(json.dumps(changed, sort_keys=True) + "\n")
    seals = {"baseline_sha256": sha(source), "candidate_sha256": sha(candidate),
             "generator_sha256": sha(generator), "holdout_config_sha256": sha(config_path)}
    (ART / "pre_evaluation_seal.json").write_text(json.dumps(seals, indent=2), encoding="utf-8")
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    truth = FRESH / "datasets/locked_test/ground_truth_private"
    for prediction, output in ((source, ART / "fresh_baseline_evaluation.json"),
                               (candidate, ART / "fresh_candidate_evaluation.json")):
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(prediction),
                        "--truth-root", str(truth), "--out", str(output)], check=True)
    base = json.loads((ART / "fresh_baseline_evaluation.json").read_text(encoding="utf-8"))
    cand = json.loads((ART / "fresh_candidate_evaluation.json").read_text(encoding="utf-8"))
    with (HERE / "HOLDOUT_RESULTS.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = ["queue_id", "baseline_recall", "candidate_recall", "baseline_recoverable",
                  "candidate_recoverable", "baseline_p10", "candidate_p10", "baseline_false_pairs",
                  "candidate_false_pairs", "baseline_mixed_groups", "candidate_mixed_groups"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for x, y in zip(base["queues"], cand["queues"]):
            assert x["queue_id"] == y["queue_id"]
            writer.writerow(dict(zip(fields, [x["queue_id"], x["recall20_count"], y["recall20_count"],
                x["recoverable"], y["recoverable"], x["p10_count"], y["p10_count"],
                x["false_grouped_pairs"], y["false_grouped_pairs"],
                x["mixed_predicted_groups"], y["mixed_predicted_groups"]])))
    print(json.dumps({"baseline": base["summary"], "candidate": cand["summary"]}, indent=2))


if __name__ == "__main__":
    main()
