from pathlib import Path
import csv,json,hashlib,shutil
P=Path(__file__).resolve().parent;R=P.parent
H=R/'experiments/PHASE33_FROZEN_GENERALIZATION'; A=P/'audit';S=P/'submission'
summary=json.loads((H/'HOLDOUT_SUMMARY.json').read_text())
seal=json.loads((H/'artifacts/pre_evaluation_seal.json').read_text())
checked=[]
for rel,key in [('artifacts/baseline_predictions.jsonl','baseline'),('artifacts/candidate_predictions.jsonl','candidate')]:
 f=H/rel;got=hashlib.sha256(f.read_bytes()).hexdigest();assert got==seal['predictions_sha256'][key];checked.append((rel,got))
for rel,expected in [('experiments/PHASE31_CONTROLLED_SOC_EVIDENCE/model.py',seal['baseline_model_sha256']),('experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py',seal['candidate_model_sha256']),('experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py',seal['evaluator_sha256'])]:
 got=hashlib.sha256((R/rel).read_bytes()).hexdigest();assert got==expected;checked.append((rel,got))
ledger=[
('C01','Matched holdout includes 15 queues and 5,018 eligible alerts','HOLDOUT_SUMMARY.json','33','Untouched synthetic holdout result','5018 alerts','yes','Same generator family'),
('C02','Recall@20 baseline 250/300; candidate 260/300','HOLDOUT_SUMMARY.json','33','Untouched synthetic holdout result','250/300; 260/300','yes','Paired cohort; protocol adjustment'),
('C03','Recoverability baseline 263/300; candidate 281/300','HOLDOUT_SUMMARY.json','33','Untouched synthetic holdout result','263/300; 281/300','yes','80 percent completeness and purity'),
('C04','P@10 baseline 107/150; candidate 113/150','HOLDOUT_SUMMARY.json','33','Untouched synthetic holdout result','107/150; 113/150','yes','Evaluator-specific crediting'),
('C05','No false grouped pairs or mixed groups in either arm','HOLDOUT_SUMMARY.json; HOLDOUT_RESULTS.csv','33','Untouched synthetic holdout result','0/15 queues with errors','yes','Simulator truth only'),
('C06','28 new fallback and 711 total accepted unions genuine; 150 false token rejections; 35 genuine abstentions','POST_EVALUATION_AUDIT.json; PHASE33_FINAL_REPORT.md','33','Untouched synthetic holdout result','28/28; 711/711; 150; 35','yes','Post-evaluation truth audit'),
('C07','Development gate of 170/200 missed by one','experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/PHASE32_FINAL_REPORT.md','32','Development result','169/200','yes','Protocol adjusted before fresh holdout'),
('C08','Historical synthetic recall 407/600','experiments/PHASE16_PROVENANCE_RECONSTRUCTION/PHASE16_FINAL_REPORT.md','16','Historical result','407/600','yes','Separate population'),
('C09','Later ranking studies did not promote a new holdout','experiments/PHASE34_FROZEN_RANK_GENERALIZATION/PHASE34_FINAL_REPORT.md; experiments/PHASE38_INTEGRATED_RECALL_OPTIMIZATION/PHASE38_FINAL_REPORT.md','34-38','Development result','separate 300-opportunity cohorts','yes','No cross-cohort trend'),
('C10','GUIDE local inspection 4,147,992 evidence rows and 70,702 conflicting alert keys','experiments/PHASE39_REAL_SOC_VALIDATION/DATA_QUALITY_REPORT.md','39','Public real-world dataset inspection','4,147,992 rows; 70,702 keys','yes','No external model score'),
('C11','Real SOC effectiveness','experiments/PHASE39_REAL_SOC_VALIDATION/UNAVAILABLE_ARTIFACTS.md','39','Unverified claim','none','no','No predictions or authorized fields')]
with (A/'evidence_ledger.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['id','exact_claim','supporting_artifact_path','phase','evidence_type','metric_denominator','main_paper','qualification']);w.writerows(ledger)

refs=[
('landauer2022','10.1145/3510581','https://doi.org/10.1145/3510581'),('wang2024','10.1016/j.cose.2023.103533','https://www.sciencedirect.com/science/article/pii/S0167404823004431'),('grain2025','10.1016/j.cose.2024.104180','https://www.sciencedirect.com/science/article/abs/pii/S0167404824004851'),('malach2025','10.1016/j.cose.2024.104270','https://www.sciencedirect.com/science/article/pii/S0167404824005765'),('sadlek2025','10.1016/j.jisa.2024.103956','https://zenodo.org/records/14547669'),('chuah2025','10.1016/j.jisa.2025.104096','https://www.sciencedirect.com/science/article/pii/S2214212625001334'),('review2022','10.1109/ACCESS.2022.3168976','https://ieeexplore.ieee.org/abstract/document/9760432/'),('holmes2019','10.1109/SP.2019.00026','https://ieeexplore.ieee.org/document/8835390/'),('crosshound2026','10.1109/TIFS.2026.3734719','https://ieeexplore.ieee.org/abstract/document/11695229'),('guide2024','dataset','https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction')]
with (A/'reference_audit.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['bib_key','doi','publisher_or_authoritative_url','metadata_status','limitation']);
 for k,d,u in refs:w.writerow([k,d,u,'title/author/year/venue/DOI checked' if d!='dataset' else 'official dataset page checked','Full-text method review limited to accessible abstracts/records'])
 with_more=[('poirot2019','10.1145/3319535.3363217','https://www-personal.umd.umich.edu/~birhanu/dsplab/publications/poirot2019/'),('unicorn2020','10.14722/ndss.2020.24046','https://www.ndss-symposium.org/ndss-paper/unicorn-runtime-provenance-based-detector-for-advanced-persistent-threats/')]
 for k,d,u in with_more:w.writerow([k,d,u,'title/author/year/venue/DOI checked','Full-text review limited to available author and venue records'])
(A/'literature_comparison.csv').write_text('paper,venue,year,problem,method,dataset,evaluation,limitation_relevant_here\n'+
 '\n'.join([
 'Landauer et al.,ACM TOPS,2022,alert flooding,learned aggregation,semi-structured alerts,group reduction,not point-in-time incident membership',
 'Wang et al.,Computers and Security,2024,multistage prediction,similarity plus Transformer,testbed alerts,attack prediction,not original-root gate',
 'Xiao et al. GRAIN,Computers and Security,2025,scenario reconstruction,GNN plus RL causal graph,four public attack datasets,path accuracy,distinct evidence contract',
 'Malach et al. CyberShapley,Computers and Security,2025,alert explanation,graph-component attribution,DARPA Engagement 3 and PublicArena,explanation/triage,not incident partition',
 'Sadlek et al.,JISA,2025,incident severity,kill-chain attack graph,captured alerts,triage severity,requires different labels',
 'Chuah et al.,JISA,2025,log correlation review,systematic review,62 selected articles,quality attributes,no new partition algorithm',
 'Landauer review context,IEEE Access,2022,event correlation review,systematic taxonomy,127 studies,methods and datasets,heterogeneous evaluation',
 'HOLMES,IEEE S&P,2019,APT detection,information-flow correlation,real APT cases,precision/false alarms,not comparable queue protocol',
 'CrossHound,IEEE TIFS,2026,multisource APT investigation,provenance plus Steiner tree,OpTC and LANL,F1 and path coverage,operational provenance differs'] )+'\n',encoding='utf-8')
with (A/'literature_comparison.csv').open('a',encoding='utf-8') as f:
 f.write('POIROT,ACM CCS,2019,threat hunting,graph alignment with kernel audit,public reports and DARPA engagement,graph matching,not queue-level ranking\n')
 f.write('UNICORN,NDSS,2020,APT detection,runtime provenance graph sketching,APT scenarios,anomaly detection,not three-root attestation\n')

(A/'journal_venue_analysis.md').write_text('''# Journal fit and instruction status

The manuscript is an author-selected single-column, ragged-right article; it is not an exact journal template.

| Venue | Scope and article type | Fit | Validation and format concern |
|---|---|---|---|
| Journal of Information Security and Applications | Original and practice-driven security research; publisher explicitly rejects routine off-the-shelf AI applications | Strongest topical fit for evidence-gated SOC workflow | Synthetic-only validation and insufficient published-method comparison are serious blockers; check live Guide for Authors before submission |
| IEEE Transactions on Dependable and Secure Computing | Archival methods and evaluation of dependable secure systems | Methodological fit | 15 synthetic holdout queues and no operational validation likely insufficient; IEEE template differs from mandatory layout |
| ACM Transactions on Privacy and Security | Auditing, intrusion detection, trust and secure systems | Broad fit | Stronger formal/empirical novelty and real-world study needed; ACM submission template differs |
| IEEE Transactions on Information Forensics and Security | Forensics, integrity and security research; CrossHound is a directly relevant recent publication | Good topical fit | Recent multi-source provenance comparison raises novelty bar; real/standard evaluation needed |
| Computers & Security | Broad security practice | Scope risk | Publisher reports moratorium on submissions featuring AI/ML as significant components; avoid recommendation without editorial clarification |

Primary future target: JISA, contingent on substantial external validation and checking current author instructions. Alternatives: TDSC and ACM TOPS. No current venue-readiness claim is made. Official venue source URLs are in `submission/recommended_target_journal.md`.
''',encoding='utf-8')
(A/'research_gap_and_novelty.md').write_text('''# Research gap and novelty boundary

Published aggregation, causal graph reconstruction, provenance-based APT detection and severity triage are established. This paper addresses a narrower operational question: when can a specific cross-fragment relationship be accepted from original, timely, independently rooted process/auth/network evidence, and when may endpoint context replace the missing process witness? This is a tested design choice within one synthetic generator, not proof of first invention or superiority over prior work. CrossHound is especially relevant prior multi-source provenance work. A head-to-head comparison on compatible real data is unavailable.
''',encoding='utf-8')
(A/'reproducibility_audit.md').write_text('# Reproducibility audit\n\nVerified SHA-256 against pre-evaluation seal:\n\n'+''.join(f'- `{rel}`: `{digest}`\n' for rel,digest in checked)+'\nFigures are regenerated from immutable summary and queue CSV by `python paper/build_paper.py`; the script checks predictions and metric sums. Do not rerun the holdout generator or evaluator as part of paper reproduction.\n',encoding='utf-8')
(A/'limitations_and_threats.md').write_text('Synthetic trust roots, 15 queues, generator-family holdout, missed development gate and documented protocol adjustment, evaluator-specific 80/80 qualification, unverified real trust-domain independence, missing point-in-time real evidence, and no authorized SOC score are material threats. See manuscript Sections 10--12.\n',encoding='utf-8')
(A/'submission_readiness_audit.md').write_text('Status: NOT submission-ready. Scientific blockers: no authorized real SOC validation, limited holdout size, no compatible published-method baseline, and novelty positioning against recent multi-source provenance work. Administrative blockers: affiliation, corresponding author, author approvals, journal-specific formatting and declarations require author confirmation.\n',encoding='utf-8')
(S/'submission_checklist.md').write_text('''# Author confirmation before submission
- [ ] Confirm both author names and order, affiliations, emails, and corresponding author.
- [ ] Obtain both authors' approval of manuscript and cover letter.
- [ ] Select journal and adopt its current template; current manuscript deliberately uses single-column ragged-right format.
- [ ] Confirm funding, competing interests, data availability, ethics, AI-use and contribution declarations; none is fabricated here.
- [ ] Complete external validation and comparable published-method evaluation before claiming journal readiness.
''',encoding='utf-8')
(S/'author_metadata_required.md').write_text('Author affiliations, department, email, ORCID, correspondence, funding, conflicts, ethics, contributions, AI-use and data-availability statements are unprovided; confirm with authors before any submission.\n',encoding='utf-8')
(S/'recommended_target_journal.md').write_text('''# Provisional target

Primary: Journal of Information Security and Applications ([publisher scope](https://shop.elsevier.com/journals/journal-of-information-security-and-applications/2214-2126)). Alternatives: IEEE Transactions on Dependable and Secure Computing ([scope](https://www.computer.org/csdl/journal/tq)); ACM Transactions on Privacy and Security ([journal](https://dl.acm.org/journal/tops)). Also assessed IEEE TIFS ([recent relevant paper](https://ieeexplore.ieee.org/abstract/document/11695229)). [Computers & Security](https://shop.elsevier.com/journals/computers-and-security/0167-4048) reports an AI/ML moratorium. The current single-column format has not been certified to match any selected journal's submission template. No immediate submission recommended without external validation and live instruction check.
''',encoding='utf-8')
(S/'cover_letter_draft.md').write_text('''Dear Editor,

Please consider the enclosed manuscript, “Evidence-Aware Correlation and Constrained Reconstruction of Cybersecurity Incidents under Incomplete Telemetry,” by Hunain Shahid and Hammad Ullah Khan, after the authors have selected a suitable journal and completed the outstanding validation. It describes a provenance- and temporal-availability-gated incident reconstruction procedure and a constrained endpoint fallback, evaluated on a frozen controlled synthetic holdout. The manuscript explicitly limits its claims to this synthetic setting and reports that external validation was blocked by missing data fields.

[Authors: add a journal-specific fit paragraph and verify all required originality, funding, competing-interest, data, ethics, AI-use, and author-approval declarations before sending.]

Sincerely,
[Corresponding author to be confirmed]
''',encoding='utf-8')
(P/'supplementary/extended_results.md').write_text('Primary paired holdout: 250/300 versus 260/300 Recall@20; 263/300 versus 281/300 recoverability; 107/150 versus 113/150 P@10. Separate historical and development studies are not pooled. Original artifacts: `experiments/PHASE33_FROZEN_GENERALIZATION/`.\n',encoding='utf-8')
(P/'README.md').write_text('''# Evidence-aware incident reconstruction paper

Manuscript source: `main.tex`; primary results: `figure_data/holdout_metrics.csv`; original immutable outputs in `../experiments/PHASE33_FROZEN_GENERALIZATION/`.

From repository root: `python paper/build_paper.py` verifies the sealed prediction SHA-256 hashes and metric sums and regenerates the seven vector figures. `python paper/audit_paper.py` refreshes claim and source audits without changing experiment files. To compile from `paper/` after a working TeX distribution is installed: `pdflatex main.tex`, `bibtex main`, `pdflatex main.tex` twice; copy `main.pdf` to `research_paper.pdf`. Required packages: geometry, lmodern, microtype, ragged2e, setspace, graphicx, booktabs, tabularx, array, amsmath, amssymb, caption, subcaption, float, xcolor, hyperref, natbib.

The final manuscript uses “frozen synthetic holdout” rather than internal phase identifiers. Internal audit paths retain phase names. The currently installed MiKTeX fails on registry access and initial setup in this sandbox; a compiled PDF requires a functioning LaTeX installation. Do not substitute a rendered non-LaTeX PDF for a claimed LaTeX compilation.
''',encoding='utf-8')
(P/'figure_source/README.md').write_text('The editable source for all seven figures is `../build_paper.py`. Quantitative panels read CSV under `../figure_data/`, which is generated only after verification of original prediction hashes and summary/queue totals.\n',encoding='utf-8')
print('Audit materials created; original experiment artifacts untouched.')
