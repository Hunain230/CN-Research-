"""Broad multi-route correlation retrieval with a lightweight pair scorer."""
import argparse,csv,json,pickle,time
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from scipy import sparse
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import normalize
from sklearn.linear_model import LogisticRegression
from .guide_rerun_v2 import ROOT,PRIVATE,OUT,FIELDS,load,key,dump,read,bootstrap,features
from .phase2 import sha256_file
KS=[20,50,100,200]
THRESHOLDS=[.1,.25,.5,.75,.9]

def truth(orgs,alerts):
 result={}
 with (ROOT/'data/derived/preprocessing/evaluator/incident_membership.csv').open(encoding='utf-8',newline='') as f:
  for r in csv.DictReader(f):
   if r['OrgId'] not in orgs or r['mapping_status']!='unambiguous':continue
   ak=key(r['OrgId'],r['AlertId'])
   if ak in alerts:result[ak]=key(r['OrgId'],r['IncidentId'])
 return result

def pair_features(a,b):
 vals=[]
 for field in FIELDS:
  aa=set(a['fields'][field]);bb=set(b['fields'][field]);vals.append(len(aa&bb)/len(aa|bb) if aa|bb else 0.)
 return vals

def edges(docs,vec,ks=KS):
 # All routes operate inside a single organization, with no membership labels.
 keys=sorted(docs);n=len(keys);X=vec.transform([features(docs[k]) for k in keys]);names=vec.get_feature_names_out()
 channels=[]
 for fields in [FIELDS,['MitreTechniques','DetectorId'],['Category','EntityType','EvidenceRole']]:
  mask=np.array([x.split('=',1)[0] in fields for x in names]);channels.append(normalize(X.multiply(mask).tocsr()))
 rankedge={k:[] for k in ks};rngrank=np.argsort(np.array([key('candidate-tie',a) for a in keys]));priority=np.empty(n,int);priority[rngrank]=np.arange(n)
 for start in range(0,n,64):
  block=[(z[start:start+64]@z.T).toarray() for z in channels]
  for b in range(min(64,n-start)):
   i=start+b
   for scores in block:
    scores[b,i]=-1
    # Deterministic tie ordering; never add zero-overlap neighbors.
    possible=np.flatnonzero(scores[b]>0)
    order=possible[np.lexsort((priority[possible],-scores[b,possible]))][:max(ks)]
    for k in ks:
     jj=order[:k];lo=np.minimum(i,jj);hi=np.maximum(i,jj);rankedge[k].extend((lo*n+hi).tolist())
 return keys,{k:np.unique(np.array(v,dtype=np.int64)) for k,v in rankedge.items()}

