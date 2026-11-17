"""Write the immutable experiment contract before fresh holdout generation."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
ART = HERE / "artifacts"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    published = json.loads((V4 / "experiments/locked_test_result.json").read_text(encoding="utf-8"))["selected"]
    reproduced = json.loads((ART / "historical_reproduction.json").read_text(encoding="utf-8"))["summary"]
    assert published == reproduced
    files = [V4 / "configs/study.json", V4 / "datasets/manifest.json", V4 / "predict.py",
             V4 / "simulator.py", V4 / "METRIC_AND_SELECTION_CONTRACT.md",
             V4 / "experiments/locked_test_result.json",
             V4 / "experiments/predictions/locked_test_lineage_one_context_v.jsonl",
             V4 / "experiments/predictions/development_lineage_one_context_v.jsonl",
             ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"]
    snapshot = {"historical_reference": "Phase 16 v4 selected lineage_one_context_v",
                "published_and_reproduced": reproduced,
                "frozen_file_sha256": {rel(x): sha(x) for x in files},
                "development_baseline": json.loads((ART / "development_baseline_evaluation.json").read_text(encoding="utf-8"))["summary"]}
    (HERE / "BASELINE_METRICS.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    fresh = ART / "fresh_cohort"
    (fresh / "configs").mkdir(parents=True, exist_ok=True)
    old = (V4 / "simulator.py").read_text(encoding="utf-8")
    old_loop = '(("train",(0,1,2,3)),("development",(4,)),("locked_test",(5,)))'
    assert old.count(old_loop) == 1
    generator = old.replace(old_loop, '(("locked_test",(6,)),)').replace('phase16v4_{split}_q', 'recallh_{split}_q')
    assert generator != old
    (fresh / "simulator.py").write_text(generator, encoding="utf-8")
    config = json.loads((V4 / "configs/study.json").read_text(encoding="utf-8"))
    config["schema"] = "recall-only-fresh-phase16-family-v1"
    config["seeds"] = {"locked_test": 116437}
    config["queues"] = {"locked_test": 30}
    (fresh / "configs/study.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    frozen = [HERE / "run_development.py", HERE / "run_holdout.py", V4 / "predict.py",
              ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py",
              HERE / "artifacts/development_source_depth.jsonl"]
    seal = {"selected_candidate": "source_depth", "selection_rule": "highest development Recall@20 among candidates passing all gates",
            "development_recall": "220/300", "development_p10": "93/150",
            "frozen_files": {rel(x): sha(x) for x in frozen},
            "generator_sha256": sha(fresh / "simulator.py"),
            "holdout_config_sha256": sha(fresh / "configs/study.json")}
    (ART / "selection_freeze.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    print(json.dumps(seal, indent=2))


if __name__ == "__main__":
    main()
