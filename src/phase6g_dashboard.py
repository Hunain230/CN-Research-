"""Build an aggregate-only, self-contained Phase 6 results dashboard."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def payload(root: Path) -> dict:
    pp = root / "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/metrics.json"
    cp = root / "outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/metrics.json"
    gp = root / "phases_outputs/Phase6B_audit.json"
    for p in (pp, cp, gp):
        if not p.is_file(): raise FileNotFoundError(p)
    pri, cor, gate = (json.loads(p.read_text(encoding="utf-8")) for p in (pp, cp, gp))
    cond = {}
    for name, m in pri["conditions"].items():
        cond[name] = {"Precision@10": m["precision_at_10"]["mean"], "Recall@20": m["recall_at_20"]["mean"],
                      "nDCG@20 (rank 1 highest)": m["ndcg_at_20_rank1_highest"]["mean"],
                      "nDCG@20 (rank 20 highest)": m["ndcg_at_20_rank20_highest_sensitivity"]["mean"]}
    return {"priority": {"run": pri["prediction_run_id"], "orgs": pri["test_organizations"], "candidates": pri["candidate_count"], "conditions": cond},
            "correlation": {"run": cor["run_id"], "orgs": cor["test_organizations"], "alerts": cor["unambiguous_alert_keys"],
                            "candidate_pairs": cor["candidate_pairs"], "pair_universe": cor["full_same_org_pair_universe"],
                            "positive_pairs": cor["full_positive_pair_universe"], "micro": cor["micro"]},
            "readiness": {"production_fields": len(gate["official_field_policy_approved_fields"]),
                          "assumption_fields": gate["assumption_only_local_offline_fields"],
                          "ambiguous_keys": gate["ambiguity"]["conflicting_composite_alert_keys"],
                          "confirmatory": gate["status"]["confirmatory_real_data"],
                          "hosted_api": gate["status"]["hosted_llm_or_external_transmission"],
                          "privacy": gate["status"]["production_privacy_approval"]}}

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SOC Research Results</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#151e32;--line:#2a3854;--txt:#eef3ff;--muted:#a9b6ce;--cyan:#4dd9e8;--gold:#f4bf65}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% 0,#1b2850,transparent 35%),var(--bg);color:var(--txt);font:15px/1.55 system-ui,Segoe UI,sans-serif}.wrap{max-width:1120px;margin:auto;padding:28px 20px}h1{font-size:clamp(30px,5vw,50px);line-height:1.08;margin:20px 0}h2{font-size:18px;margin:0 0 12px}.muted{color:var(--muted)}.tag{display:inline-block;border:1px solid #796036;border-radius:999px;padding:5px 11px;color:#ffe0a1;font-size:12px}.warning{margin:20px 0;padding:14px 16px;border-radius:12px;background:#47351755;border:1px solid #795c30}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--line);margin-top:30px}.tabs button{background:none;border:0;color:var(--muted);padding:12px 16px;font:inherit;cursor:pointer}.tabs button.on{color:var(--txt);border-bottom:2px solid var(--cyan)}section{display:none;padding-top:20px}section.on{display:block}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.card,.box{background:linear-gradient(145deg,#17223a,#11192a);border:1px solid var(--line);border-radius:15px;padding:17px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.value{font-size:26px;font-weight:700;margin:5px 0}.box{margin-top:14px}.row{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)}.row:last-child{border:0}select{background:#0b1222;color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:9px}.bar{height:12px;background:#202c43;border-radius:8px;overflow:hidden;margin:6px 0 12px}.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),#a78bfa)}ul{color:var(--muted);padding-left:20px}li{margin:7px 0}footer{margin-top:28px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:12px}@media(max-width:540px){.wrap{padding:18px 13px}}
</style></head><body><main class="wrap"><span class="tag">Exploratory · local offline</span><h1>Security incident prioritization and correlation</h1><p class="muted">Aggregate view of the saved Phase 6 results and current research gates.</p><div class="warning"><b>Interpret cautiously.</b> Test labels were accessed. Results are exploratory, not confirmatory or deployment validation. No empirical LLM or multi-agent comparison was run.</div>
<p><a href="simulation.html" style="display:inline-block;color:#081421;background:#4dd9e8;border-radius:9px;padding:10px 14px;font-weight:700;text-decoration:none">Open separate synthetic live demo →</a></p>
<nav class="tabs"><button class="on" data-id="priority">Priority</button><button data-id="correlation">Correlation</button><button data-id="readiness">Readiness</button></nav>
<section id="priority" class="on"><div id="pc" class="grid"></div><div class="box"><h2>Explore priority ablations</h2><p><label>Condition&nbsp; <select id="condition"></select></label></p><div id="conditionMetrics"></div></div><div class="box"><h2>Limits</h2><ul><li>Gold incident membership formed the candidate groups; this is an oracle-group ceiling, not end-to-end correlation.</li><li>The local candidate universe proxies the publisher queue snapshot.</li><li>QueueRank direction remains unresolved; both nDCG directions are shown.</li><li>Previously accessed test results cannot be used to tune the method.</li><li>The five fields are local offline assumptions, not independent privacy/timing approval.</li></ul><b>95% recall target:</b> not established.</div></section>
<section id="correlation"><div id="cc" class="grid"></div><div class="box"><h2>Method limits</h2><ul><li>Conflicting alert keys are excluded; their assignment semantics remain unresolved.</li><li>Candidate coverage of the full within-organization pair universe is very low.</li><li>This is a bounded diagnostic, not a full-data or joint result.</li></ul><div id="pairBars"></div><div class="row"><span>Empirical LLM / multi-agent comparison</span><b>Unavailable</b></div></div></section>
<section id="readiness"><div id="rc" class="grid"></div><div class="box"><h2>Current gates</h2><div id="gates"></div><p class="muted">The dashboard displays saved aggregate reports only. It contains no alert-level rows, incident mappings, predictions, organization IDs, credentials, or live model calls.</p></div></section>
<footer>Generated from aggregate Phase 6 reports and the Module 6B audit. Single-file static page; can be hosted on a static web host. No external scripts or network requests.</footer></main>
<script>const D=__PAYLOAD__;const f=x=>Number(x).toFixed(4),pct=x=>(100*Number(x)).toFixed(3)+'%';function cards(id,items){document.getElementById(id).innerHTML=items.map(([a,b,c])=>`<article class="card"><div class="label">${a}</div><div class="value">${b}</div><div class="muted">${c||''}</div></article>`).join('')}const names=Object.keys(D.priority.conditions);const primary=D.priority.conditions.primary;cards('pc',[['Organizations',D.priority.orgs,'previously accessed test cohort'],['Candidates',D.priority.candidates.toLocaleString(),'oracle-group universe'],['Precision@10',f(primary['Precision@10']),'organization mean'],['Recall@20',f(primary['Recall@20']),'organization mean'],['nDCG@20 · rank 1 high',f(primary['nDCG@20 (rank 1 highest)']),'assumed direction'],['nDCG@20 · rank 20 high',f(primary['nDCG@20 (rank 20 highest)']),'direction sensitivity']]);const sel=document.getElementById('condition');names.forEach(n=>sel.add(new Option(n,n)));function showCondition(){const x=D.priority.conditions[sel.value];document.getElementById('conditionMetrics').innerHTML=Object.entries(x).map(([k,v])=>`<div class="row"><span>${k}</span><b>${f(v)}</b></div><div class="bar"><i style="width:${Math.max(0,Math.min(100,100*v))}%"></i></div>`).join('')}sel.onchange=showCondition;showCondition();const c=D.correlation,m=c.micro;cards('cc',[['Unambiguous alert keys',c.alerts.toLocaleString(),'conflicts excluded'],['Generated pairs',c.candidate_pairs.toLocaleString(),'bounded candidates'],['Pair precision',pct(m.precision),'micro'],['Full positive-pair recall',pct(m.recall),'micro'],['Full-pair F1',pct(m.f1),'micro'],['Pair candidate coverage',pct(m.candidate_generation_coverage),'of within-org pair universe']]);document.getElementById('pairBars').innerHTML=`<p>Full positive-pair recall ${pct(m.recall)}</p><div class="bar"><i style="width:${100*m.recall}%"></i></div><p>Candidate-generation coverage ${pct(m.candidate_generation_coverage)}</p><div class="bar"><i style="width:${100*m.candidate_generation_coverage}%"></i></div>`;const r=D.readiness;cards('rc',[['Approved production fields',r.production_fields,'official allowlist remains empty'],['Local assumption fields',r.assumption_fields.length,'offline experiments only'],['Confirmatory evaluation','Blocked','existing test is exploratory'],['Production approval','Unresolved','timing/privacy review']]);document.getElementById('gates').innerHTML=[['Fresh confirmatory cohort',r.confirmatory],['Hosted LLM calls',r.hosted_api],['Field provenance/privacy',r.privacy]].map(([a,b])=>`<div class="row"><span>${a}</span><b>${b}</b></div>`).join('');document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));document.querySelectorAll('section').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.getElementById(b.dataset.id).classList.add('on')});</script></body></html>'''

def write_dashboard(root: Path, data: dict) -> Path:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = HTML.replace("__PAYLOAD__", encoded)
    out = root / "dashboard/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--root", default="."); args = ap.parse_args()
    root = Path(args.root).resolve(); out = write_dashboard(root, payload(root))
    print(json.dumps({"status":"dashboard_built","path":out.relative_to(root).as_posix(),"bytes":out.stat().st_size}, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
