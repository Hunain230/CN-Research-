"""Evaluate one sealed, matched Phase 36 candidate on fresh development."""
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


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    manifest_path = DATA / "development_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["seed"] == 36102 and len(manifest["queues"]) == 15
    visible = DATA / "receiver_visible/development"
    params_path = ART / "candidate_params.json"
    params = json.loads(params_path.read_text(encoding="utf-8"))
    bp = ART / "development_baseline_predictions.jsonl"
    cp = ART / "development_candidate_predictions.jsonl"
    dp = ART / "development_baseline_decisions.jsonl"
    assert not any(x.exists() for x in (bp, cp, dp))
    with bp.open("w", encoding="utf-8", newline="\n") as b, cp.open("w", encoding="utf-8", newline="\n") as c, dp.open("w", encoding="utf-8", newline="\n") as d:
        for item in manifest["queues"]:
            p, decision = ranker.p32.predict_queue(visible, "development", item["queue_id"], 1)
            candidate = ranker.rerank(p, decision, visible, params)
            b.write(json.dumps(p, sort_keys=True) + "\n")
            c.write(json.dumps(candidate, sort_keys=True) + "\n")
            d.write(json.dumps(decision, sort_keys=True) + "\n")
    base, cand = lines(bp), lines(cp)
    for x, y in zip(base, cand):
        assert x["queue_id"] == y["queue_id"] and x["eligible_alert_ids"] == y["eligible_alert_ids"]
        assert x["groups_ranked"][:10] == y["groups_ranked"][:10]
        assert sorted(map(tuple, x["groups_ranked"])) == sorted(map(tuple, y["groups_ranked"]))
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    seal = {"manifest_sha256": sha(manifest_path), "config_sha256": sha(HERE / "config.json"),
            "generator_sha256": sha(HERE / "generator.py"), "ranker_sha256": sha(HERE / "ranker.py"),
            "params_sha256": sha(params_path), "phase32_model_sha256": sha(ranker.p34.P32_PATH),
            "evaluator_sha256": sha(evaluator), "baseline_prediction_sha256": sha(bp),
            "candidate_prediction_sha256": sha(cp), "decisions_sha256": sha(dp),
            "receiver_visible_sha256": {p.relative_to(HERE).as_posix(): sha(p) for p in sorted(visible.rglob("*.jsonl"))}}
    (ART / "development_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    truth = DATA / "evaluator_only/development/ground_truth_private"
    results = {}
    for name, pred in (("baseline", bp), ("candidate", cp)):
        out = ART / f"development_{name}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(pred),
                        "--truth-root", str(truth), "--out", str(out)], check=True)
        results[name] = json.loads(out.read_text(encoding="utf-8"))
    bs, cs = results["baseline"]["summary"], results["candidate"]["summary"]
    queue_rows = []
    for b, c in zip(results["baseline"]["queues"], results["candidate"]["queues"]):
        assert b["queue_id"] == c["queue_id"]
        queue_rows.append({"queue_id": b["queue_id"], "baseline_recall": b["recall20_count"],
                           "candidate_recall": c["recall20_count"], "baseline_p10": b["p10_count"],
                           "candidate_p10": c["p10_count"], "baseline_recoverable": b["recoverable"],
                           "candidate_recoverable": c["recoverable"], "baseline_pair_tp": b["pair_tp"],
                           "candidate_pair_tp": c["pair_tp"], "baseline_false_pairs": b["false_grouped_pairs"],
                           "candidate_false_pairs": c["false_grouped_pairs"],
                           "baseline_mixed_groups": b["mixed_predicted_groups"],
                           "candidate_mixed_groups": c["mixed_predicted_groups"],
                           "safety_regression": c["false_grouped_pairs"] > b["false_grouped_pairs"] or
                             c["mixed_predicted_groups"] > b["mixed_predicted_groups"] or
                             c["p10_count"] < b["p10_count"] or c["recoverable"] < b["recoverable"]})
    with (HERE / "QUEUE_LEVEL_AUDIT.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(queue_rows[0])); w.writeheader(); w.writerows(queue_rows)
    rows = []
    for name, s in (("baseline", bs), ("candidate_a_evidence_aware", cs)):
        rows.append({"method": name, "recall20_count": s["recall20_count"], "denominator": s["expert_top20"],
                     "recoverable": s["recoverable"], "p10_count": s["p10_count"],
                     "p10_denominator": 150, "pair_precision": s["grouped_pair_precision"],
                     "pair_tp": s["pair_tp"], "false_pairs": s["false_grouped_pairs"],
                     "mixed_groups": s["mixed_predicted_groups"],
                     "prediction_sha256": s["prediction_sha256"]})
    with (HERE / "DEVELOPMENT_RESULTS.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    gates = {"recall_at_least_90": cs["recall20_count"] >= 270,
             "recall_above_baseline": cs["recall20_count"] > bs["recall20_count"],
             "recoverability_noninferior": cs["recoverable"] >= bs["recoverable"],
             "p10_noninferior": cs["p10_count"] >= bs["p10_count"],
             "pair_precision_at_least_99": cs["grouped_pair_precision"] >= .99,
             "false_pairs_noninferior": cs["false_grouped_pairs"] <= bs["false_grouped_pairs"],
             "mixed_groups_noninferior": cs["mixed_predicted_groups"] <= bs["mixed_predicted_groups"],
             "queue_safety": not any(x["safety_regression"] for x in queue_rows)}
    summary = {"baseline": bs, "candidate": cs, "gates": gates,
               "provisional_development_pass_pending_integrity_audit": all(gates.values())}
    (ART / "development_selection.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
