"""Verify post-hoc telemetry predictions against their seal and Phase 37 groups."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P37 = ROOT / "experiments/PHASE37_EVIDENCE_AVAILABILITY_RESEARCH"
ART = HERE / "artifacts"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    seal = json.loads((ART / "stress_pre_evaluation_seal.json").read_text(encoding="utf-8"))
    assert sha(ART / "candidate_params.json") == seal["params_sha256"]
    assert sha(HERE / "ranker.py") == seal["ranker_sha256"]
    queues = 0
    for condition, digest in seal["predictions_sha256"].items():
        path = ART / f"stress_{condition}_predictions.jsonl"
        assert sha(path) == digest
        evaluation = json.loads((ART / f"stress_{condition}_evaluation.json").read_text(encoding="utf-8"))
        assert evaluation["summary"]["prediction_sha256"] == digest
        base = lines(P37 / "artifacts" / f"{condition}_predictions.jsonl")
        cand = lines(path)
        assert len(base) == len(cand) == 15
        for b, c in zip(base, cand):
            assert b["queue_id"] == c["queue_id"]
            assert b["eligible_alert_ids"] == c["eligible_alert_ids"]
            assert b["groups_ranked"][:10] == c["groups_ranked"][:10]
            assert sorted(map(tuple, b["groups_ranked"])) == sorted(map(tuple, c["groups_ranked"]))
            queues += 1
        assert evaluation["summary"]["false_grouped_pairs"] == 0
        assert evaluation["summary"]["mixed_predicted_groups"] == 0
    report = {"conditions": len(seal["predictions_sha256"]), "queue_evaluations": queues,
              "prediction_seals_valid": True, "group_partitions_and_top10_preserved": True,
              "previously_opened_phase37_development": True, "used_for_selection": False}
    (ART / "stress_post_evaluation_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__": main()
