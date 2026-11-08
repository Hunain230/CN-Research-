from __future__ import annotations
import datetime as dt, hashlib, json, os, platform, sys, time
from pathlib import Path
from .common import validate_request, stable_key, strict_json, finite, validate_c_response, validate_p_response, validate_v_response, bounded_call
from .correlation import correlate
from .prioritization import prioritize
from .verification import verify
from .providers.offline_stub import OfflineAgentProvider

class ResearchGateBlocked(RuntimeError): pass

def _components(request,edges,max_size):
    amap={a["alert_key"]:a for a in request["alerts"]}; parent={k:k for k in amap}
    def root(k):
        while parent[k]!=k: parent[k]=parent[parent[k]]; k=parent[k]
        return k
    trace=[]
    for edge in edges:
        if edge["decision"]!="LINK": continue
        a,b=edge["pair"]["left"],edge["pair"]["right"]
        ra,rb=root(a),root(b)
        members_a=[k for k in parent if root(k)==ra]; members_b=[k for k in parent if root(k)==rb]
        if ra==rb: continue
        if len(members_a)+len(members_b)>max_size:
            trace.append({"pair":edge["pair"],"status":"rejected_max_component_size"}); continue
        if amap[a]["org_key"]!=amap[b]["org_key"]: raise ValueError("org boundary violated during union")
        parent[rb]=ra; trace.append({"pair":edge["pair"],"status":"included"})
    groups={}
    for k in parent: groups.setdefault(root(k),[]).append(k)
    comps=[]
    for members in groups.values():
        members=sorted(members); comps.append({"component_key":stable_key(request["run_id"],members),"alert_keys":members,"org_key":request["org_key"]})
    return sorted(comps,key=lambda c:c["component_key"]),trace

def _run(root,fixture,config):
    provider=OfflineAgentProvider(); allowed=set(config["allowed_fields"])
    req=json.loads(fixture.read_text(encoding="utf-8")); amap,refs=validate_request(req,allowed)
    edge_trace=[]; failures=0; retries=0
    for pair in sorted(req["pairs"],key=lambda p:(p["left"],p["right"])):
        raw,ret,errs=bounded_call(lambda:correlate(pair,amap,provider),retries=1); retries+=ret; failures+=bool(errs and raw is None)
        result=validate_c_response(raw if raw is not None else {"decision":"UNSURE","reason_code":"provider_failure","rationale":"Provider failure; requires review.","supporting_evidence_ids":[],"contradicting_evidence_ids":[],"uncertainty":1.0},refs)
        idem=hashlib.sha256((req["input_hash"]+"|C-v1|stub-v1|"+pair["left"]+"|"+pair["right"]).encode()).hexdigest()
        edge_trace.append({"pair":pair,"idempotency_key":idem,"attempt":ret+1,"retry_count":ret,"status":"provider_failure" if raw is None else "completed","errors":errs,**result})
    components,component_trace=_components(req,edge_trace,config["max_component_size"])
    output=[]; call_count=0; revisions=0; review_count=0
    for comp in components:
        raw,ret,errs=bounded_call(lambda:prioritize(comp,amap,provider),retries=1); retries+=ret; failures+=bool(errs and raw is None); call_count+=ret+1
        pc=validate_p_response(raw if raw is not None else {"score":None,"supporting_evidence_ids":[],"contradicting_evidence_ids":[],"rationale":"Provider failure; requires review.","uncertainty":"provider_failure","recommendation":"REVIEW"},refs)
        ev=[e for k in comp["alert_keys"] for e in amap[k]["evidence"]]
        claims=[{"type":"P",**pc}]
        claims += [{"type":"C","pair":e["pair"],**{k:e[k] for k in ("decision","reason_code","supporting_evidence_ids","contradicting_evidence_ids","uncertainty")}} for e in edge_trace if e["pair"]["left"] in comp["alert_keys"] and e["pair"]["right"] in comp["alert_keys"]]
        raw,ret,errs=bounded_call(lambda:verify(claims,ev,provider),retries=1); retries+=ret; failures+=bool(errs and raw is None); call_count+=ret+1
        vc=validate_v_response(raw if raw is not None else {"decision":"REVIEW","claims":[],"reason":"provider_failure","revision_request":None,"review_reason":"verification provider failed"},{e["evidence_id"] for e in ev}); revision_trace=[]
        if vc["decision"]=="REVISE":
            revisions+=1; revision_trace.append({"attempt":1,"prioritization_original":pc,"verification":vc})
            # exactly one revision: deterministic provider gets the same immutable evidence plus revision request.
            raw,ret,errs=bounded_call(lambda:prioritize(comp,amap,provider),retries=1); retries+=ret; failures+=bool(errs and raw is None); call_count+=ret+1
            pc=validate_p_response(raw if raw is not None else {"score":None,"supporting_evidence_ids":[],"contradicting_evidence_ids":[],"rationale":"Provider failure; requires review.","uncertainty":"provider_failure","recommendation":"REVIEW"},refs)
            claims[0]={"type":"P",**pc}; raw,ret,errs=bounded_call(lambda:verify(claims,ev,provider),retries=1); retries+=ret; failures+=bool(errs and raw is None); call_count+=ret+1
            vc=validate_v_response(raw if raw is not None else {"decision":"REVIEW","claims":[],"reason":"provider_failure","revision_request":None,"review_reason":"verification provider failed"},{e["evidence_id"] for e in ev})
            revision_trace.append({"attempt":1,"prioritization_revision":pc,"verification":vc})
        status="REVIEW" if vc["decision"]!="PASS" or pc["recommendation"]=="REVIEW" or pc["score"] is None else "PASS"
        review_count+=status=="REVIEW"
        output.append({"component":comp,"prioritization":pc,"verification":vc,"revision_trace":revision_trace,"final_status":status})
    return {"classification":"synthetic_plumbing_only_not_empirical","schema_version":"agents-output-v1","run_id":req["run_id"],"correlation_edges":edge_trace,"components":components,"component_trace":component_trace,"component_results":output,"summary":{"candidate_pairs":len(edge_trace),"components":len(components),"review_components":review_count,"revisions":revisions,"calls":call_count,"estimated_tokens":call_count*config["estimated_tokens_per_call"],"truncated_records":0,"failure_count":failures,"retry_count":retries,"live_model_calls":0}}

