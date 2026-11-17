"""Render concise, reproducible Phase 26 development reports from frozen audits."""
import csv
import json
from pathlib import Path

P = Path(__file__).resolve().parent
rows = lambda name: list(csv.DictReader((P / name).open(newline="", encoding="utf-8")))
comparison = rows("PHASE26_EXPERIMENT_COMPARISON.csv")
queues = rows("PHASE26_QUEUE_METRICS.csv")
stress = rows("PHASE26_DELAY_STRESS_RESULTS.csv")
counter = rows("PHASE26_COMPONENT_COUNTERFACTUAL.csv")
reconstruction = rows("PHASE26_RECONSTRUCTION_AUDIT.csv")
summary = json.loads((P / "analysis_summary.json").read_text())
base = next(x for x in comparison if x["rule"] == "context" and x["ranker"] == "progression")


def metric(rule, ranker):
    return next(x for x in comparison if x["rule"] == rule and x["ranker"] == ranker)


def pct(value, denominator):
    return f"{100 * int(value) / denominator:.2f}%"


def put(name, content):
    (P / name).write_text(content.strip() + "\n", encoding="utf-8")


table = ["| Reconstruction / ranker | Recoverable /400 | Recall@20 /400 | P@10 /200 | Pair precision | False pairs | Mixed groups |",
         "|---|---:|---:|---:|---:|---:|---:|"]
for rule, ranker in (("context", "progression"), ("context", "blend"),
                     ("orthogonal_veto", "linear"), ("orthogonal_veto", "blend"),
                     ("pit_complete", "blend"), ("pit_selective", "blend"),
                     ("pit_direct", "blend"), ("pit_group", "blend")):
    x = metric(rule, ranker)
    table.append(f"| {rule} / {ranker} | {x['recoverable']} | {x['recall20_count']} | {x['p10_count']} | {float(x['grouped_pair_precision']):.2%} | {x['false_grouped_pairs']} | {x['mixed_predicted_groups']} |")
table = "\n".join(table)

put("PHASE26_FINAL_REPORT.md", f"""
# Phase 26 final report — NO-GO

The authoritative fresh development cohort is `v2/phase26b`: 12 scenario-disjoint training queues and 20 development queues, with 25 incidents per development queue (400 incident opportunities) and 75 interleaved benign source observations per queue. Pilot `phase26a` was diagnostic and was superseded before the authoritative run. No Phase 26 locked holdout was generated or opened because no development candidate met the predeclared improvement and safety gates.

## Same-cohort development result

{table}

The same-cohort baseline is context reconstruction plus progression ranking: **141/400 Recall@20 (35.25%)**, **154/400 recoverability (38.50%)**, 1,248 false pairs and 46 mixed groups. Orthogonal veto plus blend reached 199/400 Recall@20 (49.75%, +14.50 percentage points) and 205/400 recoverability, but created **80 controlled delayed-contradiction false merges** and regressed mixed-group safety in 16 of 20 queues. Its 99.24% pair precision does not offset those failures. The safest selective rule (`pit_selective` plus blend) had only 3 false pairs and 1 mixed group, but fell to 114/400 Recall@20 (28.50%) and 115/400 recoverability. None was eligible for holdout.

The 80% Recall@20 target is 320/400 on this development denominator. The baseline is 179 incidents (44.75 points) short; the highest-recall unsafe candidate is 121 incidents (30.25 points) short. These figures do not replace the historical Phase 25 locked 331/600 (55.17%) or Phase 16 v4 selected holdout 67.83%; cohorts differ. Phase 24's 48.44% was development recall.

## Mechanism and decision

The point-in-time ledger exposes only receiver-visible observations at minute 100. It distinguishes supported, contradicted, pending, unavailable, unknown, and unverified fields. A future correction does not change the minute-100 snapshot hash. This fixes the *temporal access path* but cannot make insufficient current evidence safe to merge. Unchanged Phase 25 orthogonal-veto logic still accepts process-only relationships before host contradiction arrives. Requiring completeness or maturity abstains on those cases, but fragments genuine incidents. Two apparent direct receipts can share a corrupted upstream controller; `pit_direct` still made 20 controlled false merges.

The original C-P-V architecture needs a component-aware, point-in-time evidence sufficiency layer before a union is committed. A better ranker cannot recover incidents that reconstruction fragments, and ranking never repairs an unsafe component. Next study: estimate calibrated relationship risk under delayed evidence and common-mode controller failure on training data, then test selective deferral or reversible provisional links with component-wide risk accounting. Holdout remains sealed until a fresh development candidate improves recoverability and passes every gate.

See the focused audits and `PHASE26_GO_NO_GO.md` for limits, exact definitions and gates.
""")

