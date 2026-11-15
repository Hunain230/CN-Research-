"""Evaluator-only Phase 9A interface, with synthetic validation only.

Incident membership and expert ranks may enter this module, never the
inference module. No GUIDE evaluator CLI exists until an authorized study
protocol, prediction freeze, and untouched confirmation cohort are supplied.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Mapping, Sequence

from src.submission_fragment_aware_v1 import connected_incidents, incident_outcomes
from src.submission_group_merge_v10_v2 import pair_group_metrics


def evaluate_matched_partition(keys: Sequence[str], candidate_edges: Sequence[int],
                               reference_groups: list[list[str]],
                               reference_scores: list[float],
                               proposed_groups: list[list[str]],
                               proposed_scores: list[float],
                               truth: Mapping[str, str],
                               expert_ranks: Mapping[str, int]) -> dict:
    """Use the existing 80% and tie-aware evaluator on supplied frozen inputs."""
    if (set(keys) != set(truth) or len(keys) != len(truth) or
            len(reference_groups) != len(reference_scores) or
            len(proposed_groups) != len(proposed_scores)):
        raise ValueError("Evaluator alert or score scope changed")
    for groups in (reference_groups, proposed_groups):
        flattened = [alert for group in groups for alert in group]
        if (sorted(flattened) != sorted(keys) or
                any(not group or len(group) > 100 for group in groups)):
            raise ValueError("Groups do not partition alerts within cap 100")
    connected = connected_incidents(list(keys), candidate_edges, truth, expert_ranks)
    result = {}
    for name, groups, scores in (("reference", reference_groups, reference_scores),
                                 ("proposed", proposed_groups, proposed_scores)):
        metric = pair_group_metrics(groups, scores, list(keys), truth, expert_ranks)
        outcome = incident_outcomes(groups, list(keys), truth, expert_ranks, connected)
        if outcome["recoverable"] != metric["recoverable"]:
            raise AssertionError("Existing evaluator recovery definitions disagree")
        tp, fp, fn = (metric[field] for field in ("tp", "fp", "fn"))
        result[name] = {**metric, **dict(outcome),
                        "pair_precision": tp / (tp + fp) if tp + fp else 0.0,
                        "pair_recall": tp / (tp + fn) if tp + fn else 0.0,
                        "false_positive_grouped_pairs": fp,
                        "mixed_predicted_groups": outcome["mixed_predicted_groups"],
                        "incomplete_top20_labels": outcome["incomplete"],
                        "impure_top20_labels": outcome["impure"]}
    result["delta"] = {field: result["proposed"][field] - result["reference"][field]
                       for field in ("recoverable", "recall20", "p10", "ndcg20",
                                     "false_positive_grouped_pairs",
                                     "mixed_predicted_groups", "incomplete_top20_labels",
                                     "impure_top20_labels")}
    result["candidate_pairs_unchanged"] = len(candidate_edges)
    result["classification"] = "synthetic_only_evaluator_interface"
    return result


def self_test() -> None:
    keys = ["a", "b", "c"]
    truth = {"a": "incident-one", "b": "incident-one", "c": "incident-two"}
    ranks = {"incident-one": 1, "incident-two": 2}
    result = evaluate_matched_partition(
        keys, [1], [["a"], ["b"], ["c"]], [0.9, 0.8, 0.7],
        [["a", "b"], ["c"]], [0.9, 0.7], truth, ranks)
    assert result["delta"]["recoverable"] == 1
    assert result["proposed"]["false_positive_grouped_pairs"] == 0
    assert result["proposed"]["mixed_predicted_groups"] == 0
    assert result["candidate_pairs_unchanged"] == 1
    try:
        evaluate_matched_partition(keys, [1], [["a"], ["b"], ["c"]],
                                   [0.9, 0.8, 0.7], [["a", "b"], ["c"]],
                                   [0.9], truth, ranks)
    except ValueError:
        pass
    else:
        raise AssertionError("Misaligned score vector was accepted")
    print(json.dumps({"status": "pass", "synthetic_assertions": 5,
                      "guide_label_reads": 0, "predictions_generated": 0}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test",))
    args = parser.parse_args()
    if args.stage == "self-test":
        self_test()


if __name__ == "__main__":
    main()
