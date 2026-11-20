"""Generate vector statistical figures from the archived frozen experiment.

Run from the repository root: python over_leaf/figure_source/metrics_charts.py
No values are manually entered into a plot. Some evidence categories overlap,
so the evidence-profile bars are counts rather than parts of a whole.
"""
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
OUT = ROOT / "over_leaf/figures"
summary = json.loads((STUDY / "HOLDOUT_SUMMARY.json").read_text(encoding="utf-8"))
validation = json.loads((STUDY / "artifacts/generator_validation.json").read_text(encoding="utf-8"))["locked_test"]
audit = json.loads((STUDY / "POST_EVALUATION_AUDIT.json").read_text(encoding="utf-8"))
with (STUDY / "HOLDOUT_RESULTS.csv").open(newline="", encoding="utf-8") as stream:
    queues = list(csv.DictReader(stream))

NAVY = "#17365d"
TEAL = "#087f76"
AMBER = "#bd6a1c"
sns.set_theme(style="whitegrid", context="paper", font="DejaVu Sans")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                     "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "pdf.fonttype": 42, "savefig.facecolor": "white"})


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


# Identical opportunities for each arm; this figure shows rates, not pooled counts.
labels = ["Incident R@20", "Recoverability", "P@10"]
fields = ["incident_recall20", "group_recoverability", "p10"]
baseline = [100 * summary["baseline"][k] for k in fields]
candidate = [100 * summary["candidate"][k] for k in fields]
y = np.arange(3)
fig, ax = plt.subplots(figsize=(3.35, 2.7))
ax.barh(y + .17, baseline, height=.31, color=NAVY, label="Baseline")
ax.barh(y - .17, candidate, height=.31, color=TEAL, label="Endpoint fallback")
for row, (b, c) in enumerate(zip(baseline, candidate)):
    ax.text(b + .8, row + .17, f"{b:.1f}", va="center", fontsize=7, color=NAVY)
    ax.text(c + .8, row - .17, f"{c:.1f}", va="center", fontsize=7, fontweight="bold", color=TEAL)
ax.set(yticks=y, yticklabels=labels, xlim=(0, 102), xlabel="Percent of evaluator opportunities")
ax.invert_yaxis()
ax.legend(loc="lower center", bbox_to_anchor=(.55, 1.02), ncol=2, frameon=False, fontsize=6.8)
ax.grid(axis="x", color="#d9e2e8", linewidth=.5)
ax.grid(axis="y", visible=False)
sns.despine(ax=ax, left=True, bottom=True)
save(fig, "performance_bars.pdf")


# Generator challenge counts are intentionally not stacked: categories overlap.
profile = [
    ("False claims", validation["false_independent_looking_claim"]),
    ("Derived copies", validation["derived_claims"]),
    ("Same-context false", validation["false_same_context_relationships"]),
    ("Late claims", validation["late_claims"]),
    ("Missing true claims", validation["missing"]),
]
fig, ax = plt.subplots(figsize=(3.35, 2.55))
ys = np.arange(len(profile))
ax.barh(ys, [n for _, n in profile], color=[NAVY, TEAL, AMBER, NAVY, TEAL], height=.65)
for row, (_, n) in enumerate(profile):
    ax.text(n + 5, row, str(n), va="center", fontsize=7, fontweight="bold")
ax.set(yticks=ys, yticklabels=[k for k, _ in profile], xlim=(0, 395), xlabel="Recorded challenge observations")
ax.invert_yaxis()
ax.grid(axis="x", color="#d9e2e8", linewidth=.5)
ax.grid(axis="y", visible=False)
sns.despine(ax=ax, left=True, bottom=True)
save(fig, "evidence_profile.pdf")


# This matrix concerns submitted relationship tokens, not all possible alert pairs.
matrix = np.array([[audit["accepted_true"], audit["accepted_false"]],
                   [audit["rejected_true"], audit["rejected_false"]]])
fig, ax = plt.subplots(figsize=(3.25, 2.55))
sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, square=False,
            linewidths=1.5, linecolor="white", annot_kws={"fontsize": 12, "fontweight": "bold"}, ax=ax)
