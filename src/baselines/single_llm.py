"""B2 single-call and B3 matched repeated single-call orchestration."""
from __future__ import annotations
import hashlib, json, statistics
from .common import stable_rank, validate_prediction
from .providers.offline_stub import OfflineStubProvider, StubTimeout

def _prompt_hash(template): return hashlib.sha256(template.encode("utf-8")).hexdigest()

def _payload(req,budget):
    items=[req["query"]]+req["candidates"]
    eb=req.get("evidence_budget",{}); records_left=int(eb.get("max_records",10**9)); tokens_left=int(eb.get("max_tokens",10**9)); chars_left=int(eb.get("max_characters",10**12))
    selected=[]; kept={}; truncated_records=0; truncated_fields=0
    for item in items:
        ev=item.get("evidence",[]); take=ev[:records_left]; records_left-=len(take); truncated_records+=len(ev)-len(take)
        ids={e.get("evidence_id") for e in take}; kept[id(item)]=take; fields={}
        for field,value in sorted(item.get("fields",{}).items()):
            sources=set(item.get("field_sources",{}).get(field,[]))&ids
            if not sources: continue
            words=str(value).split()
            words=words[:tokens_left]; tokens_left-=len(words)
            text=" ".join(words)[:chars_left]; chars_left-=len(text)
            if text!=str(value): truncated_fields+=1
            if text: fields[field]=text
        selected.append(fields)
    qfields=selected[0]
    qev=[{"evidence_id":e["evidence_id"],"timestamp_utc":e.get("timestamp_utc")} for e in kept[id(items[0])]]
    cs=[]
    for i,c in enumerate(req["candidates"],1):
        ev=kept[id(c)]
        cs.append({"candidate_key":c["candidate_key"],"fields":selected[i],"evidence_refs":[e["evidence_id"] for e in ev]})
    return {"query_key":req["query_key"],"query_evidence":qev,"query_fields":qfields,"candidates":cs,"budget_tokens":budget,"evidence_delimiter":"<UNTRUSTED_EVIDENCE>"},{"records_dropped":truncated_records,"fields_truncated":truncated_fields}

def _invoke(provider,payload,seed,all_refs,settings,run_id,method,query_key,valid_refs,fault=None):
    ph=_prompt_hash(settings["prompt_template"])
    try:
        raw,it,ot,lat=provider.generate(payload,seed,all_refs,fault=fault)
        if it+ot>payload["budget_tokens"]: raise ValueError("token_budget_exceeded")
        parsed=json.loads(raw)
        if set(parsed)!={"predictions"} or not isinstance(parsed["predictions"],list): raise ValueError("malformed_stub_schema")
        bykey={x["candidate_key"]:x for x in parsed["predictions"]}
        expected={x["candidate_key"] for x in payload["candidates"]}
        if set(bykey)!=expected: raise ValueError("candidate_set_mismatch")
        out=[]
        for c in payload["candidates"]:
            x=bykey[c["candidate_key"]]
            row={"run_id":run_id,"method":method,"query_key":query_key,"candidate_key":c["candidate_key"],"score":x["score"],"rank":None,"decision":x["decision"],"evidence_refs":x["evidence_ids"],"rationale":x["rationale"],"uncertainty":x["uncertainty"],"abstention_status":x["abstention_status"],"provider":provider.name,"provider_version":provider.version,"prompt_hash":ph,"inference_seed":seed,"input_tokens":it,"output_tokens":ot,"latency_ms":lat,"retry_count":0,"error_class":None}
            out.append(validate_prediction(row,valid_refs))
        ranked=stable_rank([dict(r) for r in out])
        return {"call_status":"valid","seed":seed,"raw_output":raw,"predictions":ranked,"input_tokens":it,"output_tokens":ot,"latency_ms":lat,"retry_count":0,"error_class":None,"prompt_hash":ph}
    except StubTimeout:
        err="synthetic_timeout"; lat=0.0; raw=""
    except Exception as e:
        err=type(e).__name__; lat=0.0; raw=locals().get("raw","")
    failed=[]
    for c in payload["candidates"]:
        failed.append(validate_prediction({"run_id":run_id,"method":method,"query_key":query_key,"candidate_key":c["candidate_key"],"score":None,"rank":None,"decision":"UNSURE","evidence_refs":[],"rationale":"Call failed or returned malformed output; recorded as abstention.","uncertainty":None,"abstention_status":"failure_abstention","provider":provider.name,"provider_version":provider.version,"prompt_hash":ph,"inference_seed":seed,"input_tokens":0,"output_tokens":0,"latency_ms":lat,"retry_count":0,"error_class":err},valid_refs))
    return {"call_status":"failed_abstention","seed":seed,"raw_output":raw,"predictions":failed,"input_tokens":0,"output_tokens":0,"latency_ms":lat,"retry_count":0,"error_class":err,"prompt_hash":ph}

