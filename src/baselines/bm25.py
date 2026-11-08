"""Small deterministic BM25 retrieval implementation with evidence citations."""
from __future__ import annotations
import math, re, unicodedata

def tokenize(text,stopwords=()):
    s=unicodedata.normalize("NFKC",str(text)).casefold()
    return [t for t in re.findall(r"[\w.]+",s,flags=re.UNICODE) if t and t not in set(stopwords)]

def fit(documents,config):
    # Caller filters to permitted fitting partitions before this pure component.
    docs=[]; df={}; total_len=0
    for d in documents:
        if d.get("partition") not in config["fit_partitions"]: continue
        toks=tokenize(d.get("text",""),config["stopwords"]); docs.append((d,toks)); total_len+=len(toks)
        for t in set(toks): df[t]=df.get(t,0)+1
    avg=total_len/len(docs) if docs else 0.0
    idf={t:math.log(1+(len(docs)-n+0.5)/(n+0.5)) for t,n in df.items()}
    return {"docs":docs,"df":df,"idf":idf,"avgdl":avg,"N":len(docs),"config":config}

def search(index,query,candidates,query_org,top_k=None):
    terms=tokenize(query,index["config"]["stopwords"])
    if not terms: return {"status":"abstain_empty_query","results":[],"terms":[]}
    counts={}; refs={}
    allowed={c["candidate_key"]:c for c in candidates if c["org_partition_key"]==query_org}
    for doc,toks in index["docs"]:
        key=doc["candidate_key"]
        if key not in allowed: continue
        dl=len(toks); tf={}
        for t in toks: tf[t]=tf.get(t,0)+1
        score=0.0
        for term in terms:
            f=tf.get(term,0)
            if f:
                k1=index["config"]["k1"]; b=index["config"]["b"]
                score+=index["idf"].get(term,0.0)*(f*(k1+1))/(f+k1*(1-b+b*dl/(index["avgdl"] or 1)))
        citations=sorted({e["evidence_id"] for e in doc.get("evidence",[]) if any(term in tokenize(" ".join(str(v) for v in e.get("fields",{}).values())) for term in terms)})
        counts[key]=score; refs[key]=citations
    result=[{"candidate_key":k,"score":counts.get(k,0.0),"evidence_refs":refs.get(k,[])} for k in allowed]
    result.sort(key=lambda r:(-r["score"],r["candidate_key"]))
    for i,r in enumerate(result,1): r["rank"]=i
    return {"status":"ok" if any(x["score"]>0 for x in result) else "no_overlap","results":result[:top_k],"terms":terms}
