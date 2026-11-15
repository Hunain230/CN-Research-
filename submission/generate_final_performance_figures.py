"""Generate aggregate-only Phase 3 figures from frozen metric files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission/figures"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = read("outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json")["reference"]
    c = read("outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json")
    e = read("outputs/phase9e_bounded_candidate_20261115_v1/metrics.json")
    losses = read("outputs/phase6_grouping_failure_analysis_20261115_v4.json")["categories"]
    v2 = read("outputs/submission_entity_time_pair_v2_20261114_v1/metrics.json")
    v4 = read("outputs/submission_group_ranker_v4_20261114_v1/metrics.json")
    assert baseline["group_recoverable"] == 6969 and round(baseline["recall20"], 6) == round(4972/9980, 6)
    assert e["reference"]["pair_fp"] == 28606 and c["proposed"]["pair_fp"] == 28774

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "savefig.facecolor": "white"})
    colors = ["#b8c9d6", "#f3bb73", "#ed8d70", "#d17b79", "#7aa9ad", "#234e70"]
    labels = ["Absent scope", "Candidate disconnected", "Grouped incomplete", "Grouped impure", "Below top 20", "Recovered"]
    values = [losses[k] for k in ("absent", "candidate_disconnected", "incomplete", "impure")]
    values += [1997, 4972]
    assert sum(values) == 9980
    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    left = 0
    for label, value, color in zip(labels, values, colors):
        ax.barh([0], [value], left=left, height=.55, color=color, label=f"{label}: {value:,}")
        if value >= 400:
            ax.text(left+value/2, 0, f"{value:,}", ha="center", va="center", fontsize=10,
                    color="white" if color == "#234e70" else "#152b3d", fontweight="bold")
        left += value
    ax.set_xlim(0, 9980)
    ax.set_yticks([])
    ax.set_xlabel("Expert top-20 labels (n = 9,980)")
    ax.set_title("Where end-to-end recovery is lost - frozen v2 + v7", loc="left", weight="bold")
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(.5, -.55), frameon=False, fontsize=9)
    fig.subplots_adjust(bottom=.29, top=.84)
    fig.savefig(OUT / "final_loss_decomposition.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.4, 5.1))
    stages = ["Candidate-connected\n(oracle)", "Recoverable groups\n(oracle ordering)", "Recovered @20\n(measured)"]
    rates = [8638/9980, 6969/9980, 4972/9980]
    bars = ax.bar(stages, np.array(rates)*100, color=["#a9c6d1", "#729fb3", "#234e70"], width=.57)
    ax.axhline(80, color="#c45a4d", ls="--", lw=1.2, label="Proposed 80% Recall@20 target")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of 9,980 expert labels (%)")
    ax.set_title("Diagnostic ceilings and achieved recovery", loc="left", weight="bold")
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5, f"{rate*100:.2f}%", ha="center", weight="bold")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "final_recovery_funnel.png", dpi=220)
    plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(12.8, 4.4))
    methods = ["Frozen v2+v7", "Phase 9C", "Phase 9E"]
    variants = [baseline, c["proposed"], e["proposed"]]
    series = [("Recall@20", [v["recall20"]*100 for v in variants], "%", (0, 55)),
              ("Pair precision", [v["pair_precision"]*100 for v in variants], "%", (88, 92)),
              ("False grouped pairs", [v["pair_fp"] for v in variants], "pairs", (28000, 29000))]
    for ax, (title, vals, unit, ylim) in zip(axs, series):
        bars = ax.bar(methods, vals, color=["#234e70", "#c57c70", "#b8a478"], width=.58)
        ax.set_title(title, loc="left", weight="bold")
        ax.set_ylim(*ylim)
        ax.tick_params(axis="x", labelrotation=20)
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+(ylim[1]-ylim[0])*.015,
                    f"{value:.2f}" if unit == "%" else f"{value:,.0f}", ha="center", fontsize=9)
    fig.suptitle("Matched retrospective grouping experiments - both variants rejected", weight="bold", y=.98)
    fig.tight_layout(rect=(0, 0, 1, .92))
    fig.savefig(OUT / "final_grouping_controls.png", dpi=220)
    plt.close(fig)

    sources = ["outputs/phase6_grouping_failure_analysis_20261115_v4.json",
               "outputs/submission_entity_time_pair_v2_20261114_v1/metrics.json",
               "outputs/submission_group_ranker_v4_20261114_v1/metrics.json",
               "outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json",
               "outputs/phase9e_bounded_candidate_20261115_v1/metrics.json"]
    figures = ["final_loss_decomposition.png", "final_recovery_funnel.png", "final_grouping_controls.png"]
    manifest = {"classification": "aggregate_only_exploratory_phase3_figures",
                "source_sha256": {s: sha(ROOT / s) for s in sources},
                "figure_sha256": {f: sha(OUT / f) for f in figures},
                "script_sha256": sha(Path(__file__))}
    (OUT / "final_performance_figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"figures": figures, "status": "pass"}))


if __name__ == "__main__":
    main()
