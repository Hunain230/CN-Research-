"""Read-only aggregate diagnosis of the opened Phase 33 holdout."""
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    predictions = lines(P33 / "artifacts/candidate_predictions.jsonl")
    counts = Counter()
    unranked_positions = Counter()
    missing_family_incidents = Counter()
    for pred in predictions:
        q = pred["queue_id"]
        truth_root = P33 / "dataset/evaluator_only/locked_test/ground_truth_private"
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        claim_rows = lines(P33 / "dataset/receiver_visible/locked_test/claims" / f"{q}.jsonl")
        relation_truth = lines(P33 / "dataset/evaluator_only/locked_test/relationship_truth" / f"{q}.jsonl")
        true_tokens = {x["relationship_token"] for x in relation_truth if x["true_relation"]}
        by_token = defaultdict(list)
        for claim in claim_rows:
            if claim["relationship_token"] in true_tokens and claim["evidence_available_minute"] <= 100:
                by_token[claim["relationship_token"]].append(claim)
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        qualified = defaultdict(list)
        by_incident_groups = defaultdict(list)
        for pos, group in enumerate(pred["groups_ranked"], 1):
            composition = Counter(truth[a] for a in group)
            for incident, hits in composition.items():
                if incident not in top20: continue
                by_incident_groups[incident].append((hits, len(group)))
                if hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                    qualified[incident].append(pos)
        for incident in top20:
            if qualified[incident]:
                pos = min(qualified[incident])
                if pos <= 20: counts["recalled"] += 1
                else:
                    counts["recoverable_but_unranked"] += 1
                    unranked_positions[pos] += 1
            else:
                counts["unrecoverable"] += 1
                hits, size = max(by_incident_groups[incident], key=lambda x: x[0])
                counts["fragmented"] += hits / sizes[incident] < .8
                counts["impure_only"] += hits / sizes[incident] >= .8 and hits / size < .8
                missing = set()
                for token in true_tokens:
                    token_claims = [c for c in claim_rows if c["relationship_token"] == token]
                    if not token_claims or truth[token_claims[0]["left_alert_id"]] != incident: continue
                    available_families = {c["family"] for c in by_token[token] if c["derived_from"] is None}
                    missing |= {"process", "authentication", "network_flow"} - available_families
                for family in missing: missing_family_incidents[family] += 1
    out = {"category_counts": dict(counts), "unranked_first_qualifying_position": dict(sorted(unranked_positions.items())),
           "unrecoverable_missing_family_incidents_overlapping": dict(missing_family_incidents),
           "use": "diagnostic only; no Phase 34 candidate fitted or selected on this opened holdout"}
    (HERE / "artifacts").mkdir(exist_ok=True)
    (HERE / "artifacts/phase33_failure_diagnosis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__": main()
