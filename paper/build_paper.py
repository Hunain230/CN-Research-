"""Build editable research figures and the manuscript from audited repository outputs.
Never writes into experiments/ or data/.
"""
from pathlib import Path
import csv, json, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

P=Path(__file__).resolve().parent; R=P.parent
for d in ('sections','figures','figure_source','figure_data','tables','audit','submission','supplementary'): (P/d).mkdir(exist_ok=True)
source=R/'experiments/PHASE33_FROZEN_GENERALIZATION'
s=json.loads((source/'HOLDOUT_SUMMARY.json').read_text())
seal=json.loads((source/'artifacts/pre_evaluation_seal.json').read_text())
for kind in ('baseline','candidate'):
 f=source/f'artifacts/{kind}_predictions.jsonl'
 assert hashlib.sha256(f.read_bytes()).hexdigest()==seal['predictions_sha256'][kind]
 assert hashlib.sha256(f.read_bytes()).hexdigest()==s[kind]['prediction_sha256']
assert s['candidate']['recall20_count']==260 and s['baseline']['recall20_count']==250
assert s['candidate']['eligible_alerts']==s['baseline']['eligible_alerts']==5018
rows=list(csv.DictReader((source/'HOLDOUT_RESULTS.csv').open()))
assert len(rows)==15
for field,key in [('baseline_recall','recall20_count'),('candidate_recall','recall20_count'),('baseline_recoverable','recoverable'),('candidate_recoverable','recoverable'),('baseline_p10','p10_count'),('candidate_p10','p10_count')]:
 arm=field.split('_')[0]; assert sum(int(r[field]) for r in rows)==s[arm][key]

with (P/'figure_data/holdout_metrics.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['metric','baseline_n','candidate_n','denominator','artifact'])
 for m,k,d in [('Incident Recall@20','recall20_count',300),('Group recoverability','recoverable',300),('P@10','p10_count',150)]: w.writerow([m,s['baseline'][k],s['candidate'][k],d,'experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json'])
with (P/'figure_data/holdout_safety.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['arm','pair_true','false_grouped_pairs','mixed_groups','queues_with_no_false_pairs_or_mixed_groups'])
 for arm in ('baseline','candidate'):w.writerow([arm,s[arm]['pair_tp'],s[arm]['false_grouped_pairs'],s[arm]['mixed_predicted_groups'],sum(int(r[arm+'_false_pairs'])==int(r[arm+'_mixed_groups'])==0 for r in rows)])
(P/'figure_data/holdout_queue_metrics.csv').write_bytes((source/'HOLDOUT_RESULTS.csv').read_bytes())

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
def flow(name,boxes,edges,caption=None,wide=11):
 fig,ax=plt.subplots(figsize=(wide,3.9)); ax.set_xlim(0,wide);ax.set_ylim(0,4);ax.axis('off')
 for ident,x,y,w,h,label,shade in boxes:
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04,rounding_size=0.07',fc=shade,ec='#283b52',lw=1))
  ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9,wrap=True)
 lookup={b[0]:b for b in boxes}
 for a,b,l in edges:
  aa=lookup[a];bb=lookup[b];x1=aa[1]+aa[3]/2;y1=aa[2]+aa[4]/2;x2=bb[1]+bb[3]/2;y2=bb[2]+bb[4]/2
  dx=x2-x1;dy=y2-y1
  if abs(dx)>abs(dy): x1+=aa[3]/2*(1 if dx>0 else -1);x2-=bb[3]/2*(1 if dx>0 else -1)
  else:y1+=aa[4]/2*(1 if dy>0 else -1);y2-=bb[4]/2*(1 if dy>0 else -1)
  ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=10,lw=1,color='#364c60'))
  if l:ax.text((x1+x2)/2,(y1+y2)/2+.08,l,ha='center',va='bottom',fontsize=7.5,bbox={'fc':'white','ec':'none','pad':1})
 if caption:ax.text(wide/2,.13,caption,ha='center',fontsize=8,color='#44566a')
 fig.tight_layout(pad=.25);fig.savefig(P/f'figures/{name}.pdf',bbox_inches='tight');plt.close(fig)

L='#e9f2f5';B='#f3f3f3';A='#e6f0e7';W='#faeedf'
flow('architecture',[
 ('input',.1,2,1.65,.8,'Alerts + original\nobservations',L),('c',2.15,2,1.65,.8,'C: correlate\nsource, tree, refs',L),('v',4.2,2,1.65,.8,'V: verify\nclaim bundles',A),('g',6.25,2,1.65,.8,'Safe group\npartition',A),('p',8.3,2,1.35,.8,'P: prioritize\ngroups',L),('out',9.95,2,1,.8,'Ranked\noutput',L),('gates',3.85,.55,3.05,.75,'Provenance, identity, availability,\n3 roots, consistency, contradictions',B),('no',7.25,.55,2.1,.75,'Reject or abstain:\nno new union',W)], [('input','c',''),('c','v','candidate tokens'),('v','g','accepted'),('g','p',''),('p','out',''),('gates','v','checks'),('v','no','failed / missing')])
