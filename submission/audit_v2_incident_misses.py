"""Aggregate evaluator-only incident failure audit for frozen v2 predictions."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT


RUN = "submission_entity_time_pair_v2_20261114_v1"
FREEZE = ROOT / "outputs" / RUN / "prediction_freeze.json"
PARENT = ROOT / "data/derived/submission_full_entity_time_20261114_v1"
PARENT_FREEZE = ROOT / "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json"
OUT = ROOT / "outputs/submission_v2_incident_miss_audit_20261114_v1.json"


def bucket(size: int) -> str:
    return "absent" if size == 0 else "1" if size == 1 else "2-10" if size <= 10 else "11-100" if size <= 100 else ">100"


def audit() -> dict:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    parent_freeze = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    orgs = sorted(freeze["prediction_sha256"])
    if len(orgs) != 499 or set(orgs) != set(parent_freeze["prediction_sha256"]):
        raise ValueError("Frozen organization cohort changed")
    # The parent holds only alert keys and candidate edges; label access starts here.
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    truth = read_truth(set(baseline), {a for x in baseline.values() for a in x["input_alert_keys"]})
    ranks = labels(set(baseline))
    overall, by_size, by_cohort = Counter(), defaultdict(Counter), defaultdict(Counter)
    split = json.loads((ROOT / "data/derived/guide_rerun_v2/split.json").read_text(encoding="utf-8"))
    for org in sorted(baseline):
        name = key(org)
        v2_path = ROOT / "data/derived" / RUN / f"v2_{name}.pkl"
        parent_path = PARENT / f"{name}.pkl"
        if sha256_file(v2_path) != freeze["prediction_sha256"][name]:
            raise ValueError("V2 prediction changed")
        if sha256_file(parent_path) != parent_freeze["prediction_sha256"][name]:
            raise ValueError("Candidate parent changed")
        with v2_path.open("rb") as stream:
            predicted = pickle.load(stream)
        with parent_path.open("rb") as stream:
            candidate = pickle.load(stream)
        keys = predicted["input_alert_keys"]
        if keys != candidate["input_alert_keys"]:
            raise ValueError("Candidate alert scope changed")
        n = len(keys)
        parent = list(range(n))
        sizes = [1] * n

        def root(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for edge in candidate["candidate_edges"]:
            i, j = divmod(int(edge), n)
            if truth[keys[i]] != truth[keys[j]]:
                continue
            a, b = root(i), root(j)
            if a != b:
                if sizes[a] < sizes[b]:
                    a, b = b, a
                parent[b] = a
                sizes[a] += sizes[b]
        gold_sizes = Counter(truth[a] for a in keys)
        candidate_parts = defaultdict(Counter)
        for i, alert in enumerate(keys):
            candidate_parts[truth[alert]][root(i)] += 1
        group_parts = defaultdict(list)
        order = sorted(range(len(predicted["groups"])), key=lambda i: (-predicted["scores"][i], i))
        position = {i: at for at, i in enumerate(order)}
        for i, group in enumerate(predicted["groups"]):
            for gold, overlap in Counter(truth[a] for a in group).items():
                if gold in ranks[org]:
                    group_parts[gold].append((overlap, len(group), position[i]))
        for gold in ranks[org]:
            count = gold_sizes[gold]
            if not count:
                reason = "absent_from_unambiguous_scope"
            elif max(candidate_parts[gold].values(), default=0) / count < .8:
                reason = "candidate_disconnected"
            else:
                parts = group_parts[gold]
                complete = [(overlap, size, pos) for overlap, size, pos in parts if overlap / count >= .8]
                if not complete:
                    reason = "split_by_linker_or_cap"
                elif not any(overlap / size >= .8 for overlap, size, _ in complete):
                    reason = "impure_group"
                elif not any(overlap / size >= .8 and pos < 20 for overlap, size, pos in complete):
                    reason = "recoverable_but_ranked_below_20"
                else:
                    reason = "recovered_deterministic_order"
            overall[reason] += 1
            by_size[bucket(count)][reason] += 1
            by_cohort[split.get(org, "unknown")][reason] += 1
    return {
        "classification": "evaluator_only_aggregate_frozen_v2_miss_audit_not_new_model_evaluation",
        "run": RUN, "organizations": len(orgs), "gold_top20_labels": sum(overall.values()),
        "reasons_are_mutually_exclusive": True,
        "counts": dict(overall),
        "by_incident_size": {k: dict(v) for k, v in sorted(by_size.items())},
        "by_historical_split": {k: dict(v) for k, v in sorted(by_cohort.items())},
        "ranking_tie_note": "Deterministic score/index order is diagnostic; official Recall@20 uses tie-aware expected ordering.",
        "v2_prediction_freeze_sha256": sha256_file(FREEZE),
        "candidate_prediction_freeze_sha256": sha256_file(PARENT_FREEZE),
        "analysis_code_sha256": sha256_file(Path(__file__)),
    }


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Audit already frozen")
    result = audit()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "audit_frozen", "counts": result["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
