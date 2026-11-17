"""Two fixed endpoint-fallback candidates on the frozen Phase 31 v2 development set."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
ART = HERE / "artifacts"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ART.mkdir(exist_ok=True)
    manifest = json.loads((P31 / "dataset/development_manifest.json").read_text(encoding="utf-8"))
    visible = P31 / "dataset/receiver_visible/development"
    outputs = {}
    for bonus in (1, 2):
        name = f"endpoint_fallback_bonus{bonus}"
        pred = ART / f"development_{name}_predictions.jsonl"
        audit = ART / f"development_{name}_decisions.jsonl"
        if pred.exists() or audit.exists(): raise FileExistsError(pred)
        with pred.open("w", encoding="utf-8", newline="\n") as f, audit.open("w", encoding="utf-8", newline="\n") as a:
            for q in manifest["queues"]:
                row, decisions = model.predict_queue(visible, "development", q["queue_id"], bonus)
                f.write(json.dumps(row, sort_keys=True) + "\n")
                a.write(json.dumps(decisions, sort_keys=True) + "\n")
        outputs[name] = (pred, audit)
    seal = {"model_sha256": sha(HERE / "model.py"),
        "phase31_model_sha256": sha(P31 / "model.py"),
        "generator_sha256": sha(P31 / "generator.py"),
        "config_sha256": sha(P31 / "config.json"),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"),
        "predictions_sha256": {name: sha(pred) for name, (pred, _) in outputs.items()},
        "decisions_sha256": {name: sha(audit) for name, (_, audit) in outputs.items()}}
    (ART / "development_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("official_evaluator", ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec); spec.loader.exec_module(evaluator)
    baseline = json.loads((P31 / "artifacts/development_evidence_aware_ranked_evaluation.json").read_text(encoding="utf-8"))
    b = baseline["summary"]
    rows = []; queue_rows = []
    for name, (pred, audit) in outputs.items():
        result_path = ART / f"development_{name}_evaluation.json"
        evaluator.evaluate(pred, P31 / "dataset/evaluator_only/development/ground_truth_private", result_path)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        s = result["summary"]
        queue_safety = 0
        for x, y in zip(baseline["queues"], result["queues"]):
            assert x["queue_id"] == y["queue_id"]
            queue_safety += y["false_grouped_pairs"] > x["false_grouped_pairs"] or y["mixed_predicted_groups"] > x["mixed_predicted_groups"]
            queue_rows.append({"candidate": name, "queue_id": x["queue_id"],
                "baseline_recall": x["recall20_count"], "candidate_recall": y["recall20_count"],
                "baseline_recoverable": x["recoverable"], "candidate_recoverable": y["recoverable"],
                "baseline_p10": x["p10_count"], "candidate_p10": y["p10_count"],
                "baseline_false_pairs": x["false_grouped_pairs"], "candidate_false_pairs": y["false_grouped_pairs"],
                "baseline_mixed_groups": x["mixed_predicted_groups"], "candidate_mixed_groups": y["mixed_predicted_groups"]})
        decisions = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines()]
        fallback_count = sum(sum(x["evidence_kind"] == "endpoint_process_plus_auth_network"
                                 for x in q["accepted"] if "evidence_kind" in x) for q in decisions)
        gate = (s["recall20_count"] >= 170 and s["recoverable"] >= 170 and
            s["p10_count"] >= b["p10_count"] and s["grouped_pair_precision"] >= .9 and
            s["false_grouped_pairs"] <= b["false_grouped_pairs"] and
            s["mixed_predicted_groups"] <= b["mixed_predicted_groups"] and queue_safety == 0)
        rows.append({"candidate": name, "recall20_count": s["recall20_count"], "recall_denominator": s["expert_top20"],
            "recoverable": s["recoverable"], "p10_count": s["p10_count"], "p10_denominator": 100,
            "pair_tp": s["pair_tp"], "false_pairs": s["false_grouped_pairs"],
            "mixed_groups": s["mixed_predicted_groups"], "pair_precision": s["grouped_pair_precision"],
            "fallback_unions": fallback_count, "queue_safety_regressions": queue_safety,
            "development_gate": gate, "prediction_sha256": sha(pred)})
    for filename in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv"):
        with (HERE / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(queue_rows[0])); writer.writeheader(); writer.writerows(queue_rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
