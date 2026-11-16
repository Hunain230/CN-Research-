"""Build Phase 13 reports from measured evaluation artifacts; no metrics invented."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REFRESH = "--refresh" in sys.argv


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write(name, body):
    path = HERE / name
    if path.exists() and not REFRESH:
        raise FileExistsError(f"Refusing overwrite: {path}")
    path.write_text(body.strip() + "\n", encoding="utf-8")


e1 = read("PHASE10_EVALUATION.json")["methods"]["E1"]
c = read("PHASE13_C_EVALUATION.json")
paired = read("PHASE13_C_PAIRED_CHANGES.json")
rank = read("PHASE13_RANK_EVALUATION.json")["methods"]
bridge = read("PHASE13_BRIDGE_EVALUATION.json")
bm = bridge["metrics"]
freeze = read("c_predictions/prediction_freeze.json")
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
parent_paths = [
    "outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json",
    "outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json",
    "outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json",
    "outputs/submission_hard_negative_ablation_v1_20261115_v1/prediction_freeze.json",
    "outputs/sprint_rank_fusion_v1_20261116/prediction_freeze.json",
    "experiments/PHASE10_FRAGMENT_RECONSTRUCTION/PHASE10_EXPERIMENT_CONFIG.json",
    "experiments/PHASE10_FRAGMENT_RECONSTRUCTION/reconstruct.py",
    "experiments/PHASE10_FRAGMENT_RECONSTRUCTION/evaluate.py",
    "experiments/PHASE10_FRAGMENT_RECONSTRUCTION/predictions/prediction_freeze.json",
]
hashes = {path: digest(ROOT / path) for path in parent_paths}
(HERE / "PHASE13_INPUT_HASHES.json").write_text(json.dumps({"git_head": head, "frozen_inputs": hashes,
    "phase13_code": {p.name: digest(p) for p in HERE.glob("*.py")}}, indent=2), encoding="utf-8")

metric_rows = []
def add_metric(experiment, kind, recall_count=None, recall=None, recover=None, p10=None, ndcg=None,
               tp=None, fp=None, mixed=None, precision=None, notes=""):
    metric_rows.append({"experiment": experiment, "kind": kind, "queues": 499,
        "expert_top20_denominator": 9980, "incident_recall20_count": recall_count,
        "incident_recall20": recall, "group_recoverability_count": recover,
        "group_recoverability": recover / 9980 if recover is not None else None,
        "p10": p10, "ndcg20": ndcg, "grouped_pair_tp": tp,
        "false_grouped_pairs": fp, "grouped_pair_precision": precision,
        "mixed_predicted_groups": mixed, "notes": notes})
add_metric("E1_reproduced", "full_pipeline", e1["incident_recall20_count"], e1["incident_recall20"],
           e1["group_recoverability_count"], e1["p10"], e1["ndcg20"], e1["grouped_pair_tp"],
           e1["false_grouped_pairs"], e1["mixed_predicted_groups"], e1["grouped_pair_precision"],
           "Exact Phase10 E1 metrics; evaluation copied to Phase13, frozen inputs hard-linked read-only")
for threshold, row in c["group_thresholds"].items():
    if threshold == "0.75":
        continue
    add_metric("C_threshold_" + threshold, "C_only", recover=row["recoverable"], tp=row["tp"],
               fp=row["fp"], mixed=row["mixed"], precision=row["pair_precision"],
               notes="Ranking not rescored; Recall@20/P@10/nDCG@20 not measured for changed groups")
add_metric("C_weak_bridge_split", "C_only", recover=bm["recoverable"], tp=bm["tp"],
           fp=bm["fp"], mixed=bm["mixed"], precision=bm["pair_precision"],
           notes="Graph bridge split below 0.80; ranking not rescored; Recall@20/P@10/nDCG@20 not measured")
for method, row in rank.items():
    if method == "blend_0.75":
        continue
    add_metric("R_" + method, "ranking_only_fixed_E1_groups", row["incident_recall20_count"],
               row["incident_recall20"], e1["group_recoverability_count"], row["p10"], row["ndcg20"],
               e1["grouped_pair_tp"], e1["false_grouped_pairs"], e1["mixed_predicted_groups"],
               e1["grouped_pair_precision"], "Frozen prior scores; full-cohort comparison is retrospective, not selection-valid")
with (HERE / "PHASE13_METRICS_COMPARISON.csv").open("w" if REFRESH else "x", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(metric_rows[0]))
    writer.writeheader()
    writer.writerows(metric_rows)

registry = []
def reg(experiment, change, population, runtime, rss, decision, artifact):
    registry.append({"experiment_id": experiment, "change": change, "population": population,
                     "code_version": head, "config_sha256": digest(HERE / "PHASE13_EXPERIMENT_CONFIG.json"),
                     "input_manifest": "PHASE13_INPUT_HASHES.json", "runtime_seconds": runtime,
                     "peak_rss_bytes": rss, "decision": decision, "metric_artifact": artifact})
reg("E1_reproduced", "no change; exact copied evaluator", "499 queues/9980 labels",
    read("PHASE10_EVALUATION.json")["evaluation_resource"]["wall_seconds"],
    read("PHASE10_EVALUATION.json")["evaluation_resource"]["peak_process_rss_bytes"],
    "FROZEN_REFERENCE_REPRODUCED", "PHASE10_EVALUATION.json")
for threshold in ("0.8", "0.85", "0.9"):
    reg("C_threshold_" + threshold, "v2 pair threshold; cap 100; C-only", "499 queues/9980 labels",
        freeze["resource"]["wall_seconds"] + c["resource"]["wall_seconds"],
        max(freeze["resource"]["peak_process_rss_bytes"], c["resource"]["peak_process_rss_bytes"]),
        "NO_GO_RECOVERABILITY_LOSS", "PHASE13_C_EVALUATION.json")
bf = read("bridge_predictions/prediction_freeze.json")
reg("C_weak_bridge_split", "remove weak single-edge bridges from frozen v2 groups; C-only",
    "499 queues/9980 labels", bf["resource"]["wall_seconds"] + bridge["resource"]["wall_seconds"],
    max(bf["resource"]["peak_process_rss_bytes"], bridge["resource"]["peak_process_rss_bytes"]),
    "NO_GO_RECOVERABILITY_LOSS", "PHASE13_BRIDGE_EVALUATION.json")
for method in rank:
    reg("R_" + method, "frozen score vector; E1 groups", "499 queues/9980 labels",
        read("PHASE13_RANK_EVALUATION.json")["resource"]["wall_seconds"],
        read("PHASE13_RANK_EVALUATION.json")["resource"]["peak_process_rss_bytes"],
        "EXPLORATORY_ONLY_NOT_RESELECTED" if method != "blend_0.75" else "VALIDATION_SELECTED_REFERENCE",
        "PHASE13_RANK_EVALUATION.json")
with (HERE / "PHASE13_EXPERIMENT_REGISTRY.csv").open("w" if REFRESH else "x", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(registry[0]))
    writer.writeheader()
    writer.writerows(registry)

crows = "\n".join(f"| {t} | {r['recoverable']:,}/9,980 ({100*r['recoverability']:.2f}%) | {100*r['pair_precision']:.4f}% | {r['fp']:,} | {r['mixed']:,} | {paired.get(t,{}).get('newly_recoverable','—')} / {paired.get(t,{}).get('lost_recoverability','—')} |" for t,r in c["group_thresholds"].items())
rrows = "\n".join(f"| {k} | {v['incident_recall20_count']:,}/9,980 ({100*v['incident_recall20']:.2f}%) | {100*v['p10']:.4f}% | {v['ndcg20']:.6f} |" for k,v in rank.items())
routes = "\n".join(f"| {k} | {v['edges']:,} | {v['true_edges']:,} | {v['false_edges']:,} | {v['connected_top20']:,}/9,980 |" for k,v in c["candidate_routes"].items())
cascade_c = "\n".join(f"| C threshold {t} | {v['absent']:,} | {v['candidate_disconnected']:,} | {v['incomplete']:,} | {v['impure']:,} | {v['recoverable']:,} | not measured |" for t,v in c["group_thresholds"].items())
cascade_rank = "\n".join(f"| Rank {k} on E1 groups | 855 | 487 | 1,451 | 218 | {6969-v['incident_recall20_count']:,} | {v['incident_recall20_count']:,} |" for k,v in rank.items())

write("PHASE13_REPOSITORY_AUDIT.md", f"""
# Phase 13 repository and dependency audit

