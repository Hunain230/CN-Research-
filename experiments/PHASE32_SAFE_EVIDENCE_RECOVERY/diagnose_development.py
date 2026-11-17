"""Evaluator-only diagnosis of Phase 31 development failures; no inference code."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def main():
    rows = list(csv.DictReader((P31 / "artifacts/incident_recovery.csv").open(encoding="utf-8")))
    remaining = {(x["queue_id"], x["incident_id"]) for x in rows if x["evidence_aware_ranked"] == "unrecoverable"}
    missing_by_incident = defaultdict(set)
    possible_process_fallback = set()
    for q in {q for q, _ in remaining}:
        visible = P31 / "dataset/receiver_visible/development"
        private = P31 / "dataset/evaluator_only/development"
        claims = lines(visible / "claims" / f"{q}.jsonl")
        alerts = {x["alert_id"]: x for x in lines(visible / "alerts" / f"{q}.jsonl")}
        truth = {x["alert_id"]: x["incident_id"] for x in lines(private / "ground_truth_private" / f"{q}.jsonl")}
        relation_truth = lines(private / "relationship_truth" / f"{q}.jsonl")
        true_tokens = {x["relationship_token"] for x in relation_truth if x["true_relation"]}
        by_token = defaultdict(list)
        for c in claims:
            if (c["relationship_token"] in true_tokens and c["evidence_available_minute"] <= 100 and
                alerts[c["left_alert_id"]]["evidence_available_minute"] <= 100 and
                alerts[c["right_alert_id"]]["evidence_available_minute"] <= 100):
                by_token[c["relationship_token"]].append(c)
        for token in true_tokens:
            all_claims = [c for c in claims if c["relationship_token"] == token]
            if not all_claims: continue
            left, right = alerts[all_claims[0]["left_alert_id"]], alerts[all_claims[0]["right_alert_id"]]
            key = (q, truth[left["alert_id"]])
            if key not in remaining: continue
            families = {c["family"] for c in by_token[token] if c["derived_from"] is None}
            missing = {"process", "authentication", "network_flow"} - families
            missing_by_incident[key].update(missing)
            if (missing == {"process"} and left["endpoint_origin"] == right["endpoint_origin"] and
                left["process_id"] == right["parent_process_id"] and left["source_id"] != right["source_id"]):
                possible_process_fallback.add(key)
    counts = Counter()
    for key in remaining:
        for family in missing_by_incident[key]: counts[f"missing_{family}"] += 1
        if not missing_by_incident[key]: counts["no_missing_family"] += 1
    result = {"remaining_incidents": len(remaining), "overlapping_missing_family_counts": dict(counts),
              "incidents_with_endpoint_process_fallback_opportunity": len(possible_process_fallback)}
    (HERE / "artifacts").mkdir(exist_ok=True)
    (HERE / "artifacts/development_failure_diagnosis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
