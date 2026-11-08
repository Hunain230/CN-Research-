"""Metrics are evaluator-only; truth objects must never be passed back to model code."""
from __future__ import annotations
import math

def _prf(tp,fp,fn):
    p=tp/(tp+fp) if tp+fp else 0.0; r=tp/(tp+fn) if tp+fn else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0.0,"precision_zero_denominator":tp+fp==0,"recall_zero_denominator":tp+fn==0}

def correlation(truth,predictions,candidate_universe,full_universe=None):
    """candidate universe is explicit; abstentions count as FN for positive truth, outside decision coverage."""
    gold={tuple(sorted(x)) for x in truth}; universe={tuple(sorted(x)) for x in candidate_universe}
    rows={tuple(sorted((p["left"],p["right"]))):p for p in predictions}
    if set(rows)-universe: raise ValueError("prediction outside candidate universe")
    tp=fp=fn=tn=0; abstain=failed=missing=0
    for pair in universe:
        pred=rows.get(pair); positive=pair in gold
        if pred is None: # eligible candidate omitted by prediction is a miss only if positive
            fn+=positive; missing+=1; continue
        if pred.get("failure"): failed+=1; fn+=positive
        elif pred.get("decision") in ("UNSURE","REVIEW") or pred.get("abstention"): abstain+=1; fn+=positive
        elif pred.get("decision")=="LINK": tp+=positive; fp+=not positive
        elif pred.get("decision")=="NO_LINK": fn+=positive; tn+=not positive
        else: raise ValueError("invalid correlation decision")
    cand=_prf(tp,fp,fn)
    cand["tn"]=tn if full_universe is not None and universe=={tuple(sorted(x)) for x in full_universe} else None
    full=None
    if full_universe is not None:
        fset={tuple(sorted(x)) for x in full_universe}
        if not universe<=fset or not gold<=fset: raise ValueError("candidate/full universe mismatch")
        omitted=sum(1 for x in gold if x not in universe)
        full=_prf(tp,fp,fn+omitted)
    valid_decisions=len(universe)-abstain-failed-missing
    decision_coverage=valid_decisions/len(universe) if universe else 0.0
    generation_coverage=None; generation_status="unavailable_no_explicit_full_pair_universe"
    if full_universe is not None:
        fset={tuple(sorted(x)) for x in full_universe}
        if fset:
            covered=len(universe & fset)
            generation_coverage={"value":covered/len(fset),"numerator_candidate_pairs_in_full_universe":covered,"denominator_full_eligible_pair_count":len(fset)}
            generation_status="available"
        else:
            generation_status="unavailable_empty_full_pair_universe"
    result={"candidate_set":cand,"full_eligible_pair":full,"pair_false_positives":fp,"pair_false_negatives":{"candidate_set":fn,"full_eligible_pair":full["fn"] if full is not None else None},"abstentions":abstain,"failures":failed,"missing_predictions":missing,"candidate_count":len(universe),"valid_decision_count":valid_decisions,"decision_coverage":decision_coverage,"candidate_generation_coverage_status":generation_status,"denominator_policy":"abstention/failure/missing are separate and count as pair FN for positive recall; TN requires an explicit exhaustive universe"}
    if generation_coverage is not None: result["candidate_generation_coverage"]=generation_coverage
    return result

def false_merge_split_components(truth_by_alert,components):
    """Per-org diagnostic: each predicted component containing >1 truth group is one false merge; each truth group split across >1 predicted component is one false split."""
    pred_of={a:i for i,c in enumerate(components) for a in c}; truth_sets={}
    for alert,group in truth_by_alert.items(): truth_sets.setdefault(group,set()).add(alert)
    merges=sum(1 for c in components if len({truth_by_alert[a] for a in c if a in truth_by_alert})>1)
    splits=sum(1 for g,alerts in truth_sets.items() if len({pred_of[a] for a in alerts if a in pred_of})>1)
    return {"false_merges":merges,"false_splits":splits,"singleton_components":sum(len(c)==1 for c in components)}

def _complete_judgements(candidate_universe,judgements):
    if set(candidate_universe)!=set(judgements) or any(v is None for v in judgements.values()): raise ValueError("partial judgments: metric invalid until protocol approves a policy")

