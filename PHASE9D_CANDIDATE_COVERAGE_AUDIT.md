# Phase 9D — candidate coverage and grouping bottleneck audit

**Status: read-only retrospective diagnosis, 15 November 2026.** This report reads existing frozen outputs and recomputes only label-side category and alert counts in memory. No model, threshold, candidate graph, group, rank, dataset, configuration, or prior experiment artifact was changed. GUIDE_Test labels were previously accessed; all findings are **exploratory**, not independent validation or operational SOC performance. Incident membership and expert rank are evaluator-only and were never inference features.

## Scope and frozen reference

The matched historical scope has **499 organization queues**, **400,039 unambiguous alerts**, **1,942,648 candidate pairs**, and **9,980 expert top-20 incident labels**. The candidate graph is entity-enabled; v2 forms groups using a frozen pair model, **0.75** link cutoff, and a **100-alert** component cap; v7 orders those groups. A label is recoverable when a predicted group contains at least **80% of its in-scope expert-incident alerts** and at least **80% of that group belongs to the incident**. These rules and the tie-aware rank evaluator remain unchanged.

The current candidate, v2, and v7 prediction-freeze SHA-256 hashes were verified as `eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8`, `819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b3a074fe66b325fb9b4e`, and `40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743`, respectively. Per-queue candidate and v2 file hashes were checked against the two freeze manifests during the alert-count calculation. The [Phase 6 diagnosis](outputs/phase6_grouping_failure_analysis_20261115_v4.json) had already regenerated all 499 candidate graphs and v2 pair probabilities and verified their exact group partitions. The [v7 metrics](outputs/submission_descriptor_ranker_v7_20261114_v1/metrics.json) establish the final ranking result. The [Phase 9C prediction freeze](outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json) and [Phase 9C metrics](outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json) remain preserved; their verified SHA-256 hashes are `a734427180521f852364650c78fe9fec6ef27cb7af0bbb6161b33adbfecfe78d` and `794a02d115d78f6a8a944e0e3c5090ffd962daeabc0b23909d40628d9b279c19`.

## Mutually exclusive loss cascade

The categories below are applied in order. **“No candidate connection” means insufficient same-incident connectivity to place 80% of that label in one oracle candidate component; it does not mean that the incident has zero candidate edges.** Candidate components are built with expert membership **only inside this evaluator-side diagnostic**. Alert counts are in-scope expert-incident alert memberships for the labels in each row. The 855 absent labels have zero alerts under the current unambiguous assignment rule; this does not imply those expert incidents had no raw evidence.

| Earliest failure or outcome | Top-20 labels | In-scope alerts belonging to those labels | Diagnostic meaning |
|---|---:|---:|---|
| Absent from unambiguous alert scope | 855 | 0 | Ambiguous assignments exclude their alerts from this model scope. |
| Insufficient candidate connection | 487 | 20,693 | Even oracle selection of existing same-incident edges leaves every candidate component below 80% completeness. |
| Candidate connected, but v2 group incomplete | 1,451 | 63,655 | Existing candidate edges can connect enough alerts, but the actual v2 groups do not. |
| Complete v2 group is impure | 218 | 412 | A group reaches 80% completeness but fails the 80% purity rule. |
| Complete and pure v2 group, below rank 20 | 1,997 | Not separately exported | The fixed groups are recoverable, but v7 ordering misses the top 20. |
| Recovered in top 20 | 4,972 | Not separately exported | Frozen v2 + v7 end-to-end result. |
| **Complete and pure before ranking (last two rows)** | **6,969** | **9,003 combined** | Exact combined alert-membership count for the two rank outcomes. |

The first four row counts and the combined recoverable alert count were recomputed from frozen per-queue candidates/groups and evaluator truth/ranks; they match the [Phase 6 aggregate](outputs/phase6_grouping_failure_analysis_20261115_v4.json). The two rank outcomes are from the [Phase 2 v7 loss decomposition](PHASE2_RECALL_IMPROVEMENT_PLAN.md), cross-checked against v7 aggregate Recall@20. Their separate alert-membership counts were **not** computed here, so no split is inferred from 9,003. The 63,655 incomplete-alert count includes very large incidents; it is not a count of missing candidate edges. The 20,693 disconnected-alert count likewise includes many large incidents. Different incident labels have disjoint assigned alerts within each organization under the unambiguous truth map.

The cascade is **9,980 → 9,125 in scope → 8,638 candidate connectable → 6,969 recoverable from fixed groups → 4,972 reaching the top 20**. The achieved Recall@20 is **49.82%**; fixed-group recoverability is **69.83%**. The existing graph's gold-aware connectivity ceiling is **86.55%**. These percentages share the 9,980-label denominator, but the two ceilings use oracle information and are **not achieved model results**.