put("PHASE26_GO_NO_GO.md", f"""
# Phase 26 decision: NO-GO

No candidate passed the predeclared development selection rule. Therefore there is **no selected Phase 26 candidate, no Phase 26 holdout metric, and no holdout claim**. The locked cohorts from prior phases remain sealed.

The development gate required Recall@20 **and** recoverability above context/progression; pair precision at least 90%; no aggregate or per-queue increase in false pairs or mixed groups; P@10 no more than one correct top-ten slot below baseline; and zero false merges in the controlled delayed contradiction stress. `PHASE26_GATE_RESULTS.csv` records all 27 reconstruction/ranker combinations as failing. The gate was encoded in `v2/config.json` before the authoritative simulation.

Baseline: 141/400 recall, 154/400 recoverable, P@10 67/200, pair precision 91.74%, 1,248 false pairs, 46 mixed groups. The highest-recall tested combination, orthogonal_veto/linear, had 202/400 recall and 205/400 recoverable but 80 controlled unsafe merges and 81 mixed groups. The conservative pit_selective/blend had 114/400 recall, 115/400 recoverable, 3 false pairs and 1 mixed group. Neither meets the joint objective.

This is a development-only research decision. Phase 25 historical frozen holdout remains 331/600 Recall@20 (55.17%) with one false pair and one mixed group; it failed its own holdout safety gate. No cross-cohort performance substitution is valid.
""")

put("PHASE26_TARGET_STATUS.md", f"""
# Phase 26 target status

All Phase 26 values below are development-only, with 400 incident opportunities and 200 top-ten slots. There is no selected candidate or Phase 26 holdout.

| Target | Same-cohort baseline | Highest-recall tested (unsafe) | Safe stress rule (`pit_selective/blend`) |
|---|---:|---:|---:|
| Recall@20 ≥80% | 35.25% (141/400) | 50.50% (202/400, orthogonal_veto/linear) | 28.50% (114/400) |
| Recoverability ≥85% | 38.50% (154/400) | 51.25% (205/400) | 28.75% (115/400) |
| P@10 ≥63.88% | 33.50% (67/200) | 37.50% (75/200, linear) | 27.00% (54/200) |
| Pair precision ≥90% | 91.74% | 99.24% | 99.97% |
| False pairs: no increase | 1,248 | 125 | 3 |
| Mixed groups: no increase | 46 | 81 | 1 |

The highest-recall tested rule improves Recall@20 by 15.25 percentage points over baseline but fails delayed-contradiction and queue-level mixed-group safety. No safe recall improvement was demonstrated. Queue-cluster bootstrap 95% percentile intervals for Recall@20: baseline 29.25–41.50%; orthogonal_veto/blend 43.75–54.75%; pit_selective/blend 23.25–33.75%. These intervals measure queue sampling uncertainty in this synthetic generator; they do not validate transfer to production.
""")

