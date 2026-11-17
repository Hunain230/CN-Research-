"""Post-evaluation categories for the 34 development incidents still unrecoverable."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
ART = HERE / "artifacts"


def lines(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def main():
    rows = list(csv.DictReader((ART / "incident_recovery.csv").open(encoding="utf-8")))
    remaining = {(x["queue_id"], x["incident_id"]) for x in rows if x["evidence_aware_ranked"] == "unrecoverable"}
    reasons = Counter(); by_incident = defaultdict(set)
    for q in {x[0] for x in remaining}:
        truth_root = DATA / "evaluator_only/development"
        visible_root = DATA / "receiver_visible/development"
        incident_of = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / "ground_truth_private" / f"{q}.jsonl")}
        claims = {x["relationship_token"]: x for x in lines(visible_root / "claims" / f"{q}.jsonl")}
        relation_truth = lines(truth_root / "relationship_truth" / f"{q}.jsonl")
        genuine_tokens = {x["relationship_token"] for x in relation_truth if x["true_relation"]}
        decisions = next(x for x in lines(ART / "development_evidence_aware_ranked_decisions.jsonl") if x["queue_id"] == q)
        reject_by_token = {x["relationship_token"]: x["reason"] for x in decisions["rejected"]}
        for token in genuine_tokens:
            claim = claims.get(token)
            if claim is None: continue
            key = (q, incident_of[claim["left_alert_id"]])
            if key not in remaining: continue
            if token in reject_by_token: by_incident[key].add(reject_by_token[token])
            elif token not in {x["relationship_token"] for x in decisions["accepted"]}:
                by_incident[key].add("already_grouped_or_ineligible")
    for key in remaining:
        for reason in by_incident[key] or {"fragmented_despite_visible_links"}:
            reasons[reason] += 1
    result = {"unrecoverable_incidents": len(remaining), "overlapping_reason_counts": dict(reasons)}
    (ART / "remaining_incident_reasons.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
