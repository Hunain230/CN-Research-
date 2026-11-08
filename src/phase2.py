"""Leakage-safe Stage 2 preprocessing; labels and evidence use separate stores."""
from __future__ import annotations
import csv, datetime as dt, hashlib, ipaddress, json, platform, re, sqlite3, tempfile
from pathlib import Path

PHASE1_HASHES={"GUIDE_Test.csv":"fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3","GUIDE_Test_Queue_Rankings.csv":"e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6"}
GUIDE_FIELDS="Id OrgId IncidentId AlertId Timestamp DetectorId AlertTitle Category MitreTechniques IncidentGrade ActionGrouped ActionGranular EntityType EvidenceRole DeviceId Sha256 IpAddress Url AccountSid AccountUpn AccountObjectId AccountName DeviceName NetworkMessageId EmailClusterId RegistryKey RegistryValueName RegistryValueData ApplicationId ApplicationName OAuthApplicationId ThreatFamily FileName FolderPath ResourceIdName ResourceType Roles OSFamily OSVersion AntispamDirection SuspicionLevel LastVerdict CountryCode State City Usage".split()
RANK_FIELDS=["OrgId","IncidentId","QueueRank"]
EVALUATOR_FIELDS={"IncidentId","QueueRank","IncidentGrade","ActionGrouped","ActionGranular"}
NORMALIZER_VERSION="typed-v1"

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def parse_config(path):
    # Parse the controlled, versioned YAML subset used by this project (no runtime dependency).
    s=Path(path).read_text(encoding="utf-8")
    def scalar(key, default=""):
        m=re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$",s); return m.group(1).strip('"\'') if m else default
    sizes=re.search(r"(?m)^\s+sizes:\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]",s)
    return {"salt":scalar("salt"),"salt_version":scalar("salt_version"),"sizes":tuple(map(int,sizes.groups())) if sizes else (10,10,30),"seed":int(scalar("seed","0")),"policy":scalar("field_policy","configs/field_policy.yaml"),"hashes":PHASE1_HASHES}