**E1 reproduced exactly** with the original Phase 10 evaluator and reconstruct code copied byte-for-byte into Phase 13, an identical config, and 500 read-only hard links to the frozen prediction files. The copied evaluator wrote only inside Phase 13. Its E1 method object equals the Phase 10 object field-for-field: 499 queues, 400,039 eligible alerts, 9,980 expert top-20 labels, 5,066 recovered, 6,969 recoverable, P@10 {100*e1['p10']:.6f}%, nDCG@20 {e1['ndcg20']:.9f}, grouped-pair TP 269,832, FP 28,606, mixed groups 4,841. Exact input/code hashes are in `PHASE13_INPUT_HASHES.json`; git HEAD at audit was `{head}`. No frozen file was overwritten.

## Dependency map

| Metric/artifact | Producer and inputs |
| --- | --- |
| Eligible alert scope (400,039) and 499 queues | `data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl`, GUIDE preparation and ambiguity exclusions |
| Candidate edges (1,942,648) | `src/submission_full_entity_time.py` baseline Category+technique, bounded entity and technique time-neighbor routes; frozen candidate files and hashes |
| Pair probabilities | `src/submission_entity_time_pair_v2.py` 30-feature fitted gradient boosting model, reconstructed by `src/submission_group_merge_v10_v2.py:load_queue` |
| v2 groups | Pair score ≥0.75, descending order, 100-alert union cap; frozen `v2_*.pkl` |
| v7 and child40 scores | Frozen descriptor ranker and hard-negative ranker outputs; percentile fusion in `src/sprint_rank_fusion_v1.py` |
| E1 ranking | 75% child40 + 25% v7, frozen 499 queue score vectors |
| Incident Recall@20, P@10, nDCG@20 | `src/submission_full_guide.py:tie_aware_ranking` and `src/submission_group_merge_v10_v2.py:pair_group_metrics`; evaluator-only ranks from `src/guide_rerun_v2.py` |
| Group recoverability and cascade | 80% completeness and 80% purity in `src/submission_fragment_aware_v1.py:incident_outcomes`, evaluator truth from `src/offline_joint_comparison.py:read_truth` |
| Pair TP/FP, mixed groups | `pair_group_metrics` and `incident_outcomes` in `experiments/PHASE10_FRAGMENT_RECONSTRUCTION/evaluate.py` |
| Verification | `src/agents/verification.py` delegates to a provider; Phase 10 E4 applies offline label-blind consistency veto in `reconstruct.py`. Neither has original source-observation IDs or evidence-available time in GUIDE. |

