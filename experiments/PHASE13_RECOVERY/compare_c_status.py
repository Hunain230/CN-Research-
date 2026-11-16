"""Paired recoverability gains and losses for frozen C sensitivity groups."""
from __future__ import annotations

import json
import pickle
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_entity_time import PARENT


def recoverable(groups, keys, truth, ranks):
    sizes = Counter(truth[a] for a in keys)
    found = set()
    for group in groups:
        counts = Counter(truth[a] for a in group)
        for incident, hits in counts.items():
            if incident in ranks and hits / sizes[incident] >= .8 and hits / len(group) >= .8:
                found.add(incident)
    return found


def main():
    out = HERE / "PHASE13_C_PAIRED_CHANGES.json"
    if out.exists():
        raise FileExistsError("Refusing overwrite")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    orgs = sorted(parent)
    truth = read_truth(set(orgs), {a for item in parent.values() for a in item["input_alert_keys"]})
    ranks = labels(set(orgs))
    freeze = json.loads((HERE / "c_predictions/prediction_freeze.json").read_text())
    totals = {x: Counter() for x in ("0.8", "0.85", "0.9")}
    for org in orgs:
        name = key(org)
        path = HERE / "c_predictions" / f"{name}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][name]:
            raise ValueError("Prediction hash changed")
        with path.open("rb") as stream:
            row = pickle.load(stream)
        keys = row["keys"]
        base = recoverable(row["groups"]["0.75"], keys, truth, ranks[org])
        for threshold in totals:
            changed = recoverable(row["groups"][threshold], keys, truth, ranks[org])
            gained, lost = changed-base, base-changed
            totals[threshold].update(newly_recoverable=len(gained), lost_recoverability=len(lost),
                                     gained_alerts=sum(truth[a] in gained for a in keys),
                                     lost_alerts=sum(truth[a] in lost for a in keys))
    result = {k: dict(v) | {"net": v["newly_recoverable"]-v["lost_recoverability"]} for k,v in totals.items()}
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
