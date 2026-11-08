from __future__ import annotations
import json, math

DENY={"incidentid","queuerank","incidentgrade","actiongrouped","actiongranular","goldlabel","goldgroup","label","labelpresent","truth","outcome"}
def _norm(x): return "".join(c for c in str(x).lower() if c.isalnum())
def strict_load_json(path):
    def pairs(xs):
        d={}
        for k,v in xs:
            if k in d: raise ValueError("duplicate JSON key")
            d[k]=v
        return d
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite JSON number")))
def validate_predictions(data):
    required_top={"schema_version","classification","run_id","predictions","pair_predictions","components","ranked_candidates","top20_components"}
    if set(data)!=required_top or data["schema_version"]!="evaluation-predictions-v1" or data["classification"]!="synthetic_predictions_only_not_empirical": raise ValueError("prediction document schema/classification mismatch")
    seen=set(); org_by_query={}
    for p in data["predictions"]:
        if any(_norm(k) in DENY for k in p): raise ValueError("prediction contains evaluator field")
        required={"method","query_key","org_key","candidate_key","decision","score","rank","abstention","failure","evidence_refs","latency_ms","input_tokens","output_tokens","run_hash"}
        if set(p)!=required: raise ValueError("prediction row schema mismatch")
        if p["decision"] not in {"LINK","NO_LINK","UNSURE","SCORE","REVIEW",None}: raise ValueError("invalid decision")
        for k in ("score","latency_ms"):
            v=p[k]
            if v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)): raise ValueError("non-finite numeric prediction")
        if p["rank"] is not None and (not isinstance(p["rank"],int) or p["rank"]<1): raise ValueError("invalid predicted rank")
        if not isinstance(p["evidence_refs"],list) or any(not isinstance(r,str) for r in p["evidence_refs"]) or len(p["evidence_refs"])!=len(set(p["evidence_refs"])): raise ValueError("invalid or duplicate citation references")
        if any(not isinstance(p[k],int) or p[k]<0 for k in ("input_tokens","output_tokens")): raise ValueError("invalid resource count")
        if not isinstance(p["run_hash"],str) or not p["run_hash"]: raise ValueError("missing prediction run hash")
        key=(p["method"],p["query_key"],p["candidate_key"])
        if key in seen: raise ValueError("duplicate prediction candidate")
        seen.add(key)
        qkey=(p["method"],p["query_key"])
        if qkey in org_by_query and org_by_query[qkey]!=p["org_key"]: raise ValueError("query crosses organization boundary")
        org_by_query[qkey]=p["org_key"]
    pair_seen=set()
    for p in data["pair_predictions"]:
        if any(_norm(k) in DENY for k in p): raise ValueError("pair prediction contains evaluator field")
        if set(p)!={"left","right","org_key","left_org","right_org","decision","abstention","failure"} or p["decision"] not in {"LINK","NO_LINK","UNSURE"}: raise ValueError("pair prediction schema mismatch")
        if p["org_key"]!=p["left_org"] or p["org_key"]!=p["right_org"]: raise ValueError("cross-organization pair prediction")
        pk=tuple(sorted((p["left"],p["right"])))
        if pk in pair_seen: raise ValueError("duplicate pair prediction")
        pair_seen.add(pk)
    if any(not isinstance(x,str) for x in data["ranked_candidates"]): raise ValueError("invalid ranked candidate")
    return data