The Phase 13 evaluator independently recomputed C pair/group counts and checked all four E1 totals against the original metric implementation. New C thresholds remain C-only; no ranking metric is inferred for changed groups. The Phase 13 error table uses opaque queue/incident keys and carries no raw entity values.

## Policy and history

`configs/field_policy.yaml` has `approved_model_fields: []`. Entity/time/descriptor experiments are local retrospective sensitivity only under `configs/entity_time_sensitivity_policy.yaml`. Evaluator-only fields include `IncidentId`, `QueueRank`, grades and outcomes. GUIDE_Test labels have been exposed, so no Phase 13 GUIDE result is independent confirmation. Prior Phase 9E candidate expansion and Phase 9G hard-negative model failed; Phase 10 E2–E5 fragment reconstruction failed the safety/recovery combination. All previous experiment configs remain in `configs/` and prior experiment directories; Phase 13 changes are isolated here.
""")

write("PHASE13_FAILURE_CASCADE.md", f"""
# Phase 13 failure cascade and feasibility

The exact reproduced E1 cascade is: outside unambiguous scope **855**; candidate-disconnected **487**; candidate-connected but incomplete **1,451**; complete but impure **218**; recoverable below top 20 **1,903**; successfully recovered **5,066**. Sum = **9,980**. The incident-level `PHASE13_ERROR_ANALYSIS.csv` has one opaque keyed row per expert top-20 label, with scope, fragments, candidate connectivity, cross-fragment edge counts and max true/false scores, grouping reason, deterministic group position, and recoverability. Its positions are a diagnostic, not the tie-aware expected metric itself. Missing evidence and insufficient information cannot be diagnosed per incident from GUIDE; they are **unresolved research limitations**, not assumed model failures.

