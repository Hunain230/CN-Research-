"""Additional vector figures from the sealed synthetic holdout and frozen code.

Run through paper/build_paper.py. This module writes only under paper/.
"""
from pathlib import Path
import csv
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

P = Path(__file__).resolve().parents[1]
R = P.parent
Q = list(csv.DictReader((R / "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_RESULTS.csv").open()))
S = json.loads((R / "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json").read_text())
assert len(Q) == 15
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "pdf.fonttype": 42})

fields = [("Recall@20", "recall"), ("Recoverability", "recoverable"), ("P@10", "p10")]
delta = np.array([[int(q["candidate_" + col]) - int(q["baseline_" + col]) for _, col in fields] for q in Q])
assert list(delta.sum(axis=0)) == [10, 18, 6]
with (P / "figure_data/queue_metric_deltas.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["queue_id"] + [label + "_candidate_minus_baseline" for label, _ in fields] + ["original_artifact"])
    for q, vals in zip(Q, delta):
        w.writerow([q["queue_id"], *map(int, vals), "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_RESULTS.csv"])

fig, ax = plt.subplots(figsize=(6.6, 6.0))
im = ax.imshow(delta, cmap="BrBG", norm=TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3), aspect="auto")
ax.set_xticks(range(3), [x[0] for x in fields])
ax.set_yticks(range(15), [f"Queue {i+1:02d}" for i in range(15)])
ax.tick_params(length=0)
ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
ax.set_yticks(np.arange(-.5, 15, 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.5)
for i in range(15):
    for j in range(3):
        v = int(delta[i, j])
        ax.text(j, i, f"{v:+d}" if v else "0", ha="center", va="center", color="white" if abs(v) >= 2 else "#1e3031", weight="bold" if v else "normal")
ax.set_title("Per-queue change: endpoint fallback minus frozen baseline", pad=12)
ax.text(1, 15.2, "Column totals: +10 recalled  |  +18 recoverable  |  +6 P@10 credits", ha="center", va="top", fontsize=8)
fig.tight_layout(rect=[0, .045, 1, 1])
fig.savefig(P / "figures/queue_delta_heatmap.pdf", bbox_inches="tight")
plt.close(fig)

decomp = []
for arm in ("baseline", "candidate"):
    recalled = S[arm]["recall20_count"]
    recoverable = S[arm]["recoverable"]
    assert 0 <= recalled <= recoverable <= 300
    decomp.append([recalled, recoverable - recalled, 300 - recoverable])
with (P / "figure_data/retrieval_decomposition.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["arm", "recalled_top20", "recoverable_outside_top20", "not_recoverable", "denominator", "original_artifact"])
    for arm, row in zip(("baseline", "candidate"), decomp):
        w.writerow([arm, *row, 300, "experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json"])
fig, ax = plt.subplots(figsize=(6.6, 2.45))
colors = ["#397c85", "#b38b43", "#a6adb4"]
labels = ["Recalled in top 20", "Recoverable, outside top 20", "Not recoverable"]
for y, row in enumerate(decomp):
    x = 0
    for n, color in zip(row, colors):
        ax.barh(y, n, left=x, height=.52, color=color, edgecolor="white", linewidth=1)
        ax.text(x + n/2, y, str(n), va="center", ha="center", color="white" if color != "#a6adb4" else "#182431", weight="bold", fontsize=9)
        x += n
ax.set_yticks([0, 1], ["Baseline", "Endpoint fallback"])
ax.invert_yaxis()
ax.set_xlim(0, 300)
ax.set_xlabel("Expert top-20 incident opportunities across 15 queues (n = 300)")
ax.legend(labels, loc="upper center", bbox_to_anchor=(.5, -.37), ncol=3, frameon=False, fontsize=8)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
fig.savefig(P / "figures/retrieval_decomposition.pdf", bbox_inches="tight")
plt.close(fig)

# A source-faithful two-path decision diagram. The endpoint fallback is reachable
# only after the original verifier has reason-coded a missing-family failure.
fig, ax = plt.subplots(figsize=(6.7, 6.1))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
def box(x,y,w,h,label,face):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.08,rounding_size=.08",facecolor=face,edgecolor="#304a56",linewidth=.9))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=8.1,linespacing=1.18)
def arr(a,b,label=""):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=10,linewidth=1,color="#334955",connectionstyle="arc3"))
    if label: ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.08,label,ha="center",fontsize=7.2,bbox={"fc":"white","ec":"none","pad":.5})