put("PHASE26_EVIDENCE_AVAILABILITY_AUDIT.md", """
# Point-in-time evidence availability audit

`v2/evidence.py` is the inference access layer. It selects the latest version of each field whose receiver arrival and first observable times are at or before the configured decision minute (100), then returns a materialized `Snapshot(alerts, states, cutoff, sha256)`. Candidate reconstruction and ranking receive this snapshot, not the unfiltered atom ledger. Every prediction and union decision records the same queue snapshot hash and decision minute. The source atom ledger holds provenance fields (observation, event, source system, sensor, timestamps, original/derived, parent, duplicate, verified independence, contradictory information, version). The private evaluator files are read only after prediction freeze.

The authoritative development and training snapshots together contain 75,373 SUPPORTED, 14,829 UNAVAILABLE, 5,464 UNVERIFIED, 634 NOT_YET_AVAILABLE, and 18 UNKNOWN field states. `CONTRADICTED` is tested through post-cutoff correction; it can also be materialized when a correction is visible by the decision time. `PHASE26_FEATURE_AVAILABILITY_AUDIT.csv` gives each queue's state counts, visible alerts and receipts, cutoff and hash.

Tests cover arrival before/exactly at/one unit after/much later/never, out-of-order event time, later correction, later duplicate, later contradiction, unavailable and unknown. A post-cutoff value mutation leaves the earlier snapshot and hash invariant. The trusted loader necessarily reads the full synthetic ledger to build a snapshot; the candidate API returns only the cutoff-filtered view. This is an access boundary within the experiment, not a production security isolation claim.
""")

put("PHASE26_EVIDENCE_MATURITY_AUDIT.md", """
# Evidence maturity and abstention audit

The reconstruction candidates compute maturity from visible critical host/account fields, distinct provenance, verified independence, duplicate ratio and contradictions. `pit_complete` requires critical fields; `pit_maturity` adds a maturity threshold; `pit_selective` permits incomplete context only with separately rooted direct witnesses; `pit_group` recomputes component maturity after each proposed union; `pit_combined` and `pit_direct_mature` tighten these conditions. Scores use neither private labels nor future atoms. Missing evidence is an uncertainty state, not a contradictory observation or positive corroboration.

On the authoritative development cohort, orthogonal_veto/blend accepts 4,064 unions and abstains 1,223 times, recovering 205/400 incidents with 125 false pairs and 81 mixed groups. `pit_selective/blend` accepts 3,234 unions and abstains 2,189 times, recovering 115/400 with 3 false pairs and 1 mixed group. `pit_complete/blend` accepts 3,037 unions and abstains 2,331 times, recovering 90/400. These counts show the recall cost of the current maturity rules. `PHASE26_QUEUE_METRICS.csv`, `PHASE26_FAMILY_FAILURE_METRICS.csv`, and `PHASE26_RECONSTRUCTION_AUDIT.csv` expose queue and family breakdowns.

The maturity weights and threshold are experimental heuristics, not calibrated risk probabilities. A strong source count can still be common-mode; the correlated false-receipt stress demonstrates this limitation.
""")

put("PHASE26_DELAYED_CONTRADICTION_AUDIT.md", """
# Delayed contradiction audit

Each authoritative development queue contains controlled unrelated benign observations with host contradiction received before minute 100, exactly at 100, at 101, at 140, or never. A second fixture has two apparent direct receipts sharing a controller dependency. All decisions use minute-100 snapshots; minute-150 snapshots are retrospective evaluator views. `PHASE26_DELAY_STRESS_RESULTS.csv` records both snapshots, original decision, whether later evidence would change it, and false-pair exposure for all 20 queues and all nine reconstruction rules.

| Rule | False merges across 20 queues | Failure pattern |
|---|---:|---|
| context | 0 | Conservative rule does not propose these unions |
| orthogonal_veto | 80 | 20 each at +1, +40, never, and correlated receipts |
| pit_complete / pit_maturity / pit_selective / pit_group / pit_combined | 0 | Abstain when evidence is insufficient |
| pit_direct | 20 | Two receipts share a controller root |
| pit_direct_mature | 0 | Maturity guard abstains |

Before-cutoff and exact-cutoff contradictions are visible and do not produce a merge. The +1 and +40 cases are accepted by unchanged orthogonal veto at minute 100 and would be split with the later host value. The never-delivered case remains unresolved even retrospectively; the original merge is still false by private ground truth, illustrating why absence cannot count as corroboration. The controlled fixture primarily exercises host contradiction and process/receipt correlation. Other context dimensions and partial contradictions are represented in the broader simulator but are not exhaustively crossed in this table. The retrospective reconstruction reuses the original receipt visibility cutoff; its later-evidence comparison is a diagnostic, not a full later-time deployment replay.
""")

