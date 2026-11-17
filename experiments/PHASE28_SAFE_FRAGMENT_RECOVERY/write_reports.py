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

**Development demonstrated a large, safe synthetic gain, but the single untouched holdout failed the hard group-safety gate.** The authoritative fresh `phase28b` development cohort has 12 training and 20 development queues. Component-aware promotion increased official recoverability and Incident Recall@20 **{B['recoverable']}/400 → {S['recoverable']}/400** and **{B['recall20_count']}/400 → {S['recall20_count']}/400** (+{pct(int(S['recall20_count'])-B['recall20_count'],400)}; {int(S['recall20_count'])-B['recall20_count']} incidents), with P@10 {B['p10_count']}/200 → {S['p10_count']}/200 and zero false pairs or mixed groups. All **127 development promotions** were evaluator-correct.

On the frozen 30-queue `phase28h` holdout, the same selected rule raised recoverability and Recall@20 **{H['recoverable']}/600 → {T['recoverable']}/600** and **{H['recall20_count']}/600 → {T['recall20_count']}/600** (+20.00 percentage points), with P@10 {H['p10_count']}/300 → {T['p10_count']}/300. Yet false grouped pairs rose **{H['false_grouped_pairs']} → {T['false_grouped_pairs']}**. Seven queues regressed; mixed groups stayed {T['mixed_groups']}. Pair precision was {T['pair_precision']:.2%}, which conceals the queue-level failure. Final decision: **NO-GO**. The paired queue-bootstrap interval for holdout recall gain is {pct(lock_ci[0],1)}–{pct(lock_ci[1],1)}; it does not override safety.

## Focused development comparison

{table}

The score-only calibrated rule reached 273/400 Recall@20 but created 72 false pairs and 72 mixed groups. The component rule accepted 127 of 287 hypothesis proposals and abstained on 160. The selective rule accepted 123, recalled 204/400 and also passed development safety; the predeclared highest-recall tie break selected component-aware promotion. On unchanged groups, the hypothesis-aware ranking diagnostic matched the Phase 27 selected ranker at 107/400; ranking alone did not improve recoverability.

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

The selected holdout Recall@20 is 189 incidents (31.50 points) below 80%; recoverability is 219 incidents below 85%. The holdout gain of 120 incidents is **unsafe**. Paired queue-bootstrap 95% intervals for Recall@20 gain: development {pct(dev_ci[0],1)}–{pct(dev_ci[1],1)}, holdout {pct(lock_ci[0],1)}–{pct(lock_ci[1],1)}. These intervals measure synthetic queue variation and cannot override the false-pair gate.
""")

put("PHASE28_RECOVERY_OPPORTUNITY_AUDIT.md", f"""
# Recovery opportunity audit

The authoritative baseline leaves **293/400** priority incidents unrecalled; all 107 recoverable incidents are already in the top 20 under the Phase 27 selected ranker. Each unrecalled incident is assigned one evaluator-only category in priority order, using frozen minute-100 hypotheses and evidence states:

| Category | Incidents |
|---|---:|
""" + "\n".join(f"| {k} | {v} |" for k, v in sorted(A["opportunities"].items())) + """

No incident fell into no-candidate, visible-contradiction or ranking-only categories in this fixture. Pending evidence is an uncertainty state at minute 100, never a value read from the future. A pending-context incident can still have independent positive lineage witnesses; the component rule's development gains mostly came from this class. These categories are diagnostic and mutually exclusive by rule order, not intrinsic clinical or operational labels. Per-incident and per-family rows are in `PHASE28_RECOVERY_OPPORTUNITIES.csv` and `PHASE28_FAMILY_METRICS.csv`.
""")