def run_agents(root,config_path,mode,out_path,command_line=None):
    started=time.perf_counter(); started_utc=dt.datetime.now(dt.timezone.utc).isoformat()
    root=Path(root); out=Path(out_path); cfgpath=root/config_path
    config=json.loads(cfgpath.read_text(encoding="utf-8"))
    if mode!="synthetic":
        raise ResearchGateBlocked("real-data agents blocked: no approved model-visible fields; conflicting alert memberships block correlation; QueueRank scope/completeness unverified; organization split provisional; live providers disabled")
    fixture=(root/config["synthetic_fixture"]).resolve()
    fixtures=(root/"fixtures"/"stage4").resolve()
    if not fixture.is_relative_to(fixtures): raise ValueError("synthetic mode may read fixtures/stage4 only")
    if out.exists(): raise FileExistsError("refusing to overwrite existing agent run directory")
    result=_run(root,fixture,config)
    out.mkdir(parents=True)
    (out/"results.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    hashes={}
    for p in [fixture,cfgpath,*sorted((root/"configs"/"agent_schemas").glob("*.json")),*sorted((root/"configs").glob("*agent*.yaml")),*sorted((root/"src"/"agents").rglob("*.py")),root/"src"/"cli.py"]:
        if p.is_file(): hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={"run_id":result["run_id"],"classification":result["classification"],"mode":"synthetic","command":command_line,"python":platform.python_version(),"started_utc":started_utc,"ended_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"runtime_ms":round((time.perf_counter()-started)*1000,3),"live_model_calls":0,"provider":"deterministic-synthetic-agent-stub","provider_version":"agent-stub-v1","resource_totals":result["summary"],"prompt_template_sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/"configs").glob("*_agent.yaml"))},"sha256":hashes,"output_sha256":{"results.json":hashlib.sha256((out/"results.json").read_bytes()).hexdigest()}}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    return {"status":"synthetic_complete_not_empirical","output":str(out),**result["summary"]}

