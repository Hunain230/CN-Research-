"""Rebuild reader-scale vector diagrams used by the Springer manuscript."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parents[1] / "figures"
OUT.mkdir(exist_ok=True)
NAVY="#172D4B"; BLUE="#EAF2F9"; GREEN="#E7F3EE"; TEAL="#16695E"
AMBER="#FFF1DB"; ORANGE="#A85C17"; LAV="#F0EAF8"; GREY="#536476"

def canvas(h=5.2):
    fig, ax=plt.subplots(figsize=(11.6,h), facecolor="white")
    ax.set_xlim(0,12); ax.set_ylim(0,7); ax.axis("off")
    return fig,ax

def box(ax,x,y,w,h,title,body="",fc=BLUE,edge=NAVY):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.13,rounding_size=.13",lw=1.35,edgecolor=edge,facecolor=fc))
    ax.text(x+.18,y+h-.32,title,va="top",ha="left",size=12.4,weight="bold",color=edge)
    if body: ax.text(x+.18,y+h-.75,body,va="top",ha="left",size=10.3,linespacing=1.4,color=NAVY)

def arrow(ax,x1,y1,x2,y2,label="",color=GREY):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=14,lw=1.55,color=color,connectionstyle="arc3"))
    if label: ax.text((x1+x2)/2,(y1+y2)/2+.12,label,size=9,ha="center",va="bottom",color=GREY)

def header(ax,name,sub):
    ax.text(.18,6.72,name,size=17.5,weight="bold",color=NAVY,va="top")
    ax.text(.18,6.28,sub,size=10.5,color=GREY,va="top")
    ax.plot([.18,11.82],[6.02,6.02],color="#B8C7D4",lw=1)

def save(fig,name):
    fig.savefig(OUT/name,bbox_inches="tight",pad_inches=.08)
    plt.close(fig)

# Main pipeline: three large columns and a second row of evidence/safety outcomes.
fig,ax=canvas(5.5); header(ax,"Evidence-gated C/V/P execution","The frozen predictor is deterministic; evaluator truth is held outside the receiver boundary")
box(ax,.35,3.36,3.25,2.03,"01  CORRELATE","Visible alerts at T=100\nSame-source and process-tree\nfragments; candidate tokens",BLUE)
box(ax,4.38,3.36,3.25,2.03,"02  VERIFY","Original roots and arrival time\nIdentity and causal fields\nGuarded endpoint fallback",GREEN,TEAL)
box(ax,8.42,3.36,3.25,2.03,"03  PRIORITIZE","Accepted unions form groups\nSource score + union bonus\nSorted top-20 analyst queue",LAV)
arrow(ax,3.62,4.35,4.34,4.35); arrow(ax,7.66,4.35,8.38,4.35)
box(ax,.55,.65,3.00,1.67,"INPUT BOUNDARY","Receiver-visible alerts, claims,\norigins and arrival times",fc="#F3F6F9")
box(ax,4.55,.65,2.88,1.67,"ABSTAIN / REJECT","No new union if a required\ncheck fails; record reason",AMBER,ORANGE)
box(ax,8.52,.65,3.02,1.67,"PRIVATE EVALUATOR","Incident truth and ranks\nscore sealed predictions",fc="#F3F6F9")
arrow(ax,2.05,2.35,2.05,3.30); arrow(ax,5.8,3.30,5.8,2.35); arrow(ax,10.0,3.30,10.0,2.35)
save(fig,"architecture.pdf")

fig,ax=canvas(5.2); header(ax,"Verifier decision workflow","A rejected token never becomes a union merely because a group is plausible")
box(ax,.42,3.52,3.15,1.85,"BASE: 3 CLAIMS","Process + auth + network\nThree distinct original roots",BLUE)
box(ax,4.42,3.52,3.15,1.85,"FALLBACK RULE","Only if process claim missing\nAuth + network + endpoint\nThree roots; no conflict",GREEN,TEAL)
box(ax,8.42,3.52,3.15,1.85,"COMMON GATES","Available by cutoff; same IDs\nTime and causal fields agree\nHost/account and size cap",LAV)
arrow(ax,3.61,4.42,4.38,4.42,"if process missing"); arrow(ax,7.61,4.42,8.38,4.42)
ax.plot([2.7,2.7,10.0],[5.39,5.62,5.62],color=GREY,lw=1.35)
arrow(ax,10.0,5.62,10.0,5.41,"3 claims present")
box(ax,1.05,.72,4.5,1.62,"ACCEPTED TOKEN","If components differ and guards pass:\nunion once; preserve trace",GREEN,TEAL)
box(ax,6.5,.72,4.5,1.62,"INSUFFICIENT / CONFLICTING","Keep partition unchanged; log exact\nreason and abstention",AMBER,ORANGE)
arrow(ax,9.3,3.47,4.48,2.42); arrow(ax,10.15,3.47,9.45,2.42)
save(fig,"verification_methodology.pdf")

fig,ax=canvas(5.15); header(ax,"Bounded agent contracts","Software roles and local-model feasibility; not the measured holdout pipeline")
box(ax,.33,3.55,3.28,1.75,"C   CORRELATION","Pair: LINK / NO_LINK / UNSURE\nCited support + contradiction",BLUE)
box(ax,4.38,3.55,3.28,1.75,"P   PRIORITIZATION","Relative score for a group\nRationale + evidence IDs",LAV)
box(ax,8.43,3.55,3.28,1.75,"V   VERIFICATION","PASS / REVISE / REVIEW\nSupport check on same snapshot",GREEN,TEAL)
arrow(ax,3.65,4.44,4.34,4.44); arrow(ax,7.70,4.44,8.39,4.44)
box(ax,.45,.67,3.08,1.63,"REQUEST GATE","Approved fields; org and pair scope;\nfixed evidence/token budgets",fc="#F3F6F9")
box(ax,4.5,.67,3.00,1.63,"COMPONENT BUILDER","Join validated LINK edges\nCap size; stable order",fc="#F3F6F9")
box(ax,8.53,.67,3.00,1.63,"CONTROLLED REVIEW","One revision; retain trace\nUnresolved -> REVIEW",AMBER,ORANGE)
arrow(ax,2.0,2.34,2.0,3.5); arrow(ax,6.0,3.51,6.0,2.34); arrow(ax,10.0,3.51,10.0,2.34)
save(fig,"agent_contracts.pdf")

fig,ax=canvas(5.0); header(ax,"Research evidence tracks","Only a matched comparison on the same population permits a causal contrast")
box(ax,.35,3.15,3.3,2.13,"A  AGENT FEASIBILITY","Offline C/P/V contracts and\nlocal Qwen sample\nNo full-scale LLM advantage",BLUE)
box(ax,4.36,3.15,3.3,2.13,"B  GUIDE REFERENCE","499 queues; statistical v2+v7\n49.82% retrospective R@20\nPrior label access",LAV)
box(ax,8.37,3.15,3.3,2.13,"C  SYNTHETIC HOLDOUT","15 paired queues; frozen C/V/P\n83.33% -> 86.67% R@20\nSimulator-defined truth",GREEN,TEAL)
box(ax,1.58,.65,8.85,1.25,"EXTERNAL VALIDATION STILL OPEN","GUIDE lacks original roots, derivation and evidence-arrival time for the frozen verifier; no real-world score exists.",AMBER,ORANGE)
arrow(ax,9.95,3.10,9.95,2.0)
save(fig,"study_tracks.pdf")

fig,ax=canvas(4.8); header(ax,"Frozen experiment and leakage boundary","A documented gate adjustment preceded the unchanged candidate's single fresh-holdout evaluation")
box(ax,.4,3.26,3.22,1.91,"DEVELOPMENT","8 train + 10 dev queues\nCandidate: 169/200 R@20\nMissed 170/200 gate",BLUE)
box(ax,4.39,3.26,3.22,1.91,"PROTOCOL DECISION","Proceed unchanged, documented\nbefore holdout generation\nFreeze source and config",AMBER,ORANGE)
box(ax,8.39,3.26,3.22,1.91,"FRESH HOLDOUT","Seed 31103; variant 2\n15 queues, 5,018 alerts\nBoth arms same inputs",GREEN,TEAL)
arrow(ax,3.65,4.18,4.35,4.18); arrow(ax,7.65,4.18,8.35,4.18)
box(ax,3.07,.66,5.84,1.55,"SEALED EVALUATION","Hash predictions before truth; one unchanged evaluator pass.",fc="#F3F6F9")
arrow(ax,10,3.20,8.55,2.25)
save(fig,"experimental_protocol.pdf")
print("Wrote 5 vector diagrams to",OUT)
