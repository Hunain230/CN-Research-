"""Freeze selected Phase 28 promotion rule before any holdout data exists."""
import json

from study import HERE, PHASE27, sha, write_json


def main():
    assert not (HERE / "datasets/locked_test").exists()
    assert not (HERE / "pre_evaluation_protocol.json").exists()
    dev = json.loads((HERE / "development_freeze.json").read_text())
    for name, expected in dev["hashes"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in dev["phase27_reference_hashes"].items():
        assert sha(PHASE27 / name) == expected, name
    selected = json.loads((HERE / "development_selection.json").read_text())["selected"]
    assert selected and selected["passed"] and selected["queue_safe"]
    assert selected["mode"] == "component" and selected["ranker"] == "phase27_selected"
    names = ("config.json", "generate.py", "promote.py", "study.py", "holdout.py",
             "holdout_run.py", "promotion_model.json", "development_selection.json",
             "development_freeze.json")
    write_json(HERE / "pre_evaluation_protocol.json", {
        "selected": selected,
        "baseline": {"mode": "baseline", "ranker": "phase27_selected"},
        "holdout_namespace": "phase28h", "holdout_seed": 282251,
        "holdout_queues": 30, "independent_false_challenge_per_queue": 1,
        "one_open_rule": "predict selected and baseline, hash outputs, then open private truth once",
        "phase27_reference_hashes": dev["phase27_reference_hashes"],
        "hashes": {name: sha(HERE / name) for name in names}})


if __name__ == "__main__":
    main()
