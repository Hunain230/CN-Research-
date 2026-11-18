"""Post-evaluation integrity, paired-incident and historical-freeze audit."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts"
DATA = HERE / "dataset"
P33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
PRIVATE_KEYS = {"incident_id", "scenario_id", "template_id", "true_relation",
                "priority_rank", "priority_score", "malicious", "attack_stage", "condition"}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def statuses(pred, truth_root):
    q = pred["queue_id"]
    truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
    oracle = lines(truth_root / f"{q}_priority.jsonl")
    top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
    sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
    positions = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        counts = Counter(truth[a] for a in group)
        for i, hits in counts.items():
            if i in top20 and hits / sizes[i] >= .8 and hits / len(group) >= .8:
                positions[i].append(pos)
    return {i: "recalled" if i in positions and min(positions[i]) <= 20 else
            "recoverable_unranked" if i in positions else "unrecoverable" for i in top20}


def main():
    inventory = json.loads((HERE / "PHASE33_HASH_INVENTORY.json").read_text(encoding="utf-8"))
    for rel, digest in inventory.items(): assert sha(ROOT / rel) == digest, rel
    freeze = json.loads((HERE / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    assert sha(HERE / "PHASE33_HASH_INVENTORY.json") == freeze["phase33_inventory_sha256"]
    seal = json.loads((ART / "development_pre_evaluation_seal.json").read_text(encoding="utf-8"))
    assert sha(HERE / "ranker.py") == seal["ranker_source_sha256"]
    assert sha(ranker.P32_PATH) == seal["phase32_model_sha256"]
    for name in ("baseline", "top20_logistic", "priority_ridge"):
        assert sha(ART / f"development_{name}_predictions.jsonl") == seal["predictions_sha256"][name]
        result = json.loads((ART / f"development_{name}_evaluation.json").read_text(encoding="utf-8"))
        assert result["summary"]["prediction_sha256"] == seal["predictions_sha256"][name]
    for name in ("top20_logistic", "priority_ridge"):
        assert sha(ART / f"{name}_params.json") == seal["model_params_sha256"][name]
    base = lines(ART / "development_baseline_predictions.jsonl")
    truth_root = DATA / "evaluator_only/development/ground_truth_private"
    results = {}
    for name in ("top20_logistic", "priority_ridge"):
        cand = lines(ART / f"development_{name}_predictions.jsonl")
        counts = Counter()
        for b, c in zip(base, cand):
            q = b["queue_id"]
            assert q == c["queue_id"]
            assert not set(c) & PRIVATE_KEYS
            assert b["groups_ranked"][:10] == c["groups_ranked"][:10]
            assert b["eligible_alert_ids"] == c["eligible_alert_ids"]
            assert sorted(map(tuple, b["groups_ranked"])) == sorted(map(tuple, c["groups_ranked"]))
            ledger = {x["artifact_id"]: x["evidence_available_minute"] for x in
                lines(DATA / "receiver_visible/development/evidence_ledger" / f"{q}.jsonl")}
            assert set(c["eligible_alert_ids"]) == {aid for aid, minute in ledger.items() if minute <= 100}
            before, after = statuses(b, truth_root), statuses(c, truth_root)
            counts["newly_recalled"] += sum(before[i] != "recalled" and after[i] == "recalled" for i in before)
            counts["lost_recalled"] += sum(before[i] == "recalled" and after[i] != "recalled" for i in before)
            counts["queues"] += 1
        base_eval = json.loads((ART / "development_baseline_evaluation.json").read_text(encoding="utf-8"))
        cand_eval = json.loads((ART / f"development_{name}_evaluation.json").read_text(encoding="utf-8"))
        for b, c in zip(base_eval["queues"], cand_eval["queues"]):
            assert b["queue_id"] == c["queue_id"]
            assert b["p10_count"] == c["p10_count"]
            assert b["pair_tp"] == c["pair_tp"]
            assert b["false_grouped_pairs"] == c["false_grouped_pairs"]
            assert b["mixed_predicted_groups"] == c["mixed_predicted_groups"]
        results[name] = dict(counts)
    results["phase33_historical_hashes_valid"] = True
    results["temporal_violations"] = 0
    results["private_feature_violations"] = 0
    results["holdout_generated"] = (DATA / "locked_test_manifest.json").exists()
    (ART / "post_evaluation_audit.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__": main()
