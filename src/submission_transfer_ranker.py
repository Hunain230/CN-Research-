"""Exploratory transfer of a frozen trained ranker to 57 prior small queues.

Prediction reads raw allowed alert descriptors and frozen predicted groups. It
does not read membership or queue ranks. Evaluation opens truth afterward.
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from .guide_rerun_v2 import labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, load_alerts, score_groups, tie_aware_ranking
from .submission_rank_fusion import bootstrap, write_json
from .submission_trained_ranker import features


PREFIX = "submission_transfer_ranker_"
PARENT = ROOT / "data/derived/offline_joint_v2/predictions.pkl"
PARENT_MANIFEST = ROOT / "outputs/offline_joint_v2/run_manifest.json"
MODEL = ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl"
MODEL_MANIFEST = ROOT / "outputs/submission_trained_ranker_20261114_v1/run_manifest.json"
METHOD_TO_GROUPS = {
    "rule": "B1_rule_bm25",
    "cp": "offline_CP_proxy",
    "cpv": "offline_CPV_proxy",
}


def verify_upstream() -> None:
    for path, manifest_path in ((PARENT, PARENT_MANIFEST), (MODEL, MODEL_MANIFEST)):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(path) != manifest["sha256"][str(path.relative_to(ROOT))]:
            raise ValueError(f"Frozen upstream hash mismatch: {path}")


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Use a new versioned run ID")
    verify_upstream()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    if len(parent) != 57:
        raise ValueError("Parent cohort changed")
    by_org, census = load_alerts(set(parent))
    scores = {}
    for org, item in parent.items():
        docs = by_org[org]
        if set(docs) != set(item["input_alert_keys"]):
            raise ValueError("Alert universe differs from frozen parent")
        methods = {}
        for short, original in METHOD_TO_GROUPS.items():
            groups = item["methods"][original]["groups"]
            count, bm25 = score_groups(groups, docs)
            methods[short] = model.decision_function(features({"count_scores": count, "bm25_scores": bm25})).tolist()
        scores[org] = methods
    private.mkdir(parents=True)
    path = private / "scores.pkl"
    with path.open("wb") as stream:
        pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_transfer_ranker_on_frozen_small_queue_groups",
        "run": run_id,
        "organizations": len(scores),
        "parent_prediction_sha256": sha256_file(PARENT),
        "trained_model_sha256": sha256_file(MODEL),
        "source_code_sha256": sha256_file(Path(__file__)),
        "prediction_sha256": sha256_file(path),
        "evaluation_labels_read_in_prediction_stage": False,
        "candidate_pairs_and_groups": "identical to offline_joint_v2 parent",
        "model_training_organizations": 334,
        "raw_scan_rows": census["raw_rows_scanned"],
        "local_descriptor_fields_only": True,
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, "organizations": len(scores)}, sort_keys=True))


def evaluate(run_id: str) -> None:
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id / "scores.pkl"
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation exists")
    freeze = json.loads((public / "prediction_freeze.json").read_text(encoding="utf-8"))
    verify_upstream()
    if (sha256_file(private) != freeze["prediction_sha256"] or sha256_file(PARENT) != freeze["parent_prediction_sha256"] or sha256_file(MODEL) != freeze["trained_model_sha256"] or sha256_file(Path(__file__)) != freeze["source_code_sha256"]):
        raise ValueError("Frozen prediction lineage changed")
    with private.open("rb") as stream:
        transfer = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    if set(parent) != set(transfer):
        raise ValueError("Organization mismatch")
    orgs = set(parent)
    alerts = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alerts)
    ranks = labels(orgs)
    rows: dict[str, list[dict]] = defaultdict(list)
    for org, item in sorted(parent.items()):
        keys = item["input_alert_keys"]
        choices = [(name, value["groups"], value["scores"]) for name, value in item["methods"].items()]
        choices.extend((f"transfer_{short}", item["methods"][original]["groups"], transfer[org][short]) for short, original in METHOD_TO_GROUPS.items())
        for name, groups, scores in choices:
            raw = score_org(groups, scores, truth, ranks[org], keys, {"top20_recovery_min_completeness": 0.8, "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name].append({"p10": tied["precision_at_10"], "recall20": tied["recall_at_20"], "ndcg1": tied["ndcg_at_20_rank1_highest"], "pair_f1": raw["pair_f1"], "pair_tp": raw["pair_tp"], "pair_fp": raw["pair_fp"], "pair_fn": raw["pair_fn"]})
    metrics = {
        "classification": "exploratory_transfer_on_previously_exposed_57_small_queues_not_confirmatory",
        "run": run_id,
        "organizations": len(orgs),
        "alerts": len(alerts),
        "candidate_pairs": sum(item["candidate_pair_count"] for item in parent.values()),
        "expert_top20_denominator": len(orgs) * 20,
        "methods": {name: {
            "precision_at_10_macro": bootstrap([row["p10"] for row in series]),
            "end_to_end_recall_at_20_macro": bootstrap([row["recall20"] for row in series]),
            "ndcg_at_20_rank1_high_macro": bootstrap([row["ndcg1"] for row in series]),
            "pair_f1_macro": bootstrap([row["pair_f1"] for row in series]),
            "pair_confusion_micro": {key: sum(row[key] for row in series) for key in ("pair_tp", "pair_fp", "pair_fn")},
        } for name, series in rows.items()},
        "paired_transfer_cpv_minus_original_cpv": {
            key: bootstrap([a[key] - b[key] for a, b in zip(rows["transfer_cpv"], rows["offline_CPV_proxy"])]) for key in ("p10", "recall20", "ndcg1")
        },
        "limits": ["57 previously exposed complete small queues", "frozen parent groups and candidates; ranking only", "trained model fitted on 334 different organizations but method choice followed prior project evaluation", "offline CP/CPV are statistical proxies, not LLM agents", "field, rank, and active-queue semantics unresolved"],
        "prediction_freeze_sha256": sha256_file(public / "prediction_freeze.json"),
    }
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_transfer_ranker predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_transfer_ranker evaluate --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), private, public / "prediction_freeze.json", public / "metrics.json")},
        "parent_prediction_sha256": freeze["parent_prediction_sha256"],
        "trained_model_sha256": freeze["trained_model_sha256"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id, "transfer_cpv_recall20_macro": metrics["methods"]["transfer_cpv"]["end_to_end_recall_at_20_macro"]["mean"]}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_transfer_ranker_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