blue="#e9f2f5"; green="#e7f1e7"; amber="#fcf0df"; gray="#f2f3f4"
box(3.2,9.0,3.6,.72,"Candidate relationship token\n+ receiver-visible observations",blue)
box(3.2,7.75,3.6,.73,"Validate ledger, endpoint identity\nand availability by cutoff T",blue)
box(.35,6.35,4.1,.85,"Complete original process + auth + network?\n3 distinct roots; no conflicting claims",green)
box(5.55,6.35,4.1,.85,"Missing-family reason only?\nNo contradictory or late claim",amber)
box(.35,4.95,4.1,.9,"Match events, host/account, causal IDs,\nevent-time guard, component cap",green)
box(5.55,4.95,4.1,.9,"Exactly original auth + network; 2 roots;\n2 original endpoints supply third root",amber)
box(5.55,3.55,4.1,.9,"Distinct source / observation IDs;\nall fields and current components agree",amber)
box(.35,2.20,4.1,.75,"Accept original-bundle union",green)
box(5.55,2.20,4.1,.75,"Accept endpoint-fallback union",green)
box(2.9,.65,4.2,.78,"Otherwise retain partition: reject or abstain\n(no new claim created by an earlier union)",gray)
arr((5,9),(5,8.58));arr((4.1,7.75),(2.4,7.2));arr((5.9,7.75),(7.6,7.2));
arr((2.4,6.35),(2.4,5.85));arr((7.6,6.35),(7.6,5.85))
arr((2.4,4.95),(2.4,2.95));arr((7.6,4.95),(7.6,4.45));arr((7.6,3.55),(7.6,2.95))
arr((4.45,6.72),(5.55,6.72),"missing family")
ax.text(5,1.73,"Any failed or unsupported gate",ha="center",va="center",fontsize=7.2,color="#394e5a")
ax.text(5,8.82,"visible only",ha="center",va="top",fontsize=7.2)
fig.tight_layout(pad=.05)
fig.savefig(P / "figures/verification_methodology.pdf",bbox_inches="tight")
plt.close(fig)

# Provenance / point-in-time schematic; example minutes only, not measurements.
fig, ax = plt.subplots(figsize=(6.7, 4.0))
ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off")
ax.text(.2,6.65,"Observation and lineage",weight="bold",fontsize=9)
ax.text(4.55,6.65,"Upstream root",weight="bold",fontsize=9)
ax.text(6.35,6.65,"Event time",weight="bold",fontsize=9)
ax.text(7.75,6.65,"Available",weight="bold",fontsize=9)
ax.text(9.25,6.65,"At cutoff",weight="bold",fontsize=8,ha="center")
records = [
 ("Original endpoint observation", "E", "60", "80", "eligible", green),
 ("Original identity claim", "I", "62", "85", "eligible", green),
 ("Derived copy of identity claim", "I (from identity)", "62", "90", "same root", amber),
 ("Original network-flow claim", "N", "64", "95", "eligible", green),
 ("Original conflicting observation", "C", "63", "88", "conflict", amber),
 ("Original late observation", "L", "60", "105", "excluded", gray),
]
for i,(name,root,event,avail,decision,face) in enumerate(records):
 y=5.75-.88*i
 ax.add_patch(FancyBboxPatch((.12,y-.30),9.75,.66,boxstyle="round,pad=.04,rounding_size=.05",facecolor=face,edgecolor="#aab8ba",linewidth=.6))
 ax.text(.28,y,name,va="center",fontsize=8)
 ax.text(4.58,y,root,va="center",fontsize=8)
 ax.text(6.72,y,event,va="center",ha="center",fontsize=8)
 ax.text(8.22,y,avail,va="center",ha="center",fontsize=8)
 ax.text(9.27,y,decision,va="center",ha="center",fontsize=7.8)
ax.annotate("derivation",xy=(4.05,4.0),xytext=(3.46,4.87),arrowprops={"arrowstyle":"->","color":"#345261"},fontsize=7,color="#345261")
ax.text(.2,.15,"Only E, I, and N form distinct eligible roots for the example relationship.",fontsize=8,color="#394e5a")
fig.tight_layout(pad=.1)
fig.savefig(P / "figures/evidence_provenance.pdf",bbox_inches="tight")
plt.close(fig)
print("Generated detailed verification/provenance diagrams and two holdout diagnostic charts.")
