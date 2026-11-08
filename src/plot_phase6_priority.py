"""Render aggregate-only figures for a completed Phase 6 priority experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _label(name: str):
    if name == "primary":
        return "Primary"
    if name.startswith("leave_out_"):
        return "w/o " + name.removeprefix("leave_out_")
    if name.startswith("mask_"):
        parts = name.split("_")
        return f"Mask {parts[1]}%\nseed {parts[3]}"
    return name


def render(run_dir: Path, tie_aware=False):
    run_dir = run_dir.resolve()
    result_dir = run_dir / "evaluation/tie_aware" if tie_aware else run_dir / "evaluation"
    metrics_path = result_dir / "metrics.json"
    report_path = result_dir / "report.md"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    conditions = data["conditions"]
    names = list(conditions)
    labels = [_label(x) for x in names]
    x = np.arange(len(names))
    width = 0.38
    out = result_dir / "figures"
    out.mkdir(exist_ok=False)
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 12, "axes.labelsize": 10,
                         "figure.dpi": 140, "savefig.dpi": 300, "font.family": "DejaVu Sans"})

    fig, ax = plt.subplots(figsize=(15, 6.8))
    for offset, metric, color, title in [
        (-width / 2, "precision_at_10", "#2b6cb0", "Precision@10"),
        (width / 2, "recall_at_20", "#d97706", "Recall@20"),
    ]:
        means = [conditions[n][metric]["mean"] for n in names]
        lows = [means[i] - conditions[n][metric]["ci95"][0] for i, n in enumerate(names)]
        highs = [conditions[n][metric]["ci95"][1] - means[i] for i, n in enumerate(names)]
        ax.bar(x + offset, means, width, label=title, color=color, alpha=0.9,
               yerr=np.array([lows, highs]), capsize=2,
               error_kw={"elinewidth": 0.8, "ecolor": "#303030"})
    ax.set_ylabel("Macro mean across held-out organizations")
    ax.set_ylim(0, 1)
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.suptitle("Phase 6 priority retrieval: feature ablations and evidence masking", y=0.99, weight="bold")
    fig.text(0.5, 0.01,
             "30 organizations · 95% organization-bootstrap intervals · gold-group oracle ceiling · local candidate-universe assumption",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.045, 1, 0.96))
    fig.savefig(out / "priority_precision_recall.png", bbox_inches="tight")
    fig.savefig(out / "priority_precision_recall.svg", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(15, 6.8))
    for offset, metric, color, label in [
        (-width / 2, "ndcg_at_20_rank1_highest", "#2b6cb0", "Assumption: rank 1 highest"),
        (width / 2, "ndcg_at_20_rank20_highest_sensitivity", "#d97706", "Sensitivity: rank 20 highest"),
    ]:
        means = [conditions[n][metric]["mean"] for n in names]
        lows = [means[i] - conditions[n][metric]["ci95"][0] for i, n in enumerate(names)]
        highs = [conditions[n][metric]["ci95"][1] - means[i] for i, n in enumerate(names)]
        ax.bar(x + offset, means, width, label=label, color=color, alpha=0.9,
               yerr=np.array([lows, highs]), capsize=2,
               error_kw={"elinewidth": 0.8, "ecolor": "#303030"})
    ax.set_ylabel("Macro nDCG@20")
    ax.set_ylim(0, 1)
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.grid(axis="y", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.suptitle("Rank-direction sensitivity for graded top-20 retrieval", y=0.99, weight="bold")
    fig.text(0.5, 0.01,
             "30 organizations · 95% organization-bootstrap intervals · nDCG depends on assumed numeric rank direction",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.045, 1, 0.96))
    fig.savefig(out / "priority_ndcg_direction_sensitivity.png", bbox_inches="tight")
    fig.savefig(out / "priority_ndcg_direction_sensitivity.svg", bbox_inches="tight")
    plt.close(fig)

    links = [
        "",
        "## Figures",
        "",
        "![Precision@10 and Recall@20 with organization-bootstrap intervals](figures/priority_precision_recall.png)",
        "",
        "![nDCG@20 sensitivity to numeric rank direction](figures/priority_ndcg_direction_sensitivity.png)",
        "",
    ]
    report_path.write_text(report_path.read_text(encoding="utf-8") + "\n".join(links), encoding="utf-8")
    files = sorted(p for p in out.iterdir() if p.is_file())
    manifest = {
        "classification": "aggregate_only_phase6_figures",
        "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__,
        "python": platform.python_version(),
        "metrics_sha256": _sha(metrics_path),
        "report_sha256": _sha(report_path),
        "plot_code_sha256": _sha(Path(__file__).resolve()),
        "figure_sha256": {p.name: _sha(p) for p in files},
    }
    (out / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True, type=Path)
    p.add_argument("--tie-aware", action="store_true", help="plot tie-aware exploratory re-analysis")
    args = p.parse_args()
    result = render(args.run, args.tie_aware)
    print(json.dumps({"status": "figures_created", "files": list(result["figure_sha256"])}, sort_keys=True))


if __name__ == "__main__":
    main()
