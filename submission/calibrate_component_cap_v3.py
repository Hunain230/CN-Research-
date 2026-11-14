"""Development-only threshold/component-cap selection for frozen v2 pair scores."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth, score_org
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, score_groups, tie_aware_ranking, write_json
from src.submission_full_entity_time import PARENT, RANKER, read_docs, generate
from src.submission_entity_time_pair_v2 import (shard_map, predict_probability,
                                                source_hashes, SPLIT)
from src.submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


RUN = "submission_entity_time_pair_v2_20261114_v1"
MODEL = ROOT / "data/derived" / RUN / "pair_model.pkl"
OUT = ROOT / "outputs/submission_component_cap_calibration_20261114_v1.json"
THRESHOLDS = (0.5, 0.75)
CAPS = (5, 10, 20, 50, 100)


def groups_at(keys: list[str], edges: np.ndarray, probability: np.ndarray,
              threshold: float, cap: int) -> list[list[str]]:
    n = len(keys)
    parent = list(range(n))
    sizes = [1] * n

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    selected = np.flatnonzero(probability >= threshold)
    order = selected[np.lexsort((edges[selected], -probability[selected]))]
    for t in order:
        a, b = divmod(int(edges[t]), n)
        x, y = root(a), root(b)
        if x == y or sizes[x] + sizes[y] > cap:
            continue
        if sizes[x] < sizes[y]:
            x, y = y, x
        parent[y] = x
        sizes[x] += sizes[y]
    grouped: dict[int, list[str]] = defaultdict(list)
    for i, alert in enumerate(keys):
        grouped[root(i)].append(alert)
    return sorted((sorted(v) for v in grouped.values()), key=lambda g: g[0])


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Calibration already frozen")
    fit_freeze = json.loads((ROOT / "outputs" / RUN / "fit_freeze.json").read_text(encoding="utf-8"))
    if fit_freeze["source_sha256"] != source_hashes() or sha256_file(MODEL) != fit_freeze["model_sha256"]:
        raise ValueError("Frozen pair model changed")
    with MODEL.open("rb") as stream:
        pair_model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    chosen = sorted(o for o, x in parent.items() if split.get(o) == "validation"
                    and len(x["input_alert_keys"]) <= 500)
    if len(chosen) != 42:
        raise ValueError("Development cohort changed")
    truth = read_truth(set(chosen), {a for o in chosen for a in parent[o]["input_alert_keys"]})
    ranks = labels(set(chosen))
    sentinels, _ = detect_modal_sentinels()
    paths, manifest = shard_map()
    rows = {f"{t}:{cap}": [] for t in THRESHOLDS for cap in CAPS}
    for index, org in enumerate(chosen, 1):
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        edges, flags, _ = generate(keys, docs, parent[org]["candidate_edges"])
        probability = predict_probability(keys, docs, edges, flags, pair_model)
        fields = {a: docs[a]["fields"] for a in keys}
        for threshold in THRESHOLDS:
            for cap in CAPS:
                groups = groups_at(keys, edges, probability, threshold, cap)
                count, bm25 = score_groups(groups, fields)
                ranked = ranker.decision_function(rank_features({"count_scores": count,
                                                                   "bm25_scores": bm25})).tolist()
                tied = tie_aware_ranking(groups, ranked, truth, ranks[org])
                raw = score_org(groups, ranked, truth, ranks[org], keys,
                                {"top20_recovery_min_completeness": 0.8,
                                 "top20_recovery_min_purity": 0.8})
                rows[f"{threshold}:{cap}"].append({"recall20": tied["recall_at_20"],
                                                     "p10": tied["precision_at_10"],
                                                     "tp": raw["pair_tp"],
                                                     "fp": raw["pair_fp"],
                                                     "fn": raw["pair_fn"]})
        if index % 10 == 0:
            print(f"Calibrated {index}/42 development organizations", flush=True)
    table = {}
    for config, series in rows.items():
        tp, fp, fn = (sum(r[k] for r in series) for k in ("tp", "fp", "fn"))
        table[config] = {"recall20_macro": sum(r["recall20"] for r in series) / len(series),
                         "p10_macro": sum(r["p10"] for r in series) / len(series),
                         "pair_precision_micro": tp / (tp + fp) if tp + fp else 0,
                         "pair_f1_micro": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0}
    selected = max(table, key=lambda config: (table[config]["recall20_macro"],
                                              table[config]["pair_precision_micro"],
                                              -int(config.split(":")[1])))
    result = {"classification": "exploratory_development_only_component_cap_calibration",
              "validation_organizations": len(chosen), "table": table,
              "selected_config": selected,
              "selection_rule": "maximize_macro_recall20_then_pair_precision_then_smaller_cap",
              "validation_labels_read": True, "holdout_labels_read": False,
              "pair_model_sha256": sha256_file(MODEL),
              "analysis_code_sha256": sha256_file(Path(__file__))}
    write_json(OUT, result)
    print(json.dumps({"selected_config": selected,
                      "selected_metrics": table[selected]}, sort_keys=True))


if __name__ == "__main__":
    main()
