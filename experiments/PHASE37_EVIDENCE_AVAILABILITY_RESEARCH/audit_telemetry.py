"""Verify sealed telemetry experiments and unchanged historical files."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts"
DATA = HERE / "dataset"
PRIVATE = {"incident_id", "scenario_id", "template_id", "true_relation", "priority_rank",
           "priority_score", "malicious", "attack_stage", "condition"}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    freeze = json.loads((HERE / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    inventory_path = HERE / "HISTORICAL_HASH_INVENTORY.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert len(inventory) == freeze["files"] and sha(inventory_path) == freeze["inventory_sha256"]
    for rel, digest in inventory.items(): assert sha(ROOT / rel) == digest, rel
    seal = json.loads((ART / "pre_evaluation_seal.json").read_text(encoding="utf-8"))
    assert sha(DATA / "development_manifest.json") == seal["manifest_sha256"]
    assert sha(ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py") == seal["model_sha256"]
    assert sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py") == seal["evaluator_sha256"]
    assert sha(HERE / "run_telemetry.py") == seal["runner_sha256"]
    for rel, digest in seal["visible_sha256"].items(): assert sha(HERE / rel) == digest, rel
    counts = {"conditions": 0, "queues": 0, "false_pairs": 0, "mixed_groups": 0,
              "temporal_violations": 0, "private_field_violations": 0}
    for condition in seal["predictions_sha256"]:
        pred = ART / f"{condition}_predictions.jsonl"
        decisions = ART / f"{condition}_decisions.jsonl"
        evaluation = json.loads((ART / f"{condition}_evaluation.json").read_text(encoding="utf-8"))
        assert sha(pred) == seal["predictions_sha256"][condition]
        assert sha(decisions) == seal["decisions_sha256"][condition]
        assert evaluation["summary"]["prediction_sha256"] == sha(pred)
        assert len(lines(pred)) == len(lines(decisions)) == len(evaluation["queues"]) == 15
        visible = DATA / "telemetry_conditions" / condition
        for row in lines(pred):
            q = row["queue_id"]
            alerts = lines(visible / "alerts" / f"{q}.jsonl")
            ledger = lines(visible / "evidence_ledger" / f"{q}.jsonl")
            claims = lines(visible / "claims" / f"{q}.jsonl")
            assert not any(set(x) & PRIVATE for x in alerts + ledger + claims)
            eligible = {x["alert_id"] for x in alerts if x["evidence_available_minute"] <= 100}
            assert set(row["eligible_alert_ids"]) == eligible
            assert row["cutoff"] == 100
        s = evaluation["summary"]
        counts["conditions"] += 1; counts["queues"] += 15
        counts["false_pairs"] += s["false_grouped_pairs"]
        counts["mixed_groups"] += s["mixed_predicted_groups"]
    assert counts["false_pairs"] == counts["mixed_groups"] == 0
    assert not (DATA / "locked_test_manifest.json").exists()
    counts["historical_hashes_verified"] = len(inventory)
    counts["additional_independent_capture_available"] = False
    (ART / "post_evaluation_audit.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__": main()
