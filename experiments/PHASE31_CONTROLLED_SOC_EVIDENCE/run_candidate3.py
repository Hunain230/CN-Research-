"""One remaining development candidate: verified-union priority bonus."""
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
ARM = "evidence_aware_ranked"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = json.loads((DATA / "development_manifest.json").read_text(encoding="utf-8"))
    visible = DATA / "receiver_visible/development"
    pred = ART / f"development_{ARM}_predictions.jsonl"
    audit = ART / f"development_{ARM}_decisions.jsonl"
    if pred.exists() or audit.exists(): raise FileExistsError(pred)
    with pred.open("w", encoding="utf-8", newline="\n") as f, audit.open("w", encoding="utf-8", newline="\n") as a:
        for q in manifest["queues"]:
            row, decisions = model.predict_queue(visible, "development", q["queue_id"], ARM)
            f.write(json.dumps(row, sort_keys=True) + "\n")
            a.write(json.dumps(decisions, sort_keys=True) + "\n")
    seal = {"candidate": ARM, "prediction_sha256": sha(pred), "decisions_sha256": sha(audit),
        "model_sha256": sha(HERE / "model.py"), "config_sha256": sha(HERE / "config.json"),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (ART / "development_candidate3_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("official_evaluator", ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec); spec.loader.exec_module(evaluator)
    output = ART / f"development_{ARM}_evaluation.json"
    evaluator.evaluate(pred, DATA / "evaluator_only/development/ground_truth_private", output)
    candidate = json.loads(output.read_text(encoding="utf-8"))
    baseline = json.loads((ART / "development_original_subset_evaluation.json").read_text(encoding="utf-8"))
    r, b = candidate["summary"], baseline["summary"]
    regressions = sum(x["false_grouped_pairs"] > y["false_grouped_pairs"] or
                      x["mixed_predicted_groups"] > y["mixed_predicted_groups"]
                      for y, x in zip(baseline["queues"], candidate["queues"]))
    gate = (r["incident_recall20"] >= .8 and r["p10_count"] >= b["p10_count"] and
        r["grouped_pair_precision"] >= .9 and r["false_grouped_pairs"] <= b["false_grouped_pairs"] and
        r["mixed_predicted_groups"] <= b["mixed_predicted_groups"] and regressions == 0)
    row = {"split": "development", "arm": ARM, "queues": r["queues"],
        "recall_count": r["recall20_count"], "recall_denominator": r["expert_top20"],
        "recoverable": r["recoverable"], "p10_count": r["p10_count"],
        "p10_denominator": 10 * r["queues"], "pair_tp": r["pair_tp"],
        "false_pairs": r["false_grouped_pairs"], "mixed_groups": r["mixed_predicted_groups"],
        "pair_precision": r["grouped_pair_precision"], "accepted_unions": sum(len(json.loads(x)["accepted"])
            for x in audit.read_text(encoding="utf-8").splitlines()),
        "queue_safety_regressions": regressions, "gate": gate, "prediction_sha256": seal["prediction_sha256"]}
    for name in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv"):
        with (HERE / name).open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row)); writer.writerow(row)
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("a", encoding="utf-8", newline="") as f:
        fields = ["split", "arm", "queue_id", "recall", "recoverable", "p10", "pair_tp", "false_pairs", "mixed_groups"]
        writer = csv.DictWriter(f, fieldnames=fields)
        for q in candidate["queues"]:
            writer.writerow({"split": "development", "arm": ARM, "queue_id": q["queue_id"],
                "recall": q["recall20_count"], "recoverable": q["recoverable"], "p10": q["p10_count"],
                "pair_tp": q["pair_tp"], "false_pairs": q["false_grouped_pairs"],
                "mixed_groups": q["mixed_predicted_groups"]})
    print(json.dumps(row, indent=2))


if __name__ == "__main__": main()
