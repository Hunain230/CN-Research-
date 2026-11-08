"""Two-step ambiguity-excluded offline ATT&CK-overlap correlation diagnostic."""
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
from .empirical_priority import INPUT_HASHES, _candidate_key, _load_split, _org_key
from .phase2 import sha256_file


def _hash(text: str):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _alert_key(org: str, alert: str):
    return _hash("empirical-alert-v1\0" + org + "\0" + alert)


def _read_config(root: Path):
    path = root / "configs/empirical_correlation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "empirical-correlation-v1":
        raise ValueError("correlation config version mismatch")
    policy_path = root / "configs/empirical_field_policy.yaml"
    policy = policy_path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^approved_model_fields:\s*\n((?:\s+-\s+[^\n]+\n)+)", policy)
    policy_fields = [line.strip()[2:].strip() for line in match.group(1).splitlines()] if match else []
    if policy_fields != data.get("fields"):
        raise ValueError("correlation fields differ from the adopted empirical field policy")
    return path, data, policy_path


def _source_hashes(root: Path, config: dict):
    result = {}
    for filename, path in [("GUIDE_Test.csv", root / config["alerts"]),
                           ("GUIDE_Test_Queue_Rankings.csv", root / config["rankings"])]:
        result[filename] = sha256_file(path)
        if result[filename] != INPUT_HASHES[filename]:
            raise RuntimeError(f"raw source hash changed: {filename}")
    return result


def _read_ambiguous(path: Path):
    keys = set()
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys.add((row["OrgId"], row["AlertId"]))
    return keys


def _collect_alert_features(root: Path, config: dict, test_orgs: set[str]):
    """Build alert features without reading IncidentId or any ranking labels."""
    ambiguous = _read_ambiguous(root / config["ambiguous_memberships"])
    fields = config["fields"]
    docs = {}
    excluded_rows = 0
    missing_alert_rows = 0
    with (root / config["alerts"]).open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"OrgId", "AlertId", *fields}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("GUIDE header missing correlation fields")
        for row in reader:
            org = (row.get("OrgId") or "").strip()
            if org not in test_orgs:
                continue
            alert = (row.get("AlertId") or "").strip()
            if not alert:
                missing_alert_rows += 1
                continue
            if (org, alert) in ambiguous:
                excluded_rows += 1
                continue
            key = _alert_key(org, alert)
            item = docs.setdefault(key, {"org_key": _org_key(org), "tokens": set(), "techniques": set()})
            for field in fields:
                value = (row.get(field) or "").strip()
                if not value:
                    continue
                vals = tokenize(value)
                item["tokens"].update(f"{field.casefold()}={token}" for token in vals)
                if field == "MitreTechniques":
                    item["techniques"].update(t.upper() for t in vals if re.fullmatch(r"T\d{4}(?:\.\d{3})?", t.upper()))
    for item in docs.values():
        item["tokens"] = sorted(item["tokens"])
        item["techniques"] = sorted(item["techniques"])
    return docs, {
        "ambiguous_keys_in_source": len(ambiguous),
        "test_evidence_rows_excluded_for_ambiguity": excluded_rows,
        "test_rows_missing_alert_key": missing_alert_rows,
        "unambiguous_test_alert_keys": len(docs),
        "alerts_with_technique_context": sum(bool(x["techniques"]) for x in docs.values()),
    }


def _candidate_pairs(docs: dict, max_neighbors: int, seed: int):
    by_org = defaultdict(list)
    for key, item in docs.items():
        by_org[item["org_key"]].append(key)
    pairs = set()
    per_org_counts = {}
    for orgkey, keys in sorted(by_org.items()):
        postings = defaultdict(set)
        for key in keys:
            for tech in docs[key]["techniques"]:
                postings[tech].add(key)
        selected = set()
        for left in keys:
            candidates = set()
            for tech in docs[left]["techniques"]:
                candidates.update(postings[tech])
            candidates.discard(left)
            scored = []
            left_tokens = set(docs[left]["tokens"])
            for right in candidates:
                right_tokens = set(docs[right]["tokens"])
                union = len(left_tokens | right_tokens)
                similarity = len(left_tokens & right_tokens) / union if union else 0.0
                # Pseudorandom label-independent tie resolution. The hash keys are used
                # only for joins and deterministic sampling, never as feature values.
                tie = _hash(f"tie-v1\0{seed}\0{left}\0{right}")
                scored.append((similarity, tie, right))
            scored.sort(key=lambda row: (-row[0], row[1]))
            for _, _, right in scored[:max_neighbors]:
                selected.add((left, right) if left < right else (right, left))
        for left, right in selected:
            pairs.add((orgkey, left, right))
        per_org_counts[orgkey] = {"alerts": len(keys), "candidate_pairs": len(selected)}
    return pairs, per_org_counts


