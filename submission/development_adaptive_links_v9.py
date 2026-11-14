"""Development-only small-component link expansion with matched v7 ranking."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction import FeatureHasher

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth, score_org
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from src.submission_full_entity_time import PARENT, RANKER, read_docs, generate
from src.submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability
from src.submission_group_ranker_v4 import group_features
from src.submission_trained_ranker import features as rank_features
from src.submission_descriptor_ranker_v7 import featurize, old_scores as unused_old_scores
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


OUT = ROOT / "outputs/submission_development_adaptive_links_v9_20261114_v1.json"
PAIR = ROOT / "data/derived/submission_entity_time_pair_v2_20261114_v1/pair_model.pkl"
V4 = ROOT / "data/derived/submission_group_ranker_v4_20261114_v1/rank_model.pkl"
V7 = ROOT / "data/derived/submission_descriptor_ranker_v7_20261114_v1/descriptor_rank_model.pkl"
V2_FREEZE = ROOT / "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json"
V7_FREEZE = ROOT / "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json"
CONFIGS = ("base", "floor50_cap3", "floor50_cap5", "floor60_cap5", "floor65_cap5",
           "floor50_cap5_descriptor", "floor60_cap8_descriptor")


def source_hashes() -> dict:
    paths = (Path(__file__), PAIR, V4, V7, V2_FREEZE, V7_FREEZE, SPLIT)
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def adaptive_groups(keys: list[str], docs: dict, edges: np.ndarray, probability: np.ndarray,
                    floor: float, cap: int, descriptor: bool) -> list[list[str]]:
    n = len(keys)
    parent = list(range(n))
    sizes = [1] * n

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    order = np.flatnonzero(probability >= floor)
    order = order[np.lexsort((edges[order], -probability[order]))]
    for t in order:
        a, b = divmod(int(edges[t]), n)
        x, y = root(a), root(b)
        if x == y:
            continue
        if probability[t] < .75:
            if sizes[x] + sizes[y] > cap:
                continue
            if descriptor:
                da, db = docs[keys[a]]["fields"], docs[keys[b]]["fields"]
                if not any(da[field] & db[field] for field in ("DetectorId", "Category", "MitreTechniques")):
                    continue
        if sizes[x] < sizes[y]:
            x, y = y, x
        parent[y] = x
        sizes[x] += sizes[y]
    groups = defaultdict(list)
    for i, alert in enumerate(keys):
        groups[root(i)].append(alert)
    return sorted((sorted(group) for group in groups.values()), key=lambda group: group[0])


def priority(groups: list[list[str]], docs: dict, base_ranker, v4, v7, hasher) -> list[float]:
    count, bm25 = score_groups(groups, {alert: doc["fields"] for alert, doc in docs.items()})
    initial = base_ranker.decision_function(rank_features({"count_scores": count,
                                                            "bm25_scores": bm25})).tolist()
    numeric = group_features(groups, docs, initial)
    tree = v4.predict_proba(numeric)[:, 1]
    descriptor = v7.predict_proba(featurize(groups, docs, initial, hasher))[:, 1]
    return (.25*tree + .75*descriptor).tolist()


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Development audit already frozen")
    with PAIR.open("rb") as stream:
        pair_model = pickle.load(stream)
    with V4.open("rb") as stream:
        v4 = pickle.load(stream)
    with V7.open("rb") as stream:
        v7 = pickle.load(stream)
    with RANKER.open("rb") as stream:
        base_ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    chosen = sorted(org for org in parent if split.get(org) == "validation"
                    and len(parent[org]["input_alert_keys"]) <= 500)
    if len(chosen) != 42:
        raise ValueError("Development cohort changed")
    truth = read_truth(set(chosen), {alert for org in chosen for alert in parent[org]["input_alert_keys"]})
    ranks = labels(set(chosen))
    paths, shard_manifest = shard_map()
    sentinels, _ = detect_modal_sentinels()
    hasher = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)
    rows = {config: [] for config in CONFIGS}
    for index, org in enumerate(chosen, 1):
        path = paths[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, pair_model)
        for config in CONFIGS:
            if config == "base":
                groups = adaptive_groups(keys, docs, edges, probability, .75, 0, False)
            else:
                parts = config.split("_")
                groups = adaptive_groups(keys, docs, edges, probability,
                                         int(parts[0][5:]) / 100, int(parts[1][3:]),
                                         "descriptor" in parts)
            scores = priority(groups, docs, base_ranker, v4, v7, hasher)
            ranking = tie_aware_ranking(groups, scores, truth, ranks[org])
            pairs = score_org(groups, scores, truth, ranks[org], keys,
                              {"top20_recovery_min_completeness": .8,
                               "top20_recovery_min_purity": .8})
            gold_counts = Counter(truth[alert] for alert in keys)
            recoverable = set()
            for group in groups:
                membership = Counter(truth[alert] for alert in group)
                gold, overlap = max(membership.items(), key=lambda item: (item[1], item[0]))
                if gold in ranks[org] and overlap / gold_counts[gold] >= .8 and overlap / len(group) >= .8:
                    recoverable.add(gold)
            rows[config].append({"recall20": ranking["recall_at_20"],
                                 "p10": ranking["precision_at_10"],
                                 "ndcg20": ranking["ndcg_at_20_rank1_highest"],
                                 "tp": pairs["pair_tp"], "fp": pairs["pair_fp"],
                                 "fn": pairs["pair_fn"], "recoverable": len(recoverable),
                                 "groups": len(groups)})
        if index % 10 == 0:
            print(f"Adaptive links checked {index}/42 development queues", flush=True)
    table = {}
    for config, series in rows.items():
        tp, fp, fn = (sum(row[field] for row in series) for field in ("tp", "fp", "fn"))
        table[config] = {"recall20_macro": float(np.mean([row["recall20"] for row in series])),
                         "p10_macro": float(np.mean([row["p10"] for row in series])),
                         "ndcg20_macro": float(np.mean([row["ndcg20"] for row in series])),
                         "pair_precision_micro": tp/(tp+fp) if tp+fp else 0,
                         "pair_recall_micro": tp/(tp+fn),
                         "pair_f1_micro": 2*tp/(2*tp+fp+fn),
                         "pair_false_positives": fp,
                         "recoverable_labels": sum(row["recoverable"] for row in series),
                         "predicted_groups": sum(row["groups"] for row in series)}
    base = table["base"]
    eligible = [config for config in CONFIGS if table[config]["pair_precision_micro"] >= .8
                and table[config]["p10_macro"] >= base["p10_macro"]]
    selected = max(eligible, key=lambda config: (table[config]["recall20_macro"],
                                                  table[config]["recoverable_labels"],
                                                  table[config]["pair_precision_micro"]))
    if table[selected]["recall20_macro"] <= base["recall20_macro"]:
        selected = "base"
    write_json(OUT, {"classification": "exploratory_development_only_adaptive_link_group_study",
                     "development_organizations": 42, "selected_config": selected,
                     "selection_rule": "maximize_development_recall20_subject_to_pair_precision_0.8_and_p10_at_least_base_with_strict_recall_gain",
                     "table": table, "source_sha256": source_hashes(),
                     "holdout_labels_read": False})
    print(json.dumps({"selected": selected, "table": table}, sort_keys=True))


if __name__ == "__main__":
    main()
