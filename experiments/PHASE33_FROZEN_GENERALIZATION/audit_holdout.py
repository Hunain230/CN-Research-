"""Post-evaluation audit of sealed predictions, true unions, and paired queues."""
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"
ART = HERE / "artifacts"
VISIBLE = HERE / "dataset/receiver_visible/locked_test"
PRIVATE = HERE / "dataset/evaluator_only/locked_test"
PRIVATE_KEYS = {"incident_id", "scenario_id", "template_id", "true_relation",
                "priority_rank", "priority_score", "malicious", "attack_stage", "condition"}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def incident_status(pred, truth_root):
    q = pred["queue_id"]
    truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
    priority = lines(truth_root / f"{q}_priority.jsonl")
    top20 = {x["incident_id"] for x in priority if x["priority_rank"] <= 20}
    sizes = Counter(truth[aid] for aid in pred["eligible_alert_ids"])
    positions = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        by_incident = Counter(truth[aid] for aid in group)
        for incident, hits in by_incident.items():
            if incident in top20 and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                positions[incident].append(pos)
    return {i: "recalled" if i in positions and min(positions[i]) <= 20 else
            "recoverable_unranked" if i in positions else "unrecoverable" for i in top20}


def main():
    seal = json.loads((ART / "pre_evaluation_seal.json").read_text(encoding="utf-8"))
    frozen = json.loads((HERE / "PHASE33_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in frozen["sha256"].items(): assert sha(ROOT / rel) == digest, rel
    assert sha(P31 / "model.py") == seal["baseline_model_sha256"]
    assert sha(P32 / "model.py") == seal["candidate_model_sha256"]
    assert sha(HERE / "generator.py") == seal["generator_sha256"]
    assert sha(HERE / "config.json") == seal["config_sha256"]
    assert sha(ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py") == seal["evaluator_sha256"]
    for rel, digest in seal["receiver_visible_sha256"].items(): assert sha(HERE / rel) == digest, rel
    for name in ("baseline", "candidate"):
        assert sha(ART / f"{name}_predictions.jsonl") == seal["predictions_sha256"][name]
        assert sha(ART / f"{name}_decisions.jsonl") == seal["decisions_sha256"][name]
        result = json.loads((ART / f"{name}_evaluation.json").read_text(encoding="utf-8"))
        assert result["summary"]["prediction_sha256"] == seal["predictions_sha256"][name]
    p31 = module("p31_frozen_model_for_audit", P31 / "model.py")
    p32 = module("p32_frozen_model_for_audit", P32 / "model.py")
    baseline = lines(ART / "baseline_predictions.jsonl")
    candidate = lines(ART / "candidate_predictions.jsonl")
    baseline_decisions = lines(ART / "baseline_decisions.jsonl")
    candidate_decisions = lines(ART / "candidate_decisions.jsonl")
    counts = Counter()
    for b, c, bd, cd in zip(baseline, candidate, baseline_decisions, candidate_decisions):
        q = b["queue_id"]
        assert q == c["queue_id"] == bd["queue_id"] == cd["queue_id"]
        assert b["eligible_alert_ids"] == c["eligible_alert_ids"]
        assert not set(b) & PRIVATE_KEYS and not set(c) & PRIVATE_KEYS
        assert not set(bd) & PRIVATE_KEYS and not set(cd) & PRIVATE_KEYS
        alerts = {a["alert_id"]: a for a in lines(VISIBLE / "alerts" / f"{q}.jsonl")}
        ledger = {a["artifact_id"]: a["evidence_available_minute"] for a in lines(VISIBLE / "evidence_ledger" / f"{q}.jsonl")}
        claims = lines(VISIBLE / "claims" / f"{q}.jsonl")
        eligible = {aid for aid, minute in ledger.items() if minute <= 100}
        assert eligible == set(c["eligible_alert_ids"])
        assert all(ledger[aid] <= 100 for aid in c["eligible_alert_ids"])
        assert {aid for group in c["groups_ranked"] for aid in group} == eligible
        assert max(map(len, c["groups_ranked"])) <= 100
        token_truth = {x["relationship_token"]: x["true_relation"] for x in
            lines(PRIVATE / "relationship_truth" / f"{q}.jsonl") if "observation_id" in x}
        for item in cd["accepted"]:
            token = item["relationship_token"]
            counts["accepted_true"] += bool(token_truth[token])
            counts["accepted_false"] += not token_truth[token]
            assert len(item["upstream_roots"]) == 3
            bundle = [x for x in claims if x["relationship_token"] == token and
                      x["evidence_available_minute"] <= 100 and
                      x["left_alert_id"] in eligible and x["right_alert_id"] in eligible]
            visible_alerts = {aid: alerts[aid] for aid in eligible}
            if item.get("evidence_kind") == "endpoint_process_plus_auth_network":
                counts["fallback_unions"] += 1
                counts["fallback_true"] += bool(token_truth[token])
                good, reason = p32.endpoint_process_fallback(bundle, visible_alerts, 100)
            else:
                good, reason = p31.validate_attestation_bundle(bundle, visible_alerts, 100)
            assert good, (q, token, reason)
        for item in cd["rejected"]:
            counts["rejected_true"] += bool(token_truth[item["relationship_token"]])
            counts["rejected_false"] += not token_truth[item["relationship_token"]]
        base_status = incident_status(b, PRIVATE / "ground_truth_private")
        cand_status = incident_status(c, PRIVATE / "ground_truth_private")
        counts["newly_recoverable"] += sum(base_status[i] == "unrecoverable" and cand_status[i] != "unrecoverable"
                                            for i in base_status)
        counts["newly_recalled"] += sum(base_status[i] != "recalled" and cand_status[i] == "recalled"
                                         for i in base_status)
        counts["lost_recalled"] += sum(base_status[i] == "recalled" and cand_status[i] != "recalled"
                                        for i in base_status)
        counts["queues"] += 1
    paired = json.loads((HERE / "HOLDOUT_SUMMARY.json").read_text(encoding="utf-8"))
    assert all(paired["gates"].values())
    assert counts["accepted_false"] == 0
    out = {**dict(counts), "temporal_violations": 0, "private_feature_violations": 0,
           "seal_valid": True, "metric_gates_pass": True,
           "decision": "GO_WITHIN_CONTROLLED_SYNTHETIC_COHORT"}
    (HERE / "POST_EVALUATION_AUDIT.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__": main()