| C-only grouping | Outside scope | Candidate disconnected | Incomplete | Impure | Recoverable | Ranked success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{cascade_c}
| C weak bridge split | {bm['absent']:,} | {bm['candidate_disconnected']:,} | {bm['incomplete']:,} | {bm['impure']:,} | {bm['recoverable']:,} | not measured |

| Frozen ranking | Outside scope | Candidate disconnected | Incomplete | Impure | Recoverable below 20 | Recovered in top 20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{cascade_rank}

Every row's six exclusive cascade states total 9,980 where ranking was measured; C-only rows stop at group recoverability because their new groups were not ranked. Their first four states plus recoverable also total 9,980.

The new row-level audit confirms **1,445/1,451** incomplete connected labels have no genuine cross-fragment candidate score ≥0.75. The remaining six have such an edge; Phase 9F's replay attributes their blocking to the 100-alert cap. Among the 1,451 incomplete labels, 42 have >125 in-scope alerts and cannot meet 80% completeness under the 100-alert cap. The 218 complete-but-impure labels show false unions already exist. The 1,903 recoverable-but-below-20 labels are a ranking limit, but ranking cannot repair the 3,011 grouping/scope failures.

A new graph bridge split cut {bm['bridges_cut']:,} weak single-edge connections. It converted some impure groups into recoverable ones ({bm['newly_recoverable']} gains), but caused {bm['lost_recoverability']} previously recoverable labels to fail, net {bm['net_recoverability']}. This supports the same causal diagnosis: removing suspect links alone cannot distinguish weak true continuity from false linkage.

For 85% recoverability, the integer target is **8,483/9,980**, requiring **1,514** net new recoverable labels beyond E1's 6,969. Frozen candidate connectivity yields an optimistic 8,638/9,980 ceiling; subtracting 42 connected size-impossible labels yields **≤8,596/9,980 (86.13%)** under the unchanged 100-alert cap. This is only **113** labels above the 85% target. Reaching 8,483 would require net recovery of **1,514/1,627 (93.05%)** of the remaining cap-feasible candidate-connected labels without losing any currently recoverable label or breaking safety. It is **not a proof** that 85% is mathematically impossible. For 80% Recall@20, the integer target is **7,984/9,980**, requiring **2,918** more than E1's 5,066; it also requires recovering and ranking nearly all newly reconstructed groups. No ranking-only policy can exceed fixed-group recoverability 6,969/9,980.

The literal P@10 target 63.88% is slightly above E1's exact 63.8777555% by **0.0022445 percentage points**. Calling E1 "at target" uses rounding; this programme applies the literal threshold in gates. The target contract has no mathematical contradiction, but the rounded baseline and exact gate are different statements. The Phase 13 50/50 blend passes literal P@10 retrospectively, yet its full-cohort recall advantage is not a valid new selection because the earlier validation rule selected 75/25.
""")

write("PHASE13_CANDIDATE_GENERATION_EXPERIMENTS.md", f"""
# Candidate generation experiments

The Phase 13 route ablation filters the **same frozen 1,942,648 edges** by flags. Routes overlap; rows are not additive. Every row uses 499 queues and 9,980 expert labels. Truth is consulted only in the evaluator after the candidate graph and route flags were frozen. The measured true/false columns are evaluator diagnostics, not generator inputs.

| Route | Candidate edges | Same-incident edges | Cross-incident edges | Top-20 labels candidate-connected |
| --- | ---: | ---: | ---: | ---: |
{routes}

