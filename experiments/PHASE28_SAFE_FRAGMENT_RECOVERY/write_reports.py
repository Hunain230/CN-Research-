"""Render Phase 28 reports from frozen authoritative v2 audits."""
import csv
import json
from pathlib import Path

P = Path(__file__).resolve().parent
V = P / "v2"
A = json.loads((P / "analysis_summary.json").read_text())
comparison = list(csv.DictReader((P / "PHASE28_EXPERIMENT_COMPARISON.csv").open(newline="", encoding="utf-8")))
B = A["development_selection"]["baseline"]
S = next(x for x in comparison if x["mode"] == "component")
H = A["locked_result"]["baseline"]
T = A["locked_result"]["selected"]
DH = A["development_hypotheses"]
LH = A["locked_hypotheses"]


def pct(n, d):
    return f"{100*n/d:.2f}%"


def put(name, body):
    (P / name).write_text(body.strip() + "\n", encoding="utf-8")


table = ["| Development pipeline | Recoverable /400 | Recall@20 /400 | P@10 /200 | Pair precision | False pairs | Mixed groups | Promotions |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
for x in comparison:
    table.append(f"| {x['mode']} / {x['ranker']} | {x['recoverable']} | {x['recall20_count']} | "
                 f"{x['p10_count']} | {float(x['pair_precision']):.2%} | {x['false_grouped_pairs']} | "
                 f"{x['mixed_groups']} | {x['promotions']} |")
table = "\n".join(table)

false_queues = []
qrows = list(csv.DictReader((P / "PHASE28_LOCKED_QUEUE_METRICS.csv").open(newline="", encoding="utf-8")))
base_q = {x["queue_id"]: x for x in qrows if x["mode"] == "baseline"}
for x in qrows:
    if x["mode"] == "component" and int(x["false_grouped_pairs"]) > int(base_q[x["queue_id"]]["false_grouped_pairs"]):
        false_queues.append(x["queue_id"])

dev_ci = A["bootstrap"]["development"]["recall20_count"]
lock_ci = A["bootstrap"]["locked_test"]["recall20_count"]

put("PHASE28_FINAL_REPORT.md", f"""
# Phase 28 final report — NO-GO

**Development demonstrated a large, safe synthetic gain, but the single untouched holdout failed the hard group-safety gate.** The authoritative fresh `phase28b` development cohort has 12 training and 20 development queues. Component-aware promotion increased both official recoverability and Incident Recall@20 **{B['recoverable']}/400 → {S['recoverable']}/400** (+25.00 percentage points; 100 incidents), with P@10 {B['p10_count']}/200 → {S['p10_count']}/200 and zero false pairs or mixed groups. All **127 development promotions** were evaluator-correct.

On the frozen 30-queue `phase28h` holdout, the same selected rule raised both recoverability and Recall@20 **{H['recoverable']}/600 → {T['recoverable']}/600** (+20.00 percentage points), with P@10 {H['p10_count']}/300 → {T['p10_count']}/300. Yet false grouped pairs rose **{H['false_grouped_pairs']} → {T['false_grouped_pairs']}**. Seven queues regressed; mixed groups stayed {T['mixed_groups']}. Pair precision was {T['pair_precision']:.2%}, which conceals the queue-level failure. Final decision: **NO-GO**. The paired queue-bootstrap interval for holdout recall gain is {100*lock_ci[0]:.2f}–{100*lock_ci[1]:.2f} percentage points; it does not override safety.

## Focused development comparison

{table}

The score-only calibrated rule reached 273/400 Recall@20 but created 72 false pairs and 72 mixed groups. The component rule accepted 127 of 287 hypothesis proposals and abstained on 160. The selective rule accepted 123, recalled 204/400 and also passed development safety; the predeclared highest-recall rule selected component-aware promotion. On unchanged groups, the hypothesis-aware ranking diagnostic matched the Phase 27 selected ranker at 107/400; ranking alone did not improve recoverability.

## Exact holdout failure

The holdout generator predeclared one independent false dual-lineage challenge per queue before predictions. **Seven false promotions** out of 180 were accepted (promotion precision 173/180 = {pct(173,180)}). Each joined unrelated benign fragments through two independently rooted, mutually consistent but false relationship paths. Each added five false pairs; 14 union steps sum to all 35 added pairs. Fixed-action counterfactual replay shows that skipping exactly those seven promotions removes the 35-pair increase. The failing queues are {', '.join(false_queues)}. Receiver-visible host/account values were consistent at minute 100; later contradictory host evidence was never used for the original decision.

The present component guard distinguishes the correlated-controller decoys in development, but it cannot establish the truth of two independent-looking false paths. This is the remaining causal trust limit. Keep unpromoted hypotheses for discovery, and next test a truly independent attestation of the claimed cross-fragment event or a provisional, reversible analyst workflow. Do not tune against this opened holdout. Phase 27's frozen holdout remains historical and separate; its baseline recoverability was 171/600 for both pipelines, while Recall@20 was 159/600 → 171/600.
""")

put("PHASE28_GO_NO_GO.md", f"""
# Phase 28 decision: NO-GO

Development selection passed all predeclared gates for component-aware promotion: recoverability and Recall@20 107/400 → 207/400, P@10 43/200 → 78/200, pair precision 100%, zero false pairs and zero mixed groups in all 20 queues. Code, model, thresholds, selected rule, holdout generator and evaluator were hashed in `v2/pre_evaluation_protocol.json` before the holdout existed. Only the selected component rule and same-cohort baseline were predicted on holdout; prediction hashes were written before private truth was opened once.

The holdout failed a hard gate: false grouped pairs **41 → 76**, including seven queue-level regressions of one to six false pairs each. Grouped-pair precision remained above 90%, but that does not permit promotion. Recoverability and Recall@20 rose 171/600 → 291/600, P@10 rose 98/300 → 125/300, and mixed groups stayed 25. The seven false accepted promotions account for all 35 additional pairs. The frozen candidate is rejected; no threshold or alternative was tested on the opened holdout.

The initial `phase28a` pilot was development-only and produced no promotions because of an overconservative global threshold. A training-only guarded calibration was then evaluated on a separate fresh `phase28b` cohort. This change preceded the authoritative development prediction freeze and holdout generation.
""")

put("PHASE28_TARGET_STATUS.md", f"""
# Phase 28 target status

| Metric | Fresh development baseline → selected | Frozen holdout baseline → selected | Target |
|---|---:|---:|---:|
| Recoverability | 107/400 (26.75%) → 207/400 (51.75%) | 171/600 (28.50%) → 291/600 (48.50%) | ≥85% |
| Official Recall@20 | 107/400 (26.75%) → 207/400 (51.75%) | 171/600 (28.50%) → 291/600 (48.50%) | ≥80% |
| P@10 | 43/200 (21.50%) → 78/200 (39.00%) | 98/300 (32.67%) → 125/300 (41.67%) | ≥63.88% |
| Pair precision | 100% → 100% | 99.78% → 99.71% | ≥90% |
| False pairs | 0 → 0 | 41 → **76** | No increase |
| Mixed groups | 0 → 0 | 25 → 25 | No increase |

The selected holdout Recall@20 is 189 incidents (31.50 points) below 80%; recoverability is 219 incidents below 85%. The holdout gain of 120 incidents is **unsafe**. Paired queue-bootstrap 95% intervals for Recall@20 gain: development {100*dev_ci[0]:.2f}–{100*dev_ci[1]:.2f} points, holdout {100*lock_ci[0]:.2f}–{100*lock_ci[1]:.2f} points. These intervals measure synthetic queue variation and cannot override the false-pair gate.
""")

put("PHASE28_RECOVERY_OPPORTUNITY_AUDIT.md", f"""
# Recovery opportunity audit

The authoritative baseline leaves **293/400** priority incidents unrecalled; all 107 recoverable incidents are already in the top 20 under the Phase 27 selected ranker. Each unrecalled incident is assigned one evaluator-only category in priority order, using frozen minute-100 hypotheses and evidence states:

| Category | Incidents |
|---|---:|
""" + "\n".join(f"| {k} | {v} |" for k, v in sorted(A["opportunities"].items())) + """

No incident fell into no-candidate, visible-contradiction or ranking-only categories in this fixture. Pending evidence is an uncertainty state at minute 100, never a value read from the future. A pending-context incident can still have independent positive lineage witnesses; the component rule's development gains mostly came from this class. These categories are diagnostic and mutually exclusive by rule order, not intrinsic clinical or operational labels. Per-incident and per-family rows are in `PHASE28_RECOVERY_OPPORTUNITIES.csv` and `PHASE28_FAMILY_METRICS.csv`.
""")

put("PHASE28_HYPOTHESIS_PROMOTION_AUDIT.md", f"""
# Hypothesis promotion audit

The Phase 27 graph and hypothesis builder are reused unchanged. A lightweight training-only naive Bayes model scores visible dual lineage, root-disjoint witnesses, context consistency, exposure, duplicate ratio, common roots and arrival time. The threshold is calibrated inside a predeclared structural guard. In the 12 training queues, **78 true and zero false** hypotheses met the guard; the earlier diagnostic global threshold admitted none. No development or holdout labels enter inference.

The promoter outputs PROMOTE, RETAIN AS HYPOTHESIS or REJECT. Every decision stores the complete proposed component, score, threshold, visible features, pair exposure, minute-100 snapshot hash and decision time. It recomputes the resulting component's context, witness features and exposure after each accepted union. Retained and rejected hypotheses remain available to the separate discovery track.

| Split | Qualifying hypotheses / all | Top-20 incidents hypothesized | Component promotions | True promotions | Promotion precision | Retained | Promotion coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | {DH['qualifying']}/{DH['total']} ({pct(DH['qualifying'],DH['total'])}) | {DH['top20_incidents']}/400 | 127 | 127 | 100% | 160 | {pct(127,DH['qualifying'])} of qualifying hypotheses |
| Holdout | {LH['qualifying']}/{LH['total']} ({pct(LH['qualifying'],LH['total'])}) | {LH['top20_incidents']}/600 | 180 | 173 | {pct(173,180)} | 297 | {pct(173,LH['qualifying'])} of qualifying hypotheses |

The abstention rate among evaluated component proposals was {pct(160,287)} on development and {pct(297,477)} on holdout. The calibrated score-only diagnostic accepted 287/287 development proposals, including 79 nonqualifying ones, creating 72 false grouped pairs. The component guard excluded those development errors but failed on seven holdout hypotheses with two independent-looking false lineage paths. A source-root diversity count is therefore useful but insufficient as a causal-truth certificate.
""")

counter = A["counterfactual"]
put("PHASE28_COMPONENT_SAFETY_AUDIT.md", f"""
# Component and union safety audit

The selected rule examines all alerts in the proposed merged component, visible host/account contradictions, dual lineage types, root-disjoint witnesses, shared controllers, duplicate source ratio and cumulative cross-component pair exposure. It recalculates these after every accepted promotion. It never reads private incident truth at inference. Union decisions are frozen before evaluator replay.

Development: 127 accepted promotions, 127 evaluator-qualifying, zero false-pair-creating unions, zero final false pairs and zero mixed groups. Holdout: 180 promotions, 173 qualifying, **seven false**. In each failing queue the baseline had one false pair and the selected pipeline six. The seven false hypotheses produced 14 false-pair-creating union steps, with increments totaling **35**; the complete selected total is 76 versus baseline 41. The seven affected queues are {', '.join(false_queues)}.

`PHASE28_UNION_PAIR_AUDIT.csv` and locked counterparts exactly reconcile accepted-union increments with final pair counts. Fixed-action counterfactual replay skipped each of the {counter['promoted']} accepted holdout promotions in turn while replaying all subsequent unions. Exactly {counter['false_pair_avoiding_skips']} skips avoided false pairs, and their avoided increments totaled {counter['pairs_avoided_total']}; all seven touched the predeclared independent-root false witness injections. The replay holds subsequent proposals fixed and is an evaluator diagnostic, not a prediction that the system would have made identical later proposals after a skipped union.

The original cutoff lacked the later contradictory host observation, so the model could not know it. The safety failure is accepting the shared relationship without a trustworthy independent check of the asserted cross-fragment event. Aggregate pair precision of {T['pair_precision']:.2%} cannot conceal these queue-level regressions.
""")

rank_baseline = next(x for x in comparison if x["mode"] == "baseline" and x["ranker"] == "progression")
rank_hyp = next(x for x in comparison if x["mode"] == "baseline" and x["ranker"] == "hypothesis_aware")
put("PHASE28_RANKING_AUDIT.md", f"""
# Fixed-group ranking audit

The three ranking comparisons use **identical baseline group membership** on all 20 development queues:

| Ranker | Recoverable /400 | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |
|---|---:|---:|---:|---:|---:|
| Progression | {rank_baseline['recoverable']} | {rank_baseline['recall10_count']} | {rank_baseline['recall20_count']} | {rank_baseline['p10_count']} | {float(rank_baseline['ndcg20']):.3f} |
| Phase 27 selected | {B['recoverable']} | {B['recall10_count']} | {B['recall20_count']} | {B['p10_count']} | {B['ndcg20']:.3f} |
| Hypothesis aware | {rank_hyp['recoverable']} | {rank_hyp['recall10_count']} | {rank_hyp['recall20_count']} | {rank_hyp['p10_count']} | {float(rank_hyp['ndcg20']):.3f} |

The small, explicitly unverified hypothesis bonus changed no development top-20 or P@10 result. It cannot make a fragmented incident officially recoverable. The holdout protocol evaluated only the selected component-aware pipeline and same-cohort Phase 27 ranker baseline; no ranker alternative was tested after holdout truth opened. Holdout nDCG@20 rose {H['ndcg20']:.3f} → {T['ndcg20']:.3f} because grouping changed alongside ranking order, so this is not a fixed-group ranking claim.
""")

put("PHASE28_RECALL_ERROR_ANALYSIS.md", f"""
# Recall error analysis

On authoritative development, the Phase 27 selected ranker already recalled every recoverable baseline incident: 107/400. Component promotion lifted both recoverability and official Recall@20 to 207/400. This is a reconstruction gain, not a ranking-only gain. The remaining **193/400** priority incidents were unrecovered under the selected rule. The strongest score-only candidate reached 273/400 but made 72 false pairs and 72 mixed groups, demonstrating that simply promoting more hypotheses trades away safety.

On the holdout, baseline recoverability and recall were 171/600; selected reached 291/600, leaving **309/600** unrecovered. The 120-incident gain is invalid for promotion because false grouped pairs increased by 35 across seven queues. The false promotions were benign fragments with two independent-looking, mutually consistent but incorrect lineage paths. This explains why train/development precision of 127/127 did not generalize.

The discovery layer still had useful unpromoted information: 326/477 holdout hypotheses qualified by private retrospective truth, but the promoter retained 153 of these. Recovering them safely requires a signal independent of the two challenged relationship paths, or a reversible human-reviewed incident suggestion that does not claim permanent group recovery.
""")

put("PHASE28_REPRODUCIBILITY.md", """
# Phase 28 reproducibility

The authoritative experiment is `v2/` (`phase28b`): 12 training queues (seed 281231), 20 fresh development queues (seed 281677), and one post-selection `phase28h` locked cohort of 30 queues (seed 282251). Training/development variant names and seeds are disjoint; holdout family names and variants are new. The holdout adds one predeclared independent false dual-lineage challenge per queue. All are synthetic draws from the reused Phase 27 simulator, not external validation. The development-only `phase28a` pilot calibrated no promotions and is excluded from final selection.

`v2/development_freeze.json` hashes code, configuration, model and development predictions before opening development truth. `v2/pre_evaluation_protocol.json` hashes the selected component rule, thresholds, holdout builder and evaluator before holdout generation. `v2/locked_prediction_freeze.json` hashes public locked inputs, predictions, decisions and hypotheses before private truth was opened once. It also pins the unchanged Phase 27 graph, evidence layer and ranker model by hash. No Phase 27 holdout truth was used for training or tuning; earlier Phase 19 and Phase 22 locked cohorts remain sealed.

From a clean Phase 28 directory, run:

```powershell
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/generate.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/study.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/freeze_holdout.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/holdout.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/v2/holdout_run.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/analyze.py
python experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/write_reports.py
python -m unittest discover -s experiments/PHASE28_SAFE_FRAGMENT_RECOVERY/tests -q
```

Generators refuse to overwrite existing cohorts. Do not reuse the opened holdout for threshold selection. The exact official metric definition is the frozen Phase 27 evaluator: 20 oracle-priority incidents per queue; a group qualifies with ≥80% eligible incident coverage and ≥80% group purity, and Recall@20 requires its first qualifying position ≤20. P@10 credits distinct oracle top-ten incidents in the first ten groups. Hypothesis precision and promotion precision are separate retrospective metrics. Pair precision counts within-group same-incident alert pairs; false pairs and mixed groups are evaluated after predictions freeze. Paired intervals use 2,000 queue-cluster resamples.
""")

print("Wrote Phase 28 reports")
