"""Deterministic synthetic provider; never contacts a network or models."""
class OfflineAgentProvider:
    name="deterministic-synthetic-agent-stub"; version="agent-stub-v1"
    def correlation(self,pair,evidence):
        refs=sorted(e["evidence_id"] for e in evidence)
        left=[e for e in evidence if e["alert_key"]==pair["left"]]
        right=[e for e in evidence if e["alert_key"]==pair["right"]]
        a=left[0] if left else None; b=right[0] if right else None
        if not a or not b:return {"decision":"UNSURE","reason_code":"missing_evidence","rationale":"Insufficient supplied evidence.","supporting_evidence_ids":[],"contradicting_evidence_ids":[],"uncertainty":1.0}
        fa=a["fields"]; fb=b["fields"]
        same_entity=bool(set(fa.get("synthetic.entities",[]))&set(fb.get("synthetic.entities",[])))
        same_tech=bool(set(fa.get("synthetic.techniques",[]))&set(fb.get("synthetic.techniques",[])))
        dt=abs(a["minutes"]-b["minutes"])
        contradictory=bool(fa.get("synthetic.conflict") or fb.get("synthetic.conflict"))
        if contradictory:return {"decision":"UNSURE","reason_code":"conflicting_evidence","rationale":"Supplied evidence conflicts.","supporting_evidence_ids":[],"contradicting_evidence_ids":refs,"uncertainty":0.9}
        if same_entity and dt<=2880 or same_tech and dt<=60:return {"decision":"LINK","reason_code":"shared_signal_within_window","rationale":"A supplied entity or technique signal matches within its configured time window.","supporting_evidence_ids":refs,"contradicting_evidence_ids":[],"uncertainty":0.1}
        return {"decision":"NO_LINK","reason_code":"no_supported_match","rationale":"No supplied signal supports a link.","supporting_evidence_ids":[],"contradicting_evidence_ids":refs,"uncertainty":0.6}
    def prioritization(self,component,evidence):
        refs=sorted(e["evidence_id"] for e in evidence)
        if not refs:return {"score":None,"supporting_evidence_ids":[],"contradicting_evidence_ids":[],"rationale":"No evidence supplied.","uncertainty":"missing_evidence","recommendation":"REVIEW"}
        return {"score":round(min(1.0,len(component["alert_keys"])*0.2+len(refs)*0.05),3),"supporting_evidence_ids":refs,"contradicting_evidence_ids":[],"rationale":"Synthetic relative score derived only from supplied evidence count.","uncertainty":"uncalibrated_synthetic","recommendation":"PASS"}
    def verification(self,claims,evidence):
        byid={e["evidence_id"]:e for e in evidence}; statuses=[]; unsupported=False
        for c in claims:
            refs=c.get("supporting_evidence_ids",[])+c.get("contradicting_evidence_ids",[])
            valid=bool(refs) and all(r in byid for r in refs)
            if c.get("type")=="C" and valid:
                p=c["pair"]; left=[e for e in evidence if e["alert_key"]==p["left"]]; right=[e for e in evidence if e["alert_key"]==p["right"]]
                if left and right:
                    a,b=left[0],right[0]; fa,fb=a["fields"],b["fields"]
                    match=(bool(set(fa.get("synthetic.entities",[]))&set(fb.get("synthetic.entities",[]))) and abs(a["minutes"]-b["minutes"])<=2880) or (bool(set(fa.get("synthetic.techniques",[]))&set(fb.get("synthetic.techniques",[]))) and abs(a["minutes"]-b["minutes"])<=60)
                    contradiction=bool(fa.get("synthetic.conflict") or fb.get("synthetic.conflict"))
                    valid=(c["decision"]=="LINK" and match and not contradiction) or (c["decision"]=="NO_LINK" and not match and not contradiction) or c["decision"]=="UNSURE"
                else: valid=False
            elif c.get("type")=="P" and valid:
                valid=c.get("score") is not None and 0<=c["score"]<=1
            status="supported" if valid else "unverifiable" if not refs else "unsupported"
            statuses.append({"claim":c.get("reason_code","priority_claim"),"status":status,"evidence_ids":refs})
            unsupported|=status!="supported"
        return {"decision":"REVISE" if unsupported else "PASS","claims":statuses,"reason":"unsupported_or_unverifiable_claim" if unsupported else "citations_resolved","revision_request":"Use only supplied evidence and provide valid supporting citations." if unsupported else None,"review_reason":None}