flow('evidence_provenance',[
 ('ep',.2,2.45,2.2,.7,'Original endpoint observation\nroot E, available at t=80',A),('id',.2,1.35,2.2,.7,'Original identity claim\nroot I, available at t=85',A),('net',.2,.25,2.2,.7,'Original network claim\nroot N, available at t=95',A),('copy',3.55,1.3,2.15,.75,'Derived copy of I\nsame root I',W),('join',7,1.4,2.65,.9,'Pair relation at cutoff 100\nE, I, N distinct; fields agree',L),('late',3.55,.25,2.15,.75,'Delayed claim at t=105\nnot visible at cutoff',W)], [('ep','join','endpoint fields'),('id','copy','derived from'),('id','join','original'),('net','join','original'),('copy','join','not extra root'),('late','join','excluded')],wide=10.2)
flow('verification_methodology',[
 ('token',.1,2.85,1.5,.7,'Candidate\nrelationship',L),('visible',2,2.85,1.7,.7,'Visible endpoints\nand claims by 100',L),('full',4.15,2.85,2.1,.7,'Original process + auth\n+ network, 3 roots?',A),('fall',4.15,1.45,2.1,.7,'Only missing process?\nEndpoint E + auth I + net N',W),('check',6.85,2.25,2.05,.9,'IDs, host/account,\ntime, causal fields,\ncap + component context',A),('accept',9.45,2.4,1.1,.7,'Union',A),('stop',8.15,.55,2.25,.65,'Reject / abstain\nretain prior partition',W)], [('token','visible',''),('visible','full',''),('full','check','yes'),('full','fall','missing family'),('fall','check','exact gate'),('fall','stop','otherwise'),('check','accept','pass'),('check','stop','fail')])
flow('reconstruction_prioritization',[
 ('frag',.1,2.25,1.8,.85,'Initial same-source /\nprocess-tree groups',L),('union',2.35,2.25,1.9,.85,'Verified token unions\ncap and context guard',A),('groups',4.75,2.25,1.6,.85,'Final groups\npartition alerts',A),('score',6.8,2.25,1.65,.85,'Source-depth score\n+ accepted union count',L),('rank',8.9,2.25,1.75,.85,'Sorted groups\ntop-20 retrieval',L),('recover',4.35,.45,2.4,.8,'Recoverability:\nqualifying group anywhere',B),('recall',8.25,.45,2.35,.8,'Recall@20:\nqualifying group in top 20',B)], [('frag','union',''),('union','groups',''),('groups','score',''),('score','rank',''),('groups','recover','truth at evaluation'),('rank','recall','truth at evaluation')])
flow('experimental_protocol',[
 ('train',.1,2.5,1.5,.8,'8 training\nqueues',L),('dev',2,2.5,1.85,.8,'10 development queues\n169/200 candidate',L),('miss',4.2,2.5,2.25,.8,'Gate 170/200 missed\nby one incident',W),('amend',6.85,2.5,2.15,.8,'Documented decision:\nunchanged candidate',W),('hold',9.35,2.5,1.45,.8,'Fresh 15-queue\nholdout',A),('seal',6.85,.65,2.1,.75,'Predictions and decisions\nSHA-256 sealed',A),('eval',9.35,.65,1.45,.75,'Private-truth\nevaluation once',A)], [('train','dev',''),('dev','miss',''),('miss','amend',''),('amend','hold',''),('hold','seal','predict'),('seal','eval','then open truth')])

data=list(csv.DictReader((P/'figure_data/holdout_metrics.csv').open()))
fig,axs=plt.subplots(1,3,figsize=(10.8,3.3),sharey=True)
for ax,r in zip(axs,data):
 vals=[int(r['baseline_n'])/int(r['denominator'])*100,int(r['candidate_n'])/int(r['denominator'])*100]
 bars=ax.bar(['Baseline','Fallback'],vals,color=['#6d7d90','#397c85'],width=.58)
 for bar,n in zip(bars,(r['baseline_n'],r['candidate_n'])):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1.1,f'{n}/{r["denominator"]}\n{bar.get_height():.2f}%',ha='center',fontsize=8)
 ax.set_title(r['metric']);ax.set_ylim(0,108);ax.grid(axis='y',alpha=.2)
axs[0].set_ylabel('Percent of evaluator opportunities');fig.tight_layout();fig.savefig(P/'figures/phase33_results.pdf');plt.close(fig)
safe=list(csv.DictReader((P/'figure_data/holdout_safety.csv').open()))
fig,ax=plt.subplots(figsize=(8.2,2.4));ax.axis('off')
cells=[[r['arm'].capitalize(),f"{int(r['pair_true']):,}/{int(r['pair_true'])+int(r['false_grouped_pairs']):,} (100%)",r['false_grouped_pairs'],r['mixed_groups'],f"{r['queues_with_no_false_pairs_or_mixed_groups']}/15"] for r in safe]
t=ax.table(cellText=cells,colLabels=['Method','True / grouped pairs','False pairs','Mixed groups','Safe queues'],loc='center',cellLoc='center');t.auto_set_font_size(False);t.set_fontsize(10);t.scale(1,1.9)
for (i,j),c in t.get_celld().items():c.set_edgecolor('#758495');c.set_facecolor('#e9f2f5' if i==0 else 'white')
fig.tight_layout();fig.savefig(P/'figures/safety_results.pdf',bbox_inches='tight');plt.close(fig)
import runpy
runpy.run_path(str(P/'figure_source/expanded_figures.py'),run_name='__main__')
print('Verified holdout artifacts and generated ten vector figures.')
