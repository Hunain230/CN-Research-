"""Offline priority-retrieval ceiling experiment with evaluator-separated labels.

Candidate groups are formed using GUIDE IncidentId in the feature builder. This is
deliberately an oracle-group ceiling, not an end-to-end correlation system. The
model scorer receives only the configured descriptor tokens and opaque keys.
Test QueueRank values are not read by `predict`; they are opened only by `evaluate`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import platform
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from .baselines.bm25 import tokenize
from .phase2 import sha256_file

INPUT_HASHES = {
    "GUIDE_Test.csv": "fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3",
    "GUIDE_Test_Queue_Rankings.csv": "e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6",
}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_key(org: str, incident: str) -> str:
    return _hash("empirical-candidate-v1\0" + org + "\0" + incident)


def _org_key(org: str) -> str:
    return _hash("empirical-org-v1\0" + org)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_protocol(root: Path):
    config_path = root / "configs/empirical_priority.json"
    config = _load_json(config_path)
    if config.get("schema_version") != "empirical-priority-v1":
        raise ValueError("empirical priority config version mismatch")
    if config.get("classification") != "assumption_based_local_empirical_oracle_group_ceiling":
        raise ValueError("experiment classification must remain explicit")
    policy_path = root / "configs/empirical_field_policy.yaml"
    policy_text = policy_path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^approved_model_fields:\s*\n((?:\s+-\s+[^\n]+\n)+)", policy_text)
    policy_fields = [line.strip()[2:].strip() for line in match.group(1).splitlines()] if match else []
    if policy_fields != config.get("fields"):
        raise ValueError("empirical priority fields differ from the adopted field policy")
    return config_path, config, policy_path


def _check_inputs(root: Path, config: dict):
    hashes = {}
    for name in INPUT_HASHES:
        path = root / config["alerts"] if name == "GUIDE_Test.csv" else root / config["rankings"]
        actual = sha256_file(path)
        hashes[name] = actual
        if actual != INPUT_HASHES[name]:
            raise RuntimeError(f"raw source hash changed: {name}")
    return hashes


def _load_split(root: Path, config: dict):
    manifest_path = root / config["split_manifest"]
    split = _load_json(manifest_path)
    assignment = split["assignments"]
    digest = hashlib.sha256(json.dumps(assignment, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != "c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024":
        raise RuntimeError("frozen organization split digest mismatch")
    counts = {k: sum(v == k for v in assignment.values()) for k in ("pilot", "development", "test")}
    if counts != {"pilot": 10, "development": 10, "test": 30}:
        raise RuntimeError("frozen organization split counts mismatch")
    return assignment, digest, counts, manifest_path


def _ambiguous_keys(path: Path):
    ambiguous = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ambiguous.add((row["OrgId"], row["AlertId"]))
    return ambiguous


def _collect_documents(root: Path, config: dict, assignment: dict):
    """Stream raw evidence; retain only selected orgs and the five approved descriptors."""
    ambiguous = _ambiguous_keys(root / config["ambiguous_membership_artifact"])
    fields = config["fields"]
    selected = set(assignment)
    documents: dict[str, dict] = {}
    incident_org = {}
    excluded_rows = 0
    missing_key_rows = 0
    feature_values = 0
    expected_header = None
    with (root / config["alerts"]).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        expected_header = set(reader.fieldnames or [])
        required = {"OrgId", "IncidentId", "AlertId", *fields}
        if not required <= expected_header:
            raise ValueError(f"GUIDE header missing required fields: {sorted(required - expected_header)}")
        for row in reader:
            org = (row.get("OrgId") or "").strip()
            if org not in selected:
                continue
            incident = (row.get("IncidentId") or "").strip()
            if not incident:
                missing_key_rows += 1
                continue
            key = _candidate_key(org, incident)
            incident_org[key] = org
            doc = documents.setdefault(key, {"org_key": _org_key(org), "tokens_by_field": {name: set() for name in fields}})
            alert = (row.get("AlertId") or "").strip()
            if (org, alert) in ambiguous:
                excluded_rows += 1
                continue
            for field in fields:
                value = (row.get(field) or "").strip()
                if not value:
                    continue
                words = tokenize(value)
                if words:
                    before = len(doc["tokens_by_field"][field])
                    doc["tokens_by_field"][field].update(words)
                    feature_values += len(doc["tokens_by_field"][field]) - before
    for doc in documents.values():
        for field in fields:
            doc["tokens_by_field"][field] = sorted(doc["tokens_by_field"][field])
    return documents, incident_org, {
        "ambiguous_alert_keys_excluded": len(ambiguous),
        "evidence_rows_excluded_for_ambiguity": excluded_rows,
        "rows_missing_composite_incident_key": missing_key_rows,
        "candidate_incidents": len(documents),
        "distinct_descriptor_tokens": feature_values,
    }


def _doc_tokens(doc: dict, fields: list[str], mask_rate=0.0, seed=0, candidate_key=""):
    words = []
    for field in fields:
        for token in doc["tokens_by_field"].get(field, []):
            if mask_rate:
                digest = hashlib.sha256(f"{seed}\0{candidate_key}\0{field}\0{token}".encode()).digest()
                if int.from_bytes(digest[:8], "big") / 2**64 < mask_rate:
                    continue
            words.append(token)
    return words


def _fit_bm25(exemplars: list[list[str]], k1: float, b: float):
    n = len(exemplars)
    df = Counter()
    total = 0
    postings = defaultdict(list)
    for i, tokens in enumerate(exemplars):
        tf = Counter(tokens)
        total += len(tokens)
        for term, freq in tf.items():
            df[term] += 1
            postings[term].append((i, freq, len(tokens)))
    idf = {term: math.log(1.0 + (n - count + 0.5) / (count + 0.5)) for term, count in df.items()}
    return {"n": n, "avgdl": total / n if n else 0.0, "idf": idf, "postings": postings, "k1": k1, "b": b}


def _score_query(index: dict, query: list[str]):
    if not query or not index["n"]:
        return 0.0
    scores = defaultdict(float)
    qtf = Counter(query)
    for term, qcount in qtf.items():
        idf = index["idf"].get(term, 0.0)
        if not idf:
            continue
        for i, tf, dl in index["postings"].get(term, []):
            norm = tf + index["k1"] * (1.0 - index["b"] + index["b"] * dl / (index["avgdl"] or 1.0))
            scores[i] += idf * (tf * (index["k1"] + 1.0) / norm) * min(qcount, 3)
    return max(scores.values(), default=0.0)


def _ranking_conditions(fields: list[str], robustness: dict):
    result = [("primary", fields, 0.0, 0)]
    for omitted in fields:
        remain = [x for x in fields if x != omitted]
        result.append((f"leave_out_{omitted}", remain, 0.0, 0))
    for rate in robustness["mask_rates"]:
        pct = int(round(rate * 100))
        for seed in robustness["seeds"]:
            result.append((f"mask_{pct}_seed_{seed}", fields, rate, seed))
    return result


def _predict(root: Path, config: dict, assignment: dict, private_dir: Path):
    documents, incident_org, coverage = _collect_documents(root, config, assignment)
    fit_orgs = {o for o, p in assignment.items() if p in config["fit_partitions"]}
    test_orgs = {o for o, p in assignment.items() if p == config["test_partition"]}

    # Only training partition rank rows are parsed for model fitting. Test rows are skipped
    # before IncidentId or QueueRank values are read.
    positives_by_partition = defaultdict(list)
    with (root / config["rankings"]).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["OrgId", "IncidentId", "QueueRank"]:
            raise ValueError("ranking input header mismatch")
        for row in reader:
            org = (row.get("OrgId") or "").strip()
            part = assignment.get(org)
            if part not in config["fit_partitions"]:
                continue
            incident = (row.get("IncidentId") or "").strip()
            key = _candidate_key(org, incident)
            if key not in documents:
                raise ValueError("training top-20 key missing from local candidate universe")
            positives_by_partition[part].append(key)
    for part in config["fit_partitions"]:
        counts = Counter(incident_org[key] for key in positives_by_partition[part])
        if len(counts) != sum(assignment[o] == part for o in assignment) or any(n != 20 for n in counts.values()):
            raise ValueError(f"training labels must provide exactly 20 positive examples per {part} organization")

    conditions = _ranking_conditions(config["fields"], config["robustness"])
    all_predictions = {}
    k1, b = config["bm25"]["k1"], config["bm25"]["b"]
    fit_keys = positives_by_partition["pilot"] + positives_by_partition["development"]
    test_by_org = defaultdict(list)
    for key, org in incident_org.items():
        if org in test_orgs:
            test_by_org[_org_key(org)].append(key)
    for orgkey in test_by_org:
        test_by_org[orgkey].sort()

    for condition, active_fields, rate, seed in conditions:
        exemplar_docs = []
        for key in fit_keys:
            toks = _doc_tokens(documents[key], active_fields, rate, seed, key)
            if toks:
                exemplar_docs.append(toks)
        if not exemplar_docs:
            raise RuntimeError(f"no training exemplars remain for {condition}")
        index = _fit_bm25(exemplar_docs, k1, b)
        prediction_rows = []
        nonempty = 0
        for orgkey, keys in sorted(test_by_org.items()):
            scored = []
            for key in keys:
                query = _doc_tokens(documents[key], active_fields, rate, seed, key)
                nonempty += bool(query)
                scored.append((key, _score_query(index, query)))
            scored.sort(key=lambda x: (-x[1], x[0]))
            prediction_rows.extend({"organization_key": orgkey, "candidate_key": key, "score": score, "rank": pos}
                                   for pos, (key, score) in enumerate(scored, 1))
        all_predictions[condition] = {"rows": prediction_rows, "nonempty_test_candidates": nonempty, "training_exemplars": len(exemplar_docs)}

    # Evaluator-only universe has opaque hashes, never source identifiers or model features.
    universe = {orgkey: keys for orgkey, keys in sorted(test_by_org.items())}
    evaluator_dir = private_dir / "evaluator"
    evaluator_dir.mkdir(parents=True)
    (evaluator_dir / "candidate_universe.json").write_text(json.dumps(universe, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    prediction_dir = private_dir / "predictions"
    prediction_dir.mkdir()
    for condition, content in all_predictions.items():
        path = prediction_dir / f"{condition}.json"
        path.write_text(json.dumps({"condition": condition, "rows": content["rows"]}, separators=(",", ":")), encoding="utf-8")
        content["prediction_sha256"] = sha256_file(path)
        content.pop("rows")
    return all_predictions, coverage, sha256_file(evaluator_dir / "candidate_universe.json")


def predict(root: Path, out: Path):
    root, out = root.resolve(), out.resolve()
    allowed_out = (root / "outputs/phase6/priority").resolve()
    if not out.is_relative_to(allowed_out):
        raise ValueError("output must be under outputs/phase6/priority")
    if out.exists():
        raise FileExistsError("refusing to overwrite an existing Phase 6 run")
    private_dir = (root / "data/derived/empirical/priority" / out.name).resolve()
    if private_dir.exists():
        raise FileExistsError("refusing to overwrite an existing restricted Phase 6 run")
    config_path, config, policy_path = _load_protocol(root)
    hashes = _check_inputs(root, config)
    assignment, split_digest, split_counts, split_path = _load_split(root, config)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.perf_counter()
    out.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    conditions, coverage, universe_hash = _predict(root, config, assignment, private_dir)
    hashes_after = _check_inputs(root, config)
    if hashes_after != hashes:
        raise RuntimeError("raw input hashes changed during prediction run")
    manifest = {
        "protocol": "empirical-priority-v1",
        "classification": config["classification"],
        "mode": "offline_local_empirical_oracle_group_ceiling",
        "started_utc": started,
        "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "python": platform.python_version(),
        "seed": config["seed"],
        "raw_input_sha256_before": hashes,
        "raw_input_sha256_after": hashes_after,
        "config_sha256": sha256_file(config_path),
        "field_policy_sha256": sha256_file(policy_path),
        "protocol_document_sha256": sha256_file(root / "phases_outputs/empirical_protocol_freeze.md"),
        "protocol_manifest_sha256": sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"),
        "split_config_sha256": sha256_file(root / "configs/preprocessing.yaml"),
        "code_sha256": sha256_file(root / "src/empirical_priority.py"),
        "split_manifest_sha256": sha256_file(split_path),
        "split_assignment_sha256": split_digest,
        "split_counts": split_counts,
        "model_visible_fields": config["fields"],
        "evaluator_only_grouping": "gold IncidentId grouping; oracle ceiling only",
        "test_priority_labels_read": False,
        "external_calls": 0,
        "candidate_universe_sha256": universe_hash,
        "restricted_artifacts_relative_path": str(private_dir.relative_to(root)),
        "coverage": coverage,
        "conditions": conditions,
        "rank_direction_assumption": config["primary_rank_direction_assumption"],
        "method": "max BM25 similarity to pilot/development expert-top20 descriptor exemplars",
        "note": "Predictions are frozen before the evaluator reads test QueueRank labels. Index key fields are opaque hashes.",
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _ndcg(order: list[str], rank_labels: dict[str, int], reverse=False):
    gains = {}
    for key, rank in rank_labels.items():
        effective_rank = 21 - rank if reverse else rank
        gains[key] = (2 ** (21 - effective_rank) - 1)
    dcg = sum(gains.get(key, 0) / math.log2(i + 2) for i, key in enumerate(order[:20]))
    ideal = sorted(gains.values(), reverse=True)[:20]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def _org_metrics(order: list[str], rank_labels: dict[str, int]):
    relevant = set(rank_labels)
    hits10 = sum(k in relevant for k in order[:10])
    hits20 = sum(k in relevant for k in order[:20])
    return {
        "precision_at_10": hits10 / 10,
        "recall_at_20": hits20 / len(relevant) if relevant else 0.0,
        "ndcg_at_20_rank1_highest": _ndcg(order, rank_labels),
        "ndcg_at_20_rank20_highest_sensitivity": _ndcg(order, rank_labels, reverse=True),
        "top20_hits": hits20,
        "candidate_count": len(order),
        "gold_top20_count": len(relevant),
    }


def _bootstrap_mean(values: list[float], seed=20261108, resamples=10000):
    if not values:
        return {"mean": 0.0, "median": 0.0, "ci95": [0.0, 0.0], "n_orgs": 0}
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        means.append(sum(values[rng.randrange(len(values))] for _ in values) / len(values))
    means.sort()
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "ci95": [means[int(0.025 * resamples)], means[min(resamples - 1, int(0.975 * resamples))]],
        "n_orgs": len(values),
        "bootstrap_resamples": resamples,
        "seed": seed,
    }


def evaluate(root: Path, run_dir: Path):
    root, run_dir = root.resolve(), run_dir.resolve()
    manifest_path = run_dir / "run_manifest.json"
    manifest = _load_json(manifest_path)
    private_dir = (root / manifest["restricted_artifacts_relative_path"]).resolve()
    if not private_dir.is_relative_to((root / "data/derived/empirical/priority").resolve()):
        raise ValueError("restricted artifact path escaped the ignored empirical-data directory")
    config_path, config, policy_path = _load_protocol(root)
    if manifest.get("config_sha256") != sha256_file(config_path):
        raise RuntimeError("config changed after predictions were frozen")
    if manifest.get("field_policy_sha256") != sha256_file(policy_path):
        raise RuntimeError("empirical field policy changed after predictions were frozen")
    if manifest.get("protocol_document_sha256") != sha256_file(root / "phases_outputs/empirical_protocol_freeze.md") or manifest.get("protocol_manifest_sha256") != sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"):
        raise RuntimeError("protocol changed after predictions were frozen")
    if manifest.get("split_config_sha256") != sha256_file(root / "configs/preprocessing.yaml"):
        raise RuntimeError("split config changed after predictions were frozen")
    if manifest.get("code_sha256") != sha256_file(root / "src/empirical_priority.py"):
        raise RuntimeError("code changed after predictions were frozen")
    hashes = _check_inputs(root, config)
    if hashes != manifest.get("raw_input_sha256_after"):
        raise RuntimeError("raw source hash mismatch at evaluation time")
    assignment, split_digest, _, _ = _load_split(root, config)
    if split_digest != manifest.get("split_assignment_sha256"):
        raise RuntimeError("split digest mismatch at evaluation time")
    universe_path = private_dir / "evaluator/candidate_universe.json"
    if sha256_file(universe_path) != manifest.get("candidate_universe_sha256"):
        raise RuntimeError("evaluator candidate universe changed after prediction freeze")
    universe = _load_json(universe_path)

    # Read QueueRank only after frozen predictions, config, code and universe hashes pass.
    test_orgs = {org for org, part in assignment.items() if part == config["test_partition"]}
    rank_labels = defaultdict(dict)
    per_org_ranks = defaultdict(set)
    with (root / config["rankings"]).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            org = (row.get("OrgId") or "").strip()
            if org not in test_orgs:
                continue
            incident = (row.get("IncidentId") or "").strip()
            rank_text = (row.get("QueueRank") or "").strip()
            try:
                rank = int(rank_text)
            except ValueError as exc:
                raise ValueError("test rank is not an integer") from exc
            if not 1 <= rank <= 20:
                raise ValueError("test rank outside 1..20")
            orgkey, key = _org_key(org), _candidate_key(org, incident)
            if orgkey not in universe or key not in set(universe[orgkey]):
                raise ValueError("test top20 label outside frozen candidate universe")
            if key in rank_labels[orgkey] or rank in per_org_ranks[orgkey]:
                raise ValueError("duplicate test label/rank")
            rank_labels[orgkey][key] = rank
            per_org_ranks[orgkey].add(rank)
    if set(rank_labels) != set(universe) or any(len(v) != 20 or per_org_ranks[o] != set(range(1, 21)) for o, v in rank_labels.items()):
        raise ValueError("test labels are not a complete 1..20 set for every test organization")

    condition_reports = {}
    per_org_all = {}
    primary_per_org = None
    for condition in manifest["conditions"]:
        path = private_dir / "predictions" / f"{condition}.json"
        expected_hash = manifest["conditions"][condition]["prediction_sha256"]
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"frozen prediction changed: {condition}")
        pred = _load_json(path)
        grouped = defaultdict(list)
        seen = set()
        for row in pred["rows"]:
            if set(row) != {"organization_key", "candidate_key", "score", "rank"}:
                raise ValueError("prediction schema mismatch")
            orgkey, key = row["organization_key"], row["candidate_key"]
            if orgkey not in universe or key not in universe[orgkey] or (orgkey, key) in seen:
                raise ValueError("prediction outside or duplicated in candidate universe")
            seen.add((orgkey, key))
            grouped[orgkey].append(row)
        if seen != {(o, k) for o, keys in universe.items() for k in keys}:
            raise ValueError("prediction does not cover the frozen candidate universe")
        org_rows = {}
        for orgkey in sorted(universe):
            ordered = sorted(grouped[orgkey], key=lambda x: (x["rank"], x["candidate_key"]))
            if [r["rank"] for r in ordered] != list(range(1, len(ordered) + 1)):
                raise ValueError("prediction ranks are not contiguous within organization")
            org_rows[orgkey] = _org_metrics([r["candidate_key"] for r in ordered], rank_labels[orgkey])
        condition_reports[condition] = {
            metric: _bootstrap_mean([org_rows[o][metric] for o in org_rows])
            for metric in ("precision_at_10", "recall_at_20", "ndcg_at_20_rank1_highest", "ndcg_at_20_rank20_highest_sensitivity")
        }
        per_org_all[condition] = org_rows
        if condition == "primary":
            primary_per_org = org_rows

    paired_deltas = {}
    for condition, report in condition_reports.items():
        if condition == "primary":
            continue
        metric_deltas = {}
        for metric in ("precision_at_10", "recall_at_20", "ndcg_at_20_rank1_highest"):
            vals = [per_org_all[condition][o][metric] - primary_per_org[o][metric] for o in primary_per_org]
            metric_deltas[metric] = _bootstrap_mean(vals, seed=20261109)
        paired_deltas[condition] = metric_deltas

    report = {
        "classification": manifest["classification"],
        "run_id": run_dir.name,
        "test_organizations": len(universe),
        "candidate_count": sum(len(v) for v in universe.values()),
        "judged_top20_incidents": sum(len(v) for v in rank_labels.values()),
        "metrics_unit": "organization; macro mean/median and 95% nonparametric bootstrap CI; no hypothesis tests",
        "assumptions": ["A1 rank 1 is highest (nDCG sensitivity also reported)", "A2 local candidate universe proxy", "A4 five descriptor fields are alert-time features", "A5 frozen organization split", "gold-group oracle ceiling"],
        "conditions": condition_reports,
        "paired_differences_vs_primary": paired_deltas,
        "correlation_or_joint_metrics": "not evaluated",
        "llm_metrics": "not evaluated; external calls disabled",
        "test_labels_accessed_after_prediction_freeze": True,
        "raw_input_sha256": hashes,
        "protocol_freeze_sha256": sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"),
    }
    out = run_dir / "evaluation"
    out.mkdir(exist_ok=False)
    private_eval = private_dir / "evaluation"
    private_eval.mkdir(exist_ok=False)
    (private_eval / "per_organization_metrics.json").write_text(json.dumps({
        "classification": "restricted_pseudonymous_organization_metrics",
        "per_organization": per_org_all,
    }, indent=2, sort_keys=True), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    (out / "evaluation_manifest.json").write_text(json.dumps({
        "protocol": "empirical-priority-evaluation-v1",
        "classification": manifest["classification"],
        "run_manifest_sha256": sha256_file(manifest_path),
        "code_sha256": sha256_file(root / "src/empirical_priority.py"),
        "config_sha256": sha256_file(config_path),
        "raw_input_sha256": hashes,
        "metrics_sha256": sha256_file(out / "metrics.json"),
        "report_sha256": sha256_file(out / "report.md"),
        "test_labels_read": True,
    }, indent=2, sort_keys=True), encoding="utf-8")
    return report


def render_report(report: dict):
    lines = [
        "# Phase 6 priority retrieval — assumption-based local result", "",
        f"**Classification:** `{report['classification']}`  ",
        f"**Held-out organizations:** {report['test_organizations']}  ",
        f"**Local candidates:** {report['candidate_count']:,}  ",
        f"**Expert top-20 labels:** {report['judged_top20_incidents']:,}", "",
        "## Results", "",
        "| Condition | P@10 mean [95% CI] | Recall@20 mean [95% CI] | nDCG@20 (rank 1 highest) | nDCG@20 (rank 20 highest) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, result in report["conditions"].items():
        p, r = result["precision_at_10"], result["recall_at_20"]
        n1, n20 = result["ndcg_at_20_rank1_highest"], result["ndcg_at_20_rank20_highest_sensitivity"]
        lines.append(f"| {name} | {p['mean']:.4f} [{p['ci95'][0]:.4f}, {p['ci95'][1]:.4f}] | {r['mean']:.4f} [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}] | {n1['mean']:.4f} | {n20['mean']:.4f} |")
    lines += ["", "## Interpretation and limits", "",
        "Candidates are formed using gold `IncidentId` groups. Results are therefore a prioritization ceiling conditional on correct grouping; they are not end-to-end system performance. The BM25 exemplar corpus uses only pilot/development top-20 examples. Test QueueRank values were read only after prediction, configuration, code, split, and candidate-universe hashes were frozen.", "",
        "The local candidate universe is all distinct GUIDE composite incidents in the frozen test organizations, a project assumption because the local file has no `Split` or active-queue snapshot. `QueueRank=1` is assumed highest for the primary nDCG; the opposite convention is reported as a sensitivity analysis. P@10 and Recall@20 use only the complete top-20 membership set and do not depend on rank direction.", "",
        "Only `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` are model-visible. Conflicting alert keys and their evidence were excluded. The run is offline, with no live model or external API calls. No correlation, joint-system, severity-baseline, or LLM claim is made.", "",
        "Robustness conditions independently mask 20% and 40% of descriptor tokens under five fixed seeds. Field ablations remove one descriptor family at a time. Paired differences use organization-level bootstrap intervals; no significance tests are reported.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("predict", help="create frozen predictions without reading test ranks")
    p.add_argument("--root", default=".")
    p.add_argument("--out", required=True)
    e = sub.add_parser("evaluate", help="read test labels after frozen predictions and score Phase 6 experiments")
    e.add_argument("--root", default=".")
    e.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "predict":
            result = predict(Path(args.root), Path(args.out))
            print(json.dumps({"status": "predictions_frozen_test_labels_not_read", "run_dir": str(Path(args.out)), "conditions": list(result["conditions"]), "coverage": result["coverage"]}, sort_keys=True))
        else:
            report = evaluate(Path(args.root), Path(args.run))
            print(json.dumps({"status": "evaluation_complete_assumption_based_not_end_to_end", "run_dir": str(Path(args.run)), "test_organizations": report["test_organizations"], "candidate_count": report["candidate_count"], "conditions": len(report["conditions"])}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