def predict(root: Path, out: Path):
    root, out = root.resolve(), out.resolve()
    output_root = (root / "outputs/phase6/correlation").resolve()
    if not out.is_relative_to(output_root):
        raise ValueError("output must be under outputs/phase6/correlation")
    if out.exists():
        raise FileExistsError("refusing to overwrite existing correlation output")
    config_path, config, policy_path = _read_config(root)
    hashes_before = _source_hashes(root, config)
    assignment, split_digest, split_counts, split_path = _load_split(
        root, {"split_manifest": config["split_manifest"]}
    )
    test_orgs = {org for org, part in assignment.items() if part == "test"}
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.perf_counter()
    docs, coverage = _collect_alert_features(root, config, test_orgs)
    pairs, per_org_counts = _candidate_pairs(docs, config["max_neighbors_per_alert"], config["seed"])
    private_dir = (root / "data/derived/empirical/correlation" / out.name).resolve()
    if private_dir.exists():
        raise FileExistsError("refusing to overwrite restricted correlation artifacts")
    private_dir.mkdir(parents=True)
    out.mkdir(parents=True)
    universe = {org: sorted(k for k, item in docs.items() if item["org_key"] == org) for org in sorted(per_org_counts)}
    universe_path = private_dir / "alert_universe.json"
    universe_path.write_text(json.dumps(universe, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    pair_path = private_dir / "candidate_pairs.json"
    pair_path.write_text(json.dumps(sorted(pairs), separators=(",", ":")), encoding="utf-8")
    hashes_after = _source_hashes(root, config)
    if hashes_after != hashes_before:
        raise RuntimeError("raw hashes changed during correlation prediction")
    total_pairs = sum(n * (n - 1) // 2 for n in (x["alerts"] for x in per_org_counts.values()))
    manifest = {
        "protocol": "empirical-correlation-v1",
        "classification": config["classification"],
        "mode": "offline_ambiguity_excluded_local_diagnostic",
        "started_utc": started,
        "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "python": platform.python_version(),
        "raw_input_sha256_before": hashes_before,
        "raw_input_sha256_after": hashes_after,
        "config_sha256": sha256_file(config_path),
        "field_policy_sha256": sha256_file(policy_path),
        "protocol_amendment_sha256": sha256_file(root / "phases_outputs/correlation_diagnostic_amendment.md"),
        "code_sha256": sha256_file(root / "src/empirical_correlation.py"),
        "split_manifest_sha256": sha256_file(split_path),
        "split_config_sha256": sha256_file(root / "configs/preprocessing.yaml"),
        "protocol_manifest_sha256": sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"),
        "split_assignment_sha256": split_digest,
        "split_counts": split_counts,
        "test_organization_count": len(test_orgs),
        "model_visible_fields": config["fields"],
        "timestamp_used": False,
        "IncidentId_read_by_predictor": False,
        "QueueRank_read_by_predictor": False,
        "ambiguous_alert_keys_excluded": coverage["ambiguous_keys_in_source"],
        "coverage": coverage,
        "candidate_pairs": len(pairs),
        "full_same_org_pair_universe": total_pairs,
        "candidate_generation_coverage": len(pairs) / total_pairs if total_pairs else 0.0,
        "per_org_counts": per_org_counts,
        "candidate_pair_file_sha256": sha256_file(pair_path),
        "alert_universe_sha256": sha256_file(universe_path),
        "restricted_artifacts_relative_path": str(private_dir.relative_to(root)),
        "external_calls": 0,
        "method": "for each alert, top-20 Jaccard neighbors among same-org alerts sharing at least one ATT&CK technique; LINK each generated pair",
        "tie_policy": config["jaccard_similarity_ties"],
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _bootstrap(values, seed, count=10000):
    if not values:
        return {"mean": 0.0, "median": 0.0, "ci95": [0.0, 0.0], "n_orgs": 0}
    rng = random.Random(seed)
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(count))
    return {"mean": statistics.mean(values), "median": statistics.median(values), "ci95": [samples[249], samples[9749]], "n_orgs": n, "bootstrap_resamples": count, "seed": seed}


def _cluster_metrics(org_keys: list[str], gold: dict[str, str], links: list[tuple[str, str]]):
    parent = {key: key for key in org_keys}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for left, right in links:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a
    pred_groups = defaultdict(set)
    gold_groups = defaultdict(set)
    for key in org_keys:
        pred_groups[find(key)].add(key)
        if key in gold:
            gold_groups[gold[key]].add(key)
    merges = sum(len({gold[a] for a in comp if a in gold}) > 1 for comp in pred_groups.values())
    splits = sum(len({find(a) for a in alerts}) > 1 for alerts in gold_groups.values())
    return {"false_merges": merges, "false_splits": splits, "predicted_components": len(pred_groups), "singleton_components": sum(len(c) == 1 for c in pred_groups.values())}


def evaluate(root: Path, run_dir: Path):
    root, run_dir = root.resolve(), run_dir.resolve()
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_path, config, policy_path = _read_config(root)
    if manifest["config_sha256"] != sha256_file(config_path) or manifest["code_sha256"] != sha256_file(root / "src/empirical_correlation.py"):
        raise RuntimeError("correlation code/config changed after candidate generation")
    if manifest["field_policy_sha256"] != sha256_file(policy_path) or manifest["protocol_amendment_sha256"] != sha256_file(root / "phases_outputs/correlation_diagnostic_amendment.md"):
        raise RuntimeError("field policy or correlation protocol changed after candidate generation")
    if manifest["split_config_sha256"] != sha256_file(root / "configs/preprocessing.yaml") or manifest["protocol_manifest_sha256"] != sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"):
        raise RuntimeError("split or protocol freeze changed after candidate generation")
    raw_hashes = _source_hashes(root, config)
    if raw_hashes != manifest["raw_input_sha256_after"]:
        raise RuntimeError("raw input hash mismatch")
    assignment, split_digest, _, _ = _load_split(root, {"split_manifest": config["split_manifest"]})
    if split_digest != manifest["split_assignment_sha256"]:
        raise RuntimeError("split digest mismatch")
    private = (root / manifest["restricted_artifacts_relative_path"]).resolve()
    if not private.is_relative_to((root / "data/derived/empirical/correlation").resolve()):
        raise ValueError("restricted correlation artifacts escaped ignored data directory")
    pair_path, universe_path = private / "candidate_pairs.json", private / "alert_universe.json"
    if sha256_file(pair_path) != manifest["candidate_pair_file_sha256"] or sha256_file(universe_path) != manifest["alert_universe_sha256"]:
        raise RuntimeError("frozen candidate artifacts changed")
    universe = json.loads(universe_path.read_text(encoding="utf-8"))
    universe_sets = {o: set(v) for o, v in universe.items()}
    test_orgs = {org for org, part in assignment.items() if part == "test"}

    # This is the first point that evaluator IncidentId membership is opened.
    gold = defaultdict(dict)
    with (root / config["membership_truth"]).open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            org = row["OrgId"]
            if org not in test_orgs or row["mapping_status"] != "unambiguous":
                continue
            alert, incident = row["AlertId"], row["IncidentId"]
            key = _alert_key(org, alert)
            orgkey = _org_key(org)
            if key not in universe_sets.get(orgkey, set()):
                raise ValueError("unambiguous evaluator membership absent from frozen alert universe")
            gold[orgkey][key] = _hash("gold-incident-v1\0" + org + "\0" + incident)
    if set(gold) != set(universe) or any(set(gold[o]) != universe_sets[o] for o in universe):
        raise ValueError("frozen alert universe does not exactly match ambiguity-excluded truth")

    pairs = json.loads(pair_path.read_text(encoding="utf-8"))
    pair_by_org = defaultdict(list)
    seen = set()
    for orgkey, left, right in pairs:
        if orgkey not in universe_sets or left not in universe_sets[orgkey] or right not in universe_sets[orgkey] or left == right:
            raise ValueError("candidate pair outside same-org truth universe")
        key = (orgkey, left, right)
        if key in seen:
            raise ValueError("duplicate candidate pair")
        seen.add(key)
        pair_by_org[orgkey].append((left, right))

    org_results = {}
    for orgkey, alerts in universe.items():
        local_gold = gold[orgkey]
        group_sizes = Counter(local_gold.values())
        positives = sum(n * (n - 1) // 2 for n in group_sizes.values())
        full_universe = len(alerts) * (len(alerts) - 1) // 2
        candidate_pairs = pair_by_org[orgkey]
        tp = sum(local_gold[left] == local_gold[right] for left, right in candidate_pairs)
        fp = len(candidate_pairs) - tp
        candidate_positive = tp
        candidate_fn = candidate_positive - tp
        full_fn = positives - tp
        candidate_p = tp / len(candidate_pairs) if candidate_pairs else 0.0
        candidate_r = tp / candidate_positive if candidate_positive else 0.0
        candidate_f1 = 2 * candidate_p * candidate_r / (candidate_p + candidate_r) if candidate_p + candidate_r else 0.0
        full_precision = tp / (tp + fp) if tp + fp else 0.0
        full_recall = tp / positives if positives else 0.0
        full_f1 = 2 * full_precision * full_recall / (full_precision + full_recall) if full_precision + full_recall else 0.0
        org_results[orgkey] = {
            "alerts": len(alerts),
            "candidate_pairs": len(candidate_pairs),
            "candidate_positive_pairs": candidate_positive,
            "true_positive_links": tp,
            "false_positive_links": fp,
            "candidate_pair_false_negatives": candidate_fn,
            "full_positive_pair_universe": positives,
            "full_pair_false_negatives": full_fn,
            "full_same_org_pair_universe": full_universe,
            "candidate_generation_coverage": len(candidate_pairs) / full_universe if full_universe else 0.0,
            "candidate_set_precision": candidate_p,
            "candidate_set_recall": candidate_r,
            "candidate_set_f1": candidate_f1,
            "full_pair_precision": full_precision,
            "full_pair_recall": full_recall,
            "full_pair_f1": full_f1,
            "clustering_diagnostics": _cluster_metrics(alerts, local_gold, candidate_pairs),
        }

    metric_names = ["candidate_set_precision", "candidate_set_recall", "candidate_set_f1", "candidate_generation_coverage", "full_pair_precision", "full_pair_recall", "full_pair_f1"]
    macro = {name: _bootstrap([r[name] for r in org_results.values()], config["bootstrap_seed"]) for name in metric_names}
    micro_tp = sum(r["true_positive_links"] for r in org_results.values())
    micro_fp = sum(r["false_positive_links"] for r in org_results.values())
    micro_pos = sum(r["full_positive_pair_universe"] for r in org_results.values())
    micro_allpairs = sum(r["full_same_org_pair_universe"] for r in org_results.values())
    micro_p = micro_tp / (micro_tp + micro_fp) if micro_tp + micro_fp else 0.0
    micro_r = micro_tp / micro_pos if micro_pos else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    total_candidates = sum(r["candidate_pairs"] for r in org_results.values())
    report = {
        "classification": config["classification"],
        "run_id": run_dir.name,
        "test_organizations": len(org_results),
        "unambiguous_alert_keys": sum(r["alerts"] for r in org_results.values()),
        "excluded_ambiguous_alert_keys_dataset_wide": manifest["ambiguous_alert_keys_excluded"],
        "candidate_pairs": total_candidates,
        "full_same_org_pair_universe": micro_allpairs,
        "full_positive_pair_universe": micro_pos,
        "micro": {"tp": micro_tp, "fp": micro_fp, "fn_full_pair": micro_pos - micro_tp, "precision": micro_p, "recall": micro_r, "f1": micro_f1, "candidate_generation_coverage": total_candidates / micro_allpairs if micro_allpairs else 0.0},
        "macro_organization_metrics_with_bootstrap_ci": macro,
        "mean_clustering_diagnostics": {key: statistics.mean(r["clustering_diagnostics"][key] for r in org_results.values()) for key in ("false_merges", "false_splits", "predicted_components", "singleton_components")},
        "candidate_method": "same-org shared ATT&CK technique; top-20 Jaccard neighbors per alert; every generated candidate is LINK",
        "exclusions": "all ambiguous composite alert keys; all cross-org pairs; no timestamps",
        "disclosure": "Post-test-access exploratory diagnostic; not full-data correlation and not joint or LLM performance.",
        "no_significance_tests": True,
    }
    out = run_dir / "evaluation"
    out.mkdir(exist_ok=False)
    restricted_eval = private / "evaluation"
    restricted_eval.mkdir(exist_ok=False)
    (restricted_eval / "per_organization_metrics.json").write_text(json.dumps(org_results, indent=2, sort_keys=True), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (out / "report.md").write_text(render_report(report), encoding="utf-8")
    (out / "evaluation_manifest.json").write_text(json.dumps({
        "protocol": "empirical-correlation-evaluation-v1",
        "classification": report["classification"],
        "run_manifest_sha256": sha256_file(manifest_path),
        "code_sha256": sha256_file(root / "src/empirical_correlation.py"),
        "config_sha256": sha256_file(config_path),
        "raw_input_sha256": raw_hashes,
        "truth_rows_used": sum(len(v) for v in gold.values()),
        "metrics_sha256": sha256_file(out / "metrics.json"),
        "report_sha256": sha256_file(out / "report.md"),
    }, indent=2, sort_keys=True), encoding="utf-8")
    return report


def render_report(report: dict):
    m, macro = report["micro"], report["macro_organization_metrics_with_bootstrap_ci"]
    lines = [
        "# Phase 6 correlation diagnostic — ambiguity-excluded", "",
        f"**Classification:** `{report['classification']}`  ",
        f"**Organizations:** {report['test_organizations']}  ",
        f"**Unambiguous alert keys:** {report['unambiguous_alert_keys']:,}  ",
        f"**Candidate pairs:** {report['candidate_pairs']:,} / {report['full_same_org_pair_universe']:,} within-org pairs  ",
        f"**Positive gold pairs:** {report['full_positive_pair_universe']:,}", "",
        "## Pair metrics", "",
        "| Metric | Micro | Macro organization mean [95% bootstrap CI] |",
        "|---|---:|---:|",
        f"| Candidate-set precision | {m['precision']:.6f} | {macro['candidate_set_precision']['mean']:.6f} [{macro['candidate_set_precision']['ci95'][0]:.6f}, {macro['candidate_set_precision']['ci95'][1]:.6f}] |",
        f"| Candidate-set recall | {m['recall']:.6f} | {macro['candidate_set_recall']['mean']:.6f} [{macro['candidate_set_recall']['ci95'][0]:.6f}, {macro['candidate_set_recall']['ci95'][1]:.6f}] |",
        f"| Full-positive-pair recall | {m['recall']:.6f} | {macro['full_pair_recall']['mean']:.6f} [{macro['full_pair_recall']['ci95'][0]:.6f}, {macro['full_pair_recall']['ci95'][1]:.6f}] |",
        f"| Full-positive-pair F1 | {m['f1']:.6f} | {macro['full_pair_f1']['mean']:.6f} [{macro['full_pair_f1']['ci95'][0]:.6f}, {macro['full_pair_f1']['ci95'][1]:.6f}] |",
        f"| Candidate-generation coverage | {m['candidate_generation_coverage']:.6f} | {macro['candidate_generation_coverage']['mean']:.6f} [{macro['candidate_generation_coverage']['ci95'][0]:.6f}, {macro['candidate_generation_coverage']['ci95'][1]:.6f}] |",
        "", "## Method and limits", "",
        "For each unambiguous alert, candidates are limited to same-organization alerts sharing at least one ATT&CK technique. Jaccard similarity over the five assumed-safe descriptor fields selects at most 20 neighbors per alert. Every generated candidate is predicted LINK; all other pairs in the exhaustive within-organization universe are implicit NO_LINK. Time windows are omitted because timestamps are privacy-perturbed.", "",
        "All 70,702 conflicting composite alert keys are excluded; this diagnostic covers only unambiguous alert keys in the 30 frozen test organizations. It is post-test-access and exploratory. It is not a full-dataset correlation result, joint prioritization result, or LLM evaluation. Fields remain project assumptions and no external calls were made.", "",
        "Organization is the bootstrap unit (10,000 resamples); no hypothesis tests are reported.", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    pr = sub.add_parser("predict")
    pr.add_argument("--root", default=".")
    pr.add_argument("--out", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--root", default=".")
    ev.add_argument("--run", required=True)
    args = p.parse_args()
    try:
        if args.command == "predict":
            result = predict(Path(args.root), Path(args.out))
            print(json.dumps({"status": "correlation_candidates_frozen", "candidate_pairs": result["candidate_pairs"], "alerts": result["coverage"]["unambiguous_test_alert_keys"], "run": args.out}, sort_keys=True))
        else:
            result = evaluate(Path(args.root), Path(args.run))
            print(json.dumps({"status": "exploratory_ambiguity_excluded_correlation_complete", "organizations": result["test_organizations"], "candidate_pairs": result["candidate_pairs"], "micro": result["micro"]}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
