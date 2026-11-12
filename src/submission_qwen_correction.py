"""Add full-organization membership evaluation to the frozen bounded Qwen run.

The original evaluator used only the 32 selected alerts to calculate incident
completeness. This additive correction retains the original artifacts and uses
all unambiguous alerts of each selected organization for the completeness
denominator. No prediction or model call is made here.
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter
from pathlib import Path

from .empirical_priority_tie_eval import _expected_metrics
from .guide_rerun_v2 import labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_local_qwen import PREPARED, ROOT


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(run_id: str) -> None:
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    target = public / "metrics_full_membership_correction.json"
    manifest_target = public / "correction_manifest.json"
    if target.exists() or manifest_target.exists():
        raise FileExistsError("Correction already exists")
    freeze_path = public / "prediction_freeze.json"
    prior_path = public / "metrics.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    prediction_path = private / "predictions.pkl"
    if sha256_file(prediction_path) != freeze["prediction_sha256"]:
        raise ValueError("Prediction freeze mismatch")
    if sha256_file(PREPARED) != freeze["source_sha256"][r"data\derived\guide_rerun_v2\prepared.pkl"]:
        raise ValueError("Prepared input hash mismatch")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if prior["selected_candidate_positive_pairs"] != 0:
        raise ValueError("This correction expects the recorded zero-positive selected pair set")
    with prediction_path.open("rb") as stream:
        predicted = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        prepared = pickle.load(stream)
    orgs = set(predicted)
    full_alerts = {a for a, doc in prepared["alerts"].items() if doc["org"] in orgs}
    truth = read_truth(orgs, full_alerts)
    ranks = labels(orgs)
    rows = []
    for org, item in sorted(predicted.items()):
        all_org_alerts = {a for a in full_alerts if prepared["alerts"][a]["org"] == org}
        gold_counts = Counter(truth[a] for a in all_org_alerts)
        groups, scores = item["groups"], item["scores"]
        recovered = {}
        for group in groups:
            counts = Counter(truth[a] for a in group)
            gold, overlap = max(counts.items(), key=lambda row: (row[1], row[0]))
            if gold in ranks[org] and overlap / gold_counts[gold] >= 0.8 and overlap / len(group) >= 0.8:
                recovered[group[0]] = ranks[org][gold]
        ordered = sorted(zip(groups, scores), key=lambda row: (-row[1], row[0][0]))
        blocks = []
        for group, score in ordered:
            if not blocks or blocks[-1][0][1] != score:
                blocks.append([])
            blocks[-1].append((group[0], score))
        label_map = recovered | {f"unrecovered-{gold}": rank for gold, rank in ranks[org].items() if rank not in recovered.values()}
        ranking = _expected_metrics(blocks, label_map)
        rows.append({
            "all_unambiguous_alerts": len(all_org_alerts),
            "selected_alerts": len(item["alerts"]),
            "top20_labels_with_unambiguous_alerts": sum(gold in gold_counts for gold in ranks[org]),
            "recovered_labels": len(set(recovered.values())),
            "recall_at_20": ranking["recall_at_20"],
            "precision_at_10": ranking["precision_at_10"],
            "ndcg_at_20_rank1_highest": ranking["ndcg_at_20_rank1_highest"],
        })
    corrected = {
        "classification": "exploratory_bounded_local_qwen_full_membership_correction",
        "supersedes": "metrics.json cpv_batched_local_qwen ranking/recovery fields only; candidate_pair_metrics and call_summary remain valid",
        "reason": "the original evaluator computed incident completeness over selected alerts, not full organization membership",
        "organizations": len(rows),
        "selected_alerts": sum(r["selected_alerts"] for r in rows),
        "all_unambiguous_alerts_in_selected_organizations": sum(r["all_unambiguous_alerts"] for r in rows),
        "expert_top20_denominator": 20 * len(rows),
        "top20_labels_with_unambiguous_alerts": sum(r["top20_labels_with_unambiguous_alerts"] for r in rows),
        "recovered_labels": sum(r["recovered_labels"] for r in rows),
        "end_to_end_recall_at_20_macro": sum(r["recall_at_20"] for r in rows) / len(rows),
        "precision_at_10_macro": sum(r["precision_at_10"] for r in rows) / len(rows),
        "ndcg_at_20_rank1_high_macro": sum(r["ndcg_at_20_rank1_highest"] for r in rows) / len(rows),
        "prediction_freeze_sha256": sha256_file(freeze_path),
        "original_metrics_sha256": sha256_file(prior_path),
        "limits": ["two previously accessed organizations; no confidence interval", "selected-alert candidate pairs contain zero positives", "batch Qwen model calls, not full original C/P/V protocol", "all 40 expert labels stay in denominator"],
    }
    write_json(target, corrected)
    write_json(manifest_target, {
        "classification": corrected["classification"],
        "command": f"python -m src.submission_qwen_correction --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), PREPARED, prediction_path, freeze_path, prior_path, target)},
    })
    print(json.dumps({"status": "corrected_full_membership_evaluation", "recovered_labels": corrected["recovered_labels"], "denominator": corrected["expert_top20_denominator"], "recall_macro": corrected["end_to_end_recall_at_20_macro"]}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="submission_qwen_20261112_v1")
    run(parser.parse_args().run_id)


if __name__ == "__main__":
    main()
