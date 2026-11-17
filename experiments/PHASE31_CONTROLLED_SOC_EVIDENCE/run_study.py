"""Seal all matched predictions before invoking the unchanged official evaluator."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "dataset"
ART = HERE / "artifacts"
ARMS = ("original_subset", "legacy_rich", "evidence_aware")
SPEC = json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(split):
    manifest = json.loads((DATA / f"{split}_manifest.json").read_text(encoding="utf-8"))
    visible = DATA / "receiver_visible" / split
    truth = DATA / "evaluator_only" / split / "ground_truth_private"
    ART.mkdir(exist_ok=True)
    paths = {}
    for arm in ARMS:
        prediction = ART / f"{split}_{arm}_predictions.jsonl"
        audit = ART / f"{split}_{arm}_decisions.jsonl"
        if prediction.exists() or audit.exists(): raise FileExistsError(prediction)
        with prediction.open("w", encoding="utf-8", newline="\n") as f, audit.open("w", encoding="utf-8", newline="\n") as a:
            for queue in manifest["queues"]:
                row, decisions = model.predict_queue(visible, split, queue["queue_id"], arm,
                    SPEC["decision_minute"], SPEC["component_cap"])
                f.write(json.dumps(row, sort_keys=True) + "\n")
                a.write(json.dumps(decisions, sort_keys=True) + "\n")
        paths[arm] = prediction
    seal = {"split": split, "prediction_sha256": {arm: sha(path) for arm, path in paths.items()},
        "decision_sha256": {arm: sha(ART / f"{split}_{arm}_decisions.jsonl") for arm in ARMS},
        "model_sha256": sha(HERE / "model.py"), "config_sha256": sha(HERE / "config.json"),
        "generator_sha256": sha(HERE / "generator.py"),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (ART / f"{split}_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    # Private truth access begins only after all predictions and their hashes exist.
    spec = importlib.util.spec_from_file_location("official_evaluator", ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec); spec.loader.exec_module(evaluator)
    results = {}
    for arm in ARMS:
        output = ART / f"{split}_{arm}_evaluation.json"
        evaluator.evaluate(paths[arm], truth, output)
        results[arm] = json.loads(output.read_text(encoding="utf-8"))
    base = results["original_subset"]
    rows = []
    for arm in ARMS:
        r = results[arm]["summary"]
        queue_regressions = sum(x["false_grouped_pairs"] > b["false_grouped_pairs"] or
                                x["mixed_predicted_groups"] > b["mixed_predicted_groups"]
                                for b, x in zip(base["queues"], results[arm]["queues"]))
        gate = (r["incident_recall20"] >= .8 and r["recall20_count"] > base["summary"]["recall20_count"] and
            r["p10_count"] >= base["summary"]["p10_count"] and
            r["grouped_pair_precision"] >= .9 and
            r["false_grouped_pairs"] <= base["summary"]["false_grouped_pairs"] and
            r["mixed_predicted_groups"] <= base["summary"]["mixed_predicted_groups"] and
            queue_regressions == 0)
        rows.append({"split": split, "arm": arm, "queues": r["queues"],
            "recall_count": r["recall20_count"], "recall_denominator": r["expert_top20"],
            "recoverable": r["recoverable"], "p10_count": r["p10_count"],
            "p10_denominator": 10 * r["queues"], "pair_tp": r["pair_tp"],
            "false_pairs": r["false_grouped_pairs"], "mixed_groups": r["mixed_predicted_groups"],
            "pair_precision": r["grouped_pair_precision"], "accepted_unions": sum(
                len(x["accepted"]) for x in map(json.loads, (ART / f"{split}_{arm}_decisions.jsonl").read_text(encoding="utf-8").splitlines())),
            "queue_safety_regressions": queue_regressions, "gate": gate,
            "prediction_sha256": seal["prediction_sha256"][arm]})
    for filename in (("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv") if split == "development" else ("HOLDOUT_RESULTS.csv",)):
        with (HERE / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (HERE / ("QUEUE_LEVEL_AUDIT.csv" if split == "development" else "HOLDOUT_QUEUE_LEVEL_AUDIT.csv")).open(
            "w", encoding="utf-8", newline="") as f:
        fields = ["split", "arm", "queue_id", "recall", "recoverable", "p10", "pair_tp", "false_pairs", "mixed_groups"]
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for arm in ARMS:
            for q in results[arm]["queues"]:
                writer.writerow({"split": split, "arm": arm, "queue_id": q["queue_id"],
                    "recall": q["recall20_count"], "recoverable": q["recoverable"],
                    "p10": q["p10_count"], "pair_tp": q["pair_tp"],
                    "false_pairs": q["false_grouped_pairs"], "mixed_groups": q["mixed_predicted_groups"]})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--split", required=True, choices=("development", "locked_test"))
    main(parser.parse_args().split)
