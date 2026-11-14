"""Plot aggregate metrics from the frozen 57-queue transfer experiment."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN = "submission_transfer_ranker_20261114_v1"
SOURCE = ROOT / "outputs" / RUN / "metrics.json"
RUN_MANIFEST = ROOT / "outputs" / RUN / "run_manifest.json"
PAIR_ANALYSIS = ROOT / "outputs" / RUN / "paired_analysis.json"
OUTPUT = ROOT / "submission/figures/transfer_ranker_57.png"
MANIFEST = ROOT / "submission/figures/transfer_ranker_57_manifest.json"
METHODS = (
    ("B0_rule_count", "Rule + count"),
    ("B1_rule_bm25", "Rule + prior BM25"),
    ("transfer_rule", "Rule + trained ranker"),
    ("offline_CPV_proxy", "CPV statistical proxy"),
)
MEASURES = (
    ("precision_at_10_macro", "Precision@10"),
    ("end_to_end_recall_at_20_macro", "End-to-end Recall@20"),
    ("ndcg_at_20_rank1_high_macro", "nDCG@20"),
)


def main() -> None:
    if OUTPUT.exists() or MANIFEST.exists():
        raise FileExistsError("Recorded figure exists; do not overwrite")
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(SOURCE) != manifest["sha256"][str(SOURCE.relative_to(ROOT))]:
        raise ValueError("Frozen aggregate metrics changed")
    paired = json.loads(PAIR_ANALYSIS.read_text(encoding="utf-8"))
    if paired["source_sha256"]["metrics"] != sha256_file(SOURCE):
        raise ValueError("Paired analysis source differs")
    metrics = json.loads(SOURCE.read_text(encoding="utf-8"))
    colors = ["#6f8792", "#aa8f6f", "#007f86", "#726594"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.9), sharey=False, constrained_layout=True)
    x = np.arange(len(METHODS))
    for ax, (metric, title) in zip(axes, MEASURES):
        means = [metrics["methods"][method][metric]["mean"] for method, _ in METHODS]
        lows = [metrics["methods"][method][metric]["ci95"][0] for method, _ in METHODS]
        highs = [metrics["methods"][method][metric]["ci95"][1] for method, _ in METHODS]
        errors = np.array([np.array(means) - lows, np.array(highs) - means])
        ax.bar(x, means, color=colors, width=0.68, zorder=2)
        ax.errorbar(x, means, yerr=errors, fmt="none", color="#1e303a", capsize=3, lw=1.1, zorder=3)
        ax.set_title(title, fontsize=11, weight="bold")
        ax.set_xticks(x, [name for _, name in METHODS], rotation=33, ha="right", fontsize=8)
        ax.set_ylim(0, max(highs) * 1.25)
        ax.grid(axis="y", alpha=0.2, zorder=0)
        for position, value in zip(x, means):
            ax.text(position, value + max(highs) * 0.055, f"{value:.3f}", ha="center", fontsize=8)
    fig.suptitle("Frozen 57-queue exploratory ranking comparison", fontsize=14, weight="bold")
    fig.text(0.5, -0.015, "Same 11,219 alerts and 1,140 expert labels; organization bootstrap 95% descriptive intervals. Rule groups unchanged for first three rows.", ha="center", fontsize=8)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    MANIFEST.write_text(json.dumps({
        "classification": "aggregate_exploratory_figure_not_confirmatory",
        "source_metrics_sha256": sha256_file(SOURCE),
        "source_paired_analysis_sha256": sha256_file(PAIR_ANALYSIS),
        "source_code_sha256": sha256_file(Path(__file__)),
        "figure_sha256": sha256_file(OUTPUT),
        "organizations": metrics["organizations"],
        "expert_top20_denominator": metrics["expert_top20_denominator"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
