"""Tie-aware re-evaluation of frozen Phase 6 BM25 predictions.

Metric correction: ties are treated as uniformly random orderings in expectation,
so the opaque candidate key used only for JSON serialization cannot affect P@10,
Recall@20, or nDCG@20. This evaluator is separate from the prediction code.
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
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from .empirical_priority import (
    INPUT_HASHES, _bootstrap_mean, _candidate_key, _check_inputs, _load_json,
    _load_protocol, _load_split, _org_key,
)
from .phase2 import sha256_file


def _expected_metrics(groups: list[list[tuple[str, float]]], labels: dict[str, int]):
    """Expected cut-off metrics under a uniform random permutation inside each score tie."""
    gain_by_key = {k: 2 ** (21 - rank) - 1 for k, rank in labels.items()}
    reverse_gain_by_key = {k: 2 ** (21 - (21 - rank)) - 1 for k, rank in labels.items()}
    expected10 = expected20 = 0.0
    dcg = dcg_reverse = 0.0
    zero_based_start = 0
    tied10_slots = tied20_slots = 0
    tied10_blocks = tied20_blocks = 0
    for group in groups:
        size = len(group)
        relevant = sum(key in labels for key, _ in group)
        take10 = max(0, min(size, 10 - zero_based_start))
        take20 = max(0, min(size, 20 - zero_based_start))
        if size > 1 and take10:
            tied10_blocks += 1
            tied10_slots += take10
        if size > 1 and take20:
            tied20_blocks += 1
            tied20_slots += take20
        if take10:
            expected10 += take10 * relevant / size
        if take20:
            expected20 += take20 * relevant / size
            positions = range(zero_based_start, zero_based_start + take20)
            discounts = sum(1 / math.log2(pos + 2) for pos in positions)
            group_gain = sum(gain_by_key.get(key, 0) for key, _ in group) / size
            group_gain_reverse = sum(reverse_gain_by_key.get(key, 0) for key, _ in group) / size
            dcg += group_gain * discounts
            dcg_reverse += group_gain_reverse * discounts
        zero_based_start += size

    ideal = sorted((gain_by_key.get(key, 0) for key in labels), reverse=True)
    ideal_reverse = sorted((reverse_gain_by_key.get(key, 0) for key in labels), reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:20]))
    idcg_reverse = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_reverse[:20]))
    candidate_count = sum(map(len, groups))
    return {
        "precision_at_10": expected10 / 10,
        "recall_at_20": expected20 / len(labels) if labels else 0.0,
        "ndcg_at_20_rank1_highest": dcg / idcg if idcg else 0.0,
        "ndcg_at_20_rank20_highest_sensitivity": dcg_reverse / idcg_reverse if idcg_reverse else 0.0,
        "expected_relevant_at_10": expected10,
        "expected_relevant_at_20": expected20,
        "candidate_count": candidate_count,
        "gold_top20_count": len(labels),
        "tie_blocks_intersecting_top10": tied10_blocks,
        "tie_blocks_intersecting_top20": tied20_blocks,
        "top10_slots_in_tied_blocks": tied10_slots,
        "top20_slots_in_tied_blocks": tied20_slots,
    }


def _aggregate(values: list[float], seed: int):
    if not values:
        return {"mean": 0.0, "median": 0.0, "ci95": [0.0, 0.0], "n_orgs": 0}
    rng = random.Random(seed)
    n = len(values)
    boot = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "ci95": [boot[249], boot[9749]],
        "n_orgs": n,
        "bootstrap_resamples": 10000,
        "seed": seed,
    }


def evaluate(root: Path, run_dir: Path):
    root, run_dir = root.resolve(), run_dir.resolve()
    original_manifest_path = run_dir / "run_manifest.json"
    original_manifest = _load_json(original_manifest_path)
    config_path, config, policy_path = _load_protocol(root)
    if original_manifest["config_sha256"] != sha256_file(config_path):
        raise RuntimeError("config changed after predictions were frozen")
    if original_manifest["field_policy_sha256"] != sha256_file(policy_path):
        raise RuntimeError("field policy changed after predictions were frozen")
    if original_manifest["code_sha256"] != sha256_file(root / "src/empirical_priority.py"):
        raise RuntimeError("predictor code changed after predictions were frozen")
    if original_manifest["protocol_document_sha256"] != sha256_file(root / "phases_outputs/empirical_protocol_freeze.md"):
        raise RuntimeError("protocol text changed after predictions were frozen")
    if original_manifest["protocol_manifest_sha256"] != sha256_file(root / "phases_outputs/empirical_protocol_freeze_manifest.json"):
        raise RuntimeError("protocol manifest changed after predictions were frozen")
    if original_manifest["split_config_sha256"] != sha256_file(root / "configs/preprocessing.yaml"):
        raise RuntimeError("split config changed after predictions were frozen")
    raw_hashes = _check_inputs(root, config)
    if raw_hashes != original_manifest["raw_input_sha256_after"]:
        raise RuntimeError("raw input hash mismatch")
    assignment, split_digest, _, _ = _load_split(root, config)
    if split_digest != original_manifest["split_assignment_sha256"]:
        raise RuntimeError("split mismatch")
    private_dir = (root / original_manifest["restricted_artifacts_relative_path"]).resolve()
    if not private_dir.is_relative_to((root / "data/derived/empirical/priority").resolve()):
        raise ValueError("restricted artifact path escaped ignored data directory")
    universe_path = private_dir / "evaluator/candidate_universe.json"
    if sha256_file(universe_path) != original_manifest["candidate_universe_sha256"]:
        raise RuntimeError("candidate universe hash mismatch")
    universe = _load_json(universe_path)
    universe_sets = {org: set(keys) for org, keys in universe.items()}

    test_orgs = {org for org, part in assignment.items() if part == config["test_partition"]}
    labels_by_org = defaultdict(dict)
    ranks_by_org = defaultdict(set)
    with (root / config["rankings"]).open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            org = (row.get("OrgId") or "").strip()
            if org not in test_orgs:
                continue
            incident = (row.get("IncidentId") or "").strip()
            rank = int(row["QueueRank"])
            key, orgkey = _candidate_key(org, incident), _org_key(org)
            if key not in universe_sets.get(orgkey, set()) or key in labels_by_org[orgkey] or rank in ranks_by_org[orgkey]:
                raise ValueError("test labels do not join uniquely to the frozen candidate universe")
            labels_by_org[orgkey][key] = rank
            ranks_by_org[orgkey].add(rank)
    if set(labels_by_org) != set(universe) or any(len(labels_by_org[o]) != 20 or ranks_by_org[o] != set(range(1, 21)) for o in universe):
        raise ValueError("test top-20 labels incomplete or rank positions invalid")

    per_org_conditions = {}
    condition_summary = {}
    for condition in original_manifest["conditions"]:
        prediction_path = private_dir / "predictions" / f"{condition}.json"
        if sha256_file(prediction_path) != original_manifest["conditions"][condition]["prediction_sha256"]:
            raise RuntimeError(f"prediction hash mismatch: {condition}")
        rows = _load_json(prediction_path)["rows"]
        grouped = defaultdict(list)
        seen = set()
        for row in rows:
            orgkey, key = row["organization_key"], row["candidate_key"]
            if orgkey not in universe or key not in universe_sets[orgkey] or (orgkey, key) in seen:
                raise ValueError("prediction outside or duplicated in universe")
            seen.add((orgkey, key))
            grouped[orgkey].append((key, float(row["score"])))
        expected = {(org, key) for org, keys in universe.items() for key in keys}
        if seen != expected:
            raise ValueError("prediction misses candidates in frozen universe")
        org_results = {}
        tie_counts = defaultdict(int)
        for orgkey, vals in grouped.items():
            by_score = defaultdict(list)
            for key, score in vals:
                by_score[score].append(key)
            groups = [[(key, score) for key in sorted(by_score[score])] for score in sorted(by_score, reverse=True)]
            result = _expected_metrics(groups, labels_by_org[orgkey])
            org_results[orgkey] = result
            for k in ("tie_blocks_intersecting_top10", "tie_blocks_intersecting_top20", "top10_slots_in_tied_blocks", "top20_slots_in_tied_blocks"):
                tie_counts[k] += result[k]
        metrics = ("precision_at_10", "recall_at_20", "ndcg_at_20_rank1_highest", "ndcg_at_20_rank20_highest_sensitivity")
        condition_summary[condition] = {m: _aggregate([org_results[o][m] for o in sorted(org_results)], 20261108) for m in metrics}
        condition_summary[condition]["tie_impact"] = dict(tie_counts)
        per_org_conditions[condition] = org_results

    primary = per_org_conditions["primary"]
    paired = {}
    for condition, values in per_org_conditions.items():
        if condition == "primary":
            continue
        paired[condition] = {}
        for metric in ("precision_at_10", "recall_at_20", "ndcg_at_20_rank1_highest"):
            diffs = [values[o][metric] - primary[o][metric] for o in sorted(primary)]
            paired[condition][metric] = _aggregate(diffs, 20261109)

    report = {
        "classification": "exploratory_tie_aware_reanalysis_after_failed_evaluator_attempt",
        "prediction_run_id": run_dir.name,
        "test_organizations": len(universe),
        "candidate_count": sum(len(v) for v in universe.values()),
        "judged_top20_incidents": sum(len(v) for v in labels_by_org.values()),
        "metric_policy": "expected P@10/Recall@20/nDCG@20 over uniform permutations within equal-score groups; candidate key affects serialization only",
        "rank_direction": "primary assumption rank 1 highest; inverse sensitivity reported",
        "organization_bootstrap": {"resamples": 10000, "seed": 20261108, "unit": "organization"},
        "conditions": condition_summary,
        "paired_differences_vs_primary": paired,
        "tie_policy_impact": {
            "organizations_with_top20_score_ties": sum(v["tie_blocks_intersecting_top20"] > 0 for v in primary.values()),
            "organizations_with_top10_score_ties": sum(v["tie_blocks_intersecting_top10"] > 0 for v in primary.values()),
            "primary_total_top20_slots_in_tied_blocks": sum(v["top20_slots_in_tied_blocks"] for v in primary.values()),
        },
        "reanalysis_reason": "Initial evaluator used opaque key ordering inside equal scores. Audit found many cutoff ties. No predictor, configuration, feature, or score changed; all 16 frozen prediction files are byte-identical across v1/v2.",
        "limitations": ["gold-group oracle ceiling", "local candidate universe proxy", "assumed QueueRank direction", "project-assumed descriptor timing", "no correlation/joint metrics", "no live LLM results"],
        "raw_input_sha256": raw_hashes,
    }
    output = run_dir / "evaluation/tie_aware"
    output.mkdir(exist_ok=False)
    private_output = private_dir / "evaluation/tie_aware"
    private_output.mkdir(exist_ok=False)
    (private_output / "per_organization_metrics.json").write_text(json.dumps(per_org_conditions, indent=2, sort_keys=True), encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output / "report.md").write_text(render_report(report), encoding="utf-8")
    (output / "evaluation_manifest.json").write_text(json.dumps({
        "protocol": "empirical-priority-tie-aware-evaluation-v1",
        "classification": report["classification"],
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": platform.python_version(),
        "run_manifest_sha256": sha256_file(original_manifest_path),
        "metric_amendment_sha256": sha256_file(root / "phases_outputs/metric_tie_amendment.md"),
        "tie_evaluator_code_sha256": sha256_file(Path(__file__).resolve()),
        "prediction_hashes": {c: original_manifest["conditions"][c]["prediction_sha256"] for c in original_manifest["conditions"]},
        "metrics_sha256": sha256_file(output / "metrics.json"),
        "report_sha256": sha256_file(output / "report.md"),
        "test_labels_read": True,
        "prior_failed_access_logged": True,
    }, indent=2, sort_keys=True), encoding="utf-8")
    return report


def render_report(report):
    lines = [
        "# Phase 6 tie-aware priority evaluation", "",
        f"**Classification:** `{report['classification']}`  ",
        f"**Organizations:** {report['test_organizations']}  ",
        f"**Candidates:** {report['candidate_count']:,}  ",
        f"**Gold top-20 labels:** {report['judged_top20_incidents']:,}", "",
        "Metrics take the expectation over uniformly permuted orderings within each equal-score block. This prevents the opaque identifier used only to serialize output rows from deciding cut-off relevance.", "",
        "## Results", "",
        "| Condition | P@10 | Recall@20 | nDCG@20 (rank 1 highest) | nDCG@20 (rank 20 highest) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in report["conditions"].items():
        cols = [values[m]["mean"] for m in ("precision_at_10", "recall_at_20", "ndcg_at_20_rank1_highest", "ndcg_at_20_rank20_highest_sensitivity")]
        lines.append(f"| {name} | " + " | ".join(f"{x:.4f}" for x in cols) + " |")
    t = report["tie_policy_impact"]
    lines += ["", "## Tie impact", "",
        f"Primary predictions had top-20 score ties in {t['organizations_with_top20_score_ties']} of {report['test_organizations']} organizations and top-10 ties in {t['organizations_with_top10_score_ties']} organizations. {t['primary_total_top20_slots_in_tied_blocks']} of {20 * report['test_organizations']} top-20 slots were in tied score blocks.", "",
        "## Disclosure and limits", "",
        report["reanalysis_reason"], "",
        "This is a post-access metric correction, so treat the tie-aware results as exploratory. The frozen scores and all prediction files are unchanged. It remains an oracle-group ranking ceiling on the assumed local candidate universe; it is not end-to-end correlation or an LLM comparison. The primary nDCG assumes rank 1 is highest; the inverse direction is reported because the publisher's numeric direction remains unresolved.", "",
        "The governing metric amendment is [`metric_tie_amendment.md`](../../../../phases_outputs/metric_tie_amendment.md); prior access history is in [`test_evaluation_access_log.md`](../../../../phases_outputs/test_evaluation_access_log.md).", "",
        "95% organization-bootstrap intervals and paired condition differences are in `metrics.json`. No p-values are reported.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    try:
        report = evaluate(Path(args.root), Path(args.run))
        print(json.dumps({"status": "tie_aware_exploratory_reanalysis_complete", "test_organizations": report["test_organizations"], "conditions": len(report["conditions"]), "tie_impact": report["tie_policy_impact"]}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
