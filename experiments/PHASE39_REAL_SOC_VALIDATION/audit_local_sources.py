"""Read-only hash, header, policy, and frozen-model compatibility inventory."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = ROOT / "data/raw"
EXPECTED = {
    "GUIDE_Test.csv": "fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3",
    "GUIDE_Test_Queue_Rankings.csv": "e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6",
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    sources = {}
    for name, expected in EXPECTED.items():
        path = RAW / name
        digest = sha(path)
        assert digest == expected, name
        with path.open(encoding="utf-8-sig", newline="") as f:
            header = next(csv.reader(f))
        sources[name] = {"bytes": path.stat().st_size, "sha256": digest, "columns": header,
                         "prior_validation_hash_matched": True}
    prior = json.loads((ROOT / "data/derived/audit/validation.json").read_text(encoding="utf-8"))
    checks = prior["checks"]
    inventory = json.loads((ROOT / "experiments/PHASE38_INTEGRATED_RECALL_OPTIMIZATION/HISTORICAL_HASH_INVENTORY.json").read_text(encoding="utf-8"))
    assert len(inventory) == 1216
    for rel, digest in inventory.items(): assert sha(ROOT / rel) == digest, rel
    phase33 = json.loads((ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json").read_text(encoding="utf-8"))
    assert phase33["baseline"]["recall20_count"] == 250
    assert phase33["candidate"]["recall20_count"] == 260
    assert phase33["candidate"]["recoverable"] == 281
    assert phase33["candidate"]["p10_count"] == 113
    assert phase33["candidate"]["false_grouped_pairs"] == 0
    assert phase33["candidate"]["mixed_predicted_groups"] == 0
    frozen = {name: sha(ROOT / name) for name in (
        "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/predict.py",
        "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/model.py",
        "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py",
        "experiments/PHASE33_FROZEN_GENERALIZATION/config.json",
        "experiments/PHASE33_FROZEN_GENERALIZATION/PHASE33_FREEZE.json",
        "experiments/PHASE33_FROZEN_GENERALIZATION/artifacts/candidate_predictions.jsonl",
        "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json",
        "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py",
        "configs/field_policy.yaml")}
    policy = (ROOT / "configs/field_policy.yaml").read_text(encoding="utf-8")
    assert "approved_model_fields: []" in policy
    audit = {"sources": sources, "prior_validation": {
        "guide_alert_keys_distinct_composite": checks["guide_alert_keys_distinct_composite"],
        "guide_incidents_distinct_composite": checks["guide_incidents_distinct_composite"],
        "conflicting_alert_keys": checks["conflicting_incident_assignment_groups_per_composite_alert_key"],
        "ranking_rows": checks["ranking_rows"], "qualified_orgs": checks["qualified_orgs"],
        "rank_scope": checks["rank_scope"], "top20_completeness": checks["top20_completeness"]},
        "historical_files_verified": len(inventory),
        "frozen_source_sha256": frozen,
        "approved_model_fields": [],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "external_model_executed": False}
    (HERE / "LOCAL_SOURCE_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    freeze = {"candidate": "phase32_endpoint_fallback_bonus1_as_phase33",
              "baseline": "phase31_evidence_aware_ranked_as_phase33",
              "phase33_confirmed_synthetic_holdout": "260/300",
              "historical_files_verified": len(inventory),
              "historical_inventory_sha256": sha(ROOT / "experiments/PHASE38_INTEGRATED_RECALL_OPTIMIZATION/HISTORICAL_HASH_INVENTORY.json"),
              "source_sha256": frozen,
              "guide_sha256": {name: sources[name]["sha256"] for name in sources},
              "predictive_parameters": {"rank_bonus": 1, "decision_cutoff_minute": 100, "component_cap": 100},
              "preprocessing": "Phase31 visible_input; no real-data adapter approved or run",
              "real_dataset_compatible": False, "real_evaluation_run": False}
    out = HERE / "BASELINE_FREEZE.json"
    if out.exists(): assert json.loads(out.read_text(encoding="utf-8")) == freeze
    else: out.write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"guide_bytes": sources["GUIDE_Test.csv"]["bytes"],
                      "historical_files_verified": len(inventory),
                      "conflicting_alert_keys": audit["prior_validation"]["conflicting_alert_keys"],
                      "model_fields_approved": 0}))


if __name__ == "__main__": main()