Removing non-entity routes loses 119 candidate-connected labels (8,519 versus 8,638); parent exact matching alone loses 2,089. This shows route complementarity, but does **not** show that adding more routes will produce safe complete groups. [Phase 9E](../../PHASE9E_CANDIDATE_RETRIEVAL_REPORT.md) previously added 49,455 bounded sixth-neighbor edges, gained only four candidate-connected labels, recovered zero additional complete-and-pure incidents, and lost 1,215 grouped true pairs. We therefore did not launch another broad candidate expansion on exposed GUIDE labels. Independent source-context, rare-entity, temporal-only, multi-hop, and complementary-type expansion require a feature-availability and false-collision design not established here. Runtime and peak memory for the shared label-blind C prediction pass were {freeze['resource']['wall_seconds']:.2f} s and {freeze['resource']['peak_process_rss_bytes']:,} bytes; route-specific prediction runtime was not separately measured.
""")

write("PHASE13_PAIR_SCORING_EXPERIMENTS.md", f"""
# Pair scoring experiments and limits

The frozen v2 scorer uses 30 numeric descriptor, shared-entity, time-gap, and route features; the fixed 0.75 grouping threshold was development-selected in the earlier pipeline. Phase 13 reuses its fitted model and tests thresholds 0.80, 0.85, and 0.90 on **exactly the regenerated frozen candidate graph**, keeping the 100-alert cap. No scorer was refitted or calibrated. Raising the threshold is a conservative pair-decision sensitivity, not a new model and not evidence that the probabilities are calibrated.

| Threshold | Recoverable | Pair precision | False grouped pairs | Mixed groups | Newly / lost recoverable versus E1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
{crows}

At 0.80, false grouped pairs fall by 17,403 and mixed groups by 1,619, while 60 incidents become recoverable and 152 lose recoverability, net −92. At 0.85 and 0.90 the safety counts fall further but net recovery losses deepen. These are group outcomes, not pair precision-recall curves; class-conditional pair-score histograms and calibration remain in the [Phase 9F audit](../../PHASE9F_CROSS_FRAGMENT_PAIR_SCORE_AUDIT.md). That audit found true and hard false cross-fragment scores overlap. The Phase 9G hard-negative model was previously measured at 54.98% pair precision and 137,884 false grouped pairs, so it is not a successful replacement. Logistic regression, new boosted models, graph-context scoring, and calibrated probabilistic scoring were not fitted here: previous GUIDE_Test exposure and absent operational field availability prevent a defensible new model-selection claim. The only new pair-score experiment is this fixed threshold sensitivity.
""")

write("PHASE13_GROUPING_EXPERIMENTS.md", f"""
# Group reconstruction experiments

Phase 13 reran the exact frozen v2 union algorithm on the full 499-queue graph at four thresholds. It applies the existing 100-alert cap, score-descending edge order, and deterministic ties. The 0.75 partition matched every frozen v2 group exactly. No group exceeds 100 alerts. The three stricter variants are **C-only**; changed groups were not rescored by the ranking models, so Recall@20, P@10 and nDCG@20 are intentionally blank in the comparison CSV.

| Threshold | Recoverable | Pair precision | False pairs | Mixed groups | New / lost recoverable |
| ---: | ---: | ---: | ---: | ---: | ---: |
{crows}

The paired alert counts are: 0.80 gained 85 alerts in newly recoverable incidents but lost 500 alerts in no-longer-recoverable incidents; 0.85 gained 127 and lost 1,556; 0.90 gained 143 and lost 2,186. These are counts of in-scope alerts belonging to gained/lost incidents, not pair metrics. Higher thresholds mainly turn impure groups into incomplete ones: incomplete labels rise from 1,451 to 1,622/1,895/2,119 while impure labels fall from 218 to 139/65/18. This is a genuine safety–recovery tradeoff, not a solution to the 85% target.

