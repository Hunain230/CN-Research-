"""Offline Phase 36 baseline miss inventory; no truth is used for inference."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P36 = ROOT / "experiments/PHASE36_EVIDENCE_AWARE_RECALL"
ART = P36 / "artifacts"
VISIBLE = P36 / "dataset/receiver_visible/development"
TRUTH = P36 / "dataset/evaluator_only/development/ground_truth_private"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    seal = json.loads((ART / "development_pre_evaluation_seal.json").read_text(encoding="utf-8"))
    assert sha(ART / "development_baseline_predictions.jsonl") == seal["baseline_prediction_sha256"]
    assert sha(ART / "development_baseline_decisions.jsonl") == seal["decisions_sha256"]
    preds = lines(ART / "development_baseline_predictions.jsonl")
    audits = lines(ART / "development_baseline_decisions.jsonl")
    rows = []
    for pred, audit in zip(preds, audits):
        q = pred["queue_id"]
        assert q == audit["queue_id"]
        truth = {x["alert_id"]: x["incident_id"] for x in lines(TRUTH / f"{q}.jsonl")}
        priority = {x["incident_id"]: x["priority_rank"] for x in lines(TRUTH / f"{q}_priority.jsonl")}
        eligible = set(pred["eligible_alert_ids"])
        sizes = Counter(truth[a] for a in eligible)
        alerts = {x["alert_id"]: x for x in lines(VISIBLE / "alerts" / f"{q}.jsonl")}
        claims = lines(VISIBLE / "claims" / f"{q}.jsonl")
        rejected = {x["relationship_token"]: x["reason"] for x in audit["rejected"]}
        for incident, oracle_rank in priority.items():
            if oracle_rank > 20: continue
            members = {a for a in eligible if truth[a] == incident}
            qualifies = []
            best = (0, 0, 0)
            for position, group in enumerate(pred["groups_ranked"], 1):
                hits = len(members & set(group))
                if hits > best[0]: best = (hits, position, len(group))
                if hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                    qualifies.append(position)
            if qualifies and min(qualifies) <= 20: continue
            related = [c for c in claims if c["left_alert_id"] in members or c["right_alert_id"] in members]
            timely = [c for c in related if c["evidence_available_minute"] <= 100]
            originals = [c for c in timely if c["derived_from"] is None]
            internal = [c for c in originals if c["left_alert_id"] in members and c["right_alert_id"] in members]
            roots = {c["upstream_root_id"] for c in internal}
            roots |= {alerts[a]["endpoint_origin"] for a in members}
            families = {c["family"] for c in internal}
            late = [c for c in related if c["evidence_available_minute"] > 100]
            rejected_reasons = sorted({rejected[c["relationship_token"]] for c in related
                                       if c["relationship_token"] in rejected})
            missing_families = sorted({"process", "authentication", "network_flow"} - families)
            status = "recoverable_unranked" if qualifies else "fragmented_unrecoverable"
            if qualifies:
                category = "A_recoverable_outside_top20"
            elif late:
                category = "C_delayed_or_contradictory"
            elif missing_families:
                category = "E_missing_visible_telemetry"
            else:
                category = "B_insufficient_independent_evidence"
            rows.append({"queue_id": q, "incident_id_offline_only": incident,
                "oracle_rank_offline_only": oracle_rank, "eligible_alerts": sizes[incident],
                "status": status, "qualifying_rank": min(qualifies) if qualifies else "",
                "largest_fragment_rank": best[1], "largest_fragment_alerts": best[0],
                "largest_fragment_size": best[2], "visible_alerts_by_minute100": len(members),
                "timely_related_claims": len(timely), "timely_original_internal_claims": len(internal),
                "derived_related_copies": sum(c["derived_from"] is not None for c in timely),
                "late_related_claims": len(late), "independent_root_count": len(roots),
                "independent_roots": ";".join(sorted(roots)), "present_families": ";".join(sorted(families)),
                "missing_families": ";".join(missing_families),
                "rejected_reasons": ";".join(rejected_reasons),
                "contradiction_or_rejection_present": bool(rejected_reasons),
                "primary_category": category,
                "ranking_overlap": bool(qualifies),
                "potential_visible_remedy": "evidence_aware_prioritization" if qualifies else
                  "requires_independent_timely_evidence_or_safe_abstention"})
    assert len(rows) == 35, len(rows)
    with (HERE / "MISS_ANALYSIS.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    availability_fields = ["queue_id", "incident_id_offline_only", "status", "visible_alerts_by_minute100",
                           "timely_related_claims", "timely_original_internal_claims", "derived_related_copies",
                           "late_related_claims", "independent_root_count", "present_families", "missing_families",
                           "contradiction_or_rejection_present"]
    with (HERE / "EVIDENCE_AVAILABILITY.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=availability_fields); writer.writeheader()
        writer.writerows({k: row[k] for k in availability_fields} for row in rows)
    summary = Counter(x["primary_category"] for x in rows)
    with (HERE / "FAILURE_CATEGORY_SUMMARY.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "incidents"])
        writer.writeheader(); writer.writerows({"category": k, "incidents": v} for k, v in sorted(summary.items()))
    print(json.dumps({"missed": len(rows), "categories": dict(summary),
                      "recoverable_unranked": sum(x["status"] == "recoverable_unranked" for x in rows),
                      "fragmented": sum(x["status"] == "fragmented_unrecoverable" for x in rows)}))


if __name__ == "__main__": main()
