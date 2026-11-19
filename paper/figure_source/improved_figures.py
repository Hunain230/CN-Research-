"""
Improved supplementary figures for the CN research paper.
Generates additional high-quality visualisations beyond build_paper.py.
Run from the paper/ directory or via build_improved.py.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import csv

P = Path(__file__).resolve().parents[1]   # paper/
FIG = P / "figures"
FIG.mkdir(exist_ok=True)

# ── colour palette ────────────────────────────────────────────────────────────
NAVY    = "#1F4E79"
TEAL    = "#2E8B8E"
AMBER   = "#C7742A"
LGRAY   = "#F2F4F5"
MGRAY   = "#BFC9CA"
DGRAY   = "#4D5F6B"
WHITE   = "#FFFFFF"
GREEN   = "#2E7D32"
RED     = "#C62828"
LGREEN  = "#E8F5E9"
LTEAL   = "#E0F4F4"
LNAVY   = "#E8EEF4"
LAMBER  = "#FFF3E0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Metrics Comparison  –  grouped bar chart with delta annotations
# ═══════════════════════════════════════════════════════════════════════════════
metrics   = ["Incident\nRecall@20", "Group\nRecoverability", "P@10"]
baseline  = [83.33, 87.67, 71.33]
fallback  = [86.67, 93.67, 75.33]
deltas    = ["+3.33 pp", "+6.00 pp", "+4.00 pp"]
denoms    = ["n = 300", "n = 300", "n = 150"]
raw_base  = ["250/300", "263/300", "107/150"]
raw_fall  = ["260/300", "281/300", "113/150"]

x = np.arange(len(metrics))
w = 0.34

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.set_facecolor(LGRAY)
fig.patch.set_facecolor(WHITE)

b1 = ax.bar(x - w/2, baseline, w, color=NAVY,  label="Frozen Baseline",   zorder=3,
            edgecolor=WHITE, linewidth=0.6)
b2 = ax.bar(x + w/2, fallback, w, color=TEAL,  label="Endpoint Fallback", zorder=3,
            edgecolor=WHITE, linewidth=0.6)

for bar, val, raw in zip(b1, baseline, raw_base):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.7,
            f"{raw}\n{val:.2f}%", ha="center", va="bottom", fontsize=7.8,
            color=NAVY, weight="bold")
for bar, val, raw in zip(b2, fallback, raw_fall):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.7,
            f"{raw}\n{val:.2f}%", ha="center", va="bottom", fontsize=7.8,
            color=TEAL, weight="bold")

for i, (bv, fv, d) in enumerate(zip(baseline, fallback, deltas)):
    ax.annotate("", xy=(i + w/2, fv), xytext=(i + w/2, bv),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6))
    ax.text(i + w/2 + 0.21, (bv + fv)/2, d, ha="left", va="center",
            fontsize=8.5, color=GREEN, weight="bold")

ax.set_xticks(x)
ax.set_xticklabels([f"{m}\n({d})" for m, d in zip(metrics, denoms)], fontsize=9)
ax.set_ylim(0, 108)
ax.set_ylabel("Percentage of evaluator opportunities (%)", fontsize=9)
ax.yaxis.grid(True, alpha=0.35, color=MGRAY, zorder=0)
ax.set_axisbelow(True)
ax.spines["left"].set_color(MGRAY)
ax.spines["bottom"].set_color(MGRAY)
ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
ax.set_title("Primary Frozen Synthetic Holdout: Baseline vs. Endpoint Fallback",
             fontsize=11, weight="bold", color=NAVY, pad=10)

fig.tight_layout()
fig.savefig(FIG / "metrics_comparison.pdf", bbox_inches="tight")
plt.close(fig)
print("  metrics_comparison.pdf done")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Safety Scorecard
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.axis("off")
fig.patch.set_facecolor(WHITE)

cards = [
    ("15 / 15", "Safe Queues\n(zero false pairs\nAND zero mixed groups)", LGREEN, GREEN),
    ("0",       "False Grouped Pairs\n(both arms, all queues)", LGREEN, GREEN),
    ("0",       "Mixed Groups\n(both arms, all queues)", LGREEN, GREEN),
    ("100%",    "Grouped-pair Precision\nBaseline: 19,459 pairs\nFallback: 20,117 pairs", LTEAL, TEAL),
]

for idx, (val, lbl, face, edge) in enumerate(cards):
    x0 = 0.03 + idx * 0.245
    ax.add_patch(FancyBboxPatch((x0, 0.08), 0.22, 0.84,
                                boxstyle="round,pad=0.01,rounding_size=0.03",
                                facecolor=face, edgecolor=edge, linewidth=1.5,
                                transform=ax.transAxes, clip_on=False))
    ax.text(x0 + 0.11, 0.65, val, ha="center", va="center", fontsize=22,
            weight="bold", color=edge, transform=ax.transAxes)
    ax.text(x0 + 0.11, 0.26, lbl, ha="center", va="center", fontsize=7.8,
            color=DGRAY, transform=ax.transAxes, linespacing=1.4)

ax.set_title("Group Safety Results — 15-Queue Frozen Synthetic Holdout",
             fontsize=10.5, weight="bold", color=NAVY, pad=8)
ax.text(0.5, -0.04,
        "Zero observed errors under simulator truth is not a bound on real-world error rates.",
        ha="center", fontsize=7.5, color=DGRAY, transform=ax.transAxes)

fig.tight_layout(pad=0.3)
fig.savefig(FIG / "safety_overview.pdf", bbox_inches="tight")
plt.close(fig)
print("  safety_overview.pdf done")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Pipeline Overview
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 3.8))
ax.set_xlim(0, 12); ax.set_ylim(0, 4); ax.axis("off")
fig.patch.set_facecolor(WHITE)

nodes = [
    (0.1,  1.3, 1.6, 1.4, "INPUT",
     "5,018 eligible alerts\n15 queues · cutoff T=100",
     LNAVY, NAVY),
    (2.1,  1.3, 1.9, 1.4, "C: Correlate",
     "Same-source · process-tree\nlineage refs · host/acct guard",
     LTEAL, TEAL),
    (4.3,  1.3, 2.0, 1.4, "V: Verify",
     "3 original roots · availability\nidentity · causal fields · cap<=100",
     LGREEN, GREEN),
    (6.65, 1.3, 2.0, 1.4, "Fallback",
     "missing_family only:\nauth + net + endpoint root",
     LAMBER, AMBER),
    (9.0,  1.3, 1.6, 1.4, "P: Prioritize",
     "Source-depth score\n+ accepted token count",
     LTEAL, TEAL),
    (10.9, 1.3, 1.0, 1.4, "OUTPUT",
     "Ranked groups\ntop-20 retrieval",
     LNAVY, NAVY),
]

def draw_node(ax, x, y, w, h, title, subtitle, face, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.06,rounding_size=0.1",
                                facecolor=face, edgecolor=edge, linewidth=1.5))
    ax.text(x + w/2, y + h*0.68, title, ha="center", va="center",
            fontsize=9, weight="bold", color=edge)
    ax.text(x + w/2, y + h*0.28, subtitle, ha="center", va="center",
            fontsize=7.4, color=DGRAY, linespacing=1.35)

for n in nodes:
    draw_node(ax, *n)

arrow_x = [1.70, 4.00, 6.30, 8.65, 10.60]
for xp in arrow_x:
    ax.annotate("", xy=(xp + 0.42, 2.0), xytext=(xp, 2.0),
                arrowprops=dict(arrowstyle="-|>", color=DGRAY, lw=1.4))

ax.annotate("", xy=(5.3, 1.3), xytext=(5.3, 0.65),
            arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.2))
ax.add_patch(FancyBboxPatch((4.1, 0.1), 2.4, 0.55,
                            boxstyle="round,pad=0.04,rounding_size=0.06",
                            facecolor="#FFEBEE", edgecolor=RED, linewidth=1.1))
ax.text(5.3, 0.375, "Reject / abstain -- retain prior partition", ha="center",
        va="center", fontsize=7.5, color=RED)
ax.text(5.3, 1.3, "fail", ha="center", va="bottom", fontsize=7, color=RED)
ax.text(6.4, 2.6, "missing_family", ha="center", fontsize=7.2, color=AMBER,
        style="italic")

ax.set_title("Evidence-Aware C/V/P Pipeline -- Frozen Implementation",
             fontsize=11, weight="bold", color=NAVY, pad=8, x=0.5, y=0.98)

fig.tight_layout(pad=0.2)
fig.savefig(FIG / "pipeline_overview.pdf", bbox_inches="tight")
plt.close(fig)
print("  pipeline_overview.pdf done")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Development trajectory
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.axis("off"); fig.patch.set_facecolor(WHITE)
ax.set_xlim(0, 10); ax.set_ylim(0, 3)

stages = [
    (0.3, "Training\n8 queues\nMethod dev.", LNAVY, NAVY),
    (2.3, "Development\n10 queues, 200 opps\n169/200 R@20, 0 FP", LTEAL, TEAL),
    (4.3, "Gate 170/200\nMISSED by 1\nDocumented before holdout", LAMBER, AMBER),
    (6.3, "Authorization\nUnchanged candidate\nproceeds to holdout", LAMBER, AMBER),
    (8.3, "HOLDOUT\n15 queues, 300 opps\n260/300 R@20, 0 FP", LGREEN, GREEN),
]

for i, (x0, lbl, face, edge) in enumerate(stages):
    ax.add_patch(FancyBboxPatch((x0, 0.5), 1.75, 2.0,
                                boxstyle="round,pad=0.06,rounding_size=0.1",
                                facecolor=face, edgecolor=edge, linewidth=1.6))
    ax.text(x0 + 0.875, 1.5, lbl, ha="center", va="center",
            fontsize=7.9, color=DGRAY, linespacing=1.4)
    if i < len(stages) - 1:
        ax.annotate("", xy=(x0 + 1.75 + 0.5, 1.5), xytext=(x0 + 1.75, 1.5),
                    arrowprops=dict(arrowstyle="-|>", color=DGRAY, lw=1.3))

ax.add_patch(FancyBboxPatch((8.3, 0.0), 1.75, 0.45,
                            boxstyle="round,pad=0.04,rounding_size=0.06",
                            facecolor=LGREEN, edgecolor=GREEN, linewidth=0.9,
                            linestyle="dashed"))
ax.text(9.175, 0.225, "SHA-256 sealed\nbefore truth open",
        ha="center", va="center", fontsize=7, color=GREEN)

ax.set_title("Experimental Order: Training -> Development -> Gate Miss -> Holdout",
             fontsize=10.5, weight="bold", color=NAVY, pad=6)
ax.text(5.0, -0.1,
        "Protocol adjustment (gate miss) was documented before the holdout was created and opened.",
        ha="center", fontsize=7.5, color=DGRAY)

fig.tight_layout(pad=0.2)
fig.savefig(FIG / "dev_trajectory.pdf", bbox_inches="tight")
plt.close(fig)
print("  dev_trajectory.pdf done")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Per-queue recall delta bar chart
# ═══════════════════════════════════════════════════════════════════════════════
delta_csv = P / "figure_data" / "queue_metric_deltas.csv"
rows = list(csv.DictReader(delta_csv.open()))
qids   = [f"Q{i+1:02d}" for i in range(len(rows))]
recall = [int(r["Recall@20_candidate_minus_baseline"])      for r in rows]
recov  = [int(r["Recoverability_candidate_minus_baseline"]) for r in rows]
p10    = [int(r["P@10_candidate_minus_baseline"])            for r in rows]

x = np.arange(len(qids)); w = 0.26
fig, ax = plt.subplots(figsize=(11, 4.0))
ax.set_facecolor(LGRAY); fig.patch.set_facecolor(WHITE)

ax.bar(x - w, recall, w, label="Recall@20 delta",     color=NAVY,  zorder=3, edgecolor=WHITE, lw=0.5)
ax.bar(x,     recov,  w, label="Recoverability delta", color=TEAL,  zorder=3, edgecolor=WHITE, lw=0.5)
ax.bar(x + w, p10,   w, label="P@10 delta",           color=AMBER, zorder=3, edgecolor=WHITE, lw=0.5)

ax.axhline(0, color=DGRAY, lw=0.9, zorder=4)
ax.set_xticks(x); ax.set_xticklabels(qids, fontsize=8.5)
ax.set_ylabel("Endpoint fallback minus baseline (integer delta)", fontsize=9)
ax.yaxis.grid(True, alpha=0.3, color=MGRAY, zorder=0)
ax.set_axisbelow(True)
ax.spines["left"].set_color(MGRAY); ax.spines["bottom"].set_color(MGRAY)
ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
ax.set_title("Per-Queue Metric Deltas: Endpoint Fallback minus Frozen Baseline",
             fontsize=11, weight="bold", color=NAVY, pad=10)
ax.text(0.5, -0.14,
        "Totals: Recall@20 +10 | Recoverability +18 | P@10 +6  |  "
        "Positive = fallback gain, Negative = fallback loss, Zero = no change",
        ha="center", fontsize=7.8, color=DGRAY, transform=ax.transAxes)

fig.tight_layout()
fig.savefig(FIG / "queue_delta_bars.pdf", bbox_inches="tight")
plt.close(fig)
print("  queue_delta_bars.pdf done")

print("All improved figures generated.")