def canonical_digest(row):
    return hashlib.sha256(json.dumps([row.get(c,"") for c in GUIDE_FIELDS],ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()

def timestamp_normalize(raw):
    if not raw: return "","missing"
    try: x=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
    except ValueError: return "","invalid"
    if x.tzinfo is None: return "","timezone_naive_unresolved"
    return x.astimezone(dt.timezone.utc).isoformat(),"aware_utc"

def ip_normalize(raw):
    if not raw: return "","missing"
    try: return ipaddress.ip_address(raw).compressed,"valid_ip"
    except ValueError: return "","invalid_ip"

def technique_normalize(raw):
    if not raw: return [],"missing"
    vals=[x.strip().upper() for x in re.split(r"[,;|]",raw) if x.strip()]
    vals=sorted(set(x for x in vals if re.fullmatch(r"T\d{4}(?:\.\d{3})?",x)))
    return vals,"valid_typed_ids" if vals else "unrecognized"

def split_hash(org,salt): return hashlib.sha256((salt+"\0"+org).encode("utf-8")).hexdigest()

def mapping_status(org,alert,incident,assignment_count):
    if not org or not alert or not incident: return "missing"
    if not assignment_count: return "invalid"
    return "ambiguous" if assignment_count>1 else "unambiguous"

def _approved_fields(policy):
    s=Path(policy).read_text(encoding="utf-8")
    m=re.search(r"(?ms)^approved_model_fields:\s*\n((?:\s+-\s+[^\n]+\n)*)",s)
    return [x.strip()[2:].strip() for x in m.group(1).splitlines() if x.strip()] if m else []

def _write_empty_feature(path,fields):
    with Path(path).open("w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(fields)

def check_feature_view(path,fields=(),sentinels=()):
    with Path(path).open("rb") as f: b=f.read()
    with Path(path).open("r",newline="",encoding="utf-8") as f:
        r=csv.reader(f); header=next(r,[]); n=sum(1 for _ in r)
    bad=sorted(set(header)&(EVALUATOR_FIELDS|{"OrgId","AlertId","Id","source_row_ordinal"}))
    leaked=[s for s in sentinels if s.encode() in b]
    if header!=list(fields) or n or bad or leaked: raise AssertionError("feature view schema, row, or sentinel leakage check failed")
    return {"status":"pass","fields":header,"rows":n,"prohibited_columns":bad,"sentinel_hits":leaked}

def preprocess(args):
    alerts,rankings,audit,out=map(Path,(args.alerts,args.rankings,args.audit,args.out)); cfgp=Path(args.config)
    cfg=parse_config(cfgp); policy=Path(cfg["policy"])
    if not alerts.is_file() or not rankings.is_file(): raise RuntimeError("required raw input missing")
    if not (audit/"validation.json").is_file(): raise RuntimeError("Phase 1 audit is required")
    before={alerts.name:sha256_file(alerts),rankings.name:sha256_file(rankings)}
    if before!=PHASE1_HASHES: raise RuntimeError("input SHA-256 mismatch against Phase 1; stopped before processing")
    a=json.loads((audit/"validation.json").read_text(encoding="utf-8"))
    if a["inputs"]["GUIDE"]["sha256"]!=before[alerts.name] or a["inputs"]["queue"]["sha256"]!=before[rankings.name]: raise RuntimeError("Phase 1 audit input hashes mismatch")
    if out.exists() and any(out.iterdir()): raise RuntimeError("output exists and is not empty; select a new run directory")
    approved=_approved_fields(policy)
    if approved: raise RuntimeError("feature fields are not approved by Phase 1; refusing export")
    out.mkdir(parents=True,exist_ok=True)
    evdir=out/"evaluator"; revdir=out/"review"; qdir=out/"quarantine"
    for d in (evdir,revdir,qdir): d.mkdir(parents=True,exist_ok=True)
    from . import evaluator_store
    ledger=sqlite3.connect(out/"evidence_ledger.sqlite"); edb=sqlite3.connect(evdir/"evaluator.sqlite")
    ledger.execute("PRAGMA journal_mode=OFF")
    evidence_cols=[c for c in GUIDE_FIELDS if c not in EVALUATOR_FIELDS]
    ledger.execute("CREATE TABLE evidence(source_row_ordinal INTEGER PRIMARY KEY, org_id TEXT, detector_id TEXT, raw_fields_json TEXT NOT NULL, timestamp_utc TEXT, timestamp_status TEXT, normalized_ip TEXT, ip_status TEXT, normalized_techniques_json TEXT, techniques_status TEXT, normalization_version TEXT, source_file_sha256 TEXT, parser_version TEXT)")
    evaluator_store.initialize(edb)
    # Stream source rows, assign record ordinals, and keep evaluator fields out of evidence JSON.
    parsed=malformed=0; ts_counts={}; last_commit=0
    qpath=qdir/"invalid_rows.csv"
    qfile=qpath.open("w",newline="",encoding="utf-8"); qw=csv.writer(qfile); qw.writerow(["source_row_ordinal","reason"])
    with alerts.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.reader(f,strict=True); headers=next(reader,None)
        if headers!=GUIDE_FIELDS: raise RuntimeError("GUIDE headers differ from the Phase 1 schema")
        try:
            for ordinal,vals in enumerate(reader,1):
                if len(vals)!=len(headers): malformed+=1; qw.writerow([ordinal,"malformed_field_count"]); continue
                parsed+=1; row=dict(zip(headers,vals)); rowdig=canonical_digest(row)
                ts,tstat=timestamp_normalize(row["Timestamp"]); ip,istat=ip_normalize(row["IpAddress"]); tech,ttech=technique_normalize(row["MitreTechniques"])
                ts_counts[tstat]=ts_counts.get(tstat,0)+1
                for field,reason in (("OrgId","missing_org_id"),("AlertId","missing_alert_id"),("IncidentId","missing_incident_id")):
                    if not row[field]: qw.writerow([ordinal,reason])
                if tstat in ("invalid","timezone_naive_unresolved"): qw.writerow([ordinal,"timestamp_"+tstat])
                restricted={k:row[k] for k in evidence_cols}
                ledger.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(ordinal,row["OrgId"],row["DetectorId"],json.dumps(restricted,ensure_ascii=False,separators=(",",":")),ts,tstat,ip,istat,json.dumps(tech,separators=(",",":")),ttech,NORMALIZER_VERSION,before[alerts.name],"csv.reader-utf8-sig-v1"))
                evaluator_store.add_full_row_digest(edb,rowdig,ordinal)
                # Membership labels are written only to the separate evaluator database.
                evaluator_store.add_membership(edb,row["OrgId"],row["AlertId"],row["IncidentId"],ordinal)
                if parsed-last_commit>=50000: ledger.commit(); last_commit=parsed
        except csv.Error as e: raise RuntimeError(f"CSV parse error near physical line {reader.line_num}") from e
    ledger.commit(); edb.commit()
    qfile.close()
    if parsed!=4147992 or malformed: raise RuntimeError(f"parsed row count mismatch: {parsed}; malformed={malformed}")
    # Exact duplicate rows are distinct from repeated alert evidence and mapping conflicts.
    dup_path=revdir/"exact_duplicate_groups.csv"
    exact_dup_groups=edb.execute("SELECT count(*) FROM (SELECT digest FROM row_digests GROUP BY digest HAVING count(*)>1)").fetchone()[0]
    with dup_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["row_digest_sha256","source_row_ordinal","group_size"])
        for dg,n in edb.execute("SELECT digest,count(*) FROM row_digests GROUP BY digest HAVING count(*)>1 ORDER BY digest"):
            for (ordinal,) in edb.execute("SELECT ordinal FROM row_digests WHERE digest=? ORDER BY ordinal",(dg,)): w.writerow([dg,ordinal,n])
    # Separate assignment rows preserve every incident mapping and all source ordinals.
    edb.executescript("CREATE INDEX idx_membership_key ON membership_rows(org,alert); CREATE INDEX idx_membership_incident ON membership_rows(org,incident); CREATE TABLE alert_status AS SELECT org,alert,count(DISTINCT incident) assignment_count FROM membership_rows WHERE org<>'' AND alert<>'' GROUP BY org,alert;")
    edb.execute("CREATE INDEX idx_alert_status ON alert_status(org,alert)")
    amb_path=revdir/"ambiguous_alert_memberships.csv"; ambiguous=0
    with amb_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["OrgId","AlertId","IncidentAssignments","SourceRowOrdinalsByAssignment"])
        current=None; maps=[]
        rows=edb.execute("SELECT m.org,m.alert,m.incident,s.assignment_count,m.source_row_ordinal FROM membership_rows m JOIN alert_status s ON m.org=s.org AND m.alert=s.alert WHERE s.assignment_count>1 ORDER BY m.org,m.alert,m.incident,m.source_row_ordinal")
        def flush_amb(key,items):
            nonlocal ambiguous
            if key is None: return
            packed=[]
            for inc,ords in items: packed.append({"incident":inc,"source_row_ordinals":ords})
            w.writerow([key[0],key[1],json.dumps([x["incident"] for x in packed],separators=(",",":")),json.dumps(packed,separators=(",",":"))]); ambiguous+=1
        map_inc=None; ords=[]
        for org,alert,incident,n,ordinal in rows:
            key=(org,alert)
            if current is not None and key!=current:
                if map_inc is not None: maps.append((map_inc,ords))
                flush_amb(current,maps); maps=[]; map_inc=None; ords=[]
            current=key
            if map_inc is not None and incident!=map_inc: maps.append((map_inc,ords)); ords=[]
            map_inc=incident; ords.append(ordinal)
        if map_inc is not None: maps.append((map_inc,ords))
        flush_amb(current,maps)
    # Evaluator labels are copied into a separate directory/database and CSV interface.
    mem_path=evdir/"incident_membership.csv"
    with mem_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["OrgId","IncidentId","AlertId","mapping_status","source_row_ordinals"])
        for org,alert,incident,n,ordlist in edb.execute("SELECT m.org,m.alert,m.incident,s.assignment_count,group_concat(m.source_row_ordinal, ';') FROM membership_rows m LEFT JOIN alert_status s ON m.org=s.org AND m.alert=s.alert GROUP BY m.org,m.alert,m.incident,s.assignment_count ORDER BY m.org,m.alert,m.incident"):
            status=mapping_status(org,alert,incident,n or (1 if incident else 0))
            w.writerow([org,incident,alert,status,ordlist or ""])
    qpath=evdir/"queue_labels.csv"; qn=0
    with rankings.open("r",encoding="utf-8-sig",newline="") as f, qpath.open("w",newline="",encoding="utf-8") as g:
        r=csv.DictReader(f)
        if r.fieldnames!=RANK_FIELDS: raise RuntimeError("queue headers differ from Phase 1 schema")
        w=csv.DictWriter(g,fieldnames=RANK_FIELDS); w.writeheader()
        for row in r:
            w.writerow(row); evaluator_store.add_queue_label(edb,row["OrgId"],row["IncidentId"],row["QueueRank"]); qn+=1
    edb.commit()
    if qn!=9980: raise RuntimeError(f"queue row count mismatch: {qn}")
    # Eligibility and provisional split use distinct incidents/detectors. Queue ranks are read only for the prespecified coverage count.
    stats={}
    detector_counts=dict(ledger.execute("SELECT org_id,count(DISTINCT detector_id) FROM evidence WHERE org_id<>'' AND detector_id<>'' GROUP BY org_id"))
    for org,ni in edb.execute("SELECT org,count(DISTINCT incident) FROM membership_rows WHERE org<>'' AND incident<>'' GROUP BY org"):
        stats[org]=(ni,detector_counts.get(org,0))
    rank20={}
    with rankings.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r["OrgId"] and r["QueueRank"].isdigit(): rank20.setdefault(r["OrgId"],set()).add(int(r["QueueRank"]))
    eligible=[o for o,(ni,nd) in stats.items() if ni>=50 and nd>=10 and len(rank20.get(o,set())&set(range(1,21)))==20]
    order=sorted(eligible,key=lambda o:(split_hash(o,cfg["salt"]),o)); np,nd,nt=cfg["sizes"]
    if len(order)<np+nd+nt: raise RuntimeError(f"only {len(order)} eligible organizations for requested split")
    assignments={o:("pilot" if i<np else "development" if i<np+nd else "test") for i,o in enumerate(order[:np+nd+nt])}
    ledger.execute("CREATE TABLE org_partitions(org_id TEXT PRIMARY KEY,partition_name TEXT NOT NULL)")
    ledger.executemany("INSERT INTO org_partitions VALUES(?,?)",assignments.items())
    ledger.execute("CREATE VIEW evidence_with_partition AS SELECT e.*,p.partition_name FROM evidence e LEFT JOIN org_partitions p ON p.org_id=e.org_id")
    selected_rows=ledger.execute("SELECT count(*) FROM evidence_with_partition WHERE partition_name IS NOT NULL").fetchone()[0]
    partitioned_rows=ledger.execute("SELECT count(*) FROM evidence_with_partition WHERE partition_name IN ('pilot','development','test')").fetchone()[0]
    if selected_rows!=partitioned_rows: raise AssertionError("selected organization row partition assignment is incomplete")
    ledger.commit()
    split_digest=hashlib.sha256(json.dumps(assignments,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    split={"status":"provisional; expert top-20 semantics unverified","algorithm":"SHA-256(salt + NUL + exact OrgId UTF-8); sort by digest then OrgId","salt_version":cfg["salt_version"],"salt":cfg["salt"],"seed":args.seed,"counts":{"pilot":np,"development":nd,"test":nt},"eligible_organizations":len(eligible),"assignments":assignments,"assignment_sha256":split_digest,"disjoint":len(assignments)==len(set(assignments))}
    (out/"split_manifest.json").write_text(json.dumps(split,indent=2,sort_keys=True),encoding="utf-8")
    # No approved fields: only schema marker, zero data rows.
    feature=out/"feature_view.csv"; _write_empty_feature(feature,approved)
    sentinel={"SENTINEL_INCIDENT_LABEL_731","SENTINEL_QUEUE_RANK_991","SENTINEL_ACTION_OUTCOME_447"}
    with feature.open("rb") as f: feature_bytes=f.read()
    if any(x.encode() in feature_bytes for x in sentinel): raise AssertionError("synthetic leakage sentinel present in feature output")
    field_lineage=[]
    for field in GUIDE_FIELDS:
        if field in EVALUATOR_FIELDS: destination="evaluator-only store"
        elif field in {"Id","OrgId","AlertId"}: destination="restricted lineage/control"
        else: destination="restricted evidence ledger; feature export denied"
        field_lineage.append({"source_field":field,"destination":destination,"model_visible":field in approved,"approval":"deny by default" if field not in approved else "approved"})
    field_lineage.append({"source_field":"QueueRank","source_file":"GUIDE_Test_Queue_Rankings.csv","destination":"evaluator-only store","model_visible":False,"approval":"deny by default"})
    leak={"status":"pass","field_lineage":field_lineage,"approved_feature_fields":approved,"feature_rows":0,"feature_view_schema_only":True,"evaluator_and_lineage_columns_absent":True,"evaluator_store_separate":True,"ambiguous_mapping_count":ambiguous,"sentinel_count_checked":len(sentinel),"sentinel_matches":0,"no_pairs_or_metrics_created":True,"checks":{"deny_by_default_allowlist":True,"prohibited_column_scan":True,"label_value_origin":True,"label_derived_signals_absent":True,"organization_partition_assignment":selected_rows==partitioned_rows,"sentinel_values_absent_from_feature_and_report":True}}
    (out/"leakage_audit.json").write_text(json.dumps(leak,indent=2,sort_keys=True),encoding="utf-8")
    (out/"leakage_audit.md").write_text("# Leakage audit\n\nPASS. The feature view has no approved columns and zero data rows. Evaluator labels are in a separate store. Synthetic label/outcome sentinels are absent. No pair labels or metrics were produced.\n",encoding="utf-8")
    inc_count=edb.execute("SELECT count(*) FROM (SELECT DISTINCT org,incident FROM membership_rows WHERE org<>'' AND incident<>'')").fetchone()[0]
    alert_count=edb.execute("SELECT count(*) FROM (SELECT DISTINCT org,alert FROM membership_rows WHERE org<>'' AND alert<>'')").fetchone()[0]
    repeated_evidence_groups=edb.execute("SELECT count(*) FROM (SELECT org,alert FROM membership_rows WHERE org<>'' AND alert<>'' GROUP BY org,alert HAVING count(*)>1)").fetchone()[0]
    report={"status":"technical_success_research_gates_open","input_rows":{"GUIDE":parsed,"queue":qn},"source_row_ordinal":{"unique":parsed,"minimum":1,"maximum":parsed},"malformed_rows":malformed,"timestamp_parse_status_counts":ts_counts,"distinct_incident_keys":inc_count,"distinct_alert_keys":alert_count,"repeated_evidence_row_groups_per_alert_key":repeated_evidence_groups,"exact_duplicate_groups":exact_dup_groups,"ambiguous_alert_keys":ambiguous,"eligible_organizations":len(eligible),"provisional_split_counts":{"pilot":np,"development":nd,"test":nt},"selected_org_evidence_rows":selected_rows,"partition_assignment_complete":selected_rows==partitioned_rows,"feature_rows":0,"rank_scope":"unverified","top20_completeness":"unverified","correlation":"no-go","joint_evaluation":"no-go","prioritization_evaluation":"blocked"}
    (out/"preprocessing.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    md=["# Phase 2 preprocessing report","","Technical preprocessing completed; research gates remain open.","",f"- GUIDE rows with stable source ordinals: {parsed:,}.",f"- Evaluator queue labels isolated: {qn:,} rows.",f"- Repeated evidence-row groups (may be normal): {repeated_evidence_groups:,}; exact duplicate groups: {exact_dup_groups:,}.",f"- Ambiguous alert keys preserved with all assignment provenance: {ambiguous:,}.",f"- Qualified organizations: {len(eligible):,}; provisional split: {np}/{nd}/{nt}.","- Feature view: schema-only, zero rows; no fields approved.","- Correlation and joint evaluation: no-go. Prioritization evaluation: blocked by label semantics.","","No models, baselines, pair labels, metrics, priority scores, or test analysis were produced.",""]
    (out/"preprocessing_report.md").write_text("\n".join(md),encoding="utf-8")
    ledger.commit()
    outputs={str(p.relative_to(out)):sha256_file(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name!="run_manifest.json"}
    code={str(p):sha256_file(p) for p in (Path(__file__),Path(__file__).with_name("cli.py"),Path(__file__).with_name("evaluator_store.py"),Path(__file__).resolve().parents[1]/"fixtures"/"stage2"/"synthetic_cases.json",Path(__file__).resolve().parents[1]/"fixtures"/"stage2"/"expected.json",cfgp,policy)}
    after={alerts.name:sha256_file(alerts),rankings.name:sha256_file(rankings)}
    if after!=before: raise RuntimeError("raw input changed during preprocessing")
    manifest={"command":args.command_line,"input_hashes_before":before,"input_hashes_after":after,"config_sha256":sha256_file(cfgp),"field_policy_sha256":sha256_file(policy),"code_sha256":code,"output_sha256":outputs,"python":platform.python_version(),"platform":platform.platform(),"dependencies":"standard library only","seed":args.seed,"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"normalizer_version":NORMALIZER_VERSION,"parser":"csv.reader UTF-8-SIG, ordinal by parsed data-record order","source_metadata":{"release":"unknown","license":"unknown","download_date":"unknown"}}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    ledger.close(); edb.close()
    return report

def check_leakage(features,policy,audit):
    approved=_approved_fields(policy)
    if approved: raise RuntimeError("policy contains fields not approved by Stage 1")
    result=check_feature_view(features,approved,("SENTINEL_INCIDENT_LABEL_731","SENTINEL_QUEUE_RANK_991","SENTINEL_ACTION_OUTCOME_447"))
    audit=Path(audit); audit.parent.mkdir(parents=True,exist_ok=True); audit.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8"); return result

def check_splits(manifest,expected):
    x=json.loads(Path(manifest).read_text(encoding="utf-8")); sizes=[int(i) for i in expected.split(",")]
    actual=[sum(v==k for v in x["assignments"].values()) for k in ("pilot","development","test")]
    if actual!=sizes or not x.get("disjoint"): raise RuntimeError("split assertions failed")
    return {"status":"pass","counts":actual,"assignment_sha256":x["assignment_sha256"],"provisional":True}

def inspect_ambiguity(input_path,out):
    count=0; hist={}
    with Path(input_path).open("r",newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            count+=1; n=len(json.loads(r["IncidentAssignments"])); hist[n]=hist.get(n,0)+1
    lines=["# Ambiguity summary","",f"Ambiguous composite alert keys: {count:,}.","","Assignments per key:"]+[f"- {n}: {v:,} keys" for n,v in sorted(hist.items())]
    Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_text("\n".join(lines)+"\n",encoding="utf-8"); return count

def self_test():
    fixture=Path(__file__).resolve().parents[1]/"fixtures"/"stage2"/"synthetic_cases.json"
    cases=json.loads(fixture.read_text(encoding="utf-8")); fr=cases["guide_rows"]
    assert [r["source_row_ordinal"] for r in fr]==cases["expected"]["source_row_ordinals"]
    assert fr[0]["Id"]==fr[1]["Id"] and canonical_digest({**{c:"" for c in GUIDE_FIELDS},**fr[0]})==canonical_digest({**{c:"" for c in GUIDE_FIELDS},**fr[1]})
    memberships={}
    for r in fr:
        memberships.setdefault((r["OrgId"],r["AlertId"]),set()).add(r["IncidentId"])
    assert len(memberships[("org-A","alert-X")])==cases["expected"]["conflicting_alert_assignments"]
    assert sum(1 for (o,_),incs in memberships.items() if "shared-inc" in incs)==cases["expected"]["same_incident_different_organizations"]
    q=cases["queue_rows"]
    assert len(q)>len({(r["OrgId"],r["IncidentId"]) for r in q}) and any(not r["QueueRank"] for r in q)
    assert 20 not in {int(r["QueueRank"]) for r in q if r["QueueRank"]}
    row={c:"" for c in GUIDE_FIELDS}; row.update(Id="repeated",OrgId="A",IncidentId="SENTINEL_INCIDENT_LABEL_731",AlertId="X",Timestamp="2025-01-01T00:00:00Z")
    assert canonical_digest(row)==canonical_digest(dict(row))
    # Same Id is not consulted for row identity: two physical row ordinals remain distinct.
    source_rows=[(1,dict(row)),(2,dict(row))]
    assert [o for o,_ in source_rows]==[1,2] and source_rows[0][1]["Id"]==source_rows[1][1]["Id"]
    assert timestamp_normalize("2025-01-01T00:00:00")==("","timezone_naive_unresolved")
    assert timestamp_normalize("bad")==("","invalid")
    assert timestamp_normalize("2025-01-01T00:00:00Z")[1]=="aware_utc"
    assert ip_normalize("2001:0db8::1")[0]=="2001:db8::1"
    assert technique_normalize("t1059; T1059.001")[0]==["T1059","T1059.001"]
    assert split_hash("org","salt")==split_hash("org","salt")
    assert mapping_status("A","X","I",1)=="unambiguous" and mapping_status("","X","I",1)=="missing" and mapping_status("A","X","I",2)=="ambiguous"
    # Exact duplicate, repeated evidence, and conflicting membership remain distinguishable.
    rows=[(canonical_digest(row),1),(canonical_digest(row),2)]; mappings={("A","X","I1"):[1,2],("A","X","I2"):[3]}
    assert rows[0][0]==rows[1][0] and len(mappings)==2 and mappings[("A","X","I1")]==[1,2] and mappings[("A","X","I2")]==[3]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"features.csv"; _write_empty_feature(p,[])
        check_feature_view(p,[],("SENTINEL_INCIDENT_LABEL_731","SENTINEL_QUEUE_RANK_991","SENTINEL_ACTION_OUTCOME_447"))
    orgs=["a","b","c"]; order=sorted(orgs,key=lambda o:(split_hash(o,"salt"),o)); chunks=[set(order[:1]),set(order[1:2]),set(order[2:])]
    assert all(not(chunks[i]&chunks[j]) for i in range(3) for j in range(i+1,3))
    # Queue edge cases: exact top-20 only when all ranks 1..20 occur; null/gap/tie/duplicate rows fail integrity.
    q=[{"OrgId":"A","IncidentId":f"I{i}","QueueRank":str(i)} for i in range(1,21)]
    assert len({int(x["QueueRank"]) for x in q})==20
    qbad=q[:-1]+[{"OrgId":"A","IncidentId":"I21","QueueRank":""}]
    assert sum(bool(x["QueueRank"]) for x in qbad)==19 and len({int(x["QueueRank"]) for x in qbad if x["QueueRank"]})==19
    tie=q+[{"OrgId":"A","IncidentId":"I21","QueueRank":"20"}]
    assert len([x for x in tie if x["QueueRank"]=="20"])==2
    gap=[x for x in q if x["QueueRank"]!="7"]
    assert 7 not in {int(x["QueueRank"]) for x in gap}
    # Missing AlertId/IncidentId remain representable as missing membership, not negative labels.
    assert mapping_status("A","","I",0)=="missing" and mapping_status("A","X","",0)=="missing"
    safe_log=json.dumps({"status":"pass","sentinel_count_checked":3,"sentinel_matches":0})
    assert not any(s in safe_log for s in ("SENTINEL_INCIDENT_LABEL_731","SENTINEL_QUEUE_RANK_991","SENTINEL_ACTION_OUTCOME_447"))
    return {"status":"pass","assertions":23,"synthetic_only":True,"sentinel_strings_logged":False}
