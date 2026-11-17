"""Render Phase 27 reports from authoritative v3 frozen audits."""
import csv
import json
from pathlib import Path

P = Path(__file__).resolve().parent
V = P / "v3"
A = json.loads((P / "analysis_summary.json").read_text())
comparison = list(csv.DictReader((P / "PHASE27_EXPERIMENT_COMPARISON.csv").open(newline="", encoding="utf-8")))
gate = list(csv.DictReader((V / "PHASE27_GATE_RESULTS.csv").open(newline="", encoding="utf-8")))
B = next(x for x in comparison if x["mode"] == "phase26_baseline" and x["ranker"] == "progression")
S = next(x for x in comparison if x["mode"] == "phase26_baseline" and x["ranker"] == "train_fitted")
H = A["locked_result"]["baseline"]
T = A["locked_result"]["selected"]
D = A["development"]
L = A["locked_test"]


def val(mode, ranker):
    return next(x for x in comparison if x["mode"] == mode and x["ranker"] == ranker)


def percent(n, d):
    return f"{100 * n / d:.2f}%"


def put(name, text):
    (P / name).write_text(text.strip() + "\n", encoding="utf-8")


def reconstruction_table():
    lines = ["| Development pipeline | Recoverable /400 | Recall@20 /400 | P@10 /200 | False pairs | Mixed groups |",
             "|---|---:|---:|---:|---:|---:|"]
    for mode, ranker in (("phase26_baseline", "progression"), ("phase26_baseline", "train_fitted"),
                         ("phase25_veto", "progression"), ("graph_no_uncertain", "progression"),
                         ("graph_no_uncertain", "train_fitted"), ("graph_selective", "train_fitted")):
        x = val(mode, ranker)
        lines.append(f"| {mode} / {ranker} | {x['recoverable']} | {x['recall20_count']} | "
                     f"{x['p10_count']} | {x['false_grouped_pairs']} | {x['mixed_groups']} |")
    return "\n".join(lines)


def ranking_table():
    lines = ["| Ranker on fixed baseline groups | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |",
             "|---|---:|---:|---:|---:|"]
    for ranker in ("progression", "phase25_linear", "phase26_blend", "candidate_graph",
                   "fragment_aggregation", "graph_progression", "train_fitted"):
        x = val("phase26_baseline", ranker)
        lines.append(f"| {ranker} | {x['recall10_count']} | {x['recall20_count']} | "
                     f"{x['p10_count']} | {float(x['ndcg20']):.3f} |")
    return "\n".join(lines)


dev_h = D["hypotheses"]
lock_h = L["hypotheses"]
dev_e = D["edges"]
lock_e = L["edges"]
dev_delta = 100 * (int(S["recall20_count"]) - int(B["recall20_count"])) / 400
lock_delta = 100 * (T["recall20_count"] - H["recall20_count"]) / 600
ci = [100 * x for x in L["paired_recall20_delta_ci95"]]
gap = 80 - 100 * T["recall20_count"] / 600