ax.set_xticklabels(["Genuine", "False"], rotation=0)
ax.set_yticklabels(["Accepted", "Rejected / abstained"], rotation=0)
ax.set(xlabel="Simulator truth", ylabel="Verifier decision")
ax.tick_params(length=0)
save(fig, "token_confusion_heatmap.pdf")


# Exact integer differences on each matched queue; values remain visible in grayscale.
columns = [("R@20", "recall"), ("Recoverable", "recoverable"), ("P@10", "p10")]
delta = np.array([[int(q["candidate_" + key]) - int(q["baseline_" + key])
                   for _, key in columns] for q in queues])
fig, ax = plt.subplots(figsize=(5.7, 3.65))
sns.heatmap(delta, center=0, vmin=-3, vmax=3, cmap="BrBG", annot=True, fmt="d",
            cbar_kws={"label": "Candidate minus baseline", "shrink": .72},
            linewidths=.5, linecolor="white", annot_kws={"fontsize": 7, "fontweight": "bold"}, ax=ax)
ax.set_xticklabels([x for x, _ in columns], rotation=0)
ax.set_yticklabels([f"Q{i + 1:02}" for i in range(len(queues))], rotation=0)
ax.tick_params(length=0)
ax.set(xlabel="Metric (incident or position count)", ylabel="Matched queue")
save(fig, "queue_delta_heatmap.pdf")


# Recompute R@k directly from sealed predictions and private evaluator labels.
# The same 80% completeness / 80% purity rule appears in the frozen evaluator.
truth_root = STUDY / "dataset/evaluator_only/locked_test/ground_truth_private"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


rank_curves = {}
for name in ("baseline", "candidate"):
    predictions = read_jsonl(STUDY / f"artifacts/{name}_predictions.jsonl")
    counts_by_rank = np.zeros(20, dtype=int)
    for pred in predictions:
        q = pred["queue_id"]
        truth = {a["alert_id"]: a for a in read_jsonl(truth_root / f"{q}.jsonl")}
        expert = {a["incident_id"]: a["priority_rank"]
                  for a in read_jsonl(truth_root / f"{q}_priority.jsonl")}
        eligible_sizes = Counter(truth[a]["incident_id"] for a in pred["eligible_alert_ids"])
        first_qualifying = {}
        for pos, group in enumerate(pred["groups_ranked"], 1):
            hits = Counter(truth[a]["incident_id"] for a in group)
            for incident, count in hits.items():
                if (expert.get(incident, 26) <= 20 and
                        count / eligible_sizes[incident] >= .8 and count / len(group) >= .8):
                    first_qualifying.setdefault(incident, pos)
        for pos in first_qualifying.values():
            if pos <= 20:
                counts_by_rank[pos - 1:] += 1
    assert counts_by_rank[-1] == summary[name]["recall20_count"], name
    rank_curves[name] = counts_by_rank / summary[name]["expert_top20"] * 100

fig, ax = plt.subplots(figsize=(3.35, 2.45))
ks = np.arange(1, 21)
ax.plot(ks, rank_curves["baseline"], color=NAVY, marker="o", markersize=2.5,
        linewidth=1.8, label="Baseline")
ax.plot(ks, rank_curves["candidate"], color=TEAL, marker="s", markersize=2.5,
        linewidth=1.8, label="Endpoint fallback")
ax.fill_between(ks, rank_curves["baseline"], rank_curves["candidate"], color=TEAL, alpha=.12)
ax.set(xlim=(1, 20.8), xticks=[1, 5, 10, 15, 20], ylim=(0, 95),
       xlabel="Top-k group positions", ylabel="Expert incidents recalled (%)")
ax.text(20.1, rank_curves["candidate"][-1], "86.7", color=TEAL, fontsize=7,
        fontweight="bold", va="bottom")
ax.text(20.1, rank_curves["baseline"][-1], "83.3", color=NAVY, fontsize=7, va="top")
ax.legend(loc="upper left", fontsize=6.7, frameon=False)
sns.despine(ax=ax)
save(fig, "ranked_recall_curve.pdf")


# Partition the 300 expert top-20 opportunities by group qualification and rank.
states = {}
for name in ("baseline", "candidate"):
    s = summary[name]
    states[name] = (s["recall20_count"], s["recoverable"] - s["recall20_count"],
                    s["expert_top20"] - s["recoverable"])