Phase 10 already tested mutual fragment matching, bounded hierarchy, and a verification veto (E2–E5). All had net recoverability losses and higher false grouped pairs. The earlier consensus splitter reached 92.07% pair precision but only 45.13% Recall@20. New unrestricted union-find, community, multi-hop, or cap relaxation was not run because the observed high-score cross-incident edges and missing provenance make uncontrolled growth unsafe. No merge provenance is claimed for the stricter threshold variants beyond the frozen edge, score, order, and cap; their exact partitions and edge probabilities are frozen in `c_predictions/`.

## Weak bridge graph split

A separate label-blind policy built each frozen group's ≥0.75 candidate-edge graph and removed only true graph bridges scoring <0.80. It cut **{bm['bridges_cut']:,}** bridges and preserved all alerts. On identical 499 queues, group recoverability became **{bm['recoverable']:,}/9,980 ({100*bm['recoverability']:.2f}%)**, pair precision **{100*bm['pair_precision']:.4f}%**, false grouped pairs **{bm['fp']:,}**, and mixed groups **{bm['mixed']:,}**. It gained **{bm['newly_recoverable']}** and lost **{bm['lost_recoverability']}** recoverable incidents (net **{bm['net_recoverability']}**); alert counts were +{bm['gained_alerts']}/−{bm['lost_alerts']}. It improves safety counts but fails recovery. Ranking was not rescored. Three synthetic graph/count tests passed before the full run. Its exact predictions and freeze are in `bridge_predictions/`.
""")

write("PHASE13_RANKING_EXPERIMENTS.md", f"""
# Ranking experiments on fixed v2 groups

The exact existing tie-aware rank evaluator was rerun on five frozen vectors: v7, 25/50/75% child40 blends, and child40 alone. All use the **same 370,850 frozen groups** and 499 queues, so group recoverability (6,969), grouped-pair TP/FP (269,832/28,606), and mixed groups (4,841) are identical. No ranker was retrained.

| Frozen ranker | Incident Recall@20 | P@10 | nDCG@20 |
| --- | ---: | ---: | ---: |
{rrows}

The 50/50 blend gives 5,092 recovered labels, +26 versus E1, and P@10 64.3053% versus 63.8778%, but nDCG@20 falls to 0.458297 from 0.469747. This **full-cohort** advantage is retrospective; [the original sprint selection](../../24H_PERFORMANCE_SPRINT/README.md) chose 75/25 because validation Recall@20 was 45.04% versus 44.48% for 50/50, and the previously exposed holdout also favored 75/25. Selecting 50/50 now from the full GUIDE_Test outcome would violate the earlier selection rule. E1 remains the defensible frozen comparator. No ranking result breaks the 69.83% fixed-group recoverability ceiling or approaches 80% Recall@20.
""")

write("PHASE13_VERIFICATION_EXPERIMENTS.md", """
# Verification and safety findings

The provider-facing V component is `src/agents/verification.py`, which delegates claim/evidence checks to a configured provider. Phase 10 E4/E5 implemented an offline, label-blind merge veto for descriptor contradiction, long time gaps, weak endpoint coverage, and insufficient reciprocal support. It reduced accepted merges but still produced **217 cross-incident merges**, **31,705 false grouped pairs** (+3,099), and **89.6642%** grouped-pair precision (below 90%). This is a measured failure of that V gate, not evidence of a reliable merge verifier.

Phase 13's stricter v2 thresholds reduce false grouped pairs and mixed groups without a V model, but each loses net recoverability. No additional V classifier was trained. GUIDE lacks authoritative source-observation IDs and evidence-availability timestamps, so duplicate upstream evidence, contradiction, and point-in-time violations cannot be independently validated. Source-relative entity and timestamp agreement are retrospective proxies only. An operational V should require independent provenance witnesses, versioned availability, explicit contradictions, and abstention reporting on the new Stage 3B ground-truth contract. No Phase 13 verification result establishes production safety.

The weak-bridge graph filter also reduces false grouped pairs to **{bm['fp']:,}** and mixed groups to **{bm['mixed']:,}** without accepting new merges, but loses **{abs(bm['net_recoverability'])}** net recoverable incidents. It cannot verify whether a cut bridge was a false derivation; it is a graph-topology diagnostic, not evidence provenance verification.
""")

write("PHASE13_BEST_PIPELINE.md", f"""
# Best defensible pipeline and selection

