"""One sealed matched holdout evaluation of Phase 31 baseline and Phase 32 +1."""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"
ART = HERE / "artifacts"
SPLIT = "locked_test"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    frozen = json.loads((HERE / "PHASE33_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in frozen["sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    manifest_path = HERE / "dataset/locked_test_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["split"] == SPLIT and manifest["seed"] == 31103
    assert manifest["template_variant"] == 2 and len(manifest["queues"]) == 15
    visible = HERE / "dataset/receiver_visible/locked_test"
    p31 = module("frozen_phase31_model", P31 / "model.py")
    p32 = module("frozen_phase32_model", P32 / "model.py")
    ART.mkdir(exist_ok=True)
    outputs = {}
    for name in ("baseline", "candidate"):
        pred = ART / f"{name}_predictions.jsonl"
        decisions = ART / f"{name}_decisions.jsonl"
        if pred.exists() or decisions.exists(): raise FileExistsError(pred)
        with pred.open("w", encoding="utf-8", newline="\n") as f, decisions.open("w", encoding="utf-8", newline="\n") as a:
            for item in manifest["queues"]:
                q = item["queue_id"]
                if name == "baseline": row, audit = p31.predict_queue(visible, SPLIT, q, "evidence_aware_ranked", 100, 100)
                else: row, audit = p32.predict_queue(visible, SPLIT, q, 1)
                f.write(json.dumps(row, sort_keys=True) + "\n")
                a.write(json.dumps(audit, sort_keys=True) + "\n")
        outputs[name] = (pred, decisions)
    b, c = lines(outputs["baseline"][0]), lines(outputs["candidate"][0])
    assert len(b) == len(c) == 15
    for x, y in zip(b, c):
        assert x["queue_id"] == y["queue_id"]
        assert x["eligible_alert_ids"] == y["eligible_alert_ids"]
        assert max(map(len, x["groups_ranked"])) <= 100 and max(map(len, y["groups_ranked"])) <= 100
    seal = {"manifest_sha256": sha(manifest_path), "generator_sha256": sha(HERE / "generator.py"),
        "config_sha256": sha(HERE / "config.json"),
        "runner_sha256": sha(HERE / "run_holdout.py"),
        "baseline_model_sha256": sha(P31 / "model.py"), "candidate_model_sha256": sha(P32 / "model.py"),
        "evaluator_sha256": sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"),
        "predictions_sha256": {name: sha(pred) for name, (pred, _) in outputs.items()},
        "decisions_sha256": {name: sha(decisions) for name, (_, decisions) in outputs.items()},
        "receiver_visible_sha256": {p.relative_to(HERE).as_posix(): sha(p) for p in sorted(visible.rglob("*.jsonl"))}}
    (ART / "pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    truth = HERE / "dataset/evaluator_only/locked_test/ground_truth_private"
    for name, (pred, _) in outputs.items():
        result = ART / f"{name}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(pred),
                        "--truth-root", str(truth), "--out", str(result)], check=True)
    base = json.loads((ART / "baseline_evaluation.json").read_text(encoding="utf-8"))
    cand = json.loads((ART / "candidate_evaluation.json").read_text(encoding="utf-8"))
    rows = []
    for x, y in zip(base["queues"], cand["queues"]):
        assert x["queue_id"] == y["queue_id"]
        rows.append({"queue_id": x["queue_id"], "baseline_recall": x["recall20_count"],
            "candidate_recall": y["recall20_count"], "baseline_recoverable": x["recoverable"],
            "candidate_recoverable": y["recoverable"], "baseline_p10": x["p10_count"],
            "candidate_p10": y["p10_count"], "baseline_pair_tp": x["pair_tp"],
            "candidate_pair_tp": y["pair_tp"], "baseline_false_pairs": x["false_grouped_pairs"],
            "candidate_false_pairs": y["false_grouped_pairs"],
            "baseline_mixed_groups": x["mixed_predicted_groups"],
            "candidate_mixed_groups": y["mixed_predicted_groups"]})
    with (HERE / "HOLDOUT_RESULTS.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    bs, cs = base["summary"], cand["summary"]
    queue_regressions = [r["queue_id"] for r in rows if
        r["candidate_false_pairs"] > r["baseline_false_pairs"] or
        r["candidate_mixed_groups"] > r["baseline_mixed_groups"]]
    gates = {"recall_at_least_85": cs["recall20_count"] >= 255,
        "recall_above_baseline": cs["recall20_count"] > bs["recall20_count"],
        "recoverability_at_least_85": cs["recoverable"] >= 255,
        "recoverability_noninferior": cs["recoverable"] >= bs["recoverable"],
        "p10_at_least_73": cs["p10_count"] >= 110,
        "p10_noninferior": cs["p10_count"] >= bs["p10_count"],
        "pair_precision_at_least_90": cs["grouped_pair_precision"] >= .9,
        "false_pairs_noninferior": cs["false_grouped_pairs"] <= bs["false_grouped_pairs"],
        "mixed_groups_noninferior": cs["mixed_predicted_groups"] <= bs["mixed_predicted_groups"],
        "queue_safety": not queue_regressions}
    summary = {"baseline": bs, "candidate": cs, "gates": gates,
               "queue_safety_regressions": queue_regressions,
               "provisional_go_pending_post_evaluation_audit": all(gates.values())}
    (HERE / "HOLDOUT_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
