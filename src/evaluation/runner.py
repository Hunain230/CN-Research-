from __future__ import annotations
import datetime as dt, hashlib, json, platform, time
from pathlib import Path
from .prediction_validation import strict_load_json, validate_predictions
from .truth_reader import read_synthetic_truth
from . import metrics, statistics as stats
from .report import render_report

class ResearchGateBlocked(RuntimeError): pass

def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _under(p,root): return Path(p).resolve().is_relative_to(Path(root).resolve())

def _evaluate_synthetic(pred_path,label_path,config,statistics_config):
    pred=validate_predictions(strict_load_json(pred_path)); truth=read_synthetic_truth(label_path)
    corr=metrics.correlation(truth["pair_truth"],pred["pair_predictions"],truth["candidate_pairs"],truth["full_pair_universe"])
    cluster=metrics.false_merge_split_components(truth["alert_truth"],pred["components"])
    rank=metrics.ranking(truth["expert_rank"],pred["ranked_candidates"],truth["rank_candidate_universe"],truth["judgements"])
    e2e=metrics.end_to_end_recall20(truth["gold_top20_groups"],pred["top20_components"],truth["alert_truth"])
    org={"org-syn-1":corr["candidate_set"]["f1"],"org-syn-2":1.0}
    boot=stats.paired_bootstrap({"o1":.8,"o2":.6,"o3":.4},{"o1":.5,"o2":.5,"o3":.5},statistics_config["bootstrap_resamples"],statistics_config["seed"])
    perm=stats.paired_permutation({"o1":1,"o2":2,"o3":3},{"o1":0,"o2":1,"o3":2},seed=statistics_config["seed"])
    return {"classification":"synthetic_evaluation_only_not_empirical","metric_version":"evaluation-metrics-v1","correlation":corr,"clustering_diagnostics":cluster,"ranking":rank,"end_to_end":e2e,"organization_aggregation_demo":stats.aggregate_by_organization(org),"paired_bootstrap_fixture":boot,"paired_permutation_fixture":perm,"holm_fixture":stats.holm_adjust({"b0":.01,"b1":.02,"b2":.03,"b3":.04}),"reviewer_metrics":metrics.reviewer_metrics(truth["review_annotations"]),"high_priority_miss_demo":metrics.high_priority_misses(truth["high_priority_cases"]),"operational":metrics.operational(pred["predictions"]+pred["pair_predictions"]),"synthetic_statistical_demos_are_not_significance_evidence":True}

