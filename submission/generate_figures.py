"""Regenerate Task 5 aggregate-only research figures; never reads raw or restricted data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission" / "figures"
JOINT = ROOT / "outputs" / "offline_joint_v2"
CANDIDATE = ROOT / "outputs" / "phase_a" / "candidate_20261111.json"
PRIORITY = (
    ROOT
    / "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/metrics.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources() -> tuple[dict, dict, dict]:
    manifest = load(JOINT / "run_manifest.json")
    for relative, expected in manifest["sha256"].items():
        # Verify only tracked aggregate inputs and code. Never open private predictions.
        if relative.startswith("data\\"):
            continue
        path = ROOT / relative
        if digest(path) != expected:
            raise ValueError(f"Source hash mismatch: {relative}")
    joint = load(JOINT / "metrics.json")
    candidate = load(CANDIDATE)
    priority = load(PRIORITY)
    if candidate["source_sha256"]["data\\derived\\offline_joint_v2\\predictions.pkl"] != manifest["sha256"]["data\\derived\\offline_joint_v2\\predictions.pkl"]:
        raise ValueError("Candidate audit does not cite the v2 prediction freeze")
    if (joint["organizations"], joint["alerts"], joint["candidate_pairs"], joint["label_count"]) != (57, 11219, 1216600, 1140):
        raise ValueError("Unexpected joint cohort")
    if (candidate["totals"]["candidates"], candidate["totals"]["positive"]) != (joint["candidate_pairs"], 47607):
        raise ValueError("Candidate and joint counts disagree")
    if priority["test_organizations"] != 30 or priority["judged_top20_incidents"] != 600:
        raise ValueError("Unexpected priority cohort")
    return joint, candidate, priority


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 180,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def matched(joint: dict) -> None:
    keys = ["B0_rule_count", "B1_rule_bm25", "offline_CP_proxy", "offline_CPV_proxy"]
    labels = ["Rule/count B0 amendment", "Rule/BM25 B1", "Offline CP proxy", "Offline CPV proxy"]
    colors = ["#355c7d", "#5684a0", "#a66a37", "#be8740"]
    y = np.arange(4)
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
    f1 = [joint["methods"][k]["micro_pair"]["f1"] for k in keys]
    left.barh(y, f1, color=colors, height=0.58)
    left.set_yticks(y, labels)
    left.invert_yaxis()
    left.set_xlim(0, 0.17)
    left.set_xlabel("Micro positive-pair F1 (fraction)")
    left.set_title("Grouping over full pair universe")
    for yi, value in zip(y, f1):
        left.text(value + 0.003, yi, f"{value:.3f}", va="center", fontsize=9)

    recall = [joint["methods"][k]["end_to_end_recall_at_20"]["mean"] for k in keys]
    ci = [joint["methods"][k]["end_to_end_recall_at_20"]["ci95"] for k in keys]
    error = np.array([[v - lo for v, (lo, hi) in zip(recall, ci)], [hi - v for v, (lo, hi) in zip(recall, ci)]])
    right.errorbar(recall, y, xerr=error, fmt="o", color="#172d43", ecolor="#628095", capsize=4)
    right.set_yticks(y, [""] * 4)
    right.invert_yaxis()
    right.set_xlim(0, 0.19)
    right.set_xlabel("Organization-macro end-to-end Recall@20")
    right.set_title("Predicted-group recovery")
    for yi, value in zip(y, recall):
        right.text(0.184, yi, f"{value:.3f}", va="center", ha="right", fontsize=9)
    fig.suptitle("Exploratory offline comparison | 57 queues, 11,219 alerts, 1,140 labels", fontweight="bold")
    fig.text(0.5, -0.03, "Right: 95% organization-bootstrap intervals. CP/CPV are offline proxies; no LLM result is plotted.", ha="center", fontsize=9)
    fig.tight_layout()
    save(fig, "matched_offline_proxy.png")


def candidate_bottleneck(candidate: dict) -> None:
    totals = candidate["totals"]
    present = totals["candidate_positive"]
    missed = totals["positive"] - present
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.5))
    left.barh([0], [present], color="#3c806f", label="Positive pairs retrieved")
    left.barh([0], [missed], left=[present], color="#c45e4d", label="Positive pairs omitted")
    left.set_xlim(0, totals["positive"] * 1.08)
    left.set_yticks([0], ["Positive pairs"])
    left.set_xlabel("Pair count")
    left.set_title("Candidate recall: 38,807 / 47,607 = 81.52%")
    left.legend(loc="lower center", bbox_to_anchor=(0.5, -0.4), frameon=False)
    right.barh([0], [totals["candidates"]], color="#597d9b", label="Generated pairs")
    right.barh([0], [totals["possible_pairs"] - totals["candidates"]], left=[totals["candidates"]], color="#c7d3dc", label="Other possible pairs")
    right.set_xlim(0, totals["possible_pairs"] * 1.08)
    right.set_yticks([0], ["All within-queue pairs"])
    right.set_xlabel("Pair count")
    right.set_title("Pair workload: 1,216,600 / 1,510,902 = 80.52%")
    right.legend(loc="lower center", bbox_to_anchor=(0.5, -0.4), frameon=False)
    fig.suptitle("Exploratory frozen candidate set | same 57 small queues", fontweight="bold")
    fig.tight_layout()
    save(fig, "candidate_bottleneck.png")


def oracle_ablation(priority: dict) -> None:
    conditions = priority["conditions"]
    primary = conditions["primary"]["recall_at_20"]["mean"]
    fields = ["Category", "DetectorId", "EntityType", "EvidenceRole", "MitreTechniques"]
    labels = ["Primary five fields"] + [f"Omit {field}" for field in fields]
    values = [primary] + [conditions[f"leave_out_{field}"]["recall_at_20"]["mean"] for field in fields]
    fig, ax = plt.subplots(figsize=(9.8, 5.4))
    y = np.arange(len(labels))
    colors = ["#274e70"] + ["#8aa5ba"] * len(fields)
    ax.barh(y, values, color=colors, height=0.6)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.42)
    ax.set_xlabel("Organization-macro oracle-group Recall@20 (fraction)")
    ax.set_title("Exploratory leave-one-field-out analysis | 30 queues, 600 labels", fontweight="bold")
    for yi, value in zip(y, values):
        ax.text(value + 0.006, yi, f"{value:.3f}", va="center", fontsize=9)
    fig.tight_layout()
    save(fig, "oracle_group_ablation.png")


def main() -> None:
    joint, candidate, priority = verify_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    matched(joint)
    candidate_bottleneck(candidate)
    oracle_ablation(priority)
    manifest = {
        "classification": "exploratory_aggregate_figures_not_new_experiment",
        "command": ".\\.venv\\Scripts\\python.exe -m submission.generate_figures",
        "sources_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
            for path in (JOINT / "metrics.json", CANDIDATE, PRIORITY)
        },
        "figures_sha256": {
            name: digest(OUT / name)
            for name in (
                "matched_offline_proxy.png",
                "candidate_bottleneck.png",
                "oracle_group_ablation.png",
            )
        },
    }
    (OUT / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Wrote 3 exploratory aggregate-only figures to submission/figures/")


if __name__ == "__main__":
    main()
