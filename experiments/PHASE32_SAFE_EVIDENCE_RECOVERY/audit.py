"""Evaluator-only paired union, incident, temporal, and leakage audit."""
import csv
import json
from collections import Counter
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
ART = HERE / "artifacts"
PRIVATE_KEYS = {"incident_id", "scenario_id", "template_id", "true_relation",
                "priority_rank", "priority_score", "malicious", "attack_stage", "condition"}


def lines(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def main():
    prior = lines(P31 / "artifacts/development_evidence_aware_ranked_predictions.jsonl")
    outcomes = {}
    for bonus in (1, 2):
        name = f"endpoint_fallback_bonus{bonus}"
        predictions = lines(ART / f"development_{name}_predictions.jsonl")
        decisions = lines(ART / f"development_{name}_decisions.jsonl")
        counts = Counter()
        for old, new, audit in zip(prior, predictions, decisions):
            q = old["queue_id"]
            assert q == new["queue_id"] == audit["queue_id"]
            assert old["eligible_alert_ids"] == new["eligible_alert_ids"]
            assert not set(new) & PRIVATE_KEYS and not set(audit) & PRIVATE_KEYS
            assert max(map(len, new["groups_ranked"])) <= 100
            assert {a for g in new["groups_ranked"] for a in g} == set(new["eligible_alert_ids"])
            visible = P31 / "dataset/receiver_visible/development"
            private = P31 / "dataset/evaluator_only/development"
            alerts = {x["alert_id"]: x for x in lines(visible / "alerts" / f"{q}.jsonl")}
            ledger = {x["artifact_id"]: x["evidence_available_minute"] for x in lines(visible / "evidence_ledger" / f"{q}.jsonl")}
            claims = lines(visible / "claims" / f"{q}.jsonl")
            truth_tokens = {x["relationship_token"]: x["true_relation"] for x in
                lines(private / "relationship_truth" / f"{q}.jsonl") if "observation_id" in x}
            eligible = {aid for aid, minute in ledger.items() if minute <= 100}
            assert eligible == set(new["eligible_alert_ids"])
            for item in audit["accepted"]:
                token = item["relationship_token"]
                counts["accepted_true_total"] += bool(truth_tokens[token])
                counts["accepted_false_total"] += not truth_tokens[token]
                if item.get("evidence_kind") != "endpoint_process_plus_auth_network": continue
                counts["fallback_unions"] += 1
                counts["fallback_true"] += bool(truth_tokens[token])
                counts["fallback_false"] += not truth_tokens[token]
                bundle = [c for c in claims if c["relationship_token"] == token and c["evidence_available_minute"] <= 100 and
                          c["left_alert_id"] in eligible and c["right_alert_id"] in eligible]
                good, reason = model.endpoint_process_fallback(bundle, alerts, 100)
                assert good, (q, token, reason)
                assert len(item["upstream_roots"]) == 3
                assert ledger[item["left_alert_id"]] <= 100 and ledger[item["right_alert_id"]] <= 100
            for item in audit["rejected"]:
                counts["rejected_true"] += bool(truth_tokens[item["relationship_token"]])
                counts["rejected_false"] += not truth_tokens[item["relationship_token"]]
            counts["queues"] += 1
        old_eval = json.loads((P31 / "artifacts/development_evidence_aware_ranked_evaluation.json").read_text(encoding="utf-8"))
        new_eval = json.loads((ART / f"development_{name}_evaluation.json").read_text(encoding="utf-8"))
        for b, c in zip(old_eval["queues"], new_eval["queues"]):
            assert b["queue_id"] == c["queue_id"]
            assert c["false_grouped_pairs"] <= b["false_grouped_pairs"]
            assert c["mixed_predicted_groups"] <= b["mixed_predicted_groups"]
        outcomes[name] = dict(counts)
    # Incident-level deltas use the same official completeness/purity rule.
    spec = P31 / "dataset/evaluator_only/development/ground_truth_private"
    import importlib.util
    audit_spec = importlib.util.spec_from_file_location("p31_audit", P31 / "audit_phase31.py")
    p31_audit = importlib.util.module_from_spec(audit_spec); audit_spec.loader.exec_module(p31_audit)
    base_status = [p31_audit.incident_status(x, spec) for x in prior]
    for bonus in (1, 2):
        name = f"endpoint_fallback_bonus{bonus}"
        current = [p31_audit.incident_status(x, spec) for x in lines(ART / f"development_{name}_predictions.jsonl")]
        outcomes[name]["newly_recoverable"] = sum(b[i] == "unrecoverable" and c[i] != "unrecoverable"
            for b, c in zip(base_status, current) for i in b)
        outcomes[name]["newly_recalled"] = sum(b[i] != "recalled" and c[i] == "recalled"
            for b, c in zip(base_status, current) for i in b)
        outcomes[name]["lost_recalled"] = sum(b[i] == "recalled" and c[i] != "recalled"
            for b, c in zip(base_status, current) for i in b)
    outcomes["temporal_violations"] = 0
    outcomes["private_feature_violations"] = 0
    (ART / "post_evaluation_audit.json").write_text(json.dumps(outcomes, indent=2), encoding="utf-8")
    print(json.dumps(outcomes, indent=2))


if __name__ == "__main__": main()
