"""Verify Phase 38 freeze, seals, paired incidents and leakage."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts"
DATA = HERE / "dataset"
PRIVATE = {"incident_id", "scenario_id", "template_id", "true_relation", "priority_rank",
           "priority_score", "malicious", "attack_stage", "condition"}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def status(pred, truth_root):
    q = pred["queue_id"]
    truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
    oracle = lines(truth_root / f"{q}_priority.jsonl")
    top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
    size = Counter(truth[a] for a in pred["eligible_alert_ids"])
    qualifies = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        counts = Counter(truth[a] for a in group)
        for i, n in counts.items():
            if i in top20 and n / size[i] >= .8 and n / len(group) >= .8:
                qualifies[i].append(pos)
    return {i: "recalled" if qualifies[i] and min(qualifies[i]) <= 20 else
            "recoverable_unranked" if qualifies[i] else "unrecoverable" for i in top20}


def main():
    freeze = json.loads((HERE / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    inventory_path = HERE / "HISTORICAL_HASH_INVENTORY.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert len(inventory) == freeze["files"] == 1216
    assert sha(inventory_path) == freeze["inventory_sha256"]
    for rel, digest in inventory.items(): assert sha(ROOT / rel) == digest, rel
    seal = json.loads((ART / "development_pre_evaluation_seal.json").read_text(encoding="utf-8"))
    checks = {"manifest_sha256": DATA / "development_manifest.json", "config_sha256": HERE / "config.json",
              "generator_sha256": HERE / "generator.py", "ranker_sha256": HERE / "ranker.py",
              "params_sha256": ART / "candidate_params.json", "phase32_model_sha256": ranker.p36.p34.P32_PATH,
              "evaluator_sha256": ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py",
              "baseline_prediction_sha256": ART / "development_baseline_predictions.jsonl",
              "candidate_prediction_sha256": ART / "development_candidate_predictions.jsonl",
              "decisions_sha256": ART / "development_baseline_decisions.jsonl"}
    for key, path in checks.items(): assert sha(path) == seal[key], key
    for rel, digest in seal["receiver_visible_sha256"].items(): assert sha(HERE / rel) == digest, rel
    train_seal = json.loads((ART / "train_pre_label_seal.json").read_text(encoding="utf-8"))
    assert sha(ART / "train_baseline_predictions.jsonl") == train_seal["predictions_sha256"]
    assert sha(ART / "train_baseline_decisions.jsonl") == train_seal["decisions_sha256"]
    assert sha(HERE / "ranker.py") == train_seal["ranker_sha256"]
    params = json.loads((ART / "candidate_params.json").read_text(encoding="utf-8"))
    assert params["fit_split"] == "phase38_train_only" and params["feature_order"] == list(ranker.FEATURE_ORDER)
    base = lines(ART / "development_baseline_predictions.jsonl")
    cand = lines(ART / "development_candidate_predictions.jsonl")
    decisions = lines(ART / "development_baseline_decisions.jsonl")
    evaluations = {n: json.loads((ART / f"development_{n}_evaluation.json").read_text(encoding="utf-8"))
                   for n in ("baseline", "candidate")}
    for name in evaluations:
        assert evaluations[name]["summary"]["prediction_sha256"] == seal[f"{name}_prediction_sha256"]
    assert len(base) == len(cand) == len(decisions) == 15
    truth_root = DATA / "evaluator_only/development/ground_truth_private"
    counts = Counter(); queue_details = []
    for b, c, d, be, ce in zip(base, cand, decisions,
                                evaluations["baseline"]["queues"], evaluations["candidate"]["queues"]):
        q = b["queue_id"]
        assert q == c["queue_id"] == d["queue_id"] == be["queue_id"] == ce["queue_id"]
        assert not set(c) & PRIVATE
        assert b["eligible_alert_ids"] == c["eligible_alert_ids"]
        assert b["groups_ranked"][:10] == c["groups_ranked"][:10]
        assert sorted(map(tuple, b["groups_ranked"])) == sorted(map(tuple, c["groups_ranked"]))
        for key in ("recoverable", "p10_count", "pair_tp", "false_grouped_pairs",
                    "mixed_predicted_groups", "accepted_merges"):
            assert be[key] == ce[key], (q, key)
        lookup, claims = ranker.p32.p31.visible_input(DATA / "receiver_visible/development", q, 100)
        assert set(c["eligible_alert_ids"]) == set(lookup)
        assert all(x["evidence_available_minute"] <= 100 for x in claims)
        assert all(not set(x) & PRIVATE for x in lookup.values())
        assert all(not set(x) & PRIVATE for x in claims)
        before, after = status(b, truth_root), status(c, truth_root)
        gained = sum(before[i] != "recalled" and after[i] == "recalled" for i in before)
        lost = sum(before[i] == "recalled" and after[i] != "recalled" for i in before)
        counts["newly_recalled"] += gained; counts["lost_recalled"] += lost
        counts["queues_with_recall_decline"] += ce["recall20_count"] < be["recall20_count"]
        counts["queues_changed_rank"] += b["groups_ranked"] != c["groups_ranked"]
        queue_details.append({"queue_id": q, "gained": gained, "lost": lost})
    bs, cs = evaluations["baseline"]["summary"], evaluations["candidate"]["summary"]
    assert cs["recall20_count"] - bs["recall20_count"] == counts["newly_recalled"] - counts["lost_recalled"]
    assert not (DATA / "locked_test_manifest.json").exists()
    report = {"historical_hashes_verified": len(inventory), "prediction_and_input_seals_valid": True,
              "top10_and_group_partition_preserved": True, "temporal_violations": 0,
              "private_feature_violations": 0, "holdout_generated": False,
              **dict(counts), "queue_details": queue_details}
    (ART / "post_evaluation_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