fig, ax = plt.subplots(figsize=(3.35, 2.1))
parts = [("Top 20", TEAL), ("Beyond 20", NAVY), ("No group", AMBER)]
for y, name in enumerate(("baseline", "candidate")):
    left = 0
    for j, (_, color) in enumerate(parts):
        n = states[name][j]
        ax.barh(y, n, left=left, height=.54, color=color)
        if n >= 13:
            ax.text(left + n / 2, y, str(n), ha="center", va="center", color="white",
                    fontweight="bold", fontsize=7)
        left += n
ax.set(yticks=[0, 1], yticklabels=["Baseline", "Endpoint fallback"],
       xlim=(0, 300), xlabel="Expert top-20 incident opportunities")
ax.invert_yaxis()
fig.legend([plt.Rectangle((0, 0), 1, 1, fc=c) for _, c in parts],
           [label for label, _ in parts], loc="lower center", ncol=3,
           bbox_to_anchor=(.57, 1.00), fontsize=6.3, frameon=False)
ax.grid(axis="y", visible=False)
sns.despine(ax=ax, left=True, bottom=True)
save(fig, "outcome_decomposition.pdf")

print("Generated six vector charts; ranked Recall@20 matches the frozen evaluator in both arms")
print("R@k counts (baseline, candidate):", {k: (round(rank_curves["baseline"][k-1]*3),
                                                round(rank_curves["candidate"][k-1]*3))
                                          for k in (5, 10, 15, 20)})

# Descriptive queue-cluster uncertainty, exactly as in paired_queue_bootstrap.py.
# The x axis shows percentage-point differences, not absolute performance.
bootstrap_rows = list(csv.DictReader((ROOT / "over_leaf/analysis/holdout_queue_results.csv").open(newline="", encoding="utf-8")))
rng = random.Random(31103)
metrics = [("Recall@20", "recall", 20), ("Recoverability", "recoverable", 20), ("P@10", "p10", 10)]
intervals = []
for title, key, denom in metrics:
    ds = [(int(r["candidate_" + key]) - int(r["baseline_" + key])) * 100 / denom for r in bootstrap_rows]
    reps = sorted(sum(rng.choice(ds) for _ in ds) / len(ds) for _ in range(10000))
    intervals.append((title, sum(ds) / len(ds), reps[249], reps[9749]))
fig, ax = plt.subplots(figsize=(6.45, 2.55), layout="constrained")
for y, (title, point, low, high) in enumerate(intervals):
    ax.plot([low, high], [y, y], color=NAVY, linewidth=3, solid_capstyle="round")
    ax.plot(point, y, "o", markersize=8, color=TEAL, markeredgecolor="white", markeredgewidth=1.1)
    ax.text(high + .15, y, f"{point:+.2f} pp  [{low:+.2f}, {high:+.2f}]", va="center", fontsize=8)
ax.axvline(0, color=AMBER, linewidth=1.1, linestyle="--")
ax.set(yticks=range(3), yticklabels=[row[0] for row in intervals], xlim=(-1.5, 13),
       xlabel="Endpoint fallback minus frozen baseline (percentage points)")
ax.invert_yaxis()
ax.grid(axis="x", color="#e0e6eb", linewidth=.6)
ax.grid(axis="y", visible=False)
sns.despine(ax=ax, left=True)
save(fig, "paired_bootstrap_intervals.pdf")

# Controlled development ablation: retrieve counts from the archived result CSVs.
with (ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/DEVELOPMENT_RESULTS.csv").open(newline="", encoding="utf-8") as stream:
    dev31 = {r["arm"]: r for r in csv.DictReader(stream)}
with (ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/DEVELOPMENT_RESULTS.csv").open(newline="", encoding="utf-8") as stream:
    dev32 = {r["candidate"]: r for r in csv.DictReader(stream)}
dev = [("Rich claims", dev31["legacy_rich"]),
       ("Independent roots", dev31["evidence_aware_ranked"]),
       ("+ endpoint fallback", dev32["endpoint_fallback_bonus1"])]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.55, 2.6), gridspec_kw={"width_ratios": [1.4, 1]}, layout="constrained")
