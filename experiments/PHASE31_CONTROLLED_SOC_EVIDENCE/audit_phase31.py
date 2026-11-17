"""Post-evaluation truth audit; never called by inference."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import model

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
ART = HERE / "artifacts"
ARMS = ("original_subset", "legacy_rich", "evidence_aware", "evidence_aware_ranked")
PRIVATE_FIELDS = {"incident_id", "scenario_id", "template_id", "true_relation",
                  "malicious", "attack_stage", "priority_rank", "priority_score", "condition"}


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def incident_status(pred, truth_root):
    q = pred["queue_id"]
    truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
    priority = lines(truth_root / f"{q}_priority.jsonl")
    top20 = {x["incident_id"] for x in priority if x["priority_rank"] <= 20}
    sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
    positions = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        counts = Counter(truth[a] for a in group)
        for incident, hits in counts.items():
            if incident in top20 and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                positions[incident].append(pos)
    return {i: ("recalled" if i in positions and min(positions[i]) <= 20 else
                "recoverable_unranked" if i in positions else "unrecoverable") for i in top20}


def main():
    split = "development"
    manifest = json.loads((DATA / f"{split}_manifest.json").read_text(encoding="utf-8"))
    visible = DATA / "receiver_visible" / split
    private = DATA / "evaluator_only" / split
    all_predictions = {arm: lines(ART / f"{split}_{arm}_predictions.jsonl") for arm in ARMS}
    all_decisions = {arm: lines(ART / f"{split}_{arm}_decisions.jsonl") for arm in ARMS}
    summary = {arm: Counter() for arm in ARMS}
    incident_rows = []
    for qi, item in enumerate(manifest["queues"]):
        q = item["queue_id"]
        alerts = lines(visible / "alerts" / f"{q}.jsonl")
        claims = lines(visible / "claims" / f"{q}.jsonl")
        ledger = lines(visible / "evidence_ledger" / f"{q}.jsonl")
        claim_truth = lines(private / "relationship_truth" / f"{q}.jsonl")
        true_tokens = {x["relationship_token"] for x in claim_truth if x["true_relation"]}
        false_tokens = {x["relationship_token"] for x in claim_truth if not x["true_relation"]}
        assert not true_tokens & false_tokens
        ledger_times = {x["artifact_id"]: x["evidence_available_minute"] for x in ledger}
        eligible = {a["alert_id"] for a in alerts if ledger_times[a["alert_id"]] <= 100}
        assert not any(set(x) & PRIVATE_FIELDS for x in alerts + claims + ledger)
        states = {}
        for arm in ARMS:
            pred = all_predictions[arm][qi]
            decisions = all_decisions[arm][qi]
            assert pred["queue_id"] == q == decisions["queue_id"]
            assert set(pred["eligible_alert_ids"]) == eligible
            assert not any(set(pred) & PRIVATE_FIELDS or set(d) & PRIVATE_FIELDS for d in (pred, decisions))
            assert len(pred["eligible_alert_ids"]) == sum(map(len, pred["groups_ranked"]))
            assert max(map(len, pred["groups_ranked"])) <= 100
            assert {a for g in pred["groups_ranked"] for a in g} == eligible
            states[arm] = incident_status(pred, private / "ground_truth_private")
            summary[arm]["queues"] += 1
            summary[arm]["accepted_unions"] += len(decisions["accepted"])
            summary[arm]["legacy_lineage_accepts"] += decisions["decision_counts"].get("lineage_accept", 0)
            summary[arm]["rejected_hypotheses"] += len(decisions["rejected"])
            summary[arm]["visible_claims"] += decisions["visible_claims"]
            for accepted in decisions["accepted"]:
                token = accepted["relationship_token"]
                summary[arm]["accepted_true"] += token in true_tokens
                summary[arm]["accepted_false"] += token in false_tokens
                assert len(accepted["upstream_roots"]) == 3
                relevant = [c for c in claims if c["relationship_token"] == token and
                            c["evidence_available_minute"] <= 100]
                lookup = {a["alert_id"]: a for a in alerts if a["alert_id"] in eligible}
                good, reason = model.validate_attestation_bundle(relevant, lookup, 100)
                assert good, (q, token, reason)
            for rejected in decisions["rejected"]:
                token = rejected["relationship_token"]
                summary[arm]["rejected_true"] += token in true_tokens
                summary[arm]["rejected_false"] += token in false_tokens
        for incident in states["original_subset"]:
            incident_rows.append({"queue_id": q, "incident_id": incident,
                **{arm: states[arm][incident] for arm in ARMS}})
    with (ART / "incident_recovery.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(incident_rows[0])); writer.writeheader(); writer.writerows(incident_rows)
    out = {arm: dict(values) for arm, values in summary.items()}
    out["newly_recoverable_verified"] = sum(x["evidence_aware"] != "unrecoverable" and
        x["original_subset"] == "unrecoverable" for x in incident_rows)
    out["newly_recalled_verified_ranked"] = sum(x["evidence_aware_ranked"] == "recalled" and
        x["original_subset"] != "recalled" for x in incident_rows)
    out["temporal_violations"] = 0
    out["private_feature_violations"] = 0
    (ART / "post_evaluation_audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__": main()
