"""Shared baseline input/prediction contracts and deny-by-default checks."""
from __future__ import annotations
import math, re

DENY_NAMES={"incidentid","incident_id","queuerank","queue_rank","rank","rankposition","rank_position","incidentgrade","incident_grade","actiongrouped","action_grouped","actiongranular","action_granular","labelpresent","label_present","labelpresence","label_presence","outcome","severity","detectorseverity","goldgroup","goldlabel"}
PREDICTION_FIELDS={"run_id","method","query_key","candidate_key","score","rank","decision","evidence_refs","rationale","uncertainty","abstention_status","provider","provider_version","prompt_hash","inference_seed","input_tokens","output_tokens","latency_ms","retry_count","error_class"}

def norm_name(s): return re.sub(r"[^a-z0-9]","",str(s).lower())

def scan_forbidden(value,path="$",hits=None):
    hits=[] if hits is None else hits
    if isinstance(value,dict):
        for k,v in value.items():
            if norm_name(k) in {norm_name(x) for x in DENY_NAMES}: hits.append(path+"."+str(k))
            scan_forbidden(v,path+"."+str(k),hits)
    elif isinstance(value,list):
        for i,v in enumerate(value): scan_forbidden(v,f"{path}[{i}]",hits)
    return hits

def validate_request(req,allowed_fields):
    if scan_forbidden(req): raise ValueError("input rejected by prohibited-field scan")
    required={"query_key","org_partition_key","query","candidates","evidence_budget","candidate_generation_version","run_id","split_label","input_hash","schema_version"}
    if set(req)!=required: raise ValueError("baseline input keys do not match the versioned contract")
    org=req["org_partition_key"]
    if req["query"].get("org_partition_key")!=org: raise ValueError("query organization boundary violation")
    if not isinstance(req["candidates"],list): raise ValueError("candidates must be a list")
    refs=set()
    for item in [req["query"]]+req["candidates"]:
        if item.get("org_partition_key")!=org: raise ValueError("cross-organization candidate rejected")
        if item.get("key_origin") not in ("opaque_synthetic","opaque_approved"): raise ValueError("candidate key provenance is not approved")
        if set(item.get("fields",{}))-set(allowed_fields): raise ValueError("unapproved evidence field rejected")
        evidence=item.get("evidence",[])
        if not isinstance(evidence,list): raise ValueError("evidence must be a list")
        for e in evidence:
            if set(e)-{"evidence_id","timestamp_utc","fields"}: raise ValueError("evidence record schema mismatch")
            refs.add(e.get("evidence_id"))
            if set(e.get("fields",{}))-set(allowed_fields): raise ValueError("unapproved evidence field rejected")
        sources=item.get("field_sources",{})
        if set(item.get("fields",{}))-set(sources): raise ValueError("field lineage mapping is incomplete")
        known={e.get("evidence_id") for e in evidence}
        for field,ids in sources.items():
            if field not in allowed_fields or not ids or not set(ids).issubset(known): raise ValueError("field lineage points outside supplied evidence")
    return refs

def validate_prediction(row,valid_refs):
    if set(row)!=PREDICTION_FIELDS: raise ValueError("prediction schema mismatch")
    # `rank` here is a predicted output column; reject label-derived aliases/fields elsewhere.
    scrubbed={k:v for k,v in row.items() if k!="rank"}
    if scan_forbidden(scrubbed): raise ValueError("prediction contains prohibited field")
    score=row["score"]
    if score is not None and (not isinstance(score,(int,float)) or not math.isfinite(float(score))): raise ValueError("prediction score must be finite or null")
    uncertainty=row["uncertainty"]
    if uncertainty is not None and (not isinstance(uncertainty,(int,float)) or not math.isfinite(float(uncertainty)) or not 0<=uncertainty<=1): raise ValueError("uncertainty must be finite in [0,1] or null")
    if row["rank"] is not None and (not isinstance(row["rank"],int) or row["rank"]<1): raise ValueError("invalid prediction rank")
    if row["decision"] not in (None,"LINK","NO_LINK","UNSURE"): raise ValueError("invalid decision")
    if not set(row["evidence_refs"]).issubset(valid_refs): raise ValueError("fabricated evidence reference")
    for k in ("input_tokens","output_tokens","retry_count"):
        if not isinstance(row[k],int) or row[k]<0: raise ValueError("invalid resource count")
    if row["latency_ms"]<0: raise ValueError("invalid latency")
    return row

def stable_rank(rows,score_key="score",key_key="candidate_key"):
    ordered=sorted(rows,key=lambda x:(-(x[score_key] if x[score_key] is not None else float("-inf")),x[key_key]))
    for i,row in enumerate(ordered,1): row["rank"]=i if row[score_key] is not None else None
    return ordered