## Where candidate generation loses connections

The [generator](src/submission_full_entity_time.py) combines earlier exact descriptor proposals with same-organization entity postings within **48 hours** and technique postings within **one hour**. It discards a token posting with more than **500** alerts and considers only the next **five** time-nearest alerts per posting. Its route counts and edges are frozen before v2 scoring. The [pair scorer and grouping code](src/submission_entity_time_pair_v2.py) then extract descriptor overlap, entity type/rarity, time gap, and route flags; sort edges at probability ≥0.75; and union them subject to the 100-alert cap. The [v7 ranker](src/submission_descriptor_ranker_v7.py) scores the resulting groups; ranking does not repair missing or impure groups.

All **487** disconnected labels have more than one oracle same-incident candidate component. Their incident-size distribution is **350 with 2–10 in-scope alerts**, **112 with 11–100**, and **25 with more than 100**. The following exact signal inspection covered the **350 small** cases only, by checking every cross-component alert pair in evaluator memory. Counts overlap and must **not** be summed as a partition:

| Observed among 350 small disconnected incidents | Labels | Implication |
|---|---:|---|
| No shared usable entity or technique across components | 159 | Current entity/technique routes lack a direct token bridge. Detector/category overlap, if present, is not sufficient proof of a true link. |
| At least one shared entity | 87 | A possible route exists, subject to timing, token frequency, and neighbor budget. |
| Shared entity within 48 hours | 48 | Only 40 also have a route-prefilter-eligible missing pair. |
| Shared entity only beyond 48 hours | 39 | Wider time may add related pairs and unrelated collisions. |
| Shared technique | 128 | Technique can be generic; 126 share it only beyond the one-hour window. |
| Route-prefilter-eligible pair missing from frozen graph | 40 | Concrete, bounded opportunity consistent with the five-neighbor posting limit; not proof that all 40 would become 80%-connected. |
| Shared detector / category | 244 / 290 | Descriptor routes would need negative-pair and volume checks. |

Across **all 400,039** alert projections, **12,549** have no usable entity and **240,440** have no technique. Among disconnected labels, **40** have no usable entity on any incident alert, **203** have no technique on any incident alert, and **97** span more than 48 hours. These are overlapping correlates, not exclusive causes. The graph has **699,790** same-incident candidate pairs out of **159,186,107** possible positive within-organization alert pairs: **0.4396% exhaustive positive-pair coverage**. This very low pair-level ratio coexists with the **86.55% incident-level connectivity ceiling** because large incidents create many possible pairs while a few links can connect an incident. Neither ratio alone establishes safe downstream grouping.

The saved [route ablation](outputs/submission_candidate_route_ablation_v11_20261115_v1/metrics.json) is a retrospective check that entity proposals matter; dropping them lowered candidate-connected labels from **8,638 to 6,657** and Recall@20 from **49.82% to 44.33%**. That result does not establish that adding broader entity routes will improve purity or recall.

## Where candidate edges are rejected or groups fail

For **all 1,451 candidate-connected but incomplete labels**, the evaluator found at least one same-incident candidate edge crossing v2 groups, and **827** had at least two. Their best cross-fragment v2 pair scores were **138 below 0.25; 639 from 0.25 to below 0.50; 430 from 0.50 to below 0.65; 238 from 0.65 to below 0.75; and 6 at or above 0.75 but blocked by the 100-alert cap**. Thus **1,445/1,451** have no cross-fragment positive edge reaching the fixed 0.75 link cutoff; six are a component-constraint issue. The 1,451 split as **1,244 small (2–10)**, **158 medium (11–100)**, and **49 large (>100)**. This is the largest upstream failure category by labels. The Phase 8 small-incident audit found **624/1,244** with only one cross-fragment candidate edge and **429/1,244** with no Phase 7 fragment proposal at its 0.40 floor; the latter still have frozen candidate edges. Those figures explain why a two-edge-only or ≥0.40 proposal rule cannot cover all missed small incidents.

For **218** top-20 labels, v2 created a sufficiently complete group but mixed in enough unrelated alerts to fail purity. The selected groups have **636 unrelated alert memberships** across label-level cases, which can repeat when multiple labels select the same group. Every selected group contains a direct accepted cross-incident edge; **125** contain exactly one such edge, and the selected groups contain **916** direct high-score cross-incident edges in total. This is distinct from the all-group **4,841 mixed predicted groups** and **28,606 false-positive grouped alert pairs** at baseline. A high pair score is therefore not a safe merge certificate. Phase 9C demonstrated the risk: its **38** attempted merges included **25** cross-incident decisions and added **168** false grouped pairs, while recoverability fell **6,969 → 6,966** and Recall@20 **4,972 → 4,971**. Its result is [NO-GO](PHASE9C_GROUPING_EXPERIMENT_REPORT.md); it is not a new baseline.