xx = np.arange(3)
recall = [int(r.get("recall_count", r.get("recall20_count"))) / 2 for _, r in dev]
recover = [int(r["recoverable"]) / 2 for _, r in dev]
ax1.plot(xx, recall, color=NAVY, marker="o", linewidth=2, label="Recall@20")
ax1.plot(xx, recover, color=TEAL, marker="s", linewidth=2, label="Recoverability")
for i in range(3):
    ax1.text(i, recall[i]-1.25, f"{recall[i]:.1f}", color=NAVY, ha="center", fontsize=7)
    ax1.text(i, recover[i]+.6, f"{recover[i]:.1f}", color=TEAL, ha="center", fontsize=7)
ax1.set(xticks=xx, xticklabels=[s for s, _ in dev], ylim=(72, 92), ylabel="Expert incidents (%)")
ax1.tick_params(axis="x", labelrotation=12)
ax1.legend(frameon=False, fontsize=7, loc="upper left")
false_pairs = [int(r["false_pairs"]) for _, r in dev]
ax2.bar(xx, false_pairs, color=[AMBER, TEAL, TEAL], width=.53)
for i, n in enumerate(false_pairs):
    ax2.text(i, n+70, f"{n:,}", ha="center", fontweight="bold", fontsize=8)
ax2.set(xticks=xx, xticklabels=[s for s, _ in dev], ylim=(0, 3050), ylabel="False within-group pairs")
ax2.tick_params(axis="x", labelrotation=12)
for ax in (ax1, ax2):
    sns.despine(ax=ax)
    ax.grid(axis="y", alpha=.25)
    ax.grid(axis="x", visible=False)
save(fig, "development_ablation.pdf")

# Matched incident outcomes; these are the four cells of the archived paired audit.
paired = np.array([[245, 5], [15, 35]])
fig, ax = plt.subplots(figsize=(5.4, 2.85), layout="constrained")
sns.heatmap(paired, annot=True, fmt="d", cmap="YlGnBu", cbar=False, linewidths=2,
            linecolor="white", annot_kws={"fontsize": 15, "fontweight": "bold"}, ax=ax)
ax.set_xticklabels(["Candidate recalled", "Candidate missed"], rotation=0)
ax.set_yticklabels(["Baseline recalled", "Baseline missed"], rotation=0)
ax.set(xlabel="Candidate decision at rank 20", ylabel="Baseline decision at rank 20")
ax.tick_params(length=0)
save(fig, "paired_incident_outcomes.pdf")
assert recall == [77.5, 79.0, 84.5] and recover == [80.0, 83.0, 88.5]
print("Generated three additional archived-data figures (paired intervals, development ablation, incident transitions)")

# Two compact, paired panels for the manuscript. Both panels in each figure
# come from the same sealed 15-queue holdout, so no cross-cohort scale is implied.
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(7.2, 2.55), layout="constrained",
    gridspec_kw={"width_ratios": [1.15, 1]})
ax1.plot(ks, rank_curves["baseline"], color=NAVY, lw=2.1,
         marker="o", markevery=[4, 9, 14, 19], ms=4, label="Baseline")
ax1.plot(ks, rank_curves["candidate"], color=TEAL, lw=2.1,
         marker="s", markevery=[4, 9, 14, 19], ms=4, label="Endpoint fallback")
ax1.axvline(20, color=AMBER, lw=1, ls="--")
ax1.set(xlim=(1, 20.5), ylim=(0, 95), xticks=[1, 5, 10, 15, 20],
        xlabel="Rank cutoff $k$", ylabel="Incident Recall@$k$ (%)")
ax1.legend(loc="upper left", frameon=False, fontsize=7)
ax1.grid(axis="y", alpha=.25)
cuts = [0, 5, 10, 15, 20]
base_bins = np.diff([0] + [round(rank_curves["baseline"][k-1] * 3) for k in cuts[1:]])
cand_bins = np.diff([0] + [round(rank_curves["candidate"][k-1] * 3) for k in cuts[1:]])
x = np.arange(4)
ax2.bar(x - .18, base_bins, width=.34, color=NAVY, label="Baseline")
ax2.bar(x + .18, cand_bins, width=.34, color=TEAL, label="Endpoint fallback")
for i, (b, c) in enumerate(zip(base_bins, cand_bins)):
    ax2.text(i-.18, b+1, str(b), ha="center", fontsize=6.5)
    ax2.text(i+.18, c+1, str(c), ha="center", fontsize=6.5, fontweight="bold")