put("PHASE27_FINAL_REPORT.md", f"""
# Phase 27 final report — PARTIAL

**The central graph hypothesis is supported for incident discovery.** Without committing uncertain edges, bounded candidate paths formed qualifying hypotheses for **{dev_h['top20_incidents_new_beyond_groups']}/400** development and **{lock_h['top20_incidents_new_beyond_groups']}/600** untouched holdout top-20 incidents that the committed baseline groups could not recover. Hypothesis precision was **{dev_h['qualifying_hypotheses']}/{dev_h['hypotheses']} ({percent(dev_h['qualifying_hypotheses'], dev_h['hypotheses'])})** on development and **{lock_h['qualifying_hypotheses']}/{lock_h['hypotheses']} ({percent(lock_h['qualifying_hypotheses'], lock_h['hypotheses'])})** on holdout. Those discoveries are separate from official group recoverability and Incident Recall@20.

The single frozen selected pipeline kept Phase 26 baseline groups and used a train-fitted ranker. On a fresh 30-queue holdout, official Recall@20 rose **{H['recall20_count']}/600 → {T['recall20_count']}/600 (+{T['recall20_count']-H['recall20_count']}; +{lock_delta:.2f} percentage points)**. Group recoverability remained **{T['recoverable']}/600**; P@10 moved **{H['p10_count']}/300 → {T['p10_count']}/300**. Both pipelines had 100% grouped-pair precision, zero false pairs and zero mixed groups in every queue. The paired queue-bootstrap 95% interval for the recall gain is **+{ci[0]:.2f} to +{ci[1]:.2f} points**. The frozen holdout gate passed (`GO` in `v3/locked_result.json`). The final research decision is **PARTIAL**: official group recoverability did not improve, and the 80% recall target remains **{gap:.2f} points** away.

## Same-cohort development

{reconstruction_table()}

The selected development gain was **{B['recall20_count']}/400 → {S['recall20_count']}/400 (+{dev_delta:.2f} points)**, with recoverability unchanged at {S['recoverable']}/400. Phase 25 orthogonal veto created 80 false pairs and 80 mixed groups, four unsafe unions per queue. The selected pipeline committed no uncertain edges.

## Mechanism and limits

Candidate alert-edge precision was **{dev_e['same_incident_candidate_edges']}/{dev_e['candidate_edges']} ({percent(dev_e['same_incident_candidate_edges'],dev_e['candidate_edges'])})** on development and **{lock_e['same_incident_candidate_edges']}/{lock_e['candidate_edges']} ({percent(lock_e['same_incident_candidate_edges'],lock_e['candidate_edges'])})** on holdout. Direct candidate-edge coverage of same-incident cross-group alert pairs was only **{dev_e['candidate_true_cross_group_pairs']}/{dev_e['eligible_same_incident_cross_group_pairs']} ({percent(dev_e['candidate_true_cross_group_pairs'],dev_e['eligible_same_incident_cross_group_pairs'])})** and **{lock_e['candidate_true_cross_group_pairs']}/{lock_e['eligible_same_incident_cross_group_pairs']} ({percent(lock_e['candidate_true_cross_group_pairs'],lock_e['eligible_same_incident_cross_group_pairs'])})**. Sparse edges still connected enough fragments to produce many hypotheses. The corrected v3 graph counts duplicate source pairs once and requires disjoint controller roots for multiple independent witnesses.

This did **not** prove that uncertain edges caused the official rank gain. On unchanged development groups, the historical Phase 25 linear and Phase 26 blend rankers tied the selected ranker at {S['recall20_count']}/400. Three hand-set graph rankers performed worse by promoting fragmented groups. The selected model mostly penalized candidate-rich fragments. No alternative candidate was evaluated on the opened holdout.

The next experiment should present hypotheses as a separate, calibrated analyst queue or provisional reversible groups, measure false hypothesis workload, and seek additional independent evidence before permanent unions. This synthetic study does not justify operational promotion. Phase 16 v4's 67.83% selected holdout, Phase 25's 55.17% holdout with safety failure, and Phase 26's development results are different populations and are not direct percentage comparators.
""")

put("PHASE27_GO_NO_GO.md", f"""
# Phase 27 decision: PARTIAL

The predeclared development gates selected one pipeline: Phase 26 baseline committed groups plus a train-fitted ranker. Code, configuration, weights, thresholds, selection and holdout evaluator were hashed in `v3/pre_evaluation_protocol.json` before generating the `phase27k` cohort. Only that pipeline and its same-cohort progression baseline were predicted. `v3/locked_prediction_freeze.json` hashed predictions and public inputs before private truth was opened once.

The frozen holdout gate passed: Recall@20 {T['recall20_count']}/600 versus {H['recall20_count']}/600, grouped-pair precision 100%, zero false pairs, zero mixed groups and 30/30 queues without safety regression. `v3/locked_result.json` calls that narrow gate `GO`. The final scientific decision is **PARTIAL** because official recoverability stayed {T['recoverable']}/600 ({percent(T['recoverable'],600)}), hypothesis precision was only {percent(lock_h['qualifying_hypotheses'],lock_h['hypotheses'])}, and absolute recall remains far below 80%. Candidate hypotheses must never be substituted for official reconstructed groups.

The holdout uses a new namespace, seed, ten unseen family labels, 30 queues, more benign activity and delayed lineage evidence. It is independently drawn from the same synthetic simulator family, not external validation. Earlier v1/v2 cohorts are diagnostic; v2's opened holdout was not reused after the provenance-count correction.
""")

