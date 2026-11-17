"""Generator-only validation of hidden incident/template isolation before scoring."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"


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
    train = population(P31, "train")
    dev = population(P31, "development")
    hold = population(HERE, "locked_test")
    for a, b in ((train, dev), (train, hold), (dev, hold)):
        assert all(not x & y for x, y in zip(a, b))
    print(json.dumps({"train_incidents": len(train[0]), "development_incidents": len(dev[0]),
                      "holdout_incidents": len(hold[0]), "incident_scenario_template_overlap": 0}))


if __name__ == "__main__": main()
