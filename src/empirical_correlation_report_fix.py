"""Create a corrected aggregate report from a frozen Phase 6 correlation run.

This evaluator-output correction does not change predictions or reopen labels.
It removes mechanically tautological candidate-set recall for an all-LINK rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path

from .phase2 import sha256_file


def _bootstrap(values, seed=20261110, n_boot=10000):
    if not values:
        return {"mean": 0.0, "median": 0.0, "ci95": [0.0, 0.0], "n_orgs": 0}
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return {"mean": statistics.mean(values), "median": statistics.median(values), "ci95": [draws[249], draws[9749]], "n_orgs": n, "bootstrap_resamples": n_boot, "seed": seed}


def render(m):
    macro = m["macro_organization_metrics"]
    micro = m["micro"]
    lines = [
        "# Phase 6 correlation diagnostic — corrected aggregate metrics", "",
        f"**Classification:** `{m['classification']}`  ",
        f"**Organizations:** {m['test_organizations']}  ",
        f"**Unambiguous alert keys:** {m['unambiguous_alert_keys']:,}  ",
        f"**Generated candidate links:** {m['candidate_pairs']:,}  ",
        f"**Full positive-pair universe:** {m['full_positive_pair_universe']:,}  ",
        f"**Possible within-org alert pairs:** {m['full_same_org_pair_universe']:,}", "",
        "## Pair metrics", "",
        "| Metric | Micro | Macro organization mean [95% bootstrap CI] |",
        "|---|---:|---:|",
        f"| Pair precision | {micro['precision']:.6f} | {macro['full_pair_precision']['mean']:.6f} [{macro['full_pair_precision']['ci95'][0]:.6f}, {macro['full_pair_precision']['ci95'][1]:.6f}] |",
        f"| Full-positive-pair recall | {micro['recall']:.6f} | {macro['full_pair_recall']['mean']:.6f} [{macro['full_pair_recall']['ci95'][0]:.6f}, {macro['full_pair_recall']['ci95'][1]:.6f}] |",
        f"| Full-pair F1 | {micro['f1']:.6f} | {macro['full_pair_f1']['mean']:.6f} [{macro['full_pair_f1']['ci95'][0]:.6f}, {macro['full_pair_f1']['ci95'][1]:.6f}] |",
        f"| Candidate-generation coverage | {micro['candidate_generation_coverage']:.6f} | {macro['candidate_generation_coverage']['mean']:.6f} [{macro['candidate_generation_coverage']['ci95'][0]:.6f}, {macro['candidate_generation_coverage']['ci95'][1]:.6f}] |",
        "", "## Metric correction", "",
        "The original aggregate report included candidate-set recall. Because this rule predicts LINK for every generated pair, candidate-set recall is mechanically 1 whenever a generated positive exists, and its macro average mostly reflected organizations with no generated positive. That value is omitted here. Full-positive-pair recall uses all same-incident unambiguous alert pairs as its denominator, so candidate-generation misses count as false negatives.", "",
        "## Method and limits", "",
        "Candidate pairs are same-organization alerts sharing at least one ATT&CK technique; at most 20 Jaccard-nearest neighbors are selected per alert. All generated pairs are LINK. All ambiguous keys are excluded, timestamps are unused, and the five descriptors rely on the project assumptions.", "",
        "This is a post-test-access exploratory diagnostic on the unambiguous subset of the frozen test organizations. It is not full-dataset correlation, joint prioritization, end-to-end system performance, or an LLM evaluation. There are no significance tests.", "",
        "The underlying frozen candidate-pair file and predictions were not changed. See [`correlation_metric_report_amendment.md`](../../../../phases_outputs/correlation_metric_report_amendment.md) for the versioned correction.", ""]
    return "\n".join(lines)


def fix(root: Path, run: Path):
    root, run = root.resolve(), run.resolve()
    source_manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    private = (root / source_manifest["restricted_artifacts_relative_path"]).resolve()
    original_metrics_path = run / "evaluation/metrics.json"
    eval_manifest_path = run / "evaluation/evaluation_manifest.json"
    old_eval = json.loads(eval_manifest_path.read_text(encoding="utf-8"))
    if old_eval["metrics_sha256"] != sha256_file(original_metrics_path):
        raise RuntimeError("historical aggregate metrics changed; cannot reconcile report")
    per_org_path = private / "evaluation/per_organization_metrics.json"
    per_org = json.loads(per_org_path.read_text(encoding="utf-8"))
    names = ["candidate_set_precision", "full_pair_precision", "full_pair_recall", "full_pair_f1", "candidate_generation_coverage"]
    macro = {name: _bootstrap([r[name] for r in per_org.values()]) for name in names}
    tp = sum(r["true_positive_links"] for r in per_org.values())
    fp = sum(r["false_positive_links"] for r in per_org.values())
    pos = sum(r["full_positive_pair_universe"] for r in per_org.values())
    universe = sum(r["full_same_org_pair_universe"] for r in per_org.values())
    candidate_pairs = sum(r["candidate_pairs"] for r in per_org.values())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / pos if pos else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    report = {
        "classification": "exploratory_ambiguity_excluded_correlation_metric_report_correction",
        "run_id": run.name,
        "test_organizations": len(per_org),
        "unambiguous_alert_keys": sum(r["alerts"] for r in per_org.values()),
        "candidate_pairs": candidate_pairs,
        "full_positive_pair_universe": pos,
        "full_same_org_pair_universe": universe,
        "micro": {"tp": tp, "fp": fp, "fn_full_pair": pos - tp, "precision": precision, "recall": recall, "f1": f1, "candidate_generation_coverage": candidate_pairs / universe if universe else 0.0},
        "macro_organization_metrics": macro,
        "mean_clustering_diagnostics": {key: statistics.mean(r["clustering_diagnostics"][key] for r in per_org.values()) for key in ("false_merges", "false_splits", "predicted_components", "singleton_components")},
        "candidate_set_recall_status": "omitted_mechanically_perfect_for_all_LINK_candidate_rule",
        "disclosure": "Post-test-access aggregate-metric correction; no predictions, candidate pairs or labels changed.",
        "source_prediction_run_manifest_sha256": sha256_file(run / "run_manifest.json"),
        "historical_metrics_sha256": sha256_file(original_metrics_path),
    }
    output = run / "evaluation/corrected"
    output.mkdir(exist_ok=False)
    (output / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output / "report.md").write_text(render(report), encoding="utf-8")
    amendment = root / "phases_outputs/correlation_metric_report_amendment.md"
    (output / "evaluation_manifest.json").write_text(json.dumps({
        "protocol": "empirical-correlation-metric-report-correction-v1",
        "classification": report["classification"],
        "historical_eval_manifest_sha256": sha256_file(eval_manifest_path),
        "per_org_metric_source_sha256": sha256_file(per_org_path),
        "correction_code_sha256": sha256_file(Path(__file__).resolve()),
        "metric_amendment_sha256": sha256_file(amendment),
        "metrics_sha256": sha256_file(output / "metrics.json"),
        "report_sha256": sha256_file(output / "report.md"),
    }, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".")
    p.add_argument("--run", required=True)
    a = p.parse_args()
    try:
        result = fix(Path(a.root), Path(a.run))
        print(json.dumps({"status": "correlation_report_corrected_no_predictions_changed", "micro": result["micro"], "output": str(Path(a.run) / "evaluation/corrected")}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
