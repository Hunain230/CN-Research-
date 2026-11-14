"""Development-only constrained group-merge test for 2–10-alert split incidents."""

from __future__ import annotations

import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth, score_org
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from src.submission_full_entity_time import PARENT, RANKER, read_docs, generate
from src.submission_entity_time_pair_v2 import SPLIT, shard_map, predict_probability, token_frequencies
from src.submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


V2_RUN = "submission_entity_time_pair_v2_20261114_v1"
V2 = ROOT / "data/derived" / V2_RUN
V2_FREEZE = ROOT / "outputs" / V2_RUN / "prediction_freeze.json"
MODEL = V2 / "pair_model.pkl"
OUT = ROOT / "outputs/submission_development_group_merge_20261114_v1.json"
CONFIGS = (("base", 0, 0.0), ("support2_p45", 2, .45),
           ("support2_p55", 2, .55), ("support3_p45", 3, .45))


def merge_groups(keys: list[str], groups: list[list[str]], docs: dict,
                 edges: np.ndarray, probability: np.ndarray,
                 support_needed: int, floor: float) -> list[list[str]]:
    if support_needed == 0:
        return groups
    n = len(keys)
    group_of = {alert: i for i, group in enumerate(groups) for alert in group}
    frequency = token_frequencies(docs)
    support = defaultdict(set)
    strongest = defaultdict(float)
    for t in np.flatnonzero((probability >= floor) & (probability < .75)):
        a, b = divmod(int(edges[t]), n)
        ga, gb = group_of[keys[a]], group_of[keys[b]]
        if ga == gb or max(len(groups[ga]), len(groups[gb])) > 20 or len(groups[ga]) + len(groups[gb]) > 100:
            continue
        if len(groups[ga]) == len(groups[gb]) == 1:
            continue
        left, right = docs[keys[a]], docs[keys[b]]
        shared = left["entities"] & right["entities"]
        descriptor = bool(left["fields"]["Category"] & right["fields"]["Category"] or
                          left["fields"]["MitreTechniques"] & right["fields"]["MitreTechniques"])
        if not descriptor or not any(frequency[token] <= 10 for token in shared):
            continue
        pair = tuple(sorted((ga, gb)))
        support[pair].add((a, b))
        strongest[pair] = max(strongest[pair], float(probability[t]))
    parent = list(range(len(groups)))
    sizes = [len(g) for g in groups]

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    eligible = [pair for pair in support if len(support[pair]) >= support_needed]
    for ga, gb in sorted(eligible, key=lambda p: (-len(support[p]), -strongest[p], p)):
        a, b = root(ga), root(gb)
        if a == b or sizes[a] + sizes[b] > 100:
            continue
        if sizes[a] < sizes[b]:
            a, b = b, a
        parent[b] = a
        sizes[a] += sizes[b]
    result = defaultdict(list)
    for i, group in enumerate(groups):
        result[root(i)].extend(group)
    return sorted((sorted(v) for v in result.values()), key=lambda g: g[0])


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Merge study already frozen")
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
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
    rows = {name: [] for name, _, _ in CONFIGS}
    started = time.perf_counter()
    for index, org in enumerate(chosen, 1):
        v2_path = V2 / f"v2_{key(org)}.pkl"
        if sha256_file(v2_path) != v2_freeze["prediction_sha256"][key(org)]:
            raise ValueError("V2 groups changed")
        with v2_path.open("rb") as stream:
            v2 = pickle.load(stream)
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = v2["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, model)
        for name, support, floor in CONFIGS:
            groups = merge_groups(keys, v2["groups"], docs, edges, probability, support, floor)
            count, bm25 = score_groups(groups, {a: docs[a]["fields"] for a in keys})
            scores = ranker.decision_function(rank_features({"count_scores": count, "bm25_scores": bm25})).tolist()
            metric = tie_aware_ranking(groups, scores, truth, ranks[org])
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": .8, "top20_recovery_min_purity": .8})
            rows[name].append({"recall20": metric["recall_at_20"], "p10": metric["precision_at_10"],
                               "tp": raw["pair_tp"], "fp": raw["pair_fp"], "fn": raw["pair_fn"],
                               "groups": len(groups)})
        if index % 10 == 0:
            print(f"Group merge study {index}/42 queues", flush=True)
    table = {}
    for name, series in rows.items():
        tp, fp, fn = (sum(r[k] for r in series) for k in ("tp", "fp", "fn"))
        table[name] = {"recall20_macro": sum(r["recall20"] for r in series) / len(series),
                       "p10_macro": sum(r["p10"] for r in series) / len(series),
                       "pair_precision_micro": tp / (tp + fp) if tp + fp else 0,
                       "pair_f1_micro": 2 * tp / (2 * tp + fp + fn),
                       "false_positive_pairs": fp,
                       "predicted_groups": sum(r["groups"] for r in series)}
    eligible = [name for name in table if table[name]["pair_precision_micro"] >= .8]
    selected = max(eligible, key=lambda name: (table[name]["recall20_macro"], table[name]["pair_precision_micro"]))
    if table[selected]["recall20_macro"] <= table["base"]["recall20_macro"]:
        selected = "base"
    result = {"classification": "development_only_constrained_group_merge_sensitivity",
              "organizations": len(chosen), "table": table, "selected_config": selected,
              "selection_rule": "maximize_development_recall20_with_pair_precision_at_least_0.8_and_strict_gain_over_base",
              "validation_labels_read": True, "holdout_labels_read": False,
              "v2_prediction_freeze_sha256": sha256_file(V2_FREEZE),
              "analysis_code_sha256": sha256_file(Path(__file__)),
              "wall_seconds": time.perf_counter() - started}
    write_json(OUT, result)
    print(json.dumps({"selected": selected, "table": table}, sort_keys=True))


if __name__ == "__main__":
    main()