put("PHASE26_RECONSTRUCTION_AUDIT.md", f"""
# Reconstruction audit

Nine rules were run against the identical `phase26b` development snapshots. All three rankers reuse each rule's frozen group membership. Full metrics and union counts are in `PHASE26_EXPERIMENT_COMPARISON.csv`; accepted union increments are in `PHASE26_UNION_PAIR_AUDIT.csv`, and queue-level counts are in `PHASE26_QUEUE_METRICS.csv`.

{table}

Orthogonal veto creates more recoverable incidents than the baseline (+51/400) but fails controlled delayed-evidence safety. The complete and maturity rules eliminate those stress merges but lower recoverability by 64/400. Selective reconstruction recovers 25 more incidents than complete while preserving its controlled stress result, yet remains 39 below baseline recoverability. `pit_direct` tests whether two direct receipts retain recall; it still merges correlated benign observations and is unsafe. No rule reaches the joint objective.

One incident is recoverable when a predicted group reaches both 80% incident coverage and 80% group purity, with a cap of 100 alerts. Recall@20 further requires that qualifying group to rank in the first 20. Pair precision counts same-truth alert pairs inside predicted groups; singleton groups contribute no pair. False pairs and mixed groups are evaluated after prediction freeze. The baseline's 1,248 false pairs make its pair precision only 91.74%; reducing them alone is not evidence of improved recall.
""")

put("PHASE26_RANKING_AUDIT.md", """
# Ranking audit on fixed group membership

Progression, train-fitted linear and blended rankers were evaluated for every reconstruction rule without changing that rule's groups. Their features come from minute-100 snapshots. The trained ranker uses the 12 training queues; development truth is opened only after the predictions are frozen. The table below isolates ranking changes.

| Fixed reconstruction | Ranker | Recall@10 /400 | Recall@20 /400 | P@10 /200 | nDCG@20 |
|---|---|---:|---:|---:|---:|
""" + "\n".join(
    f"| {rule} | {ranker} | {metric(rule, ranker)['recall10_count']} | {metric(rule, ranker)['recall20_count']} | {metric(rule, ranker)['p10_count']} | {float(metric(rule, ranker)['ndcg20']):.3f} |"
    for rule in ("context", "orthogonal_veto", "pit_selective")
    for ranker in ("progression", "linear", "blend")) + """

On baseline groups, blend lifts Recall@20 from 141 to 150 (+9/400) while recoverability stays at 154/400 and P@10 moves 67 to 68. Linear reaches 153/400 but P@10 drops to 62. On orthogonal-veto groups, linear reaches 202/400 while blend reaches 199/400 with higher P@10 (90 versus 75). These are ranking effects only. Neither ranker can repair an unsafe union or restore an incident fragmented by reconstruction. The selected safety gate requires a recoverability improvement, so a ranking-only gain is insufficient for Phase 26 promotion.
""")

worst = max(counter, key=lambda x: int(x["pairs_avoided"]))
put("PHASE26_COMPONENT_SAFETY_AUDIT.md", f"""
# Component and union safety audit

Every accepted union in the authoritative development run has a frozen decision record with left and right components, postmerge size, reason, visible support, maturity diagnostics, snapshot hash, decision minute and premerge pair exposure. The evaluator then replays the union sequence against private truth to assign new true and false pairs (`PHASE26_UNION_PAIR_AUDIT.csv`). The per-queue sum of union false-pair increments exactly reconciles with `PHASE26_FAILURE_CASCADE.csv` and final group-pair counts.

`PHASE26_COMPONENT_COUNTERFACTUAL.csv` replays the fixed accepted-union list once for every accepted union of orthogonal_veto, pit_selective and pit_direct, skipping one union each time. There are {len(counter):,} such counterfactuals. The largest single omission avoids {worst['pairs_avoided']} final false pairs in `{worst['queue_id']}` under `{worst['rule']}`, union order {worst['order']}. The replay captures downstream transitive contamination: one edge may expose more false pairs than its immediate pair increment. It holds subsequent proposals fixed; it does not claim the predictor would have generated identical later proposals after an omitted union.

Orthogonal veto has 125 final false pairs and 81 mixed groups across 20 queues. Although its total false pairs are below the baseline's 1,248, mixed groups rise from 46 and 16 queues regress individually. Thus aggregate pair precision of 99.24% conceals a queue-level safety failure. The controlled correlated receipts show why two locally plausible links are insufficient when they share one upstream controller.
""")