ax2.set(xticks=x, xticklabels=["1–5", "6–10", "11–15", "16–20"],
        ylim=(0, 88), xlabel="First qualifying group rank",
        ylabel="Newly retrieved incidents")
ax2.grid(axis="y", alpha=.25)
ax2.grid(axis="x", visible=False)
for ax in (ax1, ax2):
    sns.despine(ax=ax)
save(fig, "rank_retrieval_panels.pdf")

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(7.2, 2.55), layout="constrained",
    gridspec_kw={"width_ratios": [1.15, 1]})
for y, name in enumerate(("baseline", "candidate")):
    left = 0
    for j, (label, color) in enumerate(parts):
        n = states[name][j]
        ax1.barh(y, n, left=left, height=.52, color=color,
                 label=label if y == 0 else None)
        ax1.text(left+n/2, y, str(n), va="center", ha="center",
                 color="white" if j < 2 else "#222222", fontsize=8,
                 fontweight="bold")
        left += n
ax1.set(yticks=[0, 1], yticklabels=["Baseline", "Endpoint fallback"],
        xlim=(0, 300), xlabel="Expert top-20 incidents (n=300)")
ax1.invert_yaxis()
ax1.legend(loc="upper center", bbox_to_anchor=(.5, 1.22),
           ncol=3, frameon=False, fontsize=6.5)
ax1.grid(axis="x", alpha=.2)
ax1.grid(axis="y", visible=False)
sns.heatmap(paired, annot=True, fmt="d", cmap="YlGnBu", cbar=False,
            linewidths=1.5, linecolor="white",
            annot_kws={"fontsize": 13, "fontweight": "bold"}, ax=ax2)
ax2.set_xticklabels(["Recalled", "Missed"], rotation=0)
ax2.set_yticklabels(["Recalled", "Missed"], rotation=0)
ax2.set(xlabel="Endpoint fallback", ylabel="Baseline")
ax2.tick_params(length=0)
sns.despine(ax=ax1, left=True, bottom=True)
save(fig, "incident_outcome_panels.pdf")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.45, 4.1),
                               layout="constrained",
                               gridspec_kw={"height_ratios": [1, 1.15]})
for y, name in enumerate(("baseline", "candidate")):
    left = 0
    for j, (label, color) in enumerate(parts):
        n = states[name][j]
        ax1.barh(y, n, left=left, height=.5, color=color,
                 label=label if y == 0 else None)
        ax1.text(left+n/2, y, str(n), ha="center", va="center",
                 color="white" if j < 2 else "#222222",
                 fontsize=7, fontweight="bold")
        left += n
ax1.set(yticks=[0, 1], yticklabels=["Baseline", "Fallback"], xlim=(0, 300),
        xlabel="Expert incident opportunities (n=300)")
ax1.invert_yaxis()
ax1.legend(loc="upper center", bbox_to_anchor=(.5, 1.32), ncol=3,
           fontsize=5.9, frameon=False)
ax1.grid(axis="x", alpha=.2)
ax1.grid(axis="y", visible=False)
sns.heatmap(paired, annot=True, fmt="d", cmap="YlGnBu", cbar=False,
            linewidths=1.5, linecolor="white",
            annot_kws={"fontsize": 12, "fontweight": "bold"}, ax=ax2)
ax2.set_xticklabels(["Recalled", "Missed"], rotation=0)
ax2.set_yticklabels(["Recalled", "Missed"], rotation=0)
ax2.set(xlabel="Endpoint fallback", ylabel="Baseline")
ax2.tick_params(length=0)
sns.despine(ax=ax1, left=True, bottom=True)
save(fig, "incident_outcome_column.pdf")
assert base_bins.sum() == 250 and cand_bins.sum() == 260
assert sum(states["baseline"]) == sum(states["candidate"]) == paired.sum() == 300
print("Generated paired rank and incident-outcome panels from sealed holdout data")
