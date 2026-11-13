"""Plot paired selected-candidate Qwen C/B2 aggregate metrics only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/submission_qwen_v2_paper_20261113_v1"
METRICS = RUN / "metrics.json"
OUT = ROOT / "submission/figures"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads((RUN / "run_manifest.json").read_text(encoding="utf-8"))
    expected = manifest["sha256"][r"outputs\submission_qwen_v2_paper_20261113_v1\metrics.json"]
    if digest(METRICS) != expected:
        raise ValueError("Qwen metrics hash does not match run manifest")
    data = json.loads(METRICS.read_text(encoding="utf-8"))
    if (data["organizations"], data["selected_pairs"], data["pair_metrics_on_selected_exact_match_candidates"]["C"]["positive_pairs"]) != (20, 240, 22):
        raise ValueError("Unexpected paired model denominator")
    methods = data["pair_metrics_on_selected_exact_match_candidates"]
    labels = ["Precision", "Recall", "F1"]
    x = np.arange(3)
    width = 0.32
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for offset, method, color, title in ((-width / 2, "C", "#326a86", "C correlation"), (width / 2, "B2", "#aa713d", "B2 single model")):
        values = [methods[method][field] for field in ("precision", "recall", "f1")]
        bars = ax.bar(x + offset, values, width, label=title, color=color)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.003, f"{100 * value:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 0.125)
    ax.set_ylabel("Micro score on selected pairs")
    ax.set_title("Exploratory local Qwen pair decisions | 20 organizations, 240 pairs", fontweight="bold")
    ax.legend(frameon=False)
    fig.text(0.5, -0.03, "22 positive pairs. Exact Category + technique candidates only; not full-queue recall. No model superiority claim.", ha="center", fontsize=9)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "qwen_v2_pair_diagnostic.png"
    fig.savefig(target, bbox_inches="tight", facecolor="white", dpi=180)
    plt.close(fig)
    record = {
        "classification": "exploratory_paired_selected_candidate_model_figure",
        "command": r".\.venv\Scripts\python.exe -m submission.generate_qwen_v2_figure",
        "source_sha256": {str(METRICS.relative_to(ROOT)).replace("\\", "/"): digest(METRICS)},
        "figure_sha256": {str(target.relative_to(ROOT)).replace("\\", "/"): digest(target)},
    }
    (OUT / "qwen_v2_figure_manifest.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote paired Qwen v2 aggregate figure and manifest")


if __name__ == "__main__":
    main()
