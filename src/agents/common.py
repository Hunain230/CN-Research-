from __future__ import annotations
import hashlib, json, math, re

DENY={"incidentid","queuerank","incidentgrade","actiongrouped","actiongranular","rank","rankposition","label","labelpresent","outcome","goldlabel","goldgroup","severity"}
def norm(x): return re.sub(r"[^a-z0-9]","",str(x).lower())
def check_tree(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if norm(k) in DENY: raise ValueError("prohibited field name")
            check_tree(v)
    elif isinstance(x,list):
        for v in x: check_tree(v)
    elif isinstance(x,str) and x.startswith("SENTINEL_LABEL_"): raise ValueError("synthetic label sentinel rejected")
def validate_request(r,allowed):
    check_tree(r)
    required={"schema_version","run_id","org_key","pairs","alerts","evidence_budget","input_hash"}
    if set(r)!=required or r["schema_version"]!="agents-v1": raise ValueError("request schema mismatch")
    alerts=r["alerts"]
    if len(alerts)>20 or len(r["pairs"])>20: raise ValueError("candidate cap exceeded")
    org=r["org_key"]; amap={a["alert_key"]:a for a in alerts}
    if len(amap)!=len(alerts): raise ValueError("duplicate alert key")
    refs=set()
    for a in alerts:
        if a["org_key"]!=org: raise ValueError("cross-organization alert")
        for e in a["evidence"]:
            if e["org_key"]!=org: raise ValueError("cross-organization evidence")
            if set(e["fields"])-set(allowed): raise ValueError("unapproved field")
            if e.get("lineage")!="synthetic_fixture": raise ValueError("unapproved evidence lineage")
            refs.add(e["evidence_id"])
    estimated=sum(len(json.dumps(e["fields"],sort_keys=True).split()) for a in alerts for e in a["evidence"])
    if estimated>r["evidence_budget"].get("max_tokens",0): raise ValueError("evidence token budget exceeded")
    for p in r["pairs"]:
        if set(p)!={"left","right","candidate_source"} or p["left"] not in amap or p["right"] not in amap: raise ValueError("pair escaped candidate set")
        if amap[p["left"]]["org_key"]!=amap[p["right"]]["org_key"]: raise ValueError("cross-organization pair")
    if len(refs)>r["evidence_budget"]["max_records"]: raise ValueError("evidence cap exceeded")
    return amap,refs
def stable_key(run_id,keys): return hashlib.sha256(("component-v1|"+run_id+"|"+"|".join(sorted(keys))).encode()).hexdigest()[:16]
def strict_json(s):
    def pairs(ps):
        d={}
        for k,v in ps:
            if k in d: raise ValueError("duplicate JSON key")
            d[k]=v
        return d
    return json.loads(s,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite JSON number")))
def finite(v): return isinstance(v,(int,float)) and math.isfinite(float(v))
def validate_c_response(r,refs):
    required={"decision","reason_code","rationale","supporting_evidence_ids","contradicting_evidence_ids","uncertainty"}
    if not isinstance(r,dict) or set(r)!=required or r["decision"] not in {"LINK","NO_LINK","UNSURE"}: raise ValueError("C response schema/enum rejected")
    if not isinstance(r["reason_code"],str) or not isinstance(r["rationale"],str): raise ValueError("C response text fields invalid")
    if not isinstance(r["supporting_evidence_ids"],list) or not isinstance(r["contradicting_evidence_ids"],list): raise ValueError("C citations invalid")
    if not set(r["supporting_evidence_ids"]+r["contradicting_evidence_ids"])<=refs: raise ValueError("C fabricated citation")
    u=r["uncertainty"]
    if u is not None and (not finite(u) or not 0<=u<=1): raise ValueError("C uncertainty invalid")
    return r
def validate_p_response(r,refs):
    required={"score","supporting_evidence_ids","contradicting_evidence_ids","rationale","uncertainty","recommendation"}
    if not isinstance(r,dict) or set(r)!=required or r["recommendation"] not in {"PASS","REVIEW"}: raise ValueError("P response schema/enum rejected")
    if r["score"] is not None and (not finite(r["score"]) or not 0<=r["score"]<=1): raise ValueError("P score invalid")
    if not isinstance(r["supporting_evidence_ids"],list) or not isinstance(r["contradicting_evidence_ids"],list): raise ValueError("P citations invalid")
    if not set(r["supporting_evidence_ids"]+r["contradicting_evidence_ids"])<=refs: raise ValueError("P fabricated citation")
    return r
def validate_v_response(r,refs):
    required={"decision","claims","reason","revision_request","review_reason"}
    if not isinstance(r,dict) or set(r)!=required or r["decision"] not in {"PASS","REVISE","REVIEW"}: raise ValueError("V response schema/enum rejected")
    for c in r["claims"]:
        if set(c)!={"claim","status","evidence_ids"} or c["status"] not in {"supported","unsupported","unverifiable","contradicted"}: raise ValueError("V claim schema/status rejected")
        if not set(c["evidence_ids"])<=refs: raise ValueError("V citation outside supplied evidence")
    return r
def bounded_call(fn, retries=1):
    errors=[]
    for attempt in range(1,retries+2):
        try: return fn(),attempt-1,errors
        except Exception as exc:
            errors.append(type(exc).__name__)
    return None,retries,errors
