"""Training-only detector/technique-aware group ranker on frozen v2 groups."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import vstack
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import LogisticRegression

from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth
from .phase2 import sha256_file
from .submission_full_guide import ROOT, tie_aware_ranking, write_json
from .submission_full_entity_time import read_docs
from .submission_entity_time_pair_v2 import SPLIT, shard_map
from .submission_group_ranker_v4 import group_features, bootstrap
from .submission_trained_ranker import training_targets
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


PREFIX = "submission_descriptor_ranker_v7_"
GROUP_RUN = "submission_entity_time_pair_v2_20261114_v1"
GROUP_FREEZE = ROOT / "outputs" / GROUP_RUN / "prediction_freeze.json"
V4_RUN = "submission_group_ranker_v4_20261114_v1"
V4_FREEZE = ROOT / "outputs" / V4_RUN / "prediction_freeze.json"
FIELDS = ("DetectorId", "Category", "MitreTechniques", "EntityType", "EvidenceRole")
BLENDS = (0.0, 0.25, 0.5, 0.75, 1.0)


def sources() -> dict:
    paths = (Path(__file__), ROOT / "src/submission_group_ranker_v4.py", GROUP_FREEZE,
             V4_FREEZE, SPLIT, ROOT / "outputs/submission_entity_time_shards_20261114_v1.json")
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def featurize(groups: list[list[str]], docs: dict, old_scores: list[float], hasher: FeatureHasher):
    numeric = group_features(groups, docs, old_scores)
    records = []
    for i, group in enumerate(groups):
        row = {f"numeric_{j}": float(value) for j, value in enumerate(numeric[i])}
        for field in FIELDS:
            values = set().union(*(docs[alert]["fields"][field] for alert in group))
            for value in values:
                row[f"descriptor_{field}={value}"] = 1.0
        records.append(row)
    return hasher.transform(records)


def load_org(org: str, group_freeze: dict, paths: dict, shard_manifest: dict, sentinels: dict):
    group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{key(org)}.pkl"
    if sha256_file(group_path) != group_freeze["prediction_sha256"][key(org)]:
        raise ValueError("Frozen groups changed")
    with group_path.open("rb") as stream:
        item = pickle.load(stream)
    path = paths[org]
    if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
        raise ValueError("Field projection changed")
    docs = read_docs(org, path, sentinels, set(item["input_alert_keys"]))
    return item, docs


def old_scores(org: str, freeze: dict) -> list[float]:
    path = ROOT / "data/derived" / V4_RUN / f"scores_{key(org)}.pkl"
    if sha256_file(path) != freeze["score_sha256"][key(org)]:
        raise ValueError("Frozen v4 scores changed")
    with path.open("rb") as stream:
        return pickle.load(stream)


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError("Versioned v7 run ID required")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new run ID")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v4_freeze = json.loads(V4_FREEZE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    train = [o for o in orgs if split.get(o) == "train"]
    development = [o for o in orgs if split.get(o) == "validation"]
    if len(orgs) != 499 or len(train) != 334 or len(development) != 67:
        raise ValueError("Historical organization split changed")
    train_truth = read_truth(set(train), {a for o in train for a in baseline[o]["input_alert_keys"]})
    train_ranks = labels(set(train))
    development_truth = read_truth(set(development), {a for o in development for a in baseline[o]["input_alert_keys"]})
    development_ranks = labels(set(development))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    x_parts, targets = [], []
    started = time.perf_counter()
    for index, org in enumerate(train, 1):
        item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
        x_parts.append(featurize(item["groups"], docs, item["scores"], hasher))
        targets.extend(training_targets(item, train_truth, train_ranks[org]))
        if index % 50 == 0:
            print(f"Prepared training groups {index}/334", flush=True)
    x_train = vstack(x_parts, format="csr")
    y_train = np.asarray(targets, dtype=np.uint8)
    if len(y_train) != 157072 or int(y_train.sum()) != 4624:
        raise ValueError("Training target changed")
    model = LogisticRegression(C=.25, solver="liblinear", max_iter=250, random_state=71)
    model.fit(x_train, y_train, sample_weight=np.where(y_train, 10.0, 1.0))
    del x_train, x_parts, targets
    table_rows = {blend: [] for blend in BLENDS}
    for org in development:
        item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
        probability = model.predict_proba(featurize(item["groups"], docs, item["scores"], hasher))[:, 1]
        v4 = np.asarray(old_scores(org, v4_freeze))
        for blend in BLENDS:
            scores = (1 - blend) * v4 + blend * probability
            metric = tie_aware_ranking(item["groups"], scores.tolist(), development_truth, development_ranks[org])
            table_rows[blend].append({"recall20": metric["recall_at_20"], "p10": metric["precision_at_10"]})
    table = {str(blend): {"recall20_macro": float(np.mean([row["recall20"] for row in rows])),
                          "p10_macro": float(np.mean([row["p10"] for row in rows]))}
             for blend, rows in table_rows.items()}
    eligible = [b for b in BLENDS if table[str(b)]["p10_macro"] >= table["0.0"]["p10_macro"]]
    selected = max(eligible, key=lambda b: (table[str(b)]["recall20_macro"], table[str(b)]["p10_macro"], -b))
    if table[str(selected)]["recall20_macro"] <= table["0.0"]["recall20_macro"]:
        selected = 0.0
    private.mkdir(parents=True)
    with (private / "descriptor_rank_model.pkl").open("wb") as stream:
        pickle.dump(model, stream, protocol=pickle.HIGHEST_PROTOCOL)
    score_hashes = {}
    for index, org in enumerate(orgs, 1):
        item, docs = load_org(org, group_freeze, paths, shard_manifest, sentinels)
        v4 = np.asarray(old_scores(org, v4_freeze))
        if selected:
            probability = model.predict_proba(featurize(item["groups"], docs, item["scores"], hasher))[:, 1]
            scores = ((1 - selected) * v4 + selected * probability).tolist()
        else:
            scores = v4.tolist()
        output = private / f"scores_{key(org)}.pkl"
        with output.open("wb") as stream:
            pickle.dump(scores, stream, protocol=pickle.HIGHEST_PROTOCOL)
        score_hashes[key(org)] = sha256_file(output)
        if index % 50 == 0:
            print(f"Frozen scores {index}/499", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_train_only_descriptor_ranker_development_blend_selection",
        "run": run_id, "training_organizations": 334, "development_organizations": 67,
        "train_groups": len(y_train), "positive_train_groups": int(y_train.sum()),
        "selected_blend": selected, "development_table": table,
        "selection_rule": "maximize_development_macro_recall20_with_p10_at_least_v4_and_strict_recall_gain",
        "validation_labels_read_for_selection": True,
        "holdout_labels_read_in_prediction_stage": False,
        "descriptor_fields": list(FIELDS),
        "model_sha256": sha256_file(private / "descriptor_rank_model.pkl"),
        "score_sha256": score_hashes, "source_sha256": sources(),
        "wall_seconds": time.perf_counter() - started,
    })
    print(json.dumps({"status": "predictions_frozen", "selected_blend": selected,
                      "development": table}, sort_keys=True))


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already frozen")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources():
        raise ValueError("Method source changed")
    if sha256_file(private / "descriptor_rank_model.pkl") != freeze["model_sha256"]:
        raise ValueError("Rank model changed")
    group_freeze = json.loads(GROUP_FREEZE.read_text(encoding="utf-8"))
    v4_freeze = json.loads(V4_FREEZE.read_text(encoding="utf-8"))
    with (ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl").open("rb") as stream:
        baseline = pickle.load(stream)
    orgs = sorted(baseline)
    truth = read_truth(set(orgs), {a for x in baseline.values() for a in x["input_alert_keys"]})
    ranks = labels(set(orgs))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(dict)
    for org in orgs:
        name = key(org)
        group_path = ROOT / "data/derived" / GROUP_RUN / f"v2_{name}.pkl"
        score_path = private / f"scores_{name}.pkl"
        if (sha256_file(group_path) != group_freeze["prediction_sha256"][name]
            or sha256_file(score_path) != freeze["score_sha256"][name]):
            raise ValueError("Frozen prediction changed")
        with group_path.open("rb") as stream:
            item = pickle.load(stream)
        with score_path.open("rb") as stream:
            selected_scores = pickle.load(stream)
        compare = (("v7_selected", selected_scores),
                   ("v4_reference", old_scores(org, v4_freeze)))
        for method, scores in compare:
            metric = tie_aware_ranking(item["groups"], scores, truth, ranks[org])
            rows[method][org] = {"recall20": metric["recall_at_20"],
                                 "p10": metric["precision_at_10"],
                                 "ndcg20": metric["ndcg_at_20_rank1_highest"]}
    cohorts = {"all_499_descriptive": orgs,
               "training_disjoint_135": [o for o in orgs if split.get(o) in ("validation", "holdout")],
               "holdout_68_previously_exposed": [o for o in orgs if split.get(o) == "holdout"]}
    result = {}
    for name, chosen in cohorts.items():
        result[name] = {"organizations": len(chosen), "expert_top20_denominator": 20 * len(chosen),
            "methods": {method: {metric: bootstrap([rows[method][o][metric] for o in chosen])
                                 for metric in ("recall20", "p10", "ndcg20")} for method in rows},
            "paired_v7_minus_v4": {metric: bootstrap([rows["v7_selected"][o][metric] - rows["v4_reference"][o][metric]
                                                   for o in chosen]) for metric in ("recall20", "p10", "ndcg20")}}
    metrics = {"classification": "exploratory_post_exposure_descriptor_ranker_not_confirmatory",
               "run": run_id, "selected_blend": freeze["selected_blend"],
               "groups_and_candidates": "identical_to_v2", "cohorts": result,
               "prediction_freeze_sha256": sha256_file(freeze_path),
               "limits": ["GUIDE_Test labels previously accessed", "No untouched cohort",
                          "Point-in-time field availability and operational approval unresolved"]}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {"classification": metrics["classification"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, private / "descriptor_rank_model.pkl", public / "metrics.json")},
        "private_score_sha256": freeze["score_sha256"]})
    print(json.dumps({"status": "exploratory_evaluation_complete", "selected_blend": freeze["selected_blend"],
                      "all_499_recall20": result["all_499_descriptive"]["methods"]["v7_selected"]["recall20"]["mean"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_descriptor_ranker_v7_20261114_v1")
    args = parser.parse_args()
    {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