def evaluate(root,mode,predictions,labels,config_path,out_path,command_line=None):
    root=Path(root); out=Path(out_path)
    if mode=="real":
        reasons=["approved model-visible feature view is empty","70,702 conflicting alert memberships block correlation and joint evaluation","QueueRank meaning/direction/query universe/top-20 completeness are unverified","organization split is provisional","no real-data predictions exist and B0 severity source/crosswalk is unavailable"]
        raise ResearchGateBlocked("real evaluation blocked: "+"; ".join(reasons))
    fixture=(root/"fixtures"/"stage5").resolve(); config_root=(root/"configs").resolve(); output_root=(root/"outputs"/"evaluation"/"synthetic").resolve()
    pp=(root/predictions).resolve(); lp=(root/labels).resolve(); cp=(root/config_path).resolve()
    if not _under(pp,fixture) or not _under(lp,fixture): raise ValueError("synthetic mode may read prediction and label fixtures/stage5 only")
    if not _under(cp,config_root) or not _under(out,output_root): raise ValueError("synthetic mode config/output path violates project boundary")
    if not pp.is_file() or not lp.is_file() or not cp.is_file(): raise FileNotFoundError("synthetic fixture/config missing")
    if out.exists(): raise FileExistsError("refusing to overwrite existing evaluation output")
    started=time.perf_counter(); start_utc=dt.datetime.now(dt.timezone.utc).isoformat()
    config=strict_load_json(cp)
    if config.get("schema_version")!="evaluation-v1" or config.get("mode")!="synthetic": raise ValueError("evaluation config schema/mode mismatch")
    metric_path=(root/config["metrics"]).resolve(); stat_path=(root/config["statistics"]).resolve(); schema_path=(root/config["prediction_schema"]).resolve()
    if not all(_under(p,config_root) for p in (metric_path,stat_path,schema_path)): raise ValueError("evaluation config path violates project boundary")
    schema=strict_load_json(schema_path)
    if schema.get("$id")!="evaluation-predictions-v1": raise ValueError("prediction schema version mismatch")
    metrics_config=strict_load_json(metric_path); statistics_config=strict_load_json(stat_path)
    if metrics_config.get("schema_version")!="evaluation-metrics-v1" or metrics_config.get("ranking",{}).get("gain")!="2^(21-expert_rank)-1 for ranks 1..20; 0 otherwise": raise ValueError("metric config violates frozen Phase 5 definitions")
    if statistics_config.get("schema_version")!="evaluation-statistics-v1" or statistics_config.get("bootstrap_resamples")!=10000 or statistics_config.get("bootstrap_confidence")!=.95: raise ValueError("statistics config violates frozen Phase 5 procedure")
    result=_evaluate_synthetic(pp,lp,config,statistics_config); out.mkdir(parents=True)
    (out/"metrics.json").write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    (out/"report.md").write_text(render_report(result),encoding="utf-8")
    code={str(p.relative_to(root)):_sha(p) for p in sorted((root/"src"/"evaluation").glob("*.py"))}
    manifest={"classification":result["classification"],"mode":"synthetic","command":command_line,"run_id":out.name,"started_utc":start_utc,"ended_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"runtime_ms":round((time.perf_counter()-started)*1000,3),"python":platform.python_version(),"prediction_sha256":_sha(pp),"synthetic_label_fixture_sha256":_sha(lp),"config_sha256":{"evaluation":_sha(cp),"metrics":_sha(metric_path),"statistics":_sha(stat_path),"prediction_schema":_sha(schema_path)},"code_sha256":code,"evaluator_version":"evaluation-v1","metric_version":"evaluation-metrics-v1","seed":config["seed"],"gate_status":"closed_for_real_data","output_sha256":{"metrics.json":_sha(out/"metrics.json"),"report.md":_sha(out/"report.md")}}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    return {"status":"synthetic_complete_not_empirical","output":str(out),"classification":result["classification"],"real_gate":"closed"}

def self_test(root):
    root=Path(root); fx=root/"fixtures"/"stage5"; expected=json.loads((fx/"expected.json").read_text()); truth=read_synthetic_truth(fx/"labels.json"); pred=validate_predictions(strict_load_json(fx/"predictions.json")); n=0
    c=metrics.correlation(truth["pair_truth"],pred["pair_predictions"],truth["candidate_pairs"],truth["full_pair_universe"])
    for k,v in expected["correlation"].items(): assert c["candidate_set"][k]==v; n+=1
    assert c["abstentions"]==1 and c["failures"]==1; n+=1
    assert c["pair_false_negatives"]==expected["pair_false_negatives"]; n+=1
    assert "false_splits" not in c and "false_merges" not in c; n+=1
    assert set(c["pair_false_negatives"])=={"candidate_set","full_eligible_pair"}; n+=1
    assert c["decision_coverage"]==expected["decision_coverage"] and c["candidate_generation_coverage"]["value"]==expected["candidate_generation_coverage"]["value"]; n+=1
    assert c["candidate_generation_coverage"]["numerator_candidate_pairs_in_full_universe"]==expected["candidate_generation_coverage"]["numerator_candidate_pairs_in_full_universe"] and c["candidate_generation_coverage"]["denominator_full_eligible_pair_count"]==expected["candidate_generation_coverage"]["denominator_full_eligible_pair_count"]; n+=1
    assert truth["org_scoped_incident_truth"]["org-a|same-incident"]!="org-b|same-incident"; n+=1
    assert c["full_eligible_pair"]["fn"]==2; n+=1
    assert metrics.correlation([],[],[],[])["candidate_set"]["f1"]==0; n+=1
    assert metrics.correlation([("x","y")],[],[("x","y")])["candidate_set"]["recall"]==0; n+=1
    missing=metrics.correlation([("a","b")],[],[("a","b")]); assert missing["missing_predictions"]==1 and missing["decision_coverage"]==0 and "candidate_generation_coverage" not in missing and missing["candidate_generation_coverage_status"].startswith("unavailable"); n+=1
    perfect=metrics.correlation([("a","b")],[{"left":"a","right":"b","decision":"LINK"}],[ ("a","b") ])
    assert perfect["candidate_set"]["f1"]==1; n+=1
    zero=metrics.correlation([], [{"left":"a","right":"b","decision":"LINK"}],[ ("a","b") ])
    assert zero["candidate_set"]["f1"]==0; n+=1
    cluster=metrics.false_merge_split_components(truth["alert_truth"],pred["components"])
    assert cluster==expected["cluster_diagnostics"] and set(cluster)=={"false_merges","false_splits","singleton_components"}; n+=1
    r=metrics.ranking(truth["expert_rank"],pred["ranked_candidates"],truth["rank_candidate_universe"],truth["judgements"])
    for k in ("precision_at_10","recall_at_20","ndcg_at_20"):
        assert abs(r[k]-expected["ranking"][k])<1e-12; n+=1
    empty_rank=metrics.ranking({},[],["only"],{"only":0})
    assert empty_rank["recall_at_20"]==0 and empty_rank["ndcg_at_20"]==0 and empty_rank["recall_at_20_denominator"]==0; n+=1
    try: metrics.ranking(truth["expert_rank"],pred["ranked_candidates"],truth["rank_candidate_universe"],{**truth["judgements"],"unknown":None}); raise AssertionError("partial labels accepted")
    except ValueError:n+=1
    e=metrics.end_to_end_recall20(truth["gold_top20_groups"],pred["top20_components"],truth["alert_truth"]); assert e["recovered"]==1; n+=1
    assert metrics.end_to_end_recall20({"g":["a","b","c","d","e"]},[["a","b","c"]],{"a":"g","b":"g","c":"g"})["recovered"]==0; n+=1
    assert metrics.end_to_end_recall20({"g":["a","b","c","d","e"]},[["a","b","c","d","x"]],{"a":"g","b":"g","c":"g","d":"g","e":"g","x":"x"})["recovered"]==1; n+=1
    assert metrics.end_to_end_recall20({"g":["a","b","c","d","e"]},[["a","b","c","d","x","y"]],{"a":"g","b":"g","c":"g","d":"g","e":"g","x":"x","y":"y"})["recovered"]==0; n+=1
    assert stats.aggregate_by_organization({"b":1,"a":0})["mean"]==.5; n+=1
    assert stats.paired_bootstrap({"a":1,"b":0},{"a":0,"b":0},10000,7)["mean_difference"]==.5; n+=1
    assert stats.paired_bootstrap({"a":.75},{"a":.5},10000,7)["ci_low"]==.25; n+=1
    assert stats.paired_permutation({"a":1,"b":2},{"a":0,"b":1})["p_value"]==.5; n+=1
    assert stats.holm_adjust({"a":.01,"b":.04,"c":.03,"d":.02})=={"a":.04,"d":.06,"c":.06,"b":.06}; n+=1
    assert metrics.reviewer_metrics(truth["review_annotations"])["agreement"]==.5; n+=1
    assert metrics.reviewer_metrics(truth["review_annotations"])["conflict_detection_recall"]==.5; n+=1
    assert metrics.reviewer_metrics(truth["review_annotations"])["citation_support_rate"]==.5; n+=1
    hm=metrics.high_priority_misses(truth["high_priority_cases"]); assert hm["misses"]==1 and hm["denominator_high_priority_auto_decided"]==2; n+=1
    for change in (lambda x:x["predictions"][0].update({"IncidentId":"SENTINEL_LABEL"}),lambda x:x["predictions"][0].update({"rank":float("nan")})):
        bad=json.loads(json.dumps(pred)); change(bad)
        try: validate_predictions(bad); raise AssertionError("invalid prediction accepted")
        except ValueError:n+=1
    try: metrics.ranking(truth["expert_rank"],pred["ranked_candidates"]+["i01"],truth["rank_candidate_universe"],truth["judgements"]); raise AssertionError("duplicate ranked candidate accepted")
    except ValueError:n+=1
    try: validate_predictions({**pred,"pair_predictions":pred["pair_predictions"]+[pred["pair_predictions"][0]]}); raise AssertionError("duplicate pair accepted")
    except ValueError:n+=1
    try:
        bad=json.loads(json.dumps(pred)); bad["pair_predictions"][0]["right_org"]="other-org"; validate_predictions(bad); raise AssertionError("cross-org pair accepted")
    except ValueError:n+=1
    try: json.loads('{"x":1,"x":2}',object_pairs_hook=lambda pairs: _no_dupes(pairs)); raise AssertionError("duplicate key accepted")
    except ValueError:n+=1
    config=json.loads((root/"configs/evaluation.yaml").read_text()); stat_config=json.loads((root/config["statistics"]).read_text())
    result1=_evaluate_synthetic(fx/"predictions.json",fx/"labels.json",config,stat_config)
    result2=_evaluate_synthetic(fx/"predictions.json",fx/"labels.json",config,stat_config)
    assert result1==result2; n+=1
    for base in (root/"src"/"agents",root/"src"/"baselines"):
        for py in base.rglob("*.py"):
            txt=py.read_text(encoding="utf-8")
            assert "evaluator_store" not in txt and "from src.evaluation" not in txt; n+=1
    try: evaluate(root,"synthetic","fixtures/stage5/predictions.json","fixtures/stage5/labels.json","data/raw/GUIDE_Test.csv","data/raw/should-not-be-created"); raise AssertionError("unsafe config/output path accepted")
    except ValueError:n+=1
    gate_out=root/"outputs"/"evaluation"/"real-self-test-blocked"
    try: evaluate(root,"real","missing-predictions","missing-real-label-store","configs/evaluation.yaml",gate_out); raise AssertionError("real gate did not block")
    except ResearchGateBlocked: n+=1
    assert not gate_out.exists(); n+=1
    return {"status":"pass","assertions":n,"classification":"synthetic_evaluation_only_not_empirical","real_data_gate":"closed"}

def _no_dupes(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError("duplicate key")
        d[k]=v
    return d

