"""Generator validation across Phase 31–34 train/dev/holdout template namespaces."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
P33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"


def lines(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def population(base, split):
    manifest = json.loads((base / "dataset" / f"{split}_manifest.json").read_text(encoding="utf-8"))
    truth = base / "dataset/evaluator_only" / split / "ground_truth_private"
    ids, templates, scenarios = set(), set(), set()
    for item in manifest["queues"]:
        for x in lines(truth / f"{item['queue_id']}_priority.jsonl"):
            ids.add(x["incident_id"]); templates.add(x["template_id"]); scenarios.add(x["scenario_id"])
    return ids, templates, scenarios


def main():
    cohorts = [population(P31, "train"), population(P31, "development"),
               population(P33, "locked_test"), population(HERE, "train"),
               population(HERE, "development")]
    for i, left in enumerate(cohorts):
        for right in cohorts[i + 1:]:
            assert all(not a & b for a, b in zip(left, right))
    print(json.dumps({"cohorts": len(cohorts), "phase34_train_incidents": len(cohorts[-2][0]),
                      "phase34_development_incidents": len(cohorts[-1][0]),
                      "hidden_incident_scenario_exact_template_overlap": 0}))


if __name__ == "__main__": main()