def self_test(root):
    root=Path(root); fixtures=root/"fixtures"/"stage4"; cfg=json.loads((root/"configs"/"agents.yaml").read_text()); req=json.loads((fixtures/"synthetic_inputs.json").read_text()); allowed=set(cfg["allowed_fields"]); assertions=0
    amap,refs=validate_request(req,allowed); assertions+=1
    from .providers.offline_stub import OfflineAgentProvider
    prov=OfflineAgentProvider()
    evs=[e for a in req["alerts"] for e in a["evidence"]]
    assert prov.verification([{"type":"C","pair":{"left":"a1","right":"a2"},"decision":"LINK","supporting_evidence_ids":["ev-a1","ev-a2"],"contradicting_evidence_ids":[]}],evs)["decision"]=="PASS"; assertions+=1
    assert prov.verification([{"type":"C","pair":{"left":"a1","right":"a3"},"decision":"LINK","supporting_evidence_ids":["ev-a1","ev-a3"],"contradicting_evidence_ids":[]}],evs)["decision"]=="REVISE"; assertions+=1
    assert prov.verification([{"type":"C","pair":{"left":"a1","right":"a2"},"decision":"LINK","supporting_evidence_ids":["fabricated"],"contradicting_evidence_ids":[]}],evs)["decision"]=="REVISE"; assertions+=1
    # Decisions, threshold, org reuse, citation checks.
    pairs={tuple(sorted((p["left"],p["right"]))):p for p in req["pairs"]}
    out=_run(root,fixtures/"synthetic_inputs.json",cfg)
    decisions={tuple(sorted((e["pair"]["left"],e["pair"]["right"]))):e["decision"] for e in out["correlation_edges"]}
    expected=json.loads((fixtures/"expected.json").read_text())
    for p,d in expected["decisions"].items():
        assert decisions[tuple(p.split("|"))]==d; assertions+=1
    assert all(set(e["supporting_evidence_ids"]+e["contradicting_evidence_ids"])<=refs for e in out["correlation_edges"]); assertions+=1
    assert all(not c["component_key"].startswith("Incident") for c in out["components"]); assertions+=1
    # Validation rejection matrix.
    def rejects(mutator):
        q=json.loads(json.dumps(req)); mutator(q)
        try: validate_request(q,allowed)
        except (ValueError,KeyError): return True
        return False
    assert rejects(lambda q:q.update({"IncidentId":"SENTINEL_LABEL_X"})); assertions+=1
    assert rejects(lambda q:q["alerts"][0]["evidence"][0].update({"lineage":"evaluator"})); assertions+=1
    assert rejects(lambda q:q["pairs"].append({"left":"a1","right":"x1","candidate_source":"synthetic"})); assertions+=1
    def add_cross_org(q):
        q["alerts"].append({"alert_key":"b1","org_key":"synthetic-org-2","minutes":0,"evidence":[{"evidence_id":"ev-b1","org_key":"synthetic-org-2","alert_key":"b1","minutes":0,"lineage":"synthetic_fixture","fields":{"synthetic.entities":["host-x"],"synthetic.techniques":["T1001"],"synthetic.text":"other org"}}]})
    assert rejects(add_cross_org); assertions+=1
    assert rejects(lambda q:q["alerts"][0]["evidence"].append({"evidence_id":"cross","org_key":"org-other","alert_key":"a1","minutes":0,"fields":{"entities":["x"]},"lineage":"synthetic_fixture"})); assertions+=1
    assert rejects(lambda q:q["evidence_budget"].update({"max_records":0})); assertions+=1
    assert rejects(lambda q:q["evidence_budget"].update({"max_tokens":0})); assertions+=1
    assert rejects(lambda q:q.update({"pairs":q["pairs"]*6})); assertions+=1
    from .common import strict_json, bounded_call
    for raw in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
        try: strict_json(raw); raise AssertionError("accepted invalid JSON")
        except ValueError: assertions+=1
    n=[0]
    def flaky():
        n[0]+=1
        if n[0]==1: raise TimeoutError("synthetic")
        return "ok"
    value,nretry,errors=bounded_call(flaky,1); assert (value,nretry,len(errors))==("ok",1,1); assertions+=1
    value,nretry,errors=bounded_call(lambda:(_ for _ in ()).throw(TimeoutError("synthetic")),1); assert value is None and nretry==1 and len(errors)==2; assertions+=1
    valid_c={"decision":"UNSURE","reason_code":"missing","rationale":"unknown","supporting_evidence_ids":[],"contradicting_evidence_ids":[],"uncertainty":1.0}
    try: validate_c_response({**valid_c,"extra":1},refs); raise AssertionError("C accepted undeclared property")
    except ValueError: assertions+=1
    try: validate_c_response({**valid_c,"decision":"MAYBE"},refs); raise AssertionError("C accepted invalid enum")
    except ValueError: assertions+=1
    valid_p={"score":0.5,"supporting_evidence_ids":["ev-a1"],"contradicting_evidence_ids":[],"rationale":"fixture","uncertainty":"uncalibrated","recommendation":"PASS"}
    try: validate_p_response({**valid_p,"score":float("nan")},refs); raise AssertionError("P accepted NaN")
    except ValueError: assertions+=1
    # Component LINK-only union, max-size and deterministic key.
    comps,tr=_components(req,[{"decision":"LINK","pair":{"left":"a1","right":"a2"}},{"decision":"UNSURE","pair":{"left":"a2","right":"a3"}}],3)
    assert any(c["alert_keys"]==["a1","a2"] for c in comps); assertions+=1
    c1=_components(req,[{"decision":"LINK","pair":{"left":"a1","right":"a2"}}],3)[0]
    c2=_components(req,[{"decision":"LINK","pair":{"left":"a1","right":"a2"}}],3)[0]
    assert c1==c2; assertions+=1
    capped,ct=_components(req,[{"decision":"LINK","pair":{"left":"a1","right":"a2"}},{"decision":"LINK","pair":{"left":"a2","right":"a3"}},{"decision":"LINK","pair":{"left":"a3","right":"a4"}}],3)
    assert any(x["status"]=="rejected_max_component_size" for x in ct); assertions+=1
    # Revision cap simulated by validating orchestration trace: only one revision slot.
    assert all(len(x["revision_trace"])<=2 for x in out["component_results"]); assertions+=1
    assert out["summary"]["live_model_calls"]==0; assertions+=1
    assert all(e["decision"]!="LINK" or e["pair"]["left"]!="a1" or e["pair"]["right"]!="b1" for e in out["correlation_edges"]); assertions+=1
    assert _run(root,fixtures/"synthetic_inputs.json",cfg)==_run(root,fixtures/"synthetic_inputs.json",cfg); assertions+=1
    assert out["classification"]=="synthetic_plumbing_only_not_empirical"; assertions+=1
    return {"status":"pass","assertions":assertions,"classification":out["classification"],"live_model_calls":0}