put("PHASE27_TARGET_STATUS.md", f"""
# Phase 27 target status

| Metric | Fresh development baseline → selected | Frozen holdout baseline → selected | Target |
|---|---:|---:|---:|
| Official Recall@20 | {B['recall20_count']}/400 ({percent(int(B['recall20_count']),400)}) → {S['recall20_count']}/400 ({percent(int(S['recall20_count']),400)}) | {H['recall20_count']}/600 ({percent(H['recall20_count'],600)}) → {T['recall20_count']}/600 ({percent(T['recall20_count'],600)}) | ≥80% |
| Official recoverability | {B['recoverable']}/400 → {S['recoverable']}/400 | {H['recoverable']}/600 → {T['recoverable']}/600 | ≥85% |
| P@10 | {B['p10_count']}/200 → {S['p10_count']}/200 | {H['p10_count']}/300 → {T['p10_count']}/300 | ≥63.88% |
| Grouped-pair precision | 100% → 100% | 100% → 100% | ≥90% |
| False pairs / mixed groups | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 | No increase |
| New uncommitted incident hypotheses | {dev_h['top20_incidents_new_beyond_groups']} | {lock_h['top20_incidents_new_beyond_groups']} | Diagnostic only |

The holdout gap to 80% Recall@20 is {480-T['recall20_count']} incidents ({gap:.2f} points); the gap to 85% recoverability is {510-T['recoverable']} incidents. The paired queue-bootstrap 95% interval for the holdout recall gain is {ci[0]:.2f}–{ci[1]:.2f} points. These intervals describe synthetic queue variation, not field transfer.
""")

put("PHASE27_GRAPH_ARCHITECTURE.md", """
# Candidate relationship graph architecture

The `v3/evidence.py` access layer materializes a minute-100 snapshot. Source-observation and alert nodes are separate; an emission edge connects a visible source to its alert. Alert-to-alert edges arise from equal source IDs, process references, auth references and flow references. Every frozen edge records endpoints, type, support, visible contradiction, receiver-visible minute, source provenance, upstream controller roots, independence status, confidence, uncertainty and VERIFIED/CANDIDATE/REJECTED outcome. Private incident and priority labels are absent from inference.

VERIFIED same-source or complete independently rooted process edges may become committed unions. CANDIDATE edges remain available to the discovery and ranking stages without automatic merging. REJECTED visible contradictions block both union and hypothesis joins. Selective and component-risk variants use predeclared high thresholds and context checks; on this cohort they did not improve recoverability.

The hypothesis builder joins committed fragments over candidate paths, bounded at eight fragments and 100 alerts. It does not alter committed groups. Duplicate alert copies from one source pair count once in graph features; multiple independent witnesses require disjoint upstream controller roots. `independent_paths` is a greedy count of root-disjoint visible witness pairs, not proof of causal correctness. Each prediction, graph and hypothesis records the decision cutoff and snapshot hash.
""")

put("PHASE27_FRAGMENT_DISCOVERY_AUDIT.md", f"""
# Fragment-level incident discovery audit

A hypothesis qualifies when it contains at least 80% of an incident's cutoff-visible alerts and at least 80% of its own alerts belong to that incident. Each oracle top-20 incident is counted once. There are 400 development and 600 holdout incident opportunities. Private truth is applied only after graph and hypothesis predictions are frozen.

Development: **{dev_h['qualifying_hypotheses']}/{dev_h['hypotheses']} qualifying hypotheses ({percent(dev_h['qualifying_hypotheses'],dev_h['hypotheses'])} precision)**, covering **{dev_h['top20_incidents_new_beyond_groups']}/400** top-20 incidents outside baseline group recoverability. Holdout: **{lock_h['qualifying_hypotheses']}/{lock_h['hypotheses']} ({percent(lock_h['qualifying_hypotheses'],lock_h['hypotheses'])})**, covering **{lock_h['top20_incidents_new_beyond_groups']}/600** such incidents. No uncertain-edge union was committed by the selected pipeline.

There were {dev_h['hypotheses']-dev_h['qualifying_hypotheses']} nonqualifying development and {lock_h['hypotheses']-lock_h['qualifying_hypotheses']} nonqualifying holdout hypotheses. All frozen hypotheses fell within each queue's first 20 confidence-ranked hypothesis slots, so those are also false top-20 hypothesis rankings. `PHASE27_HYPOTHESIS_RANKING.csv` lists the queue counts; `PHASE27_FRAGMENT_COUNTS.csv` gives the number and size of baseline committed fragments per top-20 incident. These predictions are discovery hypotheses, not recovered official groups.
""")