def evaluate_edges(keys,e,gold,model,docs):
 n=len(keys);a=e//n;b=e%n;y=np.array([gold[keys[i]]==gold[keys[j]] for i,j in zip(a,b)])
 pf=np.array([pair_features(docs[keys[i]],docs[keys[j]]) for i,j in zip(a,b)],dtype=np.float32).reshape(-1,5)
 proba=model.predict_proba(pf)[:,1] if len(pf) else np.array([])
 groups=Counter(gold[k] for k in keys);positive=sum(v*(v-1)//2 for v in groups.values())
 return y,proba,positive,n*(n-1)//2

def fit():
 data=load();alerts=data['alerts'];split=data['split'];train={o for o,p in split.items() if p=='train'};valid={o for o,p in split.items() if p=='validation'}
 g=truth(train|valid,alerts);by=defaultdict(list)
 for k,a in alerts.items():by[a['org']].append(k)
 for o in by:by[o]=sorted(by[o])[:500]
 rng=np.random.default_rng(0);xx=[];yy=[]
 for o in sorted(train):
  groups=defaultdict(list)
  for k in by[o]:groups[g[k]].append(k)
  for members in groups.values():
   if len(members)<2:continue
   for _ in range(min(10,len(members))):
    i,j=rng.choice(len(members),2,replace=False);xx.append(pair_features(alerts[members[i]],alerts[members[j]]));yy.append(1)
  for _ in range(min(200,len(by[o])*2)):
   if len(by[o])<2:continue
   i,j=rng.choice(len(by[o]),2,replace=False);a,b=by[o][i],by[o][j]
   if g[a]!=g[b]:xx.append(pair_features(alerts[a],alerts[b]));yy.append(0)
 model=LogisticRegression(class_weight='balanced',max_iter=300,random_state=0).fit(xx,yy)
 vec=DictVectorizer(dtype=np.float32);vec.fit([features(a) for a in alerts.values() if a['org'] in train])
 stats={k:{'candidate_recall':[],'coverage':[],'n':0,'tp':0,'positive':0,'confusion':{t:[0,0,0] for t in THRESHOLDS}} for k in KS}
 for z,o in enumerate(sorted(valid),1):
  docs={k:alerts[k] for k in by[o]};keys,ee=edges(docs,vec)
  for k,e in ee.items():
   y,p,pos,total=evaluate_edges(keys,e,g,model,docs);s=stats[k];s['n']+=len(e);s['tp']+=int(y.sum());s['positive']+=pos
   if pos:s['candidate_recall'].append(float(y.sum()/pos))
   s['coverage'].append(len(e)/total if total else 0.)
   for t in THRESHOLDS:
    link=p>=t;tp=int((y&link).sum());fp=int((~y&link).sum());s['confusion'][t]=[a+b for a,b in zip(s['confusion'][t],[tp,fp,pos-tp])]
  print('correlation validation',z,'/',len(valid),flush=True)
 report={}
 for k,s in stats.items():
  report[str(k)]={'macro_candidate_recall':bootstrap(s['candidate_recall']),'micro_candidate_recall':s['tp']/s['positive'] if s['positive'] else None,'mean_pair_coverage':float(np.mean(s['coverage'])),'candidate_pairs':s['n'],'thresholds':{str(t):{'tp':v[0],'fp':v[1],'fn':v[2],'f1':2*v[0]/(2*v[0]+v[1]+v[2]) if sum(v) else 0.} for t,v in s['confusion'].items()}}
 selected=next((k for k in KS if report[str(k)]['micro_candidate_recall']>=.95),200)
 threshold=max(THRESHOLDS,key=lambda t:report[str(selected)]['thresholds'][str(t)]['f1'])
 dump(OUT/'correlation_validation.json',{'routes':'union top-K per route: five fields; ATT&CK/detector; category/entity/role','curve':report,'selected_neighbors_per_route':selected,'threshold':threshold,'target_met':report[str(selected)]['micro_candidate_recall']>=.95,'sample_max_alerts_per_org':500,'zero_positive_orgs_excluded_from_macro_recall':len(valid)-len(stats[selected]['candidate_recall'])})
 with (PRIVATE/'correlation_model.pkl').open('wb') as f:pickle.dump((model,vec),f)
 dump(OUT/'correlation_freeze.json',{'K':selected,'threshold':threshold,'sample_max_alerts_per_org':500,'code_sha256':sha256_file(Path(__file__)),'split_sha256':sha256_file(PRIVATE/'split.json'),'model_sha256':sha256_file(PRIVATE/'correlation_model.pkl')})

def predict():
 freeze=read(OUT/'correlation_freeze.json');assert freeze['code_sha256']==sha256_file(Path(__file__))
 with (PRIVATE/'correlation_model.pkl').open('rb') as f:model,vec=pickle.load(f)
 data=load();alerts=data['alerts'];split=data['split'];by=defaultdict(dict)
 for k,a in alerts.items():
  if split[a['org']]=='holdout':by[a['org']][k]=a
 hashes={}
 for no,(o,docs) in enumerate(sorted(by.items()),1):
  docs={k:docs[k] for k in sorted(docs)[:500]}
  keys,ee=edges(docs,vec,[freeze['K']]);e=ee[freeze['K']];n=len(keys);pf=np.array([pair_features(docs[keys[i]],docs[keys[j]]) for i,j in zip(e//n,e%n)],dtype=np.float32).reshape(-1,5);p=model.predict_proba(pf)[:,1] if len(pf) else np.array([])
  path=PRIVATE/'correlation_predictions'/f'{key(o)}.npz';path.parent.mkdir(exist_ok=True);np.savez_compressed(path,keys=np.array(keys),edges=e,probability=p);hashes[key(o)]=sha256_file(path);print('correlation predictions',no,'/',len(by),flush=True)
 dump(OUT/'correlation_prediction_freeze.json',{'hashes':hashes,'holdout_labels_read':False,'freeze_sha256':sha256_file(OUT/'correlation_freeze.json')})

def evaluate():
 if (OUT/'correlation_holdout.json').exists():raise FileExistsError('already evaluated')
 freeze=read(OUT/'correlation_freeze.json');manifest=read(OUT/'correlation_prediction_freeze.json');assert manifest['freeze_sha256']==sha256_file(OUT/'correlation_freeze.json')
 data=load();orgs={o for o,p in data['split'].items() if p=='holdout'};gold=truth(orgs,data['alerts']);results=[]
 for o in sorted(orgs):
  path=PRIVATE/'correlation_predictions'/f'{key(o)}.npz';assert sha256_file(path)==manifest['hashes'][key(o)]
  a=np.load(path);keys=a['keys'].tolist();n=len(keys);e=a['edges'];y=np.array([gold[keys[i]]==gold[keys[j]] for i,j in zip(e//n,e%n)]);link=a['probability']>=freeze['threshold'];sizes=Counter(gold[k] for k in keys);pos=sum(v*(v-1)//2 for v in sizes.values());tp=int((y&link).sum());fp=int((~y&link).sum());fn=pos-tp
  results.append({'tp':tp,'fp':fp,'fn':fn,'positives':pos,'candidate_positives':int(y.sum()),'pairs':n*(n-1)//2,'candidates':len(e),'precision':tp/(tp+fp) if tp+fp else 0.,'recall':tp/pos if pos else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.})
 sums={k:sum(r[k] for r in results) for k in ['tp','fp','fn','positives','candidate_positives','pairs','candidates']};s=sums;s.update({'precision':s['tp']/(s['tp']+s['fp']) if s['tp']+s['fp'] else 0,'recall':s['tp']/s['positives'],'f1':2*s['tp']/(2*s['tp']+s['fp']+s['fn']),'candidate_recall':s['candidate_positives']/s['positives'],'candidate_coverage':s['candidates']/s['pairs']})
 dump(OUT/'correlation_holdout.json',{'classification':'exploratory_ambiguity_excluded_sampled_500_alerts_per_org','organizations':len(results),'micro':s,'macro':{k:bootstrap([r[k] for r in results if r[k] is not None]) for k in ['precision','recall','f1']},'zero_positive_orgs':sum(r['recall'] is None for r in results),'military_certification':False})
 print(json.dumps(s,indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['fit','predict','evaluate']);a=ap.parse_args();globals()[a.stage]()