**Retain Phase 10 E1** as the frozen exploratory comparator: C = v2 pair scorer at 0.75 with the 100-alert cap; P = validation-selected 75% child40 + 25% v7 blend; V = existing verification functionality, without claiming empirical GUIDE provenance verification. E1 has 5,066/9,980 Recall@20 (50.7665%), 6,969/9,980 recoverability (69.8297%), P@10 63.8778%, nDCG@20 0.469747, pair precision 90.4148%, 28,606 false grouped pairs, and 4,841 mixed groups.

All stricter C thresholds satisfy the pair precision, false-pair, and mixed-group safety conditions but reduce recoverability by 92–468 labels. The 50/50 ranking blend gives a retrospective +26 Recall@20 and higher P@10 on the full cohort with the same C safety counts; it was **not** the validation-selected candidate and has lower nDCG. It is a useful sensitivity result, not a selected replacement or an independent improvement claim. Prior Phase 10 E2–E5 reconstruction policies fail pair or false-merge safety. No new complete pipeline passes the target contract.

The weak-bridge split is the strongest new C safety trade-off measured here: {100*bm['pair_precision']:.4f}% pair precision, {bm['fp']:,} false grouped pairs, and {bm['mixed']:,} mixed groups. It still loses {abs(bm['net_recoverability'])} net recoverable incidents and has no end-to-end ranking evaluation, so it is not selected.

The single most valuable next experiment is the Stage 3B authorized/controlled cohort with original source-observation IDs, derivation links, receiver-side evidence-availability ledger, and independently adjudicated interleaved incidents. Train a fragment-level complete-and-pure objective with hard cross-incident negatives on its development partition, then freeze and evaluate once on a genuinely sealed test population. This addresses the observed information gap instead of repeatedly tuning exposed GUIDE labels.
""")

write("PHASE13_FINAL_REPORT.md", f"""
# Phase 13 final report — PARTIAL IMPROVEMENT (retrospective sensitivity only)

**Research decision:** no pipeline replacement. E1 reproduced exactly. A frozen 50/50 rank blend scores +26 Recall@20 labels and +0.4275 P@10 percentage points on the full exposed GUIDE cohort, but was not validation-selected and has lower nDCG. All newly run C threshold variants lose group recoverability despite safer pair counts. The original 80%/85% targets remain unmet; the 69.83% fixed-group ceiling was not broken. The classification **PARTIAL IMPROVEMENT** refers only to measured retrospective ranking metrics, not independent generalization or a successful reconstruction redesign.

## Completed work

- Audited C/P/V dependencies, feature policy, frozen artifacts and exact evaluators; reproduced Phase 10 E1 field-for-field on 499 queues and 9,980 labels.
- Ran label-blind full-population candidate-route ablations and four grouping thresholds, with evaluator-only truth opened after prediction freeze. Produced a 9,980-row incident-level error table.
- Implemented and tested a label-blind weak-bridge graph split; froze all 499 queue predictions before its evaluator opened truth.
- Reran exact tie-aware ranking for five existing frozen score vectors on unchanged groups.
- Compared paired recovery gains/losses, runtime, peak process RSS, and original safety gates. No new pair model or V model was trained; no Phase 10 artifact was changed.

## Main measured results

| C threshold | Recoverable | Pair precision | False pairs | Mixed groups | New / lost recoverable |
| ---: | ---: | ---: | ---: | ---: | ---: |
{crows}

| Frozen ranking, fixed E1 groups | Recall@20 | P@10 | nDCG@20 |
| --- | ---: | ---: | ---: |
{rrows}

For the stricter C policies, ranking metrics were **not measured** because changed groups were not rescored. The exact comparison CSV leaves them blank; no fabricated end-to-end result is attached to these C-only experiments. Candidate route counts, full cascade, paired gains/losses, and source hashes are in the accompanying files.

