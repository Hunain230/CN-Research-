"""Seal Phase 34 baseline and two fixed rank predictions before official scoring."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts"
DATA = HERE / "dataset"
NAMES = ("baseline", "top20_logistic", "priority_ridge")


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    manifest = json.loads((DATA / "development_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["queues"]) == 15 and manifest["seed"] == 34102
    visible = DATA / "receiver_visible/development"
    params = {name: json.loads((ART / f"{name}_params.json").read_text(encoding="utf-8"))
              for name in NAMES[1:]}
    for name in NAMES:
        if (ART / f"development_{name}_predictions.jsonl").exists():
            raise FileExistsError(name)
    files = {name: (ART / f"development_{name}_predictions.jsonl").open("w", encoding="utf-8", newline="\n")
             for name in NAMES}
    decisions_path = ART / "development_baseline_decisions.jsonl"
    if decisions_path.exists(): raise FileExistsError(decisions_path)
    try:
        with decisions_path.open("w", encoding="utf-8", newline="\n") as audit:
            for item in manifest["queues"]:
                q = item["queue_id"]
                baseline, decisions = ranker.p32.predict_queue(visible, "development", q, 1)
                files["baseline"].write(json.dumps(baseline, sort_keys=True) + "\n")
                audit.write(json.dumps(decisions, sort_keys=True) + "\n")
                for name in NAMES[1:]:
                    candidate = ranker.rerank(baseline, decisions, visible, params[name], name)
                    files[name].write(json.dumps(candidate, sort_keys=True) + "\n")
    finally:
        for f in files.values(): f.close()
    predictions = {name: ART / f"development_{name}_predictions.jsonl" for name in NAMES}
    base = lines(predictions["baseline"])
    for name in NAMES[1:]:
        for x, y in zip(base, lines(predictions[name])):
            assert x["queue_id"] == y["queue_id"] and x["eligible_alert_ids"] == y["eligible_alert_ids"]
            assert x["groups_ranked"][:10] == y["groups_ranked"][:10]
            assert sorted(map(tuple, x["groups_ranked"])) == sorted(map(tuple, y["groups_ranked"]))
    seal = {"manifest_sha256": sha(DATA / "development_manifest.json"),
        "config_sha256": sha(HERE / "config.json"), "generator_sha256": sha(HERE / "generator.py"),
        "phase32_model_sha256": sha(ranker.P32_PATH), "ranker_source_sha256": sha(HERE / "ranker.py"),
        "model_params_sha256": {name: sha(ART / f"{name}_params.json") for name in NAMES[1:]},
        "predictions_sha256": {name: sha(path) for name, path in predictions.items()},
        "decisions_sha256": sha(decisions_path),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (ART / "development_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    truth = DATA / "evaluator_only/development/ground_truth_private"
    results = {}
    for name in NAMES:
        output = ART / f"development_{name}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(predictions[name]),
                        "--truth-root", str(truth), "--out", str(output)], check=True)
        results[name] = json.loads(output.read_text(encoding="utf-8"))
    baseline = results["baseline"]["summary"]
    rows = []; queues = []
    for name in NAMES:
        s = results[name]["summary"]
        regressions = 0
        for b, c in zip(results["baseline"]["queues"], results[name]["queues"]):
            assert b["queue_id"] == c["queue_id"]
            regressions += c["false_grouped_pairs"] > b["false_grouped_pairs"] or c["mixed_predicted_groups"] > b["mixed_predicted_groups"]
            queues.append({"candidate": name, "queue_id": b["queue_id"],
                "baseline_recall": b["recall20_count"], "candidate_recall": c["recall20_count"],
                "baseline_recoverable": b["recoverable"], "candidate_recoverable": c["recoverable"],
                "baseline_p10": b["p10_count"], "candidate_p10": c["p10_count"],
                "baseline_false_pairs": b["false_grouped_pairs"], "candidate_false_pairs": c["false_grouped_pairs"],
                "baseline_mixed_groups": b["mixed_predicted_groups"], "candidate_mixed_groups": c["mixed_predicted_groups"]})
        gate = (name != "baseline" and s["recall20_count"] >= 270 and
            s["recall20_count"] > baseline["recall20_count"] and
            s["recoverable"] >= 255 and s["recoverable"] >= baseline["recoverable"] and
            s["p10_count"] >= baseline["p10_count"] and s["grouped_pair_precision"] >= .9 and
            s["false_grouped_pairs"] <= baseline["false_grouped_pairs"] and
            s["mixed_predicted_groups"] <= baseline["mixed_predicted_groups"] and regressions == 0)
        rows.append({"candidate": name, "recall20_count": s["recall20_count"],
            "recall_denominator": s["expert_top20"], "recoverable": s["recoverable"],
            "p10_count": s["p10_count"], "p10_denominator": 150,
            "pair_tp": s["pair_tp"], "false_pairs": s["false_grouped_pairs"],
            "mixed_groups": s["mixed_predicted_groups"], "pair_precision": s["grouped_pair_precision"],
            "queue_safety_regressions": regressions, "development_gate": gate,
            "prediction_sha256": seal["predictions_sha256"][name]})
    for filename in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv"):
        with (HERE / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(queues[0])); writer.writeheader(); writer.writerows(queues)
    selected = sorted((r for r in rows if r["development_gate"]),
                      key=lambda r: (-r["recall20_count"], -r["p10_count"], r["candidate"]))
    decision = {"selected": selected[0]["candidate"] if selected else None,
                "development_gate_passed": bool(selected), "rows": rows}
    (ART / "development_selection.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__": main()
