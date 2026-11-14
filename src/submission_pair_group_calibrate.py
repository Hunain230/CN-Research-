"""Choose a stricter pair-link threshold on development organizations only."""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_correlation_v2 import edges as candidate_edges
from .guide_rerun_v2 import key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import ROOT, DSU, score_groups, tie_aware_ranking, write_json
from .submission_pair_model_grouping import (FIELDS, PREPARED, RANKER, SPLIT,
                                             pair_features, verify_sources)
from .submission_trained_ranker import features as rank_features


PARENT_RUN = "submission_pair_model_grouping_20261114_v1"
OUT = ROOT / "outputs/submission_pair_group_calibration_20261114_v1.json"
CORRELATION_MODEL = ROOT / "data/derived/guide_rerun_v2/correlation_model.pkl"
THRESHOLDS = (0.5, 0.75, 0.9, 0.95, 0.98, 0.995)


def groups_at(keys: list[str], pairs: np.ndarray, probability: np.ndarray,
              threshold: float) -> list[list[str]]:
    n = len(keys)
    dsu = DSU(n)
    selected = np.flatnonzero(probability >= threshold)
    order = selected[np.lexsort((pairs[selected], -probability[selected]))]
    for i in order:
        a, b = divmod(int(pairs[i]), n)
        dsu.union(a, b)
    groups: dict[int, list[str]] = defaultdict(list)
    for i, alert in enumerate(keys):
        groups[dsu.root(i)].append(alert)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Calibration already frozen")
    source_hashes = verify_sources()
    pair_path = ROOT / "data/derived" / PARENT_RUN / "pair_model.pkl"
    fit_freeze = ROOT / "outputs" / PARENT_RUN / "fit_freeze.json"
    if sha256_file(pair_path) != json.loads(fit_freeze.read_text(encoding="utf-8"))["model_sha256"]:
        raise ValueError("Pair model changed")
    with pair_path.open("rb") as stream:
        pair_model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    with CORRELATION_MODEL.open("rb") as stream:
        _, vectorizer = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    counts = Counter(item["org"] for item in data["alerts"].values())
    orgs = sorted(o for o, n in counts.items() if split.get(o) == "validation" and 0 < n <= 500)
    if len(orgs) != 42:
        raise ValueError("Complete small development cohort changed")
    by_org: dict[str, dict] = defaultdict(dict)
    for alert, item in data["alerts"].items():
        if item["org"] in orgs:
            by_org[item["org"]][alert] = item
    truth = read_truth(set(orgs), set().union(*(set(v) for v in by_org.values())))
    ranks = labels(set(orgs))
    stats = {str(t): [] for t in THRESHOLDS}
    candidate_total = 0
    for index, org in enumerate(orgs, 1):
        docs = by_org[org]
        keys, found = candidate_edges(docs, vectorizer, [200])
        pairs = found[200]
        candidate_total += len(pairs)
        x = np.asarray([pair_features(docs[keys[int(a)]]['fields'],
                                      docs[keys[int(b)]]['fields'])
                        for a, b in zip(pairs // len(keys), pairs % len(keys))], dtype=np.float32)
        probability = pair_model.predict_proba(x)[:, 1] if len(x) else np.array([])
        score_docs = {a: docs[a]["fields"] for a in keys}
        for threshold in THRESHOLDS:
            groups = groups_at(keys, pairs, probability, threshold)
            count_scores, bm25_scores = score_groups(groups, score_docs)
            scores = ranker.decision_function(rank_features({"count_scores": count_scores,
                                                               "bm25_scores": bm25_scores})).tolist()
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            stats[str(threshold)].append({"recall20": tied["recall_at_20"],
                                          "p10": tied["precision_at_10"],
                                          "pair_tp": raw["pair_tp"], "pair_fp": raw["pair_fp"],
                                          "pair_fn": raw["pair_fn"]})
        if index % 10 == 0:
            print(f"Calibrated {index}/{len(orgs)} development organizations", flush=True)
    table = {}
    for threshold in THRESHOLDS:
        rows = stats[str(threshold)]
        tp = sum(row["pair_tp"] for row in rows)
        fp = sum(row["pair_fp"] for row in rows)
        fn = sum(row["pair_fn"] for row in rows)
        table[str(threshold)] = {
            "recall_at_20_macro": sum(r["recall20"] for r in rows) / len(rows),
            "precision_at_10_macro": sum(r["p10"] for r in rows) / len(rows),
            "pair_f1_micro": 2 * tp / (2 * tp + fp + fn),
            "pair_precision_micro": tp / (tp + fp) if tp + fp else 0.0,
            "pair_recall_micro": tp / (tp + fn) if tp + fn else 0.0,
        }
    chosen = max(THRESHOLDS, key=lambda t: (table[str(t)]["recall_at_20_macro"],
                                            table[str(t)]["pair_f1_micro"], t))
    write_json(OUT, {"classification": "exploratory_development_only_threshold_selection",
                     "training_model_run": PARENT_RUN, "validation_organizations": len(orgs),
                     "candidate_pairs": candidate_total, "table": table,
                     "selected_threshold": chosen,
                     "selection_rule": "maximize_macro_end_to_end_recall_at_20_then_pair_f1_then_higher_threshold",
                     "validation_labels_read": True, "holdout_labels_read": False,
                     "source_sha256": {**source_hashes,
                                       str(pair_path.relative_to(ROOT)): sha256_file(pair_path),
                                       str(CORRELATION_MODEL.relative_to(ROOT)): sha256_file(CORRELATION_MODEL),
                                       str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__))}})
    print(json.dumps({"selected_threshold": chosen, "table": table}, sort_keys=True))


if __name__ == "__main__":
    main()