put("PHASE27_UNCERTAIN_EDGE_UTILITY.md", f"""
# Uncertain-edge utility audit

After freeze, evaluator truth marked **{dev_e['same_incident_candidate_edges']}/{dev_e['candidate_edges']}** development and **{lock_e['same_incident_candidate_edges']}/{lock_e['candidate_edges']}** locked candidate alert edges as same-incident. Edge precision is {percent(dev_e['same_incident_candidate_edges'],dev_e['candidate_edges'])} and {percent(lock_e['same_incident_candidate_edges'],lock_e['candidate_edges'])}. Among all true same-incident alert pairs in different committed baseline groups, direct candidate edges covered **{dev_e['candidate_true_cross_group_pairs']}/{dev_e['eligible_same_incident_cross_group_pairs']}** and **{lock_e['candidate_true_cross_group_pairs']}/{lock_e['eligible_same_incident_cross_group_pairs']}**. This direct pair recall differs from incident-hypothesis recall.

Bounded paths over sparse candidate edges discovered {dev_h['top20_incidents_new_beyond_groups']} and {lock_h['top20_incidents_new_beyond_groups']} otherwise unrecoverable top-20 incidents. Candidate edges produced no false grouped pairs because they were not committed. But {dev_e['candidate_edges']-dev_e['same_incident_candidate_edges']} development and {lock_e['candidate_edges']-lock_e['same_incident_candidate_edges']} holdout candidate edges connected unrelated incidents. The downstream nonqualifying hypotheses number {dev_h['hypotheses']-dev_h['qualifying_hypotheses']} and {lock_h['hypotheses']-lock_h['qualifying_hypotheses']}.

Graph witness counts deduplicate source pairs and require disjoint controller roots. This prevents duplicate or shared-controller observations from being counted as multiple independent paths. It does not certify that independently rooted claims are true. The selected ranker's graph feature contribution was mostly negative; historical rankers tied its official development Recall@20. No alternative ranker was evaluated on the opened holdout, so official rank gain cannot be uniquely credited to uncertain edges.
""")

put("PHASE27_RECONSTRUCTION_AUDIT.md", f"""
# Reconstruction and union audit

Seven reconstruction modes were predicted on identical 20-queue development snapshots. Group recoverability requires ≥80% incident coverage and ≥80% group purity among cutoff-visible alerts; candidate paths do not count.

{reconstruction_table()}

The Phase 26 context baseline and all tested graph commit modes recovered {B['recoverable']}/400. Graph conservative, selective, no-uncertain, component-risk and bounded variants differed in group composition but did not improve recoverability. The unchanged Phase 25 orthogonal-veto reconstruction created 80 false pairs and 80 mixed groups, four false-pair-creating unions per queue. It fails every queue-level safety comparison to the zero-error baseline.

`PHASE27_UNION_PAIR_AUDIT.csv` replays accepted unions against evaluator truth after prediction freeze; sums reconcile exactly to final pair counts in `PHASE27_FAILURE_CASCADE.csv`. No union in the selected pipeline creates a false pair. The benign collision fixture makes the veto's worst single increment one pair; this is not a large-component common-mode stress certificate.
""")

attribution = L["rank_attribution"]
put("PHASE27_RANKING_AUDIT.md", f"""
# Ranking audit on unchanged committed groups

{ranking_table()}

On fixed development baseline groups, Phase 25 linear, Phase 26 blend and Phase 27 train-fitted rankers tied at {S['recall20_count']}/400 official Recall@20; progression reached {B['recall20_count']}/400. The frozen tie break selected train-fitted. The three hand-set graph rankers performed worse because they promoted fragmented groups that could not satisfy official recoverability. Ranking hypotheses separately from official groups is therefore necessary.

The selected model has nine historical group features and six graph features, with deduplicated source-pair and disjoint-root counts. On holdout, graph features contributed a negative score to {attribution['negative_contribution_groups']:,} of {attribution['groups_scored']:,} groups and a positive score to {attribution['positive_contribution_groups']:,}. This is score decomposition, not a causal ablation. The frozen selected and progression baseline used identical holdout groups: Recall@20 {H['recall20_count']}/600 versus {T['recall20_count']}/600, P@10 {H['p10_count']}/300 versus {T['p10_count']}/300, nDCG@20 {H['ndcg20']:.3f} versus {T['ndcg20']:.3f}. Recoverability stayed {T['recoverable']}/600.
""")

put("PHASE27_SAFETY_AUDIT.md", f"""
# Group, edge and temporal safety audit

The selected pipeline and its same-cohort baseline share committed groups. Both have 100% grouped-pair precision, zero false grouped pairs and zero mixed groups on all 30 locked queues, with no queue-level regression. The same holds on all 20 authoritative development queues. Union increments exactly reconcile with final group-pair counts. The Phase 25 veto diagnostic had 80 false-pair-creating unions and 80 mixed groups on development, failing all 20 queue checks.

Candidate-edge errors remain separate: {dev_e['candidate_edges']-dev_e['same_incident_candidate_edges']} development and {lock_e['candidate_edges']-lock_e['same_incident_candidate_edges']} holdout false candidate edges produced no grouped-pair error. Nonqualifying hypotheses numbered {dev_h['hypotheses']-dev_h['qualifying_hypotheses']} and {lock_h['hypotheses']-lock_h['qualifying_hypotheses']}; all appeared within their queues' first 20 confidence-ranked hypothesis slots. This is a false analyst-suggestion workload even when group safety is intact.

Every frozen graph, hypothesis, prediction and decision records minute-100 cutoff and snapshot hash. The access layer excludes later evidence; tests mutate future values and confirm an earlier snapshot's hash is invariant. V3 deduplicates source pairs and requires disjoint controller roots before counting multiple independent witnesses. The synthetic simulator still does not prove causal reliability or field calibration.
""")

