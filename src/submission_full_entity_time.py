"""Full-GUIDE entity/time sensitivity correlation with frozen offline baselines.

The entity and time fields are research-only assumptions, not approved model
inputs. Prediction never opens incident membership or queue ranking labels.
Evaluation opens them only after all 499 per-organization files are frozen.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import psutil

from .guide_rerun_v2 import FIELDS, key, labels
from .offline_joint_comparison import read_truth, score_org
from .phase2 import sha256_file
from .submission_full_guide import (ROOT, DSU, score_groups,
                                    tie_aware_ranking, write_json)
from .submission_pair_model_grouping import pair_features
from .submission_trained_ranker import features as rank_features
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels, present


PREFIX = "submission_full_entity_time_"
PARENT = ROOT / "data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl"
PARENT_FREEZE = ROOT / "outputs/submission_full_guide_paper_20261113_v1/prediction_freeze.json"
SHARD_MANIFEST = ROOT / "outputs/submission_entity_time_shards_20261114_v1.json"
PAIR_MODEL = ROOT / "data/derived/submission_pair_model_grouping_20261114_v1/pair_model.pkl"
PAIR_FREEZE = ROOT / "outputs/submission_pair_model_grouping_20261114_v1/fit_freeze.json"
RANKER = ROOT / "data/derived/submission_trained_ranker_20261114_v1/model.pkl"
RANKER_FREEZE = ROOT / "outputs/submission_trained_ranker_20261114_v1/prediction_freeze.json"
BASELINE_SCORES = ROOT / "data/derived/submission_full_ranker_transfer_20261114_v1/scores.pkl"
BASELINE_FREEZE = ROOT / "outputs/submission_full_ranker_transfer_20261114_v1/prediction_freeze.json"
CALIBRATION = ROOT / "outputs/submission_pair_group_calibration_20261114_v1.json"
SPLIT = ROOT / "data/derived/guide_rerun_v2/split.json"
FIELD_AUDIT = ROOT / "outputs/entity_time_field_audit_20261114_v3.json"
ENTITY_FIELDS = ("DeviceId", "AccountObjectId", "Sha256", "IpAddress",
                 "NetworkMessageId", "EmailClusterId")
MAX_TOKEN_FREQUENCY = 500
RARE_TOKEN_FREQUENCY = 10
MAX_NEAREST_PER_SIDE = 5
TIME_ENTITY_SECONDS = 48 * 3600
TIME_TECHNIQUE_SECONDS = 3600


def sources() -> dict:
    parent_freeze = json.loads(PARENT_FREEZE.read_text(encoding="utf-8"))
    pair_freeze = json.loads(PAIR_FREEZE.read_text(encoding="utf-8"))
    rank_freeze = json.loads(RANKER_FREEZE.read_text(encoding="utf-8"))
    base_freeze = json.loads(BASELINE_FREEZE.read_text(encoding="utf-8"))
    checks = ((PARENT, parent_freeze["prediction_sha256"]),
              (PAIR_MODEL, pair_freeze["model_sha256"]),
              (RANKER, rank_freeze["model_sha256"]),
              (BASELINE_SCORES, base_freeze["prediction_sha256"]))
    for path, expected in checks:
        if sha256_file(path) != expected:
            raise ValueError(f"Upstream source hash mismatch: {path.name}")
    shard_manifest = json.loads(SHARD_MANIFEST.read_text(encoding="utf-8"))
    if shard_manifest["organizations"] != 499:
        raise ValueError("Ranked projection changed")
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if float(calibration["selected_threshold"]) != 0.995:
        raise ValueError("Development-selected threshold changed")
    audit = json.loads(FIELD_AUDIT.read_text(encoding="utf-8"))
    if audit["composite_alert_keys"] != 637320:
        raise ValueError("Field audit changed")
    paths = (PARENT, PARENT_FREEZE, SHARD_MANIFEST, PAIR_MODEL, PAIR_FREEZE,
             RANKER, RANKER_FREEZE, BASELINE_SCORES, BASELINE_FREEZE,
             CALIBRATION, SPLIT, FIELD_AUDIT,
             ROOT / "submission/audit_entity_time_fields_v3.py")
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def read_docs(org: str, parquet_path: Path, sentinels: dict[str, str],
              allowed: set[str]) -> dict[str, dict]:
    docs: dict[str, dict] = {}
    con = duckdb.connect()
    con.execute("SET memory_limit='700MB'")
    cursor = con.execute("SELECT AlertId,Timestamp,DetectorId,Category,MitreTechniques,EntityType,EvidenceRole,DeviceId,AccountObjectId,Sha256,IpAddress,NetworkMessageId,EmailClusterId FROM read_parquet(?)", [str(parquet_path)])
    columns = [x[0] for x in cursor.description]
    while batch := cursor.fetchmany(10000):
        for values in batch:
            row = dict(zip(columns, values))
            alert_id = row["AlertId"]
            if not alert_id:
                continue
            alert = key(org, alert_id)
            if alert not in allowed:
                continue
            doc = docs.get(alert)
            if doc is None:
                stamp = datetime.fromisoformat(row["Timestamp"].replace("Z", "+00:00")).timestamp()
                doc = {"fields": {field: set() for field in FIELDS},
                       "entities": set(), "stamp": stamp}
                docs[alert] = doc
            for field in FIELDS:
                value = row[field]
                if not value:
                    continue
                if field == "MitreTechniques":
                    from .submission_full_guide import feature_values
                    doc["fields"][field].update(feature_values({field: value}, field))
                else:
                    doc["fields"][field].add(value.strip().lower())
            for field in ENTITY_FIELDS:
                value = row[field]
                if value and present(value, field, sentinels):
                    doc["entities"].add((field, value.strip().lower()))
    con.close()
    return docs


def _neighbor_edges(posting: list[int], stamps: list[float], seconds: int,
                    n: int, proposals: dict[int, int], flag: int) -> None:
    if len(posting) < 2 or len(posting) > MAX_TOKEN_FREQUENCY:
        return
    ordered = sorted(posting, key=lambda i: (stamps[i], i))
    for pos, a in enumerate(ordered):
        for b in ordered[pos + 1: pos + 1 + MAX_NEAREST_PER_SIDE]:
            if stamps[b] - stamps[a] > seconds:
                break
            lo, hi = (a, b) if a < b else (b, a)
            encoded = lo * n + hi
            proposals[encoded] = proposals.get(encoded, 0) | flag


def generate(keys: list[str], docs: dict[str, dict], baseline: list[tuple[str, str]]) -> tuple[np.ndarray, np.ndarray, dict]:
    n = len(keys)
    index = {alert: i for i, alert in enumerate(keys)}
    stamps = [docs[alert]["stamp"] for alert in keys]
    proposals: dict[int, int] = {}
    for a, b in baseline:
        i, j = index[a], index[b]
        lo, hi = (i, j) if i < j else (j, i)
        proposals[lo * n + hi] = 1
    entity: dict[tuple[str, str], list[int]] = defaultdict(list)
    technique: dict[str, list[int]] = defaultdict(list)
    for i, alert in enumerate(keys):
        for token in docs[alert]["entities"]:
            entity[token].append(i)
        for token in docs[alert]["fields"]["MitreTechniques"]:
            technique[token].append(i)
    for posting in entity.values():
        flag = 4 if len(posting) <= RARE_TOKEN_FREQUENCY else 2
        _neighbor_edges(posting, stamps, TIME_ENTITY_SECONDS, n, proposals, flag)
    for posting in technique.values():
        _neighbor_edges(posting, stamps, TIME_TECHNIQUE_SECONDS, n, proposals, 8)
    edge = np.fromiter(sorted(proposals), dtype=np.int64)
    flags = np.fromiter((proposals[int(e)] for e in edge), dtype=np.uint8)
    counts = Counter()
    for f in flags:
        counts["entity"] += bool(f & 6)
        counts["technique"] += bool(f & 8)
        counts["baseline"] += bool(f & 1)
    return edge, flags, dict(counts)


def grouped(keys: list[str], docs: dict[str, dict], edges: np.ndarray,
            flags: np.ndarray, pair_model) -> tuple[list[list[str]], dict]:
    n = len(keys)
    dsu = DSU(n)
    high = []
    strong_entity = []
    accepted = Counter()
    for start in range(0, len(edges), 10000):
        part = edges[start:start + 10000]
        x = np.asarray([pair_features(docs[keys[int(e // n)]]["fields"],
                                      docs[keys[int(e % n)]]["fields"])
                        for e in part], dtype=np.float32)
        probability = pair_model.predict_proba(x)[:, 1] if len(x) else np.array([])
        for offset, p in enumerate(probability):
            at = start + offset
            if p >= 0.995:
                high.append((float(p), int(edges[at])))
            elif flags[at] & 4:
                a, b = divmod(int(edges[at]), n)
                fa, fb = docs[keys[a]]["fields"], docs[keys[b]]["fields"]
                if (abs(docs[keys[a]]["stamp"] - docs[keys[b]]["stamp"]) <= TIME_TECHNIQUE_SECONDS and
                    (fa["Category"] & fb["Category"] or
                     fa["MitreTechniques"] & fb["MitreTechniques"])):
                    strong_entity.append(int(edges[at]))
    # Rare-entity links are attempted first; high-probability descriptor links follow.
    for e in sorted(strong_entity):
        a, b = divmod(e, n)
        accepted["rare_entity"] += dsu.union(a, b)
    for _, e in sorted(high, key=lambda row: (-row[0], row[1])):
        a, b = divmod(e, n)
        accepted["pair_model"] += dsu.union(a, b)
    groups: dict[int, list[str]] = defaultdict(list)
    for i, alert in enumerate(keys):
        groups[dsu.root(i)].append(alert)
    return sorted((sorted(group) for group in groups.values()), key=lambda g: g[0]), dict(accepted)


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Choose a new versioned run ID")
    source_hashes = sources()
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with PAIR_MODEL.open("rb") as stream:
        pair_model = pickle.load(stream)
    with RANKER.open("rb") as stream:
        ranker = pickle.load(stream)
    shard_manifest = json.loads(SHARD_MANIFEST.read_text(encoding="utf-8"))
    by_org = {path.parent.name.split("=", 1)[1]: path for path in
              (ROOT / "data/derived/submission_entity_time_shards_20261114_v1/parts").rglob("*.parquet")}
    if len(parent) != 499 or set(parent) != set(by_org):
        raise ValueError("Full ranked organization cohort changed")
    sentinels, _ = detect_modal_sentinels()
    private.mkdir(parents=True)
    result_hashes, seconds, peak_rss = {}, [], 0
    census = Counter()
    process = psutil.Process()
    started = time.perf_counter()
    for index, org in enumerate(sorted(parent), 1):
        path = by_org[org]
        if sha256_file(path) != shard_manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Private projection changed")
        item = parent[org]
        tic = time.perf_counter()
        keys = item["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        if set(docs) != set(keys):
            raise ValueError("Alert universe differs from frozen full-run parent")
        edges, flags, route_counts = generate(keys, docs, item["candidate_edges"])
        groups, accepted = grouped(keys, docs, edges, flags, pair_model)
        field_docs = {alert: docs[alert]["fields"] for alert in keys}
        counts, bm25 = score_groups(groups, field_docs)
        rank_scores = ranker.decision_function(rank_features({
            "count_scores": counts, "bm25_scores": bm25})).tolist()
        output_path = private / f"{key(org)}.pkl"
        with output_path.open("wb") as stream:
            pickle.dump({"input_alert_keys": keys, "candidate_edges": edges,
                         "groups": groups, "scores": rank_scores,
                         "route_counts": route_counts, "accepted": accepted},
                        stream, protocol=pickle.HIGHEST_PROTOCOL)
        result_hashes[key(org)] = sha256_file(output_path)
        census.update({"alerts": len(keys), "candidate_pairs": len(edges),
                       "predicted_groups": len(groups),
                       **{f"route_{k}": v for k, v in route_counts.items()},
                       **{f"accepted_{k}": v for k, v in accepted.items()}})
        seconds.append(time.perf_counter() - tic)
        peak_rss = max(peak_rss, process.memory_info().rss)
        del docs, field_docs, edges, flags, groups
        if index % 25 == 0:
            print(f"Predicted {index}/499 organizations", flush=True)
    public.mkdir(parents=True)
    write_json(public / "prediction_freeze.json", {
        "classification": "exploratory_full_guide_entity_time_sensitivity_not_approved_operational_input",
        "run": run_id, "organizations": 499, "census": dict(census),
        "prediction_sha256": result_hashes, "source_sha256": source_hashes,
        "source_code_sha256": sha256_file(Path(__file__)),
        "no_evaluation_labels_read": True,
        "resource": {"wall_seconds": time.perf_counter() - started,
                     "organization_seconds_p50": float(np.quantile(seconds, 0.5)),
                     "organization_seconds_p95": float(np.quantile(seconds, 0.95)),
                     "peak_process_rss_bytes": peak_rss},
        "candidate_rule": "frozen descriptor edges plus rare shared entity within 48h or shared technique within 1h, nearest five per token, max token frequency 500",
        "link_rule": "development-selected pair model probability >=0.995 or rare-entity plus descriptor agreement within 1h; size cap 100",
        "field_policy": "local_sensitivity_only_official_allowlist_remains_empty",
    })
    print(json.dumps({"status": "predictions_frozen", "run": run_id,
                      "alerts": census["alerts"], "candidate_pairs": census["candidate_pairs"]}))


def bootstrap(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    rng = np.random.default_rng(29)
    draws = a[rng.integers(0, len(a), size=(10000, len(a)))].mean(axis=1)
    return {"mean": float(a.mean()), "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
            "organizations": len(a), "resamples": 10000}


def evaluate(run_id: str) -> None:
    public, private = ROOT / "outputs" / run_id, ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["source_sha256"] != sources() or freeze["source_code_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Frozen method lineage changed")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    with BASELINE_SCORES.open("rb") as stream:
        baseline_ranker = pickle.load(stream)
    orgs = set(parent)
    alert_keys = {a for item in parent.values() for a in item["input_alert_keys"]}
    truth = read_truth(orgs, alert_keys)
    ranks = labels(orgs)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    rows = defaultdict(list)
    pair_confusion = defaultdict(Counter)
    candidate = Counter()
    ceiling = Counter()
    resource = Counter()
    for org in sorted(orgs):
        path = private / f"{key(org)}.pkl"
        if sha256_file(path) != freeze["prediction_sha256"][key(org)]:
            raise ValueError("Frozen organization prediction changed")
        with path.open("rb") as stream:
            predicted = pickle.load(stream)
        base = parent[org]
        keys = predicted["input_alert_keys"]
        n = len(keys)
        counts = Counter(truth[a] for a in keys)
        candidate["positive_pairs"] += sum(v * (v - 1) // 2 for v in counts.values())
        candidate["possible_pairs"] += n * (n - 1) // 2
        candidate["candidate_pairs"] += len(predicted["candidate_edges"])
        candidate["positive_candidate_pairs"] += sum(
            truth[keys[int(e // n)]] == truth[keys[int(e % n)]]
            for e in predicted["candidate_edges"])
        methods = (("entity_time_grouping", predicted["groups"], predicted["scores"]),
                   ("full_rule_bm25", base["groups"], base["bm25_scores"]),
                   ("full_rule_transferred_ranker", base["groups"], baseline_ranker[org]))
        for name, groups, scores in methods:
            raw = score_org(groups, scores, truth, ranks[org], keys,
                            {"top20_recovery_min_completeness": 0.8,
                             "top20_recovery_min_purity": 0.8})
            tied = tie_aware_ranking(groups, scores, truth, ranks[org])
            rows[name].append({"org": org, "recall20": tied["recall_at_20"],
                               "p10": tied["precision_at_10"],
                               "ndcg20": tied["ndcg_at_20_rank1_highest"]})
            pair_confusion[name].update({"tp": raw["pair_tp"], "fp": raw["pair_fp"],
                                         "fn": raw["pair_fn"]})
            found = set()
            for group in groups:
                overlaps = Counter(truth[a] for a in group)
                gold, overlap = max(overlaps.items(), key=lambda item: (item[1], item[0]))
                if gold in ranks[org] and overlap / counts[gold] >= 0.8 and overlap / len(group) >= 0.8:
                    found.add(gold)
            ceiling[name] += len(found)
        resource.update(predicted["route_counts"])
    cohorts = {"all_499_descriptive": sorted(orgs),
               "training_disjoint_135": sorted(o for o in orgs if split.get(o) in ("validation", "holdout"))}
    lookup = {name: {row["org"]: row for row in series} for name, series in rows.items()}
    results = {}
    for cohort, selected in cohorts.items():
        methods = {}
        for name in rows:
            series = [lookup[name][o] for o in selected]
            methods[name] = {metric: bootstrap([row[metric] for row in series])
                             for metric in ("recall20", "p10", "ndcg20")}
        paired = {base: {metric: bootstrap([lookup["entity_time_grouping"][o][metric]
                                             - lookup[base][o][metric] for o in selected])
                         for metric in ("recall20", "p10", "ndcg20")}
                  for base in ("full_rule_bm25", "full_rule_transferred_ranker")}
        results[cohort] = {"organizations": len(selected),
                           "expert_top20_denominator": 20 * len(selected),
                           "methods": methods, "paired_new_minus": paired}
    confusion = {}
    for name, c in pair_confusion.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        confusion[name] = {"tp": tp, "fp": fp, "fn": fn,
                           "precision": tp / (tp + fp) if tp + fp else 0,
                           "recall": tp / (tp + fn) if tp + fn else 0,
                           "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                           "recoverable_top20_labels_oracle_order": ceiling[name],
                           "oracle_order_recall20_ceiling": ceiling[name] / (20 * len(orgs))}
    metrics = {"classification": "exploratory_full_guide_entity_time_sensitivity_previously_exposed_not_confirmatory",
               "run": run_id, "organizations": len(orgs), "alerts": len(alert_keys),
               "cohorts": results, "pair_and_group": confusion,
               "candidate": {**dict(candidate),
                             "candidate_recall_micro": candidate["positive_candidate_pairs"] / candidate["positive_pairs"],
                             "candidate_coverage_micro": candidate["candidate_pairs"] / candidate["possible_pairs"]},
               "prediction_resource": freeze["resource"],
               "limits": ["Previously exposed GUIDE_Test labels",
                          "499-queue aggregate includes 334 ranker and pair-model training organizations",
                          "Entity/time fields are local research sensitivity assumptions, not approved operational model inputs",
                          "Publisher adds time noise; evidence-field availability at alert creation is unverified",
                          "No Qwen calls, live SOC, or untouched test cohort"],
               "prediction_freeze_sha256": sha256_file(freeze_path)}
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {
        "classification": metrics["classification"],
        "command_predict": f"python -m src.submission_full_entity_time predict --run-id {run_id}",
        "command_evaluate": f"python -m src.submission_full_entity_time evaluate --run-id {run_id}",
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   (Path(__file__), freeze_path, public / "metrics.json")},
        "private_prediction_hashes": freeze["prediction_sha256"],
    })
    print(json.dumps({"status": "exploratory_evaluation_complete", "run": run_id,
                      "recall20_all_499": results["all_499_descriptive"]["methods"]["entity_time_grouping"]["recall20"]["mean"]}))


def self_test() -> None:
    docs = {
        "a": {"fields": {f: ({"t0001"} if f == "MitreTechniques" else set()) for f in FIELDS},
              "entities": {("DeviceId", "device-x")}, "stamp": 0},
        "b": {"fields": {f: ({"t0002"} if f == "MitreTechniques" else set()) for f in FIELDS},
              "entities": {("DeviceId", "device-x")}, "stamp": 30},
        "c": {"fields": {f: ({"t0001"} if f == "MitreTechniques" else set()) for f in FIELDS},
              "entities": set(), "stamp": 7200},
    }
    edges, flags, counts = generate(["a", "b", "c"], docs, [("a", "c")])
    assert edges.tolist() == [1, 2]
    assert flags.tolist() == [4, 1]
    assert counts["entity"] == 1 and counts["baseline"] == 1
    print("full entity/time sensitivity self-test: 3 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_full_entity_time_20261114_v1")
    args = parser.parse_args()
    if args.stage == "self-test":
        self_test()
    else:
        {"predict": predict, "evaluate": evaluate}[args.stage](args.run_id)


if __name__ == "__main__":
    main()
