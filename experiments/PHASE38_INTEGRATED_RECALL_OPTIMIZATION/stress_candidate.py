"""Post-hoc telemetry sensitivity on already opened Phase 37 development."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import ranker

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P37 = ROOT / "experiments/PHASE37_EVIDENCE_AVAILABILITY_RESEARCH"
ART = HERE / "artifacts"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    params = json.loads((ART / "candidate_params.json").read_text(encoding="utf-8"))
    seal = {"params_sha256": sha(ART / "candidate_params.json"), "ranker_sha256": sha(HERE / "ranker.py"),
            "note": "posthoc_on_previously_opened_phase37_development_not_candidate_selection"}
    conditions = ("original", "claim_delay20", "snapshot_minute80", "drop_process",
                  "drop_authentication", "drop_network_flow", "derived_copies", "collapsed_roots",
                  "contradictory_process")
    paths = {}
    for condition in conditions:
        baseline = lines(P37 / "artifacts" / f"{condition}_predictions.jsonl")
        decisions = lines(P37 / "artifacts" / f"{condition}_decisions.jsonl")
        receiver = P37 / "dataset/telemetry_conditions" / condition
        out = ART / f"stress_{condition}_predictions.jsonl"
        assert not out.exists()
        with out.open("w", encoding="utf-8", newline="\n") as f:
            for p, d in zip(baseline, decisions):
                f.write(json.dumps(ranker.rerank(p, d, receiver, params), sort_keys=True) + "\n")
        paths[condition] = out
    seal["predictions_sha256"] = {name: sha(path) for name, path in paths.items()}
    (ART / "stress_pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    truth = P37 / "dataset/evaluator_only/development/ground_truth_private"
    rows = []
    for condition, pred in paths.items():
        out = ART / f"stress_{condition}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(pred),
                        "--truth-root", str(truth), "--out", str(out)], check=True, capture_output=True, text=True)
        s = json.loads(out.read_text(encoding="utf-8"))["summary"]
        baseline = json.loads((P37 / "artifacts" / f"{condition}_evaluation.json").read_text(encoding="utf-8"))["summary"]
        rows.append({"condition": condition, "baseline_recall": baseline["recall20_count"],
                     "candidate_recall": s["recall20_count"], "baseline_recoverable": baseline["recoverable"],
                     "candidate_recoverable": s["recoverable"], "baseline_p10": baseline["p10_count"],
                     "candidate_p10": s["p10_count"], "candidate_false_pairs": s["false_grouped_pairs"],
                     "candidate_mixed_groups": s["mixed_predicted_groups"],
                     "posthoc_previously_opened": True})
    with (HERE / "TELEMETRY_SENSITIVITY.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