## Diagnostic upper bounds and target feasibility

| Hypothetical oracle condition | Max labels / 9,980 | Bound | What it assumes |
|---|---:|---:|---|
| Perfect ranking of **existing** v2 groups | 6,969 | 69.83% | No group changes; only recoverable labels can be ranked. |
| Correct **grouping and ordering on the existing graph**, ignoring score/purity mistakes | 8,638 | 86.55% | Evaluator selects same-incident candidate links; an optimistic graph bound, not a practical method. |
| Restore all 1,451 incomplete labels while leaving other failure types fixed | 8,420 | 84.37% | Pure, complete groups appear for every split label, with no new losses; still an oracle group bound. |
| Also restore all 218 impure labels on existing graph | 8,638 | 86.55% | Every candidate-connected label becomes pure and complete. |
| Also connect all 487 disconnected labels | 9,125 | 91.43% | Requires new correct candidate links and pure grouping; 855 absent labels remain outside scope. |

The **85% group-recoverability** target requires at least **8,483** recoverable labels, or **1,514 net new** relative to 6,969. Fixing *all* 1,451 incomplete labels alone remains **63 short**; at least some impure labels or candidate-disconnected labels must also be repaired. The existing candidate graph's oracle leaves only **155 labels** of slack above 8,483. The **80% Recall@20** target requires **7,984** ranked recoveries, **3,012 net new** relative to 4,972. Even if 85% group recoverability were achieved exactly, ranking would have to place **7,984/8,483 = 94.12%** of all recoverable labels in the top 20, versus **4,972/6,969 = 71.34%** today. These are arithmetic requirements, not forecasts. With existing groups alone, 80% Recall@20 is impossible; candidate expansion alone also cannot promise it. The 100-alert cap further constrains some large incidents, while the candidate oracle does not model false merges, scoring, or ranking.

## Bottleneck ranking and smallest next experiment

1. **Ranking on fixed groups: 1,997 labels** are already pure and complete yet below 20. This is the largest single end-to-end loss, but ranker changes are outside this grouping-focused step and cannot raise group recoverability.
2. **Candidate-connected grouping splits: 1,451 labels**, including 1,244 small cases. This is the largest recoverability loss. Existing edges are present, but Phase 9C and prior merge studies show that a generic boundary heuristic creates false merges. A new grouping decision needs better discriminatory evidence, not simply a lower cutoff.
3. **Candidate disconnection: 487 labels**, including 350 small cases. Within those, the **40 small route-prefilter-eligible but missing-pair cases** are the narrowest concrete retrieval-limit target. An edge added for one of them would still have to pass pair scoring, safe grouping, and ranking.
4. **Impurity: 218 labels**. Preventing or splitting accepted false bridges may recover some labels while protecting precision, but can create new false splits.
5. **Absent scope: 855 labels**. This requires an authoritative ambiguous-alert assignment rule; the model cannot infer it from evaluation labels.

**Recommended smallest next experiment:** a *single bounded candidate-retrieval ablation* for the five-neighbor posting limit, designed to expose only previously prefilter-eligible pairs while keeping the 500-posting cap, 48-hour entity window, one-hour technique window, frozen v2 pair scorer, 0.75 grouping rule, 100-alert cap, and fitted v7 ranker fixed. Before implementing, specify a per-posting/per-alert/per-queue candidate budget and a negative-pair collision audit. Freeze the route rule once; compare added pair volume, positive-pair coverage, the 487-label connectivity category, group recoverability, FP grouped pairs, mixed groups, Recall@20, P@10, nDCG@20, runtime, and peak memory on the identical 499-queue scope. Reject if false merges/purity worsen. **This is a proposal, not a result or a license to select a neighbor budget on exposed GUIDE outcomes.** If this narrow route cannot improve net recoverability, the larger 1,451-label split problem needs new provenance-rich evidence or authorized expert boundary annotations before another merge model is justified.

## Reproduction and limits

Run these **read-only** commands from `C:\Users\surface\Desktop\CN-Research-`:

```powershell
$paths = @('outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json','outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json','outputs/submission_descriptor_ranker_v7_20261114_v1/prediction_freeze.json','outputs/phase9c_small_fragment_heuristic_20261115_v1/prediction_freeze.json','outputs/phase9c_small_fragment_heuristic_20261115_v1/metrics.json')
$paths | ForEach-Object { $h = Get-FileHash -Algorithm SHA256 -LiteralPath $_; "{0}  {1}" -f $h.Hash.ToLower(), $_ }
$a = Get-Content outputs/phase6_grouping_failure_analysis_20261115_v4.json -Raw | ConvertFrom-Json
$a.categories | ConvertTo-Json
$a.incomplete_best_cross_positive_edge_score | ConvertTo-Json
$a.candidate_disconnected_2_to_10_cross_component_signals | ConvertTo-Json
$a.impure_group_diagnostics | ConvertTo-Json
```

