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

# Layered methodology overview inspired by the user's reference layout. This
# depicts actual sequential C -> V -> P execution, without LLM/agent internals.
fig, ax = plt.subplots(figsize=(7.1, 8.0))
ax.set_xlim(0, 10); ax.set_ylim(0, 14); ax.axis("off")
def panel(x,y,w,h,fill,edge="#40515e",lw=.9,rounding=.09):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=.04,rounding_size={rounding}",fc=fill,ec=edge,lw=lw))
def lbl(x,y,t,size=8.5,weight="normal",color="#172a33",ha="center"):
    ax.text(x,y,t,ha=ha,va="center",fontsize=size,weight=weight,color=color,linespacing=1.22)
def arrow(p,q,txt=None):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle="-|>",mutation_scale=10,lw=1.15,color="#344b56"))
    if txt: lbl((p[0]+q[0])/2,(p[1]+q[1])/2,txt,7.2,color="#405965")
cream="#fff4df"; pale="#eaf4f4"; mint="#e8f2e8"; neutral="#f3f5f6"

# Receiver and correlation are sequential: candidate claims cannot appear
# before availability filtering and the initial fragment partition.
panel(.45,.25,9.1,2.25,neutral)
lbl(5,2.16,"MODEL-VISIBLE QUEUE INPUT",9,weight="bold")
for x,t in [(1.85,"Alert records\nsource / event IDs"),(5,"Process · authentication\nnetwork-flow observations"),(8.15,"Evidence ledger\norigin / available time")]:
    panel(x-1.31,.79,2.62,.85,"white",lw=.75); lbl(x,1.22,t,8.2)
lbl(5,.5,"Receiver validates ledger and keeps records available by cutoff T=100",7.7)

panel(.45,2.85,9.1,1.75,pale)
lbl(1.45,4.28,"C  CORRELATE",9.5,weight="bold",ha="left")
for x,t in [(2.05,"Same-source / process-tree\ninitial fragments"),(5,"Visible lineage\nrelationships"),(7.95,"Candidate token bundles\n+ current partition")]:
    panel(x-1.36,3.12,2.72,.79,"white",lw=.75); lbl(x,3.52,t,8.1)
arrow((3.43,3.52),(3.62,3.52)); arrow((6.37,3.52),(6.57,3.52))
arrow((5,2.5),(5,2.84)); arrow((7.95,4.62),(7.95,5.15))

panel(.45,5.16,9.1,5.0,mint)
lbl(1.45,9.89,"V  VERIFY",9.5,weight="bold",ha="left")
panel(2.68,9.18,4.64,.49,"white",lw=.75)
lbl(5,9.43,"Accept only when every applicable gate passes",8.3)
arrow((7.95,5.15),(7.95,5.42))
arrow((7.95,5.42),(5,5.42))
arrow((5,5.42),(5,5.65))
panel(2.7,5.72,4.6,.54,"white",lw=.75)
lbl(5,5.99,"Candidate token + current incident fragments",8.2)
arrow((5,6.28),(5,6.48))
for x,title,body,shade in [
    (2.78,"Complete bundle","Original process + identity + network\nthree distinct upstream roots",pale),
    (7.22,"Only missing family","Original identity + network claims\noriginal endpoint supplies third root",cream)]:
    panel(x-2.01,6.58,4.02,1.0,shade,lw=.8)
    lbl(x,7.32,title,8.4,weight="bold")
    lbl(x,6.89,body,7.8)
arrow((4.7,6.28),(2.78,6.57)); arrow((5.3,6.28),(7.22,6.57))
lbl(5.05,7.74,"fallback only for reason: missing_family",7.0,color="#865b2e")
panel(1.1,8.06,7.8,.78,"white",lw=.75)
lbl(5,8.46,"Shared gates: provenance, availability, endpoint / causal-field agreement,",8.0)
lbl(5,8.20,"event timing, host/account overlap, and size cap",8.0)
arrow((2.78,7.59),(2.78,8.04)); arrow((7.22,7.59),(7.22,8.04))
arrow((5,8.86),(5,9.16))
panel(7.67,9.23,1.48,.67,cream,lw=.7)
lbl(8.41,9.57,"Reject / abstain\nno new union",7.4)
arrow((8.9,8.86),(8.41,9.21))

panel(.75,10.36,8.5,.59,"#d9ebdd")
lbl(5,10.66,"Accepted tokens unite current components; final incident groups",8.6,weight="bold")
arrow((5,9.68),(5,10.35))

panel(.45,11.12,9.1,1.4,cream)
lbl(1.5,12.23,"P  PRIORITIZE",9.5,weight="bold",ha="left")
panel(1.05,11.38,3.65,.56,"white",lw=.7)
panel(5.3,11.38,3.65,.56,"white",lw=.7)
lbl(2.88,11.66,"Score each completed group",8.4)
lbl(7.12,11.66,"Sort by score; stable tie-break",8.4)
arrow((4.74,11.66),(5.26,11.66))
arrow((5,10.97),(5,11.1))

panel(2.2,12.98,5.6,.70,"#deecf1")
lbl(5,13.33,"RANKED INCIDENT GROUPS FOR SOC ANALYST",9.0,weight="bold")
arrow((5,12.54),(5,12.95))
fig.tight_layout(pad=.05)
fig.savefig(P / "figures/methodology_overview.pdf",bbox_inches="tight")
plt.close(fig)
print("Generated layered methodology and detailed verification/provenance diagrams, plus two diagnostic charts.")
