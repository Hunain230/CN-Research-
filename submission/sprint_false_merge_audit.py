"""Evaluator-side pair-set transitions for frozen grouping experiments."""

from __future__ import annotations

import itertools
import json
import pickle
from collections import Counter

from src.guide_rerun_v2 import key
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json


V2 = "submission_entity_time_pair_v2_20261114_v1"
G = "phase9g_pair_boundary_20261115_v1"
S = "sprint_consensus_split_v1_20261116"


def false_pairs(groups, truth):
    return {tuple(sorted((a,b))) for group in groups for a,b in itertools.combinations(group,2)
            if truth[a] != truth[b]}


def main():
    out = ROOT / "outputs/sprint_false_merge_audit_20261116.json"
    if out.exists():
        raise FileExistsError("Audit already frozen")
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    freezes = {run: json.loads((ROOT / "outputs" / run / "prediction_freeze.json").read_text())
               for run in (V2,G,S)}
    totals = {run: Counter() for run in (G,S)}
    for org in orgs:
        name = key(org)
        files = {
            V2: (ROOT / "data/derived" / V2 / f"v2_{name}.pkl", freezes[V2]["prediction_sha256"][name]),
            G: (ROOT / "data/derived" / G / f"prediction_{name}.pkl", freezes[G]["prediction_sha256"][name]),
            S: (ROOT / "data/derived" / S / f"prediction_{name}.pkl", freezes[S]["prediction_sha256"][name]),
        }
        groups = {}
        for run,(path,digest) in files.items():
            if sha256_file(path) != digest:
                raise ValueError("Frozen grouping prediction changed")
            with path.open("rb") as stream:
                groups[run] = pickle.load(stream)["groups"]
        before = false_pairs(groups[V2],truth)
        for run in (G,S):
            after = false_pairs(groups[run],truth)
            totals[run].update({"baseline_false_pairs":len(before), "proposed_false_pairs":len(after),
                                "new_false_pairs":len(after-before),
                                "removed_false_pairs":len(before-after),
                                "retained_false_pairs":len(before&after)})
    expected = {G:(137884,28606), S:(21905,28606)}
    for run,(after,before) in expected.items():
        assert totals[run]["proposed_false_pairs"] == after
        assert totals[run]["baseline_false_pairs"] == before
        assert totals[run]["new_false_pairs"]-totals[run]["removed_false_pairs"] == after-before
    write_json(out,{"classification":"evaluator_side_retrospective_false_pair_transition",
                    "definition":"new_false_pairs count cross-incident alert pairs coassigned in proposed groups but not frozen v2 groups; not wrong union-edge decisions",
                    "queues":499,"baseline":V2,"transitions":{run:dict(count) for run,count in totals.items()},
                    "prediction_freeze_sha256":{run:sha256_file(ROOT / "outputs" / run / "prediction_freeze.json")
                                                for run in (V2,G,S)}})
    print(json.dumps({run:dict(count) for run,count in totals.items()}))


if __name__ == "__main__":
    main()
