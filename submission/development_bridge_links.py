"""Development-only test of corroborated lower-probability link bridges."""

from __future__ import annotations

import json
import pickle
from collections import Counter
from pathlib import Path

import numpy as np

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth, score_org
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from src.submission_full_entity_time import PARENT, RANKER, read_docs, generate
from src.submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability, token_frequencies
from src.submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels
from submission.calibrate_component_cap_v3 import groups_at


MODEL = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl"
FREEZE = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json"
OUT = ROOT / "outputs/submission_development_bridge_links_20261114_v1.json"


def bridge_mask(keys: list[str], docs: dict, edges: np.ndarray, probability: np.ndarray,
                floor: float, route: str) -> np.ndarray:
    n = len(keys)
    frequency = token_frequencies(docs)
    mask = probability >= .75
    for t in np.flatnonzero((probability >= floor) & (probability < .75)):
        a, b = divmod(int(edges[t]), n)
        left, right = docs[keys[a]], docs[keys[b]]
        shared = left["entities"] & right["entities"]
        if route == "two_shared_entities":
            allow = len(shared) >= 2
        else:
            descriptor = bool(left["fields"]["Category"] & right["fields"]["Category"] or
                              left["fields"]["MitreTechniques"] & right["fields"]["MitreTechniques"])
            allow = descriptor and any(frequency[token] <= 5 for token in shared)
        mask[t] = allow
    return mask


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Development experiment already frozen")
    fit = json.loads(FREEZE.read_text(encoding="utf-8"))
    if sha256_file(MODEL) != fit["model_sha256"]:
        raise ValueError("Pair model changed")
    with MODEL.open("rb") as stream:
        model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    chosen = sorted(o for o in parent if split.get(o) == "validation" and len(parent[o]["input_alert_keys"]) <= 500)
    if len(chosen) != 42:
        raise ValueError("Development cohort changed")
    truth = read_truth(set(chosen), {a for o in chosen for a in parent[o]["input_alert_keys"]})
    ranks = labels(set(chosen))
    paths, manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    configs = ["base_075", "two_entities_050", "rare_descriptor_050", "two_entities_065", "rare_descriptor_065"]
    rows = {name: [] for name in configs}
    for index, org in enumerate(chosen, 1):
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        for name in configs:
            if name == "base_075":
                selected = probability
                threshold = .75
            else:
                route, floor = name.rsplit("_", 1)
                threshold = int(floor) / 100
                mask = bridge_mask(keys, docs, edges, probability, threshold,
                                   "two_shared_entities" if route == "two_entities" else "rare_and_descriptor")
                selected = np.where(mask, probability, 0)
            groups = groups_at(keys, edges, selected, threshold, 100)
            count, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in keys})
            scores = ranker.decision_function(rank_features({"count_scores": count, "bm25_scores": bm25})).tolist()
            metric = tie_aware_ranking(groups, scores, truth, ranks[org])
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": .8, "top20_recovery_min_purity": .8})
            rows[name].append({"recall20": metric["recall_at_20"], "p10": metric["precision_at_10"],
                               "tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"],
                               "groups": len(groups)})
        if index % 10 == 0:
            print(f"Bridge test {index}/42 development queues", flush=True)
    table = {}
    for name, series in rows.items():
        tp, fp, fn = (sum(row[field] for row in series) for field in ("tp", "fp", "fn"))
        table[name] = {"recall20_macro": sum(row["recall20"] for row in series) / len(series),
                       "p10_macro": sum(row["p10"] for row in series) / len(series),
                       "pair_precision_micro": tp / (tp + fp) if tp + fp else 0,
                       "pair_f1_micro": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                       "false_positive_pairs": fp, "predicted_groups": sum(row["groups"] for row in series)}
    baseline = table["base_075"]
    eligible = [name for name in configs if table[name]["pair_precision_micro"] >= .8]
    selected = max(eligible, key=lambda name: (table[name]["recall20_macro"],
                                                table[name]["pair_precision_micro"]))
    if table[selected]["recall20_macro"] <= baseline["recall20_macro"]:
        selected = "base_075"
    result = {"classification": "development_only_bridge_link_sensitivity_not_new_test",
              "organizations": len(chosen), "table": table, "selected_config": selected,
              "selection_rule": "maximize_development_recall20_with_pair_precision_at_least_0.8_and_strict_gain_over_base",
              "validation_labels_read": True, "holdout_labels_read": False,
              "pair_model_sha256": sha256_file(MODEL),
              "analysis_code_sha256": sha256_file(Path(__file__))}
    write_json(OUT, result)
    print(json.dumps({"selected": selected, "base": baseline, "chosen": table[selected]}, sort_keys=True))


if __name__ == "__main__":
    main()