def run_b2(req,allowed_fields,settings,budget,run_id,fault=None):
    valid_refs=set(e["evidence_id"] for item in [req["query"]]+req["candidates"] for e in item.get("evidence",[]))
    refs=set(valid_refs)
    payload,truncation=_payload(req,budget); provider=OfflineStubProvider()
    call=_invoke(provider,payload,0,refs,settings,run_id,"single_llm",req["query_key"],valid_refs,fault=fault)
    call["truncation"]=truncation
    return {"method":"single_llm","status":"synthetic_stub_not_empirical","call":call,"predictions":call["predictions"],"allocated_total_token_budget":budget}

def combine_b3(calls,settings,run_id,query_key,candidate_keys,valid_refs):
    combined=[]
    for key in candidate_keys:
        records=[p for c in calls for p in c["predictions"] if p["candidate_key"]==key]
        if settings.get("unsure_policy")=="abstain_if_any" and any(p["decision"]=="UNSURE" for p in records):
            votes=[]; decision=settings["tie_policy"]
        else:
            votes=[p["decision"] for p in records if p["decision"] in ("LINK","NO_LINK")]
            counts={x:votes.count(x) for x in ("LINK","NO_LINK")}
            decision=settings["tie_policy"] if counts["LINK"]==counts["NO_LINK"] else max(counts,key=counts.get)
        scores=[float(p["score"]) for p in records if isinstance(p["score"],(int,float))]
        score=statistics.median(scores) if scores else None
        uncertainties=[float(p["uncertainty"]) for p in records if isinstance(p.get("uncertainty"),(int,float))]
        uncertainty=statistics.median(uncertainties) if uncertainties else None
        refs=sorted({r for p in records for r in p["evidence_refs"]})
        row={"run_id":run_id,"method":"repeated_single_llm","query_key":query_key,"candidate_key":key,"score":score,"rank":None,"decision":decision,"evidence_refs":refs,"rationale":f"Majority over LINK/NO_LINK votes; valid-score median over {len(scores)} call(s).","uncertainty":uncertainty,"abstention_status":"none" if decision!="UNSURE" and score is not None else "partial_or_tied","provider":"deterministic-synthetic-stub","provider_version":"stub-v1","prompt_hash":calls[0]["prompt_hash"],"inference_seed":None,"input_tokens":0,"output_tokens":0,"latency_ms":sum(c["latency_ms"] for c in calls),"retry_count":sum(c["retry_count"] for c in calls),"error_class":"partial_call_failure" if any(c["call_status"]!="valid" for c in calls) else None}
        combined.append(validate_prediction(row,valid_refs))
    return stable_rank(combined)

def run_b3(req,settings,total_budget,per_call_budget,seeds,run_id,faults=None):
    valid_refs=set(e["evidence_id"] for item in [req["query"]]+req["candidates"] for e in item.get("evidence",[]))
    provider=OfflineStubProvider(); faults=faults or {}; calls=[]; payload,truncation=_payload(req,per_call_budget)
    for seed in seeds:
        calls.append(_invoke(provider,payload,seed,valid_refs,settings,run_id,"repeated_single_llm",req["query_key"],valid_refs,fault=faults.get(seed)))
        calls[-1]["truncation"]=truncation
    predictions=combine_b3(calls,settings,run_id,req["query_key"],[c["candidate_key"] for c in req["candidates"]],valid_refs)
    used=sum(c["input_tokens"]+c["output_tokens"] for c in calls)
    allocated=per_call_budget*len(seeds)
    matched=(allocated==total_budget and used<=total_budget and len(seeds)==3)
    return {"method":"repeated_single_llm","status":"synthetic_stub_not_empirical","calls":calls,"predictions":predictions,"evidence_truncation":truncation,"budget_match":{"target_total_tokens":total_budget,"per_call_budget_tokens":per_call_budget,"allocated_total_tokens":allocated,"actual_estimated_tokens":used,"call_count":len(seeds),"matched_total_token_budget":matched,"calculation":f"{per_call_budget} x {len(seeds)} = {allocated}; target {total_budget}; actual use <= target: {used <= total_budget}"}}