put("PHASE27_RECALL_ERROR_ANALYSIS.md", f"""
# Recall error analysis

Official Recall@20 cannot exceed group recoverability. On development, the selected ranker recalled all {S['recoverable']}/400 recoverable top-20 incidents; **{400-int(S['recoverable'])}/400** remained outside official recovery. On holdout, it recalled all **{T['recoverable']}/600** recoverable incidents; **{600-T['recoverable']}/600** remained outside official recovery. It removed the progression baseline's {H['recoverable']-H['recall20_count']} holdout ranking misses, but could not turn the {lock_h['top20_incidents_new_beyond_groups']} newly discovered uncommitted hypotheses into official reconstructed groups.

The key bottleneck is now safe conversion of a useful hypothesis into a committed group. Simply ranking candidate-linked fragments higher worsened official recall in three development diagnostics. Permanent grouping would also expose the {lock_h['hypotheses']-lock_h['qualifying_hypotheses']} nonqualifying holdout hypotheses to false-group risk. A reviewer-visible suggestion or reversible provisional group can exploit discovery information while new independent evidence is sought.

The holdout gaps are {480-T['recall20_count']} more recalled incidents for 80% Recall@20 and {510-T['recoverable']} more recoverable incidents for 85% group recoverability. These are Phase 27 denominators only.
""")

put("PHASE27_REPRODUCIBILITY.md", """
# Phase 27 reproducibility

The authoritative run is `v3/` (`phase27c`), train seed 272411 and development seed 272923, with 12 train and 20 development queues. Earlier root/v2 cohorts were diagnostic; v2's opened holdout was never reused after detecting duplicate-source witness counting. V3 deduplicates source pairs and requires root-disjoint witnesses before train/development selection. `v3/freeze_manifest.json` hashes development code, model and predictions before private audit. `v3/pre_evaluation_protocol.json` hashes the selected pipeline, weights, holdout builder and evaluator before holdout generation. `v3/locked_prediction_freeze.json` hashes public locked inputs and predictions before truth was opened once. The holdout is `phase27k`, seed 273571, 30 queues and unseen family labels with more delayed lineage evidence. Phase 19 and Phase 22 locked cohorts were not opened.

From a clean authoritative directory, run:

```powershell
python experiments/PHASE27_RECALL_GRAPH/v3/generate.py
python experiments/PHASE27_RECALL_GRAPH/v3/run_study.py
python experiments/PHASE27_RECALL_GRAPH/v3/freeze_holdout.py
python experiments/PHASE27_RECALL_GRAPH/v3/holdout.py
python experiments/PHASE27_RECALL_GRAPH/v3/holdout_run.py
python experiments/PHASE27_RECALL_GRAPH/analyze.py
python experiments/PHASE27_RECALL_GRAPH/write_reports.py
python -m unittest discover -s experiments/PHASE27_RECALL_GRAPH/tests -q
```

Generators refuse to overwrite existing cohorts. Do not rerun an opened holdout as a new model-selection opportunity. The frozen run evaluated only the selected pipeline and same-cohort baseline on holdout. All 51 relevant historical Phase 16, 19–23, 25 and 26 regression tests pass; Phase 27 adds seven tests.

Metric definitions: 20 oracle-priority incidents per queue. Official recoverability requires a predicted group with ≥80% eligible incident coverage and ≥80% group purity. Recall@20 also requires that group's first qualifying position ≤20. P@10 credits distinct oracle top-ten incidents in the first ten groups. Candidate-edge precision is same-incident alert edges divided by all candidate alert edges. Direct cross-group pair recall is true candidate alert edges crossing groups divided by all same-incident alert pairs across groups. Hypothesis precision is qualifying bounded multi-fragment hypotheses divided by all hypotheses; it is never counted as official group recovery. Paired confidence intervals use 2,000 queue-cluster resamples.
""")

print("Wrote authoritative Phase 27 reports")