put("PHASE26_RECALL_ERROR_ANALYSIS.md", """
# Recall error analysis

The denominator is 400 eligible development incidents, 20 per queue. `PHASE26_RECONSTRUCTION_AUDIT.csv` labels each incident as recalled, ranking-only, fragmented candidate, absent candidate or impure. The counts below use blended ranking so reconstruction can be compared with the same ranker.

| Reconstruction | Recalled | Ranking-only | Fragmented candidate | Absent candidate | Impure |
|---|---:|---:|---:|---:|---:|
""" + "\n".join(
    f"| {rule} | " + " | ".join(str(sum(x['status'] == status for x in reconstruction if x['rule'] == rule and x['ranker'] == 'blend')) for status in
          ('recalled', 'ranking_only', 'fragmented_candidate', 'candidate_absent', 'impure')) + " |"
    for rule in ('context', 'orthogonal_veto', 'pit_selective')) + """

Baseline blend has 154/400 recoverable and 150/400 recalled; only four recoverable incidents miss the top 20. Under selective reconstruction, 250/400 incidents remain fragmented and only one recoverable incident is a ranking miss. This identifies reconstruction, specifically safe linking under incomplete evidence, as the dominant recall bottleneck. Family and failure-mode counts are in `PHASE26_FAMILY_FAILURE_METRICS.csv`. The category figures are generator-specific and should not be treated as prevalence estimates.
""")

put("PHASE26_REPRODUCIBILITY.md", """
# Reproducibility and freeze

Authoritative run: `v2/`, namespace `phase26b`, train seed 260501, development seed 260611, 12 training queues, 20 development queues, cutoff minute 100. Training templates 80–83 and development templates 90–91 are scenario-disjoint. `v2/datasets/manifest.json` enumerates queues. `v2/freeze_manifest.json` records source, configuration, model and frozen prediction hashes. `dataset_hashes.json` records every authoritative JSONL input and the manifest. `analysis_summary.json` and the CSV audits are evaluator-only outputs. Pilot root files are `phase26a` diagnostics and are not used for the decision.

Run from repository root with the same Python environment:

```powershell
python experiments/PHASE26_POINT_IN_TIME_SAFETY/v2/generate.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/v2/run_study.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/analyze.py
python experiments/PHASE26_POINT_IN_TIME_SAFETY/write_reports.py
python -m unittest discover -s experiments/PHASE26_POINT_IN_TIME_SAFETY/tests -q
python -m unittest discover -s experiments/PHASE25_SAFE_RECALL/tests -q
```

Regeneration rewrites the authoritative synthetic data and frozen artifacts; verify hashes against the committed freeze before doing so. The study runner writes development predictions and decisions, then freezes their hashes, then opens private development truth to audit. No Phase 26 locked cohort exists because all candidates fail development gates. Prior locked cohorts are not read by these scripts. This is a synthetic, CPU-only experiment. The interval estimates use 2,000 queue-cluster bootstrap resamples; denominator definitions and per-queue metrics are in the CSVs.
""")

put("PHASE26_PRE_EVALUATION_PROTOCOL.md", """
# Holdout protocol status

No Phase 26 holdout was generated. `v2/config.json` required a development candidate to improve both Recall@20 and recoverability, preserve aggregate and per-queue pair and mixed-group safety, retain P@10 within one slot, and make zero controlled delayed-contradiction false merges. All 27 combinations failed. The next holdout must use new namespace, seeds and scenario families, and may be opened only after a new development candidate passes a newly frozen pre-evaluation protocol. Existing Phase 19 and Phase 22 locked cohorts remain sealed.
""")

print("Wrote Phase 26 reports")
