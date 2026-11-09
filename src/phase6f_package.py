"""Freeze an aggregate-only Phase 6 handoff package without changing source runs."""
from __future__ import annotations
import argparse, hashlib, json, platform, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

FILES = [
    "phases_outputs/Phase6B.md", "phases_outputs/Phase6B_audit.json", "phases_outputs/Phase6B_field_disposition.csv",
    "phases_outputs/Phase6C.md", "phases_outputs/Phase6D.md", "phases_outputs/Phase6E.md", "phases_outputs/Phase6G.md",
    "phases_outputs/Phase6.md", "phases_outputs/Phase6A_StudyProtocol.md", "phases_outputs/Phase6A.md",
    "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/metrics.json",
    "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/report.md",
    "outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/metrics.json",
    "outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/report.md",
    "dashboard/index.html", "phases_outputs/Phase6F.md", "phases_outputs/Phase6B-G.md",
    "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_precision_recall.png",
    "outputs/phase6/priority/phase6-priority-20261108-v2/evaluation/tie_aware/figures/priority_ndcg_direction_sensitivity.png",
    "outputs/phase6/correlation/phase6-correlation-20261108-v1/evaluation/corrected/figures/correlation_metrics.png",
]

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def build(root: Path, run_id: str) -> Path:
    root=root.resolve(); out=root/"outputs/phase6"/run_id
    if out.exists(): raise FileExistsError(f"refusing to overwrite {out}")
    sources={}
    for rel in FILES:
        p=root/rel
        if not p.is_file(): raise FileNotFoundError(f"required handoff input missing: {rel}")
        sources[rel]=digest(p)
    phase1=json.loads((root/"data/derived/audit/run_manifest.json").read_text(encoding="utf-8"))
    phase2=json.loads((root/"data/derived/preprocessing/run_manifest.json").read_text(encoding="utf-8"))
    pmetrics=json.loads((root/FILES[10]).read_text(encoding="utf-8"))
    cmetrics=json.loads((root/FILES[12]).read_text(encoding="utf-8"))
    out.mkdir(parents=True)
    for rel in FILES:
        src=root/rel
        dst=out/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    report=("# Final offline research handoff\n\n"
        "**Classification:** exploratory, assumption-based, local offline analysis.\n\n"
        "## Results included\n\n"
        f"- Priority retrieval: {pmetrics['test_organizations']} previously accessed organizations; {pmetrics['candidate_count']:,} oracle-group candidates. Primary tie-aware metrics are in `tie_aware_metrics.json`.\n"
        f"- Correlation: {cmetrics['test_organizations']} organizations; {cmetrics['unambiguous_alert_keys']:,} unambiguous alerts and {cmetrics['candidate_pairs']:,} candidate pairs. Full-positive-pair recall is {cmetrics['micro']['recall']:.6f}; candidate-generation coverage is {cmetrics['micro']['candidate_generation_coverage']:.6f}.\n"
        "- Interactive summary: `index.html`.\n\n"
        "## Limits\n\n"
        "The existing test cohort has been accessed, so these results are exploratory. Priority retrieval uses evaluator gold incident groups and is an oracle-group ceiling. The local queue universe and QueueRank direction are assumptions. Ambiguous alert mappings are excluded from correlation. Empirical LLM/multi-agent comparisons, valid 95% recall, a fresh confirmatory cohort, and production privacy/deployment validation are unavailable. No claim of model superiority, no-overfit guarantee, or deployment readiness is made.\n\n"
        "No raw inputs, restricted per-organization metrics, prediction rows, evaluator mappings, or credentials are included in this bundle. Reproduce artifact generation from the project root with the commands in `Phase6G.md` and the original Phase 6 run records.\n")
    (out/"FINAL_REPORT.md").write_text(report,encoding="utf-8")
    bundle_hashes={p.relative_to(out).as_posix():digest(p) for p in out.rglob("*") if p.is_file()}
    manifest={"protocol":"phase6-final-offline-handoff-v1","classification":"exploratory_assumption_based_local_offline","created_utc":datetime.now(timezone.utc).isoformat(),"run_id":run_id,"python":sys.version,"platform":platform.platform(),"source_artifact_sha256":sources,"raw_input_sha256_from_phase1_manifest":phase1["input_hashes"],"phase1_manifest_sha256":digest(root/"data/derived/audit/run_manifest.json"),"phase2_manifest_sha256":digest(root/"data/derived/preprocessing/run_manifest.json"),"split_assignment_sha256":json.loads((root/"data/derived/preprocessing/split_manifest.json").read_text(encoding="utf-8"))["assignment_sha256"],"included_files":sorted(bundle_hashes),"bundle_file_sha256":bundle_hashes,"contains_raw_or_row_level_data":False,"external_api_calls":0,"empirical_llm_comparison":"unavailable; no external model call authorized/performed","confirmatory_status":"blocked_existing_test_cohort_exploratory"}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    return out

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--root",default=".");ap.add_argument("--run-id",default="phase6-final-offline-20261109-v1");a=ap.parse_args()
    p=build(Path(a.root),a.run_id);print(json.dumps({"status":"aggregate_handoff_frozen","path":p.as_posix(),"files":len(list(p.iterdir()))},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
