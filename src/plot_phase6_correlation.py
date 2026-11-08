"""Plot the aggregate-only corrected Phase 6 correlation diagnostic."""
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


def _sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def render(run_dir: Path):
    run_dir = run_dir.resolve()
    result_dir = run_dir / "evaluation/corrected"
    metrics_path, report_path = result_dir / "metrics.json", result_dir / "report.md"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    names = ["Pair precision", "Full-pair recall", "Full-pair F1", "Candidate generation\ncoverage"]
    keys = ["full_pair_precision", "full_pair_recall", "full_pair_f1", "candidate_generation_coverage"]
    micro_values = [data["micro"][k.split("full_pair_")[-1]] if k.startswith("full_pair_") else data["micro"]["candidate_generation_coverage"] for k in keys]
    macro = data["macro_organization_metrics"]
    means = [macro[k]["mean"] for k in keys]
    lower = [means[i] - macro[k]["ci95"][0] for i, k in enumerate(keys)]
    upper = [macro[k]["ci95"][1] - means[i] for i, k in enumerate(keys)]
    out = result_dir / "figures"
    out.mkdir(exist_ok=False)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10,
                         "figure.dpi": 140, "savefig.dpi": 300, "font.family": "DejaVu Sans"})
    x = np.arange(len(keys))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
    axes[0].bar(x, micro_values, color="#2b6cb0", alpha=0.9, width=0.64)
    axes[0].set_title("Pooled across all test organizations")
    axes[0].set_ylabel("Metric value")
    axes[0].set_xticks(x, names, rotation=18, ha="right")
    axes[0].set_ylim(0, 0.32)
    axes[1].bar(x, means, color="#d97706", alpha=0.9, width=0.64,
                yerr=np.array([lower, upper]), capsize=4,
                error_kw={"elinewidth": 1, "ecolor": "#303030"})
    axes[1].set_title("Macro mean per organization")
    axes[1].set_xticks(x, names, rotation=18, ha="right")
    for ax in axes:
        ax.grid(axis="y", color="#dddddd", linewidth=0.7)
        ax.set_axisbelow(True)
    fig.suptitle("Ambiguity-excluded ATT&CK-overlap correlation diagnostic", weight="bold")
    fig.text(0.5, 0.01,
             "30 organizations · 95% organization-bootstrap intervals on macro means · exploratory · maximum 20 candidates per alert",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(out / "correlation_metrics.png", bbox_inches="tight")
    fig.savefig(out / "correlation_metrics.svg", bbox_inches="tight")
    plt.close(fig)
    report_path.write_text(report_path.read_text(encoding="utf-8") +
                           "\n## Figure\n\n![Pooled and macro correlation metrics](figures/correlation_metrics.png)\n",
                           encoding="utf-8")
    files = sorted(p for p in out.iterdir() if p.is_file())
    manifest = {
        "classification": "aggregate_only_corrected_correlation_figure",
        "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__,
        "python": platform.python_version(),
        "metrics_sha256": _sha(metrics_path),
        "report_sha256": _sha(report_path),
        "plot_code_sha256": _sha(Path(__file__).resolve()),
        "figure_sha256": {p.name: _sha(p) for p in files},
    }
    (out / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    eval_manifest_path = result_dir / "evaluation_manifest.json"
    eval_manifest = json.loads(eval_manifest_path.read_text(encoding="utf-8"))
    eval_manifest["report_sha256"] = _sha(report_path)
    eval_manifest["figure_manifest_sha256"] = _sha(out / "figure_manifest.json")
    eval_manifest_path.write_text(json.dumps(eval_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    result = render(args.run)
    print(json.dumps({"status": "correlation_figure_created", "files": list(result["figure_sha256"])}, sort_keys=True))


if __name__ == "__main__":
    main()