The weak-bridge graph split cut {bm['bridges_cut']:,} edges and reached {bm['recoverable']:,}/9,980 recoverability, {100*bm['pair_precision']:.4f}% pair precision, {bm['fp']:,} false grouped pairs, and {bm['mixed']:,} mixed groups. It gained {bm['newly_recoverable']} recoverable incidents but lost {bm['lost_recoverability']} (net {bm['net_recoverability']}); no ranking metric was measured for its changed groups.

## Targets

| Target | Outcome |
| --- | --- |
| Incident Recall@20 ≥80% | **Not achieved.** Best measured frozen-score sensitivity: 5,092/9,980 = 51.03%; validation-selected E1: 5,066/9,980 = 50.77%. |
| Group recoverability ≥85% | **Not achieved.** Best measured remains E1 6,969/9,980 = 69.83%; stricter C falls below it. |
| P@10 ≥63.88% literal | **Achieved only by unselected 50/50 sensitivity** at 64.3053%; E1 exact 63.8778% is marginally below literal 63.88%. |
| Grouped-pair precision ≥90% | **Achieved** by E1 and stricter C sensitivities; the latter lose recovery. |
| No increase in mixed groups | **Achieved** by E1 and stricter C sensitivities. |
| No increase in false grouped pairs | **Achieved** by E1 and stricter C sensitivities. |

The target set is not proven mathematically impossible under the current candidate graph: the optimistic cap-aware recoverability ceiling is 8,596/9,980 = 86.13%, slightly above 85%. However, attaining 85% requires net recovery of 1,514 labels while preserving safety, and current pair evidence cannot distinguish many true weak links from hard false links. GUIDE has no approved operational model fields or point-in-time evidence availability. All GUIDE_Test results are retrospective exploratory because labels were previously exposed. A new independent cohort is necessary for a defensible generalization claim.
""")

write("PHASE13_REPRODUCIBILITY.md", f"""
# Phase 13 reproducibility

Run from repository root with the existing `.venv` on Windows. Phase 13 is local retrospective research only. Code version at audit: `{head}`; individual untracked Phase 13 script hashes and all frozen parent hashes are in `PHASE13_INPUT_HASHES.json`. The Phase 13 copy of `evaluate.py`, `reconstruct.py`, and `PHASE10_EXPERIMENT_CONFIG.json` is byte-identical to Phase 10. `predictions/` contains hard links to 500 frozen Phase 10 files; no file is rewritten through those links. To reproduce in a fresh directory, make read-only copies or hard links of the prediction files; do **not** run a generator that overwrites the original.

```powershell
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/evaluate.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/run_c_sensitivity.py --sample-queues 3
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/run_c_sensitivity.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/evaluate_c_sensitivity.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/compare_c_status.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/evaluate_rank_matrix.py
.\\.venv\\Scripts\\python.exe -m unittest discover -s experiments/PHASE13_RECOVERY -p 'test_phase13.py' -v
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/run_bridge_split.py --sample-queues 3
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/run_bridge_split.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/evaluate_bridge_split.py
.\\.venv\\Scripts\\python.exe experiments/PHASE13_RECOVERY/write_phase13_reports.py
```

Most scripts refuse to overwrite their outputs. Run the sequence in a fresh Phase 13 copy for reproduction. The exact Phase 10 E1 method object matched the reproduced Phase 13 method object; the 0.75 threshold partition matched every frozen v2 group and its TP/FP/mixed/recoverability totals. The full C prediction took {freeze['resource']['wall_seconds']:.2f} seconds with peak process RSS {freeze['resource']['peak_process_rss_bytes']:,} bytes; C evaluation took {c['resource']['wall_seconds']:.2f} seconds with peak RSS {c['resource']['peak_process_rss_bytes']:,} bytes. Ranking evaluation took {read('PHASE13_RANK_EVALUATION.json')['resource']['wall_seconds']:.2f} seconds with peak RSS {read('PHASE13_RANK_EVALUATION.json')['resource']['peak_process_rss_bytes']:,} bytes. These are shared-pass measurements, not per-threshold or per-ranker estimates. The incident table has 9,980 data rows.
""")

print("Phase 13 reports, metrics CSV, registry, and input hashes written")
