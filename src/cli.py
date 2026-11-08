"""Bounded-memory Stage 1 dataset audit for GUIDE and AIP queue labels."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import struct
import json
import math
import os
import platform
import sqlite3
import sys
import traceback
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

GUIDE = ["Id","OrgId","IncidentId","AlertId","Timestamp","DetectorId","AlertTitle","Category","MitreTechniques","IncidentGrade","ActionGrouped","ActionGranular","EntityType","EvidenceRole","DeviceId","Sha256","IpAddress","Url","AccountSid","AccountUpn","AccountObjectId","AccountName","DeviceName","NetworkMessageId","EmailClusterId","RegistryKey","RegistryValueName","RegistryValueData","ApplicationId","ApplicationName","OAuthApplicationId","ThreatFamily","FileName","FolderPath","ResourceIdName","ResourceType","Roles","OSFamily","OSVersion","AntispamDirection","SuspicionLevel","LastVerdict","CountryCode","State","City","Usage"]
RANK = ["OrgId","IncidentId","QueueRank"]
LABELS = {"IncidentId","QueueRank","IncidentGrade","ActionGrouped","ActionGranular"}
SENSITIVE = {"DeviceId","Sha256","IpAddress","Url","AccountSid","AccountUpn","AccountObjectId","AccountName","DeviceName","NetworkMessageId","EmailClusterId","RegistryKey","RegistryValueName","RegistryValueData","ApplicationId","ApplicationName","OAuthApplicationId","FileName","FolderPath","ResourceIdName","CountryCode","State","City"}

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def parse_time(s):
    if not s: return None
    try:
        x=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
        if x.tzinfo is None: x=x.replace(tzinfo=dt.timezone.utc)
        return x.astimezone(dt.timezone.utc).isoformat()
    except ValueError: return None

def type_of(v):
    if not v: return "null"
    if v.lower() in ("true","false"): return "boolean_like"
    try: int(v); return "integer_like"
    except ValueError: pass
    try: float(v); return "numeric_like"
    except ValueError: return "string"

class HLL:
    """Fixed-memory cardinality estimate (p=12), keyed only by field/value hashes."""
    def __init__(self): self.registers=bytearray(4096)
    def add(self, value):
        x=int.from_bytes(hashlib.blake2b(value.encode("utf-8"),digest_size=8).digest(),"big")
        idx=x>>52; rem=x&((1<<52)-1); rank=(53-rem.bit_length()) if rem else 53
        if rank>self.registers[idx]: self.registers[idx]=rank
    def count(self):
        m=4096; alpha=0.7213/(1+1.079/m); z=sum(2.0**(-r) for r in self.registers)
        e=alpha*m*m/z; zeros=self.registers.count(0)
        return int(round(m*math.log(m/zeros))) if e<=2.5*m and zeros else int(round(e))

def disposition(col, null_rate, cardinality):
    if col in LABELS: return "deny", "Evaluator label/outcome; prohibited from all model-visible paths."
    if col == "Id": return "deny", "Lineage key; preserve for citations only after source review; never inference input."
    if col in ("OrgId","AlertId"): return "deny", "Partition/join key; keep in restricted control plane, never model input."
    if col in SENSITIVE: return "deny", "Sensitive identifier/entity value; requires approved transformation and privacy review."
    if col == "Timestamp": return "deny_pending", "Temporal availability and timezone semantics require source confirmation."
    if col in {"SuspicionLevel","LastVerdict","ThreatFamily","Usage"}: return "deny", "Potentially post-event or outcome-derived; source timing/provenance unverified."
    if col in {"DetectorId","AlertTitle","Category","MitreTechniques","EntityType","EvidenceRole","Roles","OSFamily","OSVersion","AntispamDirection"}:
        return "deny_pending", "Candidate evidence; point-in-time availability, provenance, and safe encoding require confirmation."
    return "deny_pending", "Default deny until source timing and feature safety are documented."

def main_validate(args):
    guide=Path(args.alerts); rank=Path(args.rankings); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    if not guide.is_file() or not rank.is_file(): raise RuntimeError("Required input file is missing")
    config=Path(args.config) if args.config else None
    config_text=config.read_text(encoding="utf-8") if config and config.exists() else "default: stage1-v1\n"
    cfg_hash=hashlib.sha256(config_text.encode()).hexdigest()
    # SQLite holds exact distinct-key and per-alert membership state on disk.
    with tempfile.TemporaryDirectory(prefix="cnet-audit-") as td:
        db=sqlite3.connect(str(Path(td)/"audit.sqlite")); db.execute("PRAGMA journal_mode=OFF")
        db.executescript("CREATE TABLE incidents(org TEXT,inc TEXT,PRIMARY KEY(org,inc)); CREATE TABLE alerts(org TEXT,alert TEXT,inc TEXT,det TEXT,ts TEXT); CREATE TABLE ranks(org TEXT,inc TEXT,rank TEXT); CREATE TABLE ids(id TEXT);")
        prof={}; schemas={}; rowcounts={}; malformed={}; files={}; cards_by_label={}
        for label,path,expected in (("GUIDE",guide,GUIDE),("queue",rank,RANK)):
            files[label]={"path":str(path),"bytes":path.stat().st_size,"sha256":digest(path)}
            nulls=Counter(); cards=defaultdict(HLL); distinct={}; inferred=defaultdict(Counter); whitespace=Counter(); leading=Counter(); rows=0; bad=0; headers=None
            # Text mode and explicit strings preserve IDs and leading zeroes.
            with open(path,"r",encoding="utf-8-sig",newline="") as f:
                reader=csv.reader(f)
                try: headers=next(reader)
                except StopIteration: raise RuntimeError(f"Empty CSV: {label}")
                if len(headers)!=len(set(headers)): raise RuntimeError(f"Duplicate headers in {label}")
                schemas[label]={"headers":headers,"expected_headers":expected,"missing_required":sorted(set(expected)-set(headers)),"additional_headers":sorted(set(headers)-set(expected)),"inferred_types":{}}
                if set(expected)-set(headers): raise RuntimeError(f"Required schema absent in {label}: {sorted(set(expected)-set(headers))}")
                # Dict reader equivalent without materializing rows.
                for vals in reader:
                    if len(vals)!=len(headers): bad+=1; continue
                    rows+=1; d=dict(zip(headers,vals))
                    for c,v in d.items():
                        if not v: nulls[c]+=1
                        else:
                            inferred[c][type_of(v)]+=1
                            if v!=v.strip(): whitespace[c]+=1
                            if v.startswith("0") and v.isdigit() and len(v)>1: leading[c]+=1
                            cards[c].add(v)
                    if label=="GUIDE":
                        org,inc,alert=d.get("OrgId",""),d.get("IncidentId",""),d.get("AlertId","")
                        if d.get("Id",""): db.execute("INSERT INTO ids VALUES(?)",(d["Id"],))
                        if org and inc: db.execute("INSERT OR IGNORE INTO incidents VALUES(?,?)",(org,inc))
                        if org and alert: db.execute("INSERT INTO alerts VALUES(?,?,?,?,?)",(org,alert,inc,d.get("DetectorId",""),parse_time(d.get("Timestamp",""))))
                    else: db.execute("INSERT INTO ranks VALUES(?,?,?)",(d.get("OrgId",""),d.get("IncidentId",""),d.get("QueueRank","")))
                    if rows%args.chunk_rows==0: db.commit()
            db.commit(); rowcounts[label]=rows; malformed[label]=bad
            cards_by_label[label]=cards
            prof[label]={"rows":rows,"malformed_rows":bad,"null_counts":dict(nulls),"non_null_rates":{c:round((rows-nulls[c])/rows,8) if rows else 0 for c in headers},"inferred_types":{c:dict(inferred[c]) for c in headers},"whitespace_values":dict(whitespace),"leading_zero_numeric_values":dict(leading)}
        # Fixed-memory HLL estimates; no distinct entity strings are retained.
        for label in ("GUIDE","queue"):
            prof[label]["cardinality_estimated"]={c:cards_by_label[label][c].count() for c in schemas[label]["headers"]}
        # relational summaries
        inc_count=db.execute("SELECT count(*) FROM incidents").fetchone()[0]
        alert_keys=db.execute("SELECT count(DISTINCT org||char(31)||alert) FROM alerts WHERE org<>'' AND alert<>''").fetchone()[0]
        repeated_evidence_groups=db.execute("SELECT count(*) FROM (SELECT org,alert FROM alerts WHERE alert<>'' GROUP BY org,alert HAVING count(*)>1)").fetchone()[0]
        conflicting_incident_groups=db.execute("SELECT count(*) FROM (SELECT org,alert FROM alerts WHERE alert<>'' GROUP BY org,alert HAVING count(DISTINCT inc)>1)").fetchone()[0]
        duplicate_id_groups=db.execute("SELECT count(*) FROM (SELECT id FROM ids GROUP BY id HAVING count(*)>1)").fetchone()[0]
        duplicate_id_rows=db.execute("SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM ids GROUP BY id HAVING count(*)>1)").fetchone()[0]
        rank_dups=db.execute("SELECT count(*) FROM (SELECT org,inc FROM ranks GROUP BY org,inc HAVING count(*)>1)").fetchone()[0]
        rank_null=db.execute("SELECT count(*) FROM ranks WHERE org='' OR inc='' OR rank=''").fetchone()[0]
        rank_values=[r[0] for r in db.execute("SELECT rank FROM ranks WHERE rank<>''")]; ints=[]; conv_err=0
        for x in rank_values:
            try: ints.append(int(x))
            except ValueError: conv_err+=1
        ties=db.execute("SELECT count(*) FROM (SELECT org,rank FROM ranks WHERE rank<>'' GROUP BY org,rank HAVING count(*)>1)").fetchone()[0]
        gaps=0; restarts=True
        for org, in db.execute("SELECT DISTINCT org FROM ranks"):
            vals=[]
            for v, in db.execute("SELECT rank FROM ranks WHERE org=?",(org,)):
                try: vals.append(int(v))
                except ValueError: pass
            if vals:
                s=set(vals); gaps+=sum(1 for n in range(min(s),max(s)+1) if n not in s)
                if min(s)!=1: restarts=False
        # Join with distinct guide incident keys only.
        guide_orgs={o for o, in db.execute("SELECT DISTINCT org FROM incidents")}
        rank_orgs={o for o, in db.execute("SELECT DISTINCT org FROM ranks")}
        matched=db.execute("SELECT count(*) FROM incidents i JOIN (SELECT DISTINCT org,inc FROM ranks) r ON i.org=r.org AND i.inc=r.inc").fetchone()[0]
        matched_r=db.execute("SELECT count(*) FROM (SELECT DISTINCT org,inc FROM ranks) r JOIN incidents i ON i.org=r.org AND i.inc=r.inc").fetchone()[0]
        rank_keys=db.execute("SELECT count(*) FROM (SELECT DISTINCT org,inc FROM ranks)").fetchone()[0]
        org_rows=[]
        for org, ninc, ndet, nlabels in db.execute("SELECT i.org,count(DISTINCT i.inc),count(DISTINCT a.det),count(DISTINCT r.inc) FROM incidents i LEFT JOIN alerts a ON i.org=a.org AND i.inc=a.inc LEFT JOIN ranks r ON i.org=r.org AND i.inc=r.inc GROUP BY i.org"):
            top20=db.execute("SELECT count(*) FROM ranks WHERE org=? AND rank IN ('1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20')",(org,)).fetchone()[0]
            eligible=ninc>=50 and ndet>=10 and top20==20
            org_rows.append((org,ninc,ndet,nlabels,top20,eligible))
        eligible=sum(bool(x[-1]) for x in org_rows)
        # Evidence columns disposition includes cardinality/null rates and no values.
        dispositions=[]
        for c in schemas["GUIDE"]["headers"]:
            allow,why=disposition(c,prof["GUIDE"]["non_null_rates"].get(c,0),prof["GUIDE"]["cardinality_estimated"].get(c,0))
            dispositions.append({"column":c,"null_rate":round(1-prof["GUIDE"]["non_null_rates"].get(c,0),8),"cardinality_estimate":prof["GUIDE"]["cardinality_estimated"].get(c,0),"allow_decision":allow,"rationale":why})
        for c in schemas["queue"]["headers"]:
            dispositions.append({"column":c,"null_rate":round(1-prof["queue"]["non_null_rates"].get(c,0),8),"cardinality_estimate":prof["queue"]["cardinality_estimated"].get(c,0),"allow_decision":"deny","rationale":"Evaluator label/join key; queue data is isolated from model-visible features."})
        # Anonymous org aggregate summary only; no org IDs in the report.
        org_summary=[{"org_ordinal":i+1,"guide_incidents":x[1],"distinct_detectors":x[2],"matched_label_keys":x[3],"top20_rank_count":x[4],"phase2_eligible":bool(x[5])} for i,x in enumerate(sorted(org_rows,key=lambda x:(-x[1],-x[2])))]
        checks={"schemas_match_observed":not schemas["GUIDE"]["additional_headers"] and not schemas["GUIDE"]["missing_required"] and not schemas["queue"]["additional_headers"] and not schemas["queue"]["missing_required"],"malformed_rows":sum(malformed.values()),"guide_id_missing_rows":prof["GUIDE"]["null_counts"].get("Id",0),"guide_id_duplicate_value_groups":duplicate_id_groups,"guide_id_duplicate_rows_beyond_first":duplicate_id_rows,"guide_incidents_distinct_composite":inc_count,"guide_alert_keys_distinct_composite":alert_keys,"repeated_evidence_row_groups_per_composite_alert_key":repeated_evidence_groups,"conflicting_incident_assignment_groups_per_composite_alert_key":conflicting_incident_groups,"ranking_rows":rowcounts["queue"],"duplicate_rank_key_groups":rank_dups,"null_rank_rows":rank_null,"rank_integer_conversion_errors":conv_err,"rank_tie_groups_within_org":ties,"rank_gaps_within_org":gaps,"rank_numbering_restarts_at_one_each_org":restarts,"composite_matched_keys":matched,"unmatched_guide_incidents":inc_count-matched,"unmatched_ranking_keys":rank_keys-matched_r,"incident_id_only_diagnostic_matches":db.execute("SELECT count(*) FROM (SELECT DISTINCT inc FROM incidents) i JOIN (SELECT DISTINCT inc FROM ranks) r USING(inc)").fetchone()[0],"qualified_orgs":eligible,"required_orgs_for_split":50,"split_feasible":eligible>=50,"alert_correlation_go":"no-go" if conflicting_incident_groups or not alert_keys else "conditional","incident_prioritization_preprocessing":"allowed with evaluator labels isolated and ambiguity preserved for investigation","incident_prioritization_evaluation":"blocked until rank scope and top-20 completeness are verified","joint_evaluation_go":"no-go","top20_completeness":"unverified; source evidence required","rank_scope":"unverified; source evidence required","candidate_pair_ceiling":"not computed: conflicting alert mappings block valid alert-level truth; labels remain evaluator-only"}
        for p in (guide,rank):
            pass
        validation={"audit_version":"stage1-v1","inputs":files,"rows":rowcounts,"checks":checks,"guide_profile":prof["GUIDE"],"queue_profile":prof["queue"],"per_organization_aggregate":org_summary,"source_metadata":{"release":"unverified","license":"unverified","download_date":"unverified"},"limitations":["The two local CSVs do not establish source release, license, download date, rank meaning, query universe, or top-20 label completeness.","All model-visible fields remain denied pending temporal provenance review.","Candidate pair recall ceiling requires verified alert-level truth and an approved entity normalization policy."]}
        (out/"validation.json").write_text(json.dumps(validation,indent=2,sort_keys=True),encoding="utf-8")
        (out/"schema.json").write_text(json.dumps(schemas,indent=2,sort_keys=True),encoding="utf-8")
        with (out/"field_disposition.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=dispositions[0].keys()); w.writeheader(); w.writerows(dispositions)
        with (out/"join_summary.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=org_summary[0].keys() if org_summary else ["org_ordinal","guide_incidents","distinct_detectors","matched_label_keys","top20_rank_count","phase2_eligible"]); w.writeheader(); w.writerows(org_summary)
        manifest={"command":"python -m src.cli validate","arguments":{"alerts":str(guide),"rankings":str(rank),"out":str(out),"chunk_rows":args.chunk_rows,"config":str(config) if config else None},"input_hashes":{k:v["sha256"] for k,v in files.items()},"config_sha256":cfg_hash,"python":platform.python_version(),"platform":platform.platform(),"csv_encoding":"utf-8-sig","identifier_policy":"preserved as strings; no numeric casts","seed":0,"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"source_metadata":validation["source_metadata"]}
        (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
        md=["# Stage 1 dataset validation","",f"Inputs: GUIDE {rowcounts['GUIDE']:,} rows; queue {rowcounts['queue']:,} rows.","","## Decisions","","- Alert correlation: **no-go** until conflicting alert mappings are understood.","- Incident prioritization preprocessing: **allowed** with evaluator labels isolated and ambiguity preserved for investigation.","- Incident prioritization evaluation: **blocked** until rank scope and top-20 completeness are verified.","- Joint evaluation: **no-go**.","","## Grain and key integrity","",f"- GUIDE Id: {checks['guide_id_missing_rows']:,} missing rows; {duplicate_id_groups:,} duplicated values across {duplicate_id_rows:,} excess rows.",f"- Repeated evidence-row groups per composite alert key: {repeated_evidence_groups:,} (may be normal at evidence-row grain).",f"- Conflicting incident assignment groups per composite alert key: {conflicting_incident_groups:,}.",f"- Distinct GUIDE composite incidents: {inc_count:,}; distinct alert keys: {alert_keys:,}.","","## Joins and ranking","",f"- Composite matched incidents: {matched:,}; unmatched GUIDE incidents: {inc_count-matched:,}; unmatched ranking keys: {rank_keys-matched_r:,}.",f"- Qualified organizations: {eligible} (50 required by the proposed 10/10/30 split).",f"- Duplicate ranking keys: {rank_dups:,}; missing rank rows: {rank_null:,}; conversion errors: {conv_err:,}; rank ties: {ties:,}; rank gaps: {gaps:,}.","- Rank direction, scope, query universe, and top-20 completeness are unverified from the local files.","","## Leakage and Stage 2 boundary","","All fields default denied. IncidentId, QueueRank, IncidentGrade, ActionGrouped and ActionGranular are evaluator-only. Stage 2 may develop leakage-safe preprocessing with labels stored separately and ambiguous alert mappings preserved for investigation. Do not create final evaluation-ready alert pairs or ranking results until Stage 1 gaps and label semantics are resolved.","","## Required evidence","","Provide the source release/license citation, download record/date, documentation that QueueRank 1 is highest and ranks 1-20 are complete expert labels for a defined query universe, and point-in-time provenance for evidence fields.",""]
        (out/"validation.md").write_text("\n".join(md),encoding="utf-8")
        db.close()
    return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    v=sub.add_parser("validate"); v.add_argument("--alerts",required=True); v.add_argument("--rankings",required=True); v.add_argument("--out",required=True); v.add_argument("--chunk-rows",type=int,default=250000); v.add_argument("--config",default="configs/validation.yaml"); a=p.parse_args()
    if a.chunk_rows<1: p.error("--chunk-rows must be positive")
    try: return main_validate(a)
    except Exception as e:
        traceback.print_exc(); return 2

if __name__=="__main__": raise SystemExit(main())
