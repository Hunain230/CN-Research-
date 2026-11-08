from __future__ import annotations
import itertools, math, random

def aggregate_by_organization(values):
    vals=[float(values[k]) for k in sorted(values)]
    if not vals:return {"n_organizations":0,"mean":None,"median":None,"per_organization":{}}
    s=sorted(vals); n=len(s); med=(s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2)
    return {"n_organizations":n,"mean":sum(vals)/n,"median":med,"per_organization":{k:values[k] for k in sorted(values)}}

def paired_bootstrap(a,b,n_resamples=10000,seed=0,confidence=.95):
    keys=sorted(set(a)&set(b)); diffs=[float(a[k])-float(b[k]) for k in keys]
    if not diffs:return {"n_organizations":0,"excluded_unpaired_organizations":len(set(a)^set(b)),"mean_difference":None,"ci_low":None,"ci_high":None,"resamples":n_resamples,"seed":seed}
    rng=random.Random(seed); samples=[]; n=len(diffs)
    for _ in range(n_resamples): samples.append(sum(diffs[rng.randrange(n)] for _ in range(n))/n)
    samples.sort(); alpha=(1-confidence)/2
    return {"n_organizations":n,"excluded_unpaired_organizations":len(set(a)^set(b)),"mean_difference":sum(diffs)/n,"ci_low":samples[int(alpha*n_resamples)],"ci_high":samples[min(n_resamples-1,int((1-alpha)*n_resamples))],"resamples":n_resamples,"seed":seed,"unit":"organization"}

def paired_permutation(a,b,n_permutations=10000,seed=0):
    keys=sorted(set(a)&set(b)); d=[float(a[k])-float(b[k]) for k in keys]; n=len(d)
    if not n:return {"n_organizations":0,"excluded_unpaired_organizations":len(set(a)^set(b)),"effect":None,"p_value":1.0,"permutations":0}
    obs=abs(sum(d)/n)
    if n<=16:
        vals=[abs(sum(x*s for x,s in zip(d,signs))/n) for signs in itertools.product((-1,1),repeat=n)]
        extreme=sum(v>=obs-1e-15 for v in vals); count=len(vals); p=extreme/count
    else:
        rng=random.Random(seed); count=n_permutations; extreme=0
        for _ in range(count):
            v=abs(sum(x*(1 if rng.random()<.5 else -1) for x in d)/n); extreme+=v>=obs-1e-15
        p=(extreme+1)/(count+1)
    return {"n_organizations":n,"excluded_unpaired_organizations":len(set(a)^set(b)),"effect":sum(d)/n,"p_value":p,"permutations":count,"seed":seed,"alternative":"two-sided sign-flip paired permutation","unit":"organization"}

def holm_adjust(p_values):
    m=len(p_values); order=sorted(p_values,key=lambda k:(p_values[k],k)); out={}; running=0.0
    for i,k in enumerate(order):
        adj=min(1.0,(m-i)*float(p_values[k])); running=max(running,adj); out[k]=running
    return out
