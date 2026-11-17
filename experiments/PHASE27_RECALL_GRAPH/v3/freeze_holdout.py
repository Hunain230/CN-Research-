"""Write the single-candidate pre-evaluation protocol before holdout exists."""
import json
from pathlib import Path

from run_study import HERE, dump_json, sha


def main():
    assert not (HERE / "datasets/locked_test").exists()
    assert not (HERE / "pre_evaluation_protocol.json").exists()
    freeze = json.loads((HERE / "freeze_manifest.json").read_text())
    for name, expected in freeze["hashes"].items():
        assert sha(HERE / name) == expected, name
    selected = json.loads((HERE / "development_selection.json").read_text())["selected"]
    assert selected and selected["passed"] and selected["queue_safe"]
    assert selected["mode"] == "phase26_baseline" and selected["ranker"] == "train_fitted"
    names = ("config.json", "generate.py", "evidence.py", "graph.py", "run_study.py",
             "holdout.py", "holdout_run.py", "ranker_model.json",
             "development_selection.json", "freeze_manifest.json")
    dump_json(HERE / "pre_evaluation_protocol.json", {
        "selection_rule": "highest development Recall@20 among candidates passing all predeclared gates",
        "selected": selected,
        "baseline": {"mode": "phase26_baseline", "ranker": "progression"},
        "holdout_namespace": "phase27k", "holdout_seed": 273571,
        "holdout_queues": 30,
        "one_open_rule": "Predict only frozen selected and baseline; hash predictions; open private truth once",
        "hashes": {name: sha(HERE / name) for name in names}})


if __name__ == "__main__":
    main()
