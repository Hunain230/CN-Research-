"""Check hidden incident, scenario, and exact-template isolation before fitting."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
P34 = ROOT / "experiments/PHASE34_FROZEN_RANK_GENERALIZATION"
P35 = ROOT / "experiments/PHASE35_NEAR_BOUNDARY_RANKING"
P36 = ROOT / "experiments/PHASE36_EVIDENCE_AWARE_RECALL"


def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def population(base, split):
    manifest = json.loads((base / "dataset" / f"{split}_manifest.json").read_text(encoding="utf-8"))
    truth = base / "dataset/evaluator_only" / split / "ground_truth_private"
    ids, scenarios, templates = set(), set(), set()
    for queue in manifest["queues"]:
        for x in lines(truth / f"{queue['queue_id']}_priority.jsonl"):
            ids.add(x["incident_id"]); scenarios.add(x["scenario_id"]); templates.add(x["template_id"])
    return ids, scenarios, templates


def main():
    cohorts = [(P31, "train"), (P31, "development"), (P33, "locked_test"),
               (P34, "train"), (P34, "development"), (P35, "train"),
               (P35, "development"), (P36, "train"), (P36, "development"),
               (HERE, "development")]
    populations = [population(*x) for x in cohorts]
    for i, a in enumerate(populations):
        for b in populations[i+1:]:
            assert all(not x & y for x, y in zip(a, b)), (cohorts[i], cohorts[populations.index(b)])
    print(json.dumps({"cohorts": len(cohorts),
                      "phase37_development_incidents": len(populations[-1][0]), "overlap": 0}))


if __name__ == "__main__": main()
