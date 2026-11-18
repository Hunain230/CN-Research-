"""Verify the frozen Phase 35 paired development evaluation and safety claims."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts"
DATA = HERE / "dataset"
PRIVATE_KEYS = {"incident_id", "scenario_id", "template_id", "true_relation",
                "priority_rank", "priority_score", "malicious", "attack_stage", "condition"}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def status(pred, truth_root):
    q = pred["queue_id"]
    truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
    oracle = lines(truth_root / f"{q}_priority.jsonl")
    top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
    sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
    positions = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        counts = Counter(truth[a] for a in group)
        for incident, hits in counts.items():
            if incident in top20 and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                positions[incident].append(pos)
    return {i: "recalled" if positions[i] and min(positions[i]) <= 20 else
            "recoverable_unranked" if positions[i] else "unrecoverable" for i in top20}


def main():
    inventory = json.loads((HERE / "PHASE34_HASH_INVENTORY.json").read_text(encoding="utf-8"))
    assert len(inventory) == 179
    for rel, digest in inventory.items(): assert sha(ROOT / rel) == digest, rel
    freeze = json.loads((HERE / "BASELINE_FREEZE.json").read_text(encoding="utf-8"))
    assert sha(HERE / "PHASE34_HASH_INVENTORY.json") == freeze["phase34_inventory_sha256"]
    seal = json.loads((ART / "development_pre_evaluation_seal.json").read_text(encoding="utf-8"))
    checks = {"manifest_sha256": DATA / "development_manifest.json",
              "config_sha256": HERE / "config.json", "generator_sha256": HERE / "generator.py",
              "ranker_sha256": HERE / "ranker.py", "params_sha256": ART / "pairwise_params.json",
              "phase32_model_sha256": ranker.p34.P32_PATH,
              "baseline_prediction_sha256": ART / "development_baseline_predictions.jsonl",
              "candidate_prediction_sha256": ART / "development_candidate_predictions.jsonl",
              "decisions_sha256": ART / "development_baseline_decisions.jsonl",
              "evaluator_sha256": ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"}
    for key, path in checks.items(): assert sha(path) == seal[key], key
    baseline = lines(ART / "development_baseline_predictions.jsonl")
    candidate = lines(ART / "development_candidate_predictions.jsonl")
    decisions = lines(ART / "development_baseline_decisions.jsonl")
    assert len(baseline) == len(candidate) == len(decisions) == 15
    results = {name: json.loads((ART / f"development_{name}_evaluation.json").read_text(encoding="utf-8"))
               for name in ("baseline", "candidate")}
    for name in results:
        key = f"{name}_prediction_sha256"
        assert results[name]["summary"]["prediction_sha256"] == seal[key]
    truth_root = DATA / "evaluator_only/development/ground_truth_private"
    counts = Counter()
    details = []
    for b, c, d, be, ce in zip(baseline, candidate, decisions,
                                results["baseline"]["queues"], results["candidate"]["queues"]):
        q = b["queue_id"]
        assert q == c["queue_id"] == d["queue_id"] == be["queue_id"] == ce["queue_id"]
        assert not set(c) & PRIVATE_KEYS
        assert b["eligible_alert_ids"] == c["eligible_alert_ids"]
        assert b["groups_ranked"][:10] == c["groups_ranked"][:10]
        assert b["groups_ranked"][30:] == c["groups_ranked"][30:]
        assert sorted(map(tuple, b["groups_ranked"])) == sorted(map(tuple, c["groups_ranked"]))
        for key in ("p10_count", "recoverable", "pair_tp", "false_grouped_pairs",
                    "mixed_predicted_groups", "accepted_merges"):
            assert be[key] == ce[key], (q, key)
        ledger = {x["artifact_id"]: x["evidence_available_minute"] for x in
                  lines(DATA / "receiver_visible/development/evidence_ledger" / f"{q}.jsonl")}
        assert set(c["eligible_alert_ids"]) == {a for a, t in ledger.items() if t <= 100}
        before, after = status(b, truth_root), status(c, truth_root)
        gains = sum(before[i] != "recalled" and after[i] == "recalled" for i in before)
        losses = sum(before[i] == "recalled" and after[i] != "recalled" for i in before)
        counts["newly_recalled"] += gains
        counts["lost_recalled"] += losses
        counts["changed_queues"] += b["groups_ranked"] != c["groups_ranked"]
        counts["queues"] += 1
        details.append({"queue_id": q, "gains": gains, "losses": losses,
                        "baseline_recall": be["recall20_count"], "candidate_recall": ce["recall20_count"]})
    bs, cs = results["baseline"]["summary"], results["candidate"]["summary"]
    assert cs["recall20_count"] - bs["recall20_count"] == counts["newly_recalled"] - counts["lost_recalled"]
    assert not (DATA / "locked_test_manifest.json").exists()
    report = {"historical_phase34_files_unchanged": len(inventory), "prediction_seal_valid": True,
              "temporal_violations": 0, "private_feature_violations": 0,
              "top10_group_partition_and_tail_preserved": True, "holdout_generated": False,
              **dict(counts), "queue_details": details}
    (ART / "post_evaluation_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
