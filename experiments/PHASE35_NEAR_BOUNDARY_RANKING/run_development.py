"""One frozen pairwise candidate, paired with Phase 32 baseline on new development."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "dataset"
ART = HERE / "artifacts"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    manifest = json.loads((DATA / "development_manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 35102 and len(manifest["queues"]) == 15
    visible = DATA / "receiver_visible/development"
    params_path = ART / "pairwise_params.json"
    params = json.loads(params_path.read_text(encoding="utf-8"))
    base_path = ART / "development_baseline_predictions.jsonl"
    cand_path = ART / "development_candidate_predictions.jsonl"
    decisions_path = ART / "development_baseline_decisions.jsonl"
    if any(x.exists() for x in (base_path, cand_path, decisions_path)):
        raise FileExistsError("development predictions already exist")
    with base_path.open("w", encoding="utf-8", newline="\n") as baseline, \
         cand_path.open("w", encoding="utf-8", newline="\n") as candidate, \
         decisions_path.open("w", encoding="utf-8", newline="\n") as decisions_file:
        for item in manifest["queues"]:
            q = item["queue_id"]
            row, decisions = ranker.p32.predict_queue(visible, "development", q, 1)
            reranked = ranker.rerank(row, decisions, visible, params)
            baseline.write(json.dumps(row, sort_keys=True) + "\n")
            candidate.write(json.dumps(reranked, sort_keys=True) + "\n")
            decisions_file.write(json.dumps(decisions, sort_keys=True) + "\n")
    base, cand = lines(base_path), lines(cand_path)
    for x, y in zip(base, cand):
        assert x["queue_id"] == y["queue_id"] and x["eligible_alert_ids"] == y["eligible_alert_ids"]
        assert x["groups_ranked"][:10] == y["groups_ranked"][:10]
        assert x["groups_ranked"][30:] == y["groups_ranked"][30:]
        assert sorted(map(tuple, x["groups_ranked"])) == sorted(map(tuple, y["groups_ranked"]))
    seal = {"manifest_sha256": sha(DATA / "development_manifest.json"),
        "config_sha256": sha(HERE / "config.json"), "generator_sha256": sha(HERE / "generator.py"),
        "ranker_sha256": sha(HERE / "ranker.py"), "params_sha256": sha(params_path),
        "phase32_model_sha256": sha(ranker.p34.P32_PATH),
        "baseline_prediction_sha256": sha(base_path), "candidate_prediction_sha256": sha(cand_path),
        "decisions_sha256": sha(decisions_path),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")}
    (ART / "development_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    truth = DATA / "evaluator_only/development/ground_truth_private"
    results = {}
    for name, prediction in (("baseline", base_path), ("candidate", cand_path)):
        out = ART / f"development_{name}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(prediction),
                        "--truth-root", str(truth), "--out", str(out)], check=True)
        results[name] = json.loads(out.read_text(encoding="utf-8"))
    bs, cs = results["baseline"]["summary"], results["candidate"]["summary"]
    queue_rows = []; queue_safety = 0
    for b, c in zip(results["baseline"]["queues"], results["candidate"]["queues"]):
        assert b["queue_id"] == c["queue_id"]
        queue_safety += c["false_grouped_pairs"] > b["false_grouped_pairs"] or c["mixed_predicted_groups"] > b["mixed_predicted_groups"]
        queue_rows.append({"queue_id": b["queue_id"], "baseline_recall": b["recall20_count"],
            "candidate_recall": c["recall20_count"], "baseline_recoverable": b["recoverable"],
            "candidate_recoverable": c["recoverable"], "baseline_p10": b["p10_count"],
            "candidate_p10": c["p10_count"], "baseline_false_pairs": b["false_grouped_pairs"],
            "candidate_false_pairs": c["false_grouped_pairs"],
            "baseline_mixed_groups": b["mixed_predicted_groups"],
            "candidate_mixed_groups": c["mixed_predicted_groups"]})
    gates = {"recall_at_least_90": cs["recall20_count"] >= 270,
        "recall_improved": cs["recall20_count"] > bs["recall20_count"],
        "recoverability_at_least_85": cs["recoverable"] >= 255,
        "recoverability_noninferior": cs["recoverable"] >= bs["recoverable"],
        "p10_noninferior": cs["p10_count"] >= bs["p10_count"],
        "pair_precision_at_least_90": cs["grouped_pair_precision"] >= .9,
        "false_pairs_noninferior": cs["false_grouped_pairs"] <= bs["false_grouped_pairs"],
        "mixed_groups_noninferior": cs["mixed_predicted_groups"] <= bs["mixed_predicted_groups"],
        "queue_safety": queue_safety == 0}
    rows = []
    for name, s, pred in (("baseline", bs, base_path), ("pairwise_boundary", cs, cand_path)):
        rows.append({"method": name, "recall20_count": s["recall20_count"],
            "recall_denominator": s["expert_top20"], "recoverable": s["recoverable"],
            "p10_count": s["p10_count"], "p10_denominator": 150,
            "pair_tp": s["pair_tp"], "false_pairs": s["false_grouped_pairs"],
            "mixed_groups": s["mixed_predicted_groups"], "pair_precision": s["grouped_pair_precision"],
            "queue_safety_regressions": queue_safety if name != "baseline" else 0,
            "prediction_sha256": sha(pred)})
    with (HERE / "DEVELOPMENT_RESULTS.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(queue_rows[0])); writer.writeheader(); writer.writerows(queue_rows)
    summary = {"baseline": bs, "candidate": cs, "gates": gates,
               "development_gate_passed": all(gates.values())}
    (ART / "development_selection.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