To reproduce the additional alert-membership totals **without creating a file**, run:

```powershell
@'
import json, pickle
from collections import Counter, defaultdict
from src.submission_full_guide import ROOT
from src.guide_rerun_v2 import key, labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file

candidate_freeze = json.loads((ROOT / 'outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json').read_text())
group_freeze = json.loads((ROOT / 'outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json').read_text())
with (ROOT / 'data/derived/submission_full_guide_paper_20261113_v1/predictions.pkl').open('rb') as f:
    baseline = pickle.load(f)
organizations = sorted(baseline)
truth = read_truth(set(organizations), {a for o in organizations for a in baseline[o]['input_alert_keys']})
ranks = labels(set(organizations))
labels_by_category, alerts_by_category = Counter(), Counter()
for org in organizations:
    name = key(org)
    cp = ROOT / 'data/derived/submission_full_entity_time_20261114_v1' / f'{name}.pkl'
    gp = ROOT / 'data/derived/submission_entity_time_pair_v2_20261114_v1' / f'v2_{name}.pkl'
    assert sha256_file(cp) == candidate_freeze['prediction_sha256'][name]
    assert sha256_file(gp) == group_freeze['prediction_sha256'][name]
    with cp.open('rb') as f: candidate = pickle.load(f)
    with gp.open('rb') as f: grouped = pickle.load(f)
    keys = grouped['input_alert_keys']
    assert keys == candidate['input_alert_keys']
    n = len(keys)
    parent = list(range(n))
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for edge in candidate['candidate_edges']:
        a, b = divmod(int(edge), n)
        if truth[keys[a]] == truth[keys[b]]:
            ra, rb = root(a), root(b)
            if ra != rb: parent[rb] = ra
    gold_alerts, oracle_parts, group_parts = defaultdict(list), defaultdict(Counter), defaultdict(list)
    for i, alert in enumerate(keys):
        gold = truth[alert]
        if gold in ranks[org]:
            gold_alerts[gold].append(i)
            oracle_parts[gold][root(i)] += 1
    for group in grouped['groups']:
        members = Counter(truth[a] for a in group)
        for gold, overlap in members.items():
            if gold in ranks[org]: group_parts[gold].append((overlap, len(group)))
    for gold in ranks[org]:
        size = len(gold_alerts[gold])
        complete = [(overlap, group_size) for overlap, group_size in group_parts[gold]
                    if size and overlap / size >= .8]
        if size == 0: category = 'absent'
        elif max(oracle_parts[gold].values(), default=0) / size < .8: category = 'candidate_disconnected'
        elif not complete: category = 'incomplete'
        elif not any(overlap / group_size >= .8 for overlap, group_size in complete): category = 'impure'
        else: category = 'recoverable'
        labels_by_category[category] += 1
        alerts_by_category[category] += size
print(json.dumps({'labels': dict(labels_by_category),
                  'in_scope_expert_alerts': dict(alerts_by_category)}, sort_keys=True))
'@ | .\.venv\Scripts\python.exe -
```

This loads the frozen candidate and v2 per-queue pickle files, verifies their prediction-freeze hashes, and uses truth/rank only inside the diagnostic. Its output was:

```json
{"labels":{"absent":855,"candidate_disconnected":487,"impure":218,"incomplete":1451,"recoverable":6969},"in_scope_expert_alerts":{"absent":0,"candidate_disconnected":20693,"impure":412,"incomplete":63655,"recoverable":9003}}
```

The existing `submission/diagnose_phase6_grouping_failures.py` is the full implementation of the evaluator-side graph/score/partition diagnosis. It refuses to overwrite its saved output; **do not rerun it in this repository** during a read-only audit. Reproduction from raw frozen inputs requires an isolated copy without that output, where it would create a new diagnostic file. The older `outputs/submission_full_candidate_bound_20261114_v1.json` uses a different pre-v2 grouping result; its **86.55% graph connectivity** agrees, but its **61.55% group ceiling does not describe v2+v7** and must not replace 69.83%.

The official [field policy](configs/field_policy.yaml) has an empty operational feature allowlist. The [Phase 9B evidence audit](PHASE9B_EVIDENCE_AND_DATA_READINESS.md) found no authoritative source-observation IDs or evidence-arrival timestamps. Entity/technique/time findings are local retrospective sensitivities; alert IDs, entity keys, and separate CSV rows do not establish independent evidence. The 67 validation, 68 holdout, and all 499 GUIDE_Test queues have been previously exposed. No result here selects a threshold or supports confirmatory generalization, an operational deployment claim, or the stated 85%/80% targets as achieved.
