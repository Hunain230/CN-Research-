"""Plot frozen aggregate results from the full GUIDE_Test offline run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/submission_full_guide_20261112_v1/metrics.json"
RUN = ROOT / "outputs/submission_full_guide_20261112_v1/run_manifest.json"
OUT = ROOT / "submission/figures"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads(RUN.read_text(encoding="utf-8"))
    recorded = manifest["sha256"][r"outputs\submission_full_guide_20261112_v1\metrics.json"]
    if digest(SOURCE) != recorded:
        raise ValueError("Full GUIDE metric hash mismatch")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if (data["organizations"], data["alerts"], data["expert_top20_denominator"]) != (499, 400039, 9980):
        raise ValueError("Unexpected full-run denominator")
    names = ["full_rule_count", "full_rule_local_bm25"]
    labels = ["Rule / count", "Rule / local BM25-like"]
    p10 = [data["methods"][name]["precision_at_10_macro"]["mean"] for name in names]
    recall = [data["methods"][name]["end_to_end_recall_at_20_macro"]["mean"] for name in names]
    colors = ["#627f9b", "#2f745f"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.4))
    for ax, values, title in zip(axes, (p10, recall), ("Precision@10", "End-to-end Recall@20")):
        bars = ax.bar(labels, values, color=colors, width=0.55)
        ax.set_ylim(0, 0.22)
        ax.set_ylabel("Organization-macro fraction")
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=12)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.005, f"{value:.3f}", ha="center")
    fig.suptitle("Full ranked GUIDE_Test offline baselines | 499 organizations", fontweight="bold")
    fig.text(0.5, -0.04, "Exploratory; 400,039 unambiguous alerts; 9,980 expert labels. Shared weak candidate rule; no LLM result.", ha="center", fontsize=9)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "full_guide_offline.png"
    fig.savefig(target, bbox_inches="tight", facecolor="white", dpi=180)
    plt.close(fig)
    record = {
        "classification": "exploratory_aggregate_only_full_guide_offline",
        "command": r".\.venv\Scripts\python.exe -m submission.generate_submission_figures",
        "source_sha256": {str(SOURCE.relative_to(ROOT)).replace("\\", "/"): digest(SOURCE)},
        "figure_sha256": {str(target.relative_to(ROOT)).replace("\\", "/"): digest(target)},
    }
    (OUT / "submission_figure_manifest.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote full GUIDE_Test offline aggregate figure and manifest")


if __name__ == "__main__":
    main()