def ranking(truth_rank, ranked_candidates, candidate_universe, judgements, k_precision=10,k_recall=20,k_ndcg=20):
    _complete_judgements(candidate_universe,judgements)
    if not set(truth_rank)<=set(candidate_universe) or any(not isinstance(v,int) or v<1 or v>20 for v in truth_rank.values()) or len(set(truth_rank.values()))!=len(truth_rank): raise ValueError("expert top-20 rank labels invalid or outside candidate universe")
    if len(ranked_candidates)!=len(set(ranked_candidates)): raise ValueError("duplicate ranked candidate")
    if not set(ranked_candidates)<=set(candidate_universe): raise ValueError("ranked item outside candidate universe")
    ordered=list(ranked_candidates); relevant=set(truth_rank)
    pden=k_precision # fixed cutoff; missing slots do not count relevant
    prec=sum(x in relevant for x in ordered[:k_precision])/pden
    retrieved=sum(x in relevant for x in ordered[:k_recall]); rden=len(relevant); rec=retrieved/rden if rden else 0.0
    def gain(x):
        r=truth_rank.get(x)
        return 2**(21-r)-1 if isinstance(r,int) and 1<=r<=20 else 0
    dcg=sum(gain(x)/math.log2(i+2) for i,x in enumerate(ordered[:k_ndcg]))
    ideal=sorted((gain(x) for x in candidate_universe),reverse=True)[:k_ndcg]
    idcg=sum(g/math.log2(i+2) for i,g in enumerate(ideal)); ndcg=dcg/idcg if idcg else 0.0
    return {"precision_at_10":prec,"precision_at_10_denominator":pden,"recall_at_20":rec,"recall_at_20_denominator":rden,"relevant_retrieved_at_20":retrieved,"ndcg_at_20":ndcg,"dcg_at_20":dcg,"idcg_at_20":idcg,"candidate_count":len(candidate_universe),"judgment_coverage":len(judgements)/len(candidate_universe) if candidate_universe else 0.0,"unjudged_policy":"invalid; never map unknown to irrelevant","missing_candidates":len(set(candidate_universe)-set(ordered))}

def end_to_end_recall20(gold_groups, top20_components, alert_truth):
    recovered=0; details=[]
    for gold_id, gold_alerts in gold_groups.items():
        found=False; reason="ranking_outside_top20"
        for comp in top20_components:
            overlap=len(set(gold_alerts)&set(comp)); completeness=overlap/len(gold_alerts) if gold_alerts else 0
            purity=sum(alert_truth.get(a)==gold_id for a in comp)/len(comp) if comp else 0
            if completeness>=.8 and purity>=.8: found=True; reason="recovered"; break
            if overlap:
                reason="false_split_completeness_below_80" if completeness<.8 else "false_merge_purity_below_80"
        recovered+=found; details.append({"gold_key":gold_id,"recovered":found,"reason":reason})
    return {"recovered":recovered,"eligible_gold_top20":len(gold_groups),"recall_at_20":recovered/len(gold_groups) if gold_groups else 0.0,"details":details,"completeness_threshold":.8,"purity_threshold":.8}

def reviewer_metrics(annotations):
    if not annotations:return {"agreement":0.0,"items":0,"kappa":None,"conflict_detection_recall":0.0,"citation_support_rate":0.0}
    n=len(annotations); agree=sum(a["r1"]==a["r2"] for a in annotations); po=agree/n
    labels={v for a in annotations for v in (a["r1"],a["r2"])}
    pe=sum((sum(a["r1"]==v for a in annotations)/n)*(sum(a["r2"]==v for a in annotations)/n) for v in labels)
    kappa=(po-pe)/(1-pe) if pe<1 else (1.0 if po==1 else 0.0)
    tp=sum(a["gold_conflict"] and a["predicted_conflict"] for a in annotations); pos=sum(a["gold_conflict"] for a in annotations)
    annotated=[a for a in annotations if "citation_supported" in a]
    return {"agreement":po,"items":n,"kappa":kappa,"conflict_detection_recall":tp/pos if pos else 0.0,"citation_support_rate":sum(a["citation_supported"] is True for a in annotated)/len(annotated) if annotated else 0.0,"citation_support_denominator":len(annotated)}

def high_priority_misses(rows):
    decided=[x for x in rows if x.get("auto_decided") is True]
    positives=[x for x in decided if x.get("gold_high_priority") is True]
    misses=sum(not x.get("recovered") for x in positives)
    return {"misses":misses,"denominator_high_priority_auto_decided":len(positives),"miss_rate":misses/len(positives) if positives else 0.0,"policy":"count only gold high-priority items among auto-decided cases"}

def operational(predictions):
    lat=sorted(p["latency_ms"] for p in predictions if p.get("latency_ms") is not None)
    def pct(q):
        if not lat:return None
        return lat[max(0,math.ceil(q*len(lat))-1)]
    n=len(predictions); abst=sum(bool(p.get("abstention")) for p in predictions); failed=sum(bool(p.get("failure")) for p in predictions)
    return {"predictions":n,"review_abstention_fraction":abst/n if n else 0.0,"failure_fraction":failed/n if n else 0.0,"p50_latency_ms":pct(.5),"p95_latency_ms":pct(.95),"input_tokens":sum(p.get("input_tokens",0) for p in predictions),"output_tokens":sum(p.get("output_tokens",0) for p in predictions)}
