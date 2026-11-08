"""Deterministic offline adapter for plumbing tests; never an LLM result."""
from __future__ import annotations
import hashlib, json, time

class StubTimeout(TimeoutError): pass

class OfflineStubProvider:
    name="deterministic-synthetic-stub"
    version="stub-v1"
    def generate(self,payload,seed,allowed_evidence,fault=None):
        start=time.perf_counter()
        if fault=="timeout": raise StubTimeout("synthetic timeout")
        if fault=="malformed": return "{not-json", 0, 0, (time.perf_counter()-start)*1000
        predictions=[]
        for c in payload["candidates"]:
            refs=sorted(set(c.get("evidence_refs",[]))&set(allowed_evidence))
            if not refs:
                decision="UNSURE"; score=None; abstain="missing_evidence"; reason="No cited evidence was supplied."
            else:
                offset=sum(c["candidate_key"].encode("utf-8"))%3
                decision=("LINK","NO_LINK","UNSURE")[(seed+offset)%3]
                raw=hashlib.sha256(f"{payload['query_key']}|{c['candidate_key']}|{seed}".encode()).digest()
                score=int.from_bytes(raw[:4],"big")/4294967295
                abstain="none" if decision!="UNSURE" else "uncertain"
                reason="Deterministic synthetic stub response; not a model judgment."
            predictions.append({"candidate_key":c["candidate_key"],"decision":decision,"score":score,"rationale":reason,"evidence_ids":refs,"uncertainty":0.0 if score is None else round(1-abs(score-0.5)*2,6),"abstention_status":abstain})
        raw=json.dumps({"predictions":predictions},sort_keys=True,separators=(",",":"))
        input_tokens=len(json.dumps(payload,sort_keys=True).split())
        output_tokens=len(raw.split())
        return raw,input_tokens,output_tokens,(time.perf_counter()-start)*1000
