"""Exploratory full-GUIDE rule/count and rule/BM25-like offline comparison.

Prediction scans all GUIDE_Test evidence rows and evaluates all 499 locally ranked
organizations. It never reads incident membership or queue rank until the separate
evaluation command. This is an amended offline baseline, not LLM C/P/V.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .guide_rerun_v2 import FIELDS, INPUT_HASHES, key, labels
from .offline_joint_comparison import read_truth, score_org
from .empirical_priority_tie_eval import _expected_metrics
from .phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
FIELD_POLICY = ROOT / "configs/empirical_field_policy.yaml"
ALERTS = ROOT / "data/raw/GUIDE_Test.csv"
RANKS = ROOT / "data/raw/GUIDE_Test_Queue_Rankings.csv"
AMBIGUOUS = ROOT / "data/derived/preprocessing/review/ambiguous_alert_memberships.csv"
SPLIT_A = ROOT / "data/derived/preprocessing/split_manifest.json"
SPLIT_B = ROOT / "data/derived/guide_rerun_v2/split.json"
TECHNIQUE = re.compile(r"t\d{4}(?:\.\d{3})?")
RUN_PREFIX = "submission_full_guide_"
MAX_NEIGHBORS = 20
MAX_COMPONENT = 100


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_sources() -> set[str]:
    for name, expected in INPUT_HASHES.items():
        if sha256_file(ROOT / "data/raw" / name) != expected:
            raise ValueError(f"Raw hash mismatch: {name}")
    policy = FIELD_POLICY.read_text(encoding="utf-8")
    if "status: adopted_assumption_for_offline_experiments" not in policy or "no_external_transmission: true" not in policy:
        raise ValueError("Local-only descriptor policy changed")
    old = set(json.loads(SPLIT_A.read_text(encoding="utf-8"))["assignments"])
    later = set(json.loads(SPLIT_B.read_text(encoding="utf-8")))
    orgs = old | later
    if len(orgs) != 499 or len(old) != 50 or len(later) != 469:
        raise ValueError("Ranked cohort is not the expected 499-organization union")
    return orgs


def feature_values(row: dict, field: str) -> set[str]:
    value = row[field].strip().lower()
    if not value:
        return set()
    return set(TECHNIQUE.findall(value)) if field == "MitreTechniques" else {value}


def load_alerts(orgs: set[str]) -> tuple[dict[str, dict[str, dict]], dict]:
    ambiguous: set[tuple[str, str]] = set()
    with AMBIGUOUS.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            ambiguous.add((row["OrgId"], row["AlertId"]))
    if len(ambiguous) != 70702:
        raise ValueError("Ambiguous-key baseline changed")
    by_org: dict[str, dict[str, dict]] = defaultdict(dict)
    rows = 0
    excluded = 0
    with ALERTS.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rows += 1
            org = row["OrgId"]
            alert = row["AlertId"]
            if org not in orgs or not alert:
                continue
            if (org, alert) in ambiguous:
                excluded += 1
                continue
            alert_key = key(org, alert)
            doc = by_org[org].setdefault(alert_key, {field: set() for field in FIELDS})
            for field in FIELDS:
                doc[field].update(feature_values(row, field))
            if rows % 1_000_000 == 0:
                print(f"Scanned {rows:,} raw evidence rows", flush=True)
    if rows != 4_147_992 or set(by_org) != orgs:
        raise ValueError("Raw row or ranked-organization count changed")
    for docs in by_org.values():
        for fields in docs.values():
            for field in FIELDS:
                fields[field] = sorted(fields[field])
    return by_org, {"raw_rows_scanned": rows, "ambiguous_keys_all_orgs": len(ambiguous), "excluded_evidence_rows_ranked_orgs": excluded, "ranked_organizations": len(orgs), "unambiguous_alerts": sum(map(len, by_org.values()))}


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.size = [1] * n

    def root(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> bool:
        x, y = self.root(a), self.root(b)
        if x == y or self.size[x] + self.size[y] > MAX_COMPONENT:
            return False
        if self.size[x] < self.size[y]:
            x, y = y, x
        self.parent[y] = x
        self.size[x] += self.size[y]
        return True


def group_org(docs: dict[str, dict]) -> tuple[list[list[str]], list[tuple[str, str]]]:
    keys = sorted(docs)
    index = {k: i for i, k in enumerate(keys)}
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for alert, fields in docs.items():
        for category in fields["Category"]:
            for technique in fields["MitreTechniques"]:
                buckets[(category, technique)].append(alert)
    proposals: set[tuple[str, str]] = set()
    for members in buckets.values():
        ordered = sorted(set(members))
        for i, left in enumerate(ordered):
            for right in ordered[i + 1 : i + 3]:
                proposals.add((left, right))
    degrees = Counter()
    edges = []
    for left, right in sorted(proposals):
        if degrees[left] >= MAX_NEIGHBORS or degrees[right] >= MAX_NEIGHBORS:
            continue
        degrees[left] += 1
        degrees[right] += 1
        edges.append((left, right))
    dsu = DSU(len(keys))
    for left, right in edges:
        dsu.union(index[left], index[right])
    groups: dict[int, list[str]] = defaultdict(list)
    for alert in keys:
        groups[dsu.root(index[alert])].append(alert)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0]), edges


def score_groups(groups: list[list[str]], docs: dict[str, dict]) -> tuple[list[float], list[float]]:
    # B1 is a label-free local BM25-like rarity scorer over the target queue.
    # It is an explicit new offline amendment, not the historical B1 implementation.
    tokens = []
    for group in groups:
        counts = Counter(field + "=" + value for alert in group for field in FIELDS for value in docs[alert][field])
        tokens.append(counts)
    df = Counter(token for bag in tokens for token in bag)
    n = len(groups)
    mean_len = sum(sum(bag.values()) for bag in tokens) / max(n, 1)
    count_scores = [float(len(group)) for group in groups]
    bm25 = []
    for bag in tokens:
        length = sum(bag.values())
        score = 0.0
        for token, tf in bag.items():
            idf = math.log(1 + (n - df[token] + 0.5) / (df[token] + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / max(mean_len, 1)))
        bm25.append(score)
    return count_scores, bm25


def predict(run_id: str) -> None:
    if not run_id.startswith(RUN_PREFIX):
        raise ValueError(f"Run ID must start with {RUN_PREFIX}")
    out = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if out.exists() or private.exists():
        raise FileExistsError("Run path exists; choose a new versioned ID")
    orgs = validate_sources()
    by_org, census = load_alerts(orgs)
    predictions = {}
    for i, org in enumerate(sorted(orgs), 1):
        docs = by_org[org]
        groups, edges = group_org(docs)
        count_scores, bm25_scores = score_groups(groups, docs)
        predictions[org] = {"input_alert_keys": sorted(docs), "candidate_edges": edges, "groups": groups, "count_scores": count_scores, "bm25_scores": bm25_scores}
        if i % 50 == 0:
            print(f"Predicted {i}/499 ranked organizations", flush=True)
        del by_org[org]
    private.mkdir(parents=True)
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    out.mkdir(parents=True)
    write_json(out / "prediction_freeze.json", {
        "classification": "exploratory_full_ranked_guide_offline_baselines",
        "prediction_sha256": sha256_file(prediction_path),
        "labels_read_in_prediction_stage": False,
        "organizations": 499,
        "source_raw_sha256": INPUT_HASHES,
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), FIELD_POLICY, AMBIGUOUS, SPLIT_A, SPLIT_B)},
        "census": census,
        "candidate_rule": "same Category and parsed MitreTechniques; sorted-hash nearest two in each exact bucket; max 20 neighbors per alert",
        "component_cap": MAX_COMPONENT,
        "methods": ["full_rule_count", "full_rule_local_bm25"],
        "seed": 0,
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id, **census}, sort_keys=True))


def bootstrap(values: list[float]) -> dict:
    import numpy as np

    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(0)
    draws = array[rng.integers(0, len(array), (10_000, len(array)))].mean(axis=1)
    return {"mean": float(array.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(), "organizations": len(array), "resamples": 10_000}


def tie_aware_ranking(groups: list[list[str]], scores: list[float], truth: dict[str, str], ranks: dict[str, int]) -> dict:
    counts = Counter(truth[a] for group in groups for a in group)
    group_labels = {}
    for group in groups:
        memberships = Counter(truth[a] for a in group)
        if memberships:
            gold, overlap = max(memberships.items(), key=lambda item: (item[1], item[0]))
            if gold in ranks and overlap / counts[gold] >= 0.8 and overlap / len(group) >= 0.8:
                group_labels[group[0]] = ranks[gold]
    ordered = sorted(zip(groups, scores), key=lambda item: (-item[1], item[0][0]))
    tied = []
    for group, score in ordered:
        if not tied or tied[-1][0][1] != score:
            tied.append([])
        tied[-1].append((group[0], score))
    return _expected_metrics(tied, group_labels | {f"unrecovered-{gold}": rank for gold, rank in ranks.items() if rank not in group_labels.values()})


def evaluate(run_id: str) -> None:
    out = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if (out / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists; do not overwrite")
    freeze = json.loads((out / "prediction_freeze.json").read_text(encoding="utf-8"))
    prediction_path = private / "predictions.pkl"
    if sha256_file(prediction_path) != freeze["prediction_sha256"]:
        raise ValueError("Frozen prediction hash mismatch")
    with prediction_path.open("rb") as stream:
        predictions = pickle.load(stream)
    orgs = set(predictions)
    if len(orgs) != 499:
        raise ValueError("Prediction cohort changed")
    all_alerts = {a for item in predictions.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    scored: dict[str, list[dict]] = defaultdict(list)
    candidate_positive = 0
    positive_pairs = 0
    candidate_pairs = 0
    possible_pairs = 0
    for org, item in sorted(predictions.items()):
        keys = item["input_alert_keys"]
        candidate_pairs += len(item["candidate_edges"])
        possible_pairs += len(keys) * (len(keys) - 1) // 2
        counts = Counter(truth[a] for a in keys)
        positive_pairs += sum(n * (n - 1) // 2 for n in counts.values())
        candidate_positive += sum(truth[a] == truth[b] for a, b in item["candidate_edges"])
        for method, scores in (("full_rule_count", item["count_scores"]), ("full_rule_local_bm25", item["bm25_scores"])):
            row = score_org(item["groups"], scores, truth, ranks[org], keys, {"top20_recovery_min_completeness": 0.8, "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(item["groups"], scores, truth, ranks[org])
            row["precision_at_10"] = tied["precision_at_10"]
            row["end_to_end_recall_at_20"] = tied["recall_at_20"]
            row["ndcg_at_20_rank1_highest"] = tied["ndcg_at_20_rank1_highest"]
            row["ndcg_at_20_rank20_highest"] = tied["ndcg_at_20_rank20_highest_sensitivity"]
            row["top20_slots_in_tied_blocks"] = tied["top20_slots_in_tied_blocks"]
            scored[method].append(row)
    result = {}
    for method, rows in scored.items():
        tp = sum(row["pair_tp"] for row in rows)
        fp = sum(row["pair_fp"] for row in rows)
        fn = sum(row["pair_fn"] for row in rows)
        result[method] = {
            "micro_pair": {"tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0},
            "pair_f1_macro": bootstrap([row["pair_f1"] for row in rows]),
            "precision_at_10_macro": bootstrap([row["precision_at_10"] for row in rows]),
            "end_to_end_recall_at_20_macro": bootstrap([row["end_to_end_recall_at_20"] for row in rows]),
            "ndcg_at_20_rank1_high_macro": bootstrap([row["ndcg_at_20_rank1_highest"] for row in rows]),
            "ndcg_at_20_rank20_high_macro": bootstrap([row["ndcg_at_20_rank20_highest"] for row in rows]),
            "gold_top20_with_alerts_total": sum(row["gold_top20_with_alerts_in_scope"] for row in rows),
            "top20_slots_in_tied_blocks": sum(row["top20_slots_in_tied_blocks"] for row in rows),
        }
    metrics = {
        "classification": "exploratory_full_ranked_guide_offline_baselines_not_llm",
        "organizations": 499,
        "alerts": len(all_alerts),
        "candidate_pairs": candidate_pairs,
        "possible_pairs": possible_pairs,
        "positive_pairs": positive_pairs,
        "candidate_positive_pairs": candidate_positive,
        "candidate_recall_micro": candidate_positive / positive_pairs if positive_pairs else None,
        "candidate_coverage_micro": candidate_pairs / possible_pairs if possible_pairs else None,
        "expert_top20_denominator": 9980,
        "tie_policy": "uniform expected ranking within equal-score blocks",
        "methods": result,
        "prediction_freeze_sha256": sha256_file(out / "prediction_freeze.json"),
        "limits": ["previously exposed cohort and labels", "ambiguous alert keys excluded but all 9980 expert labels retained", "local query universe and numeric rank direction unverified", "five descriptor fields are local-only assumptions", "rule/count and label-free local BM25-like baselines, not empirical LLM C/P/V", "no time or raw entity links because timing/privacy approval is absent"],
    }
    write_json(out / "metrics.json", metrics)
    write_json(out / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_full_guide predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_full_guide evaluate --run-id {run_id}",
        "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), FIELD_POLICY, prediction_path, out / "prediction_freeze.json", out / "metrics.json")},
        "raw_sha256": INPUT_HASHES,
        "seed": 0,
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id, "organizations": 499, "alerts": len(all_alerts), "candidate_recall_micro": metrics["candidate_recall_micro"]}, sort_keys=True))


def self_test() -> None:
    docs = {
        "a": {"Category": ["x"], "MitreTechniques": ["t0001"], "DetectorId": ["d"], "EntityType": [], "EvidenceRole": []},
        "b": {"Category": ["x"], "MitreTechniques": ["t0001"], "DetectorId": [], "EntityType": [], "EvidenceRole": []},
        "c": {"Category": ["y"], "MitreTechniques": ["t0002"], "DetectorId": [], "EntityType": [], "EvidenceRole": []},
    }
    groups, edges = group_org(docs)
    assert groups == [["a", "b"], ["c"]] and edges == [("a", "b")]
    count, bm25 = score_groups(groups, docs)
    assert count == [2.0, 1.0] and len(bm25) == 2 and all(math.isfinite(x) for x in bm25)
    assert feature_values({"MitreTechniques": "T1234.001; T5678"}, "MitreTechniques") == {"t1234.001", "t5678"}
    print("full GUIDE offline self-test: 4 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_full_guide_20261112_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": predict, "evaluate": evaluate}[args.stage](**({} if args.stage == "self-test" else {"run_id": args.run_id}))


if __name__ == "__main__":
    main()
