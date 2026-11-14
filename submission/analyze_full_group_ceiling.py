"""Evaluator-only diagnostic for the frozen full-GUIDE predicted groups."""

from __future__ import annotations

import json
import pickle
from collections import Counter

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT


def main() -> None:
    parent_path = ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl"
    parent_freeze = ROOT / "outputs/submission_full_guide_paper_20261113_v1/prediction_freeze.json"
    expected = json.loads(parent_freeze.read_text(encoding="utf-8"))["prediction_sha256"]
    if sha256_file(parent_path) != expected:
        raise ValueError("Frozen parent prediction changed")
    with parent_path.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = set(parent)
    alert_keys = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alert_keys)
    ranks = labels(orgs)
    total = len(orgs) * 20
    present = recoverable = 0
    for org, item in parent.items():
        counts = Counter(truth[a] for a in item["input_alert_keys"])
        present += len(set(counts) & set(ranks[org]))
        recovered = set()
        for group in item["groups"]:
            overlaps = Counter(truth[a] for a in group)
            gold, n = max(overlaps.items(), key=lambda pair: (pair[1], pair[0]))
            if gold in ranks[org] and n / counts[gold] >= 0.8 and n / len(group) >= 0.8:
                recovered.add(gold)
        recoverable += len(recovered)
    result = {
        "classification": "evaluator_only_oracle_order_ceiling_for_frozen_groups_not_model_performance",
        "organizations": len(orgs), "expert_top20_denominator": total,
        "top20_with_unambiguous_alerts": present,
        "top20_absent_after_ambiguous_key_exclusion": total - present,
        "top20_recoverable_in_any_predicted_group": recoverable,
        "top20_present_but_not_recoverable": present - recoverable,
        "oracle_order_recall_at_20_upper_bound": recoverable / total,
        "recovery_rule": "at_least_80_percent_gold_alerts_and_80_percent_group_purity",
        "frozen_prediction_sha256": expected,
        "labels_used": True,
        "note": "Diagnostic oracle bound only; it cannot be claimed as achieved operational performance.",
    }
    output = ROOT / "outputs/submission_full_group_ceiling_20261114_v1.json"
    if output.exists():
        raise FileExistsError("Diagnostic output exists")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
