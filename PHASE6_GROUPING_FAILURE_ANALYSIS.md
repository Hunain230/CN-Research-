# Phase 6: upstream grouping failure analysis

**Status (15 November 2026):** Read-only, evaluator-side analysis of the frozen entity-enabled candidate graph and v2 groups on 499 GUIDE_Test organization queues. No candidate route, grouping rule, model, threshold, dataset, policy, or prior result was changed. These labels have been accessed in earlier work, so every finding here is **exploratory**. This is a failure diagnosis, not a new performance result or an operational SOC evaluation.

## Reproducible scope and definitions

The cohort contains **400,039 unambiguous alerts**, **1,942,648 candidate pairs**, and **9,980 expert top-20 incident labels** (20 per queue). The source files are the [candidate freeze](outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json), [v2 grouping freeze](outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json), [v2 fit freeze](outputs/submission_entity_time_pair_v2_20261114_v1/fit_freeze.json), and [historical split](data/derived/guide_rerun_v2/split.json). The [read-only diagnostic](submission/diagnose_phase6_grouping_failures.py) hash-checks all 499 candidate, group, and evidence-projection files; regenerates the candidate edges; recomputes v2 scores; and verifies that the recomputed 0.75-threshold groups match the frozen partition. Its [aggregate output](outputs/phase6_grouping_failure_analysis_20261115_v4.json) contains source hashes, counts, anonymized examples, and resource use. No raw incident, alert, organization, or entity identifier is exported.

For an expert incident with in-scope alerts, a predicted group is **complete** if it contains at least 80% of those alerts. It is **pure** if at least 80% of its alerts belong to that incident. Candidate connectivity is an optimistic oracle: only candidate edges joining alerts of the *same expert incident* are traversed. A label is candidate-disconnected when no such candidate component covers 80% of its in-scope alerts. This oracle uses labels **only in the evaluator**, never in candidate generation or model features. Categories below are mutually exclusive in the order shown. The ranking categories use the frozen v7 scores and tie-aware evaluator documented in the [Phase 2 loss plan](PHASE2_RECALL_IMPROVEMENT_PLAN.md); this Phase 6 script rechecks the upstream categories and recoverable total, not v7 scoring.

| Stage / exclusive label category | Labels / 9,980 | Meaning |
|---|---:|---|
| Absent from unambiguous alert scope | 855 (8.57%) | No eligible alert assignment; grouping cannot recover these labels. |
| Candidate-disconnected | 487 (4.88%) | No same-incident candidate component reaches 80% completeness. |
| Candidate-connected but incompletely grouped | 1,451 (14.54%) | The graph has a sufficient oracle component, but v2 groups do not. |
| Complete group, insufficient purity | 218 (2.18%) | A sufficiently complete predicted group is contaminated below 80% purity. |
| Pure, complete group below rank 20 | 1,997 (20.01%) | Fixed-group ranking loss. |
| Recovered in top 20 | 4,972 (49.82%) | Frozen v2 + v7 end-to-end result. |

The cascade is **9,980 → 9,125 in scope → 8,638 candidate-connectable → 6,969 recoverable from actual v2 groups → 4,972 recovered at rank 20**. Thus **86.55%** candidate connectivity and **69.83%** existing-group recoverability are gold-aware upper bounds, not achieved recall. Pair recall and incident Recall@20 have different denominators and must not be conflated. The earlier [v2 metrics](outputs/submission_entity_time_pair_v2_20261114_v1/metrics.json) and [v7 report](submission/INDEPENDENT_COMPONENT_ABLATION_20261115.md) are the performance references; this phase does not replace them.

### Implementation correction: v2 has a 100-alert component limit

The [v2 grouping function](src/submission_entity_time_pair_v2.py) calls the shared [DSU.union](src/submission_full_guide.py), which refuses a union if the combined component would exceed `MAX_COMPONENT = 100`. The diagnostic reproduced the frozen groups with this function. **Six** incomplete labels have a cross-fragment candidate edge scored at least 0.75, yet the edge cannot join their groups because of that limit. The [Phase 3 narrative](PHASE3_FRAGMENT_AWARE_GROUPING_REPORT.md) states that v2 has no cap; that statement conflicts with the implementation and should not be repeated. The future-cohort `cap100` contract matches the code on this point. Its **v4 ranking** still differs from the historical **v7 reference** and requires an explicit prospective choice.

## Candidate-disconnected incidents: 487

The incident-size breakdown is **350 with 2–10 alerts**, **112 with 11–100**, and **25 with more than 100**. All 487 have more than one same-incident candidate component under the 80% rule. Among the 487, **203** have no technique on any incident alert; **40** have no usable entity on any incident alert; **97** span more than 48 hours; **46** span more than seven days. These properties overlap and do not prove causation. Larger incidents were summarized for missingness and time span; the following pair-signal inspection is deliberately limited to the **350 small incidents** so that every cross-component alert pair can be checked exactly.

| Cross-component signal among 350 small disconnected incidents | Incidents | Interpretation |
|---|---:|---|
| No shared usable entity **or** technique across components | 159 | The current entity/technique routes have no direct bridge. |
| At least one shared entity | 87 | A possible link signal, subject to frequency and time limits. |
| Shared entity within the 48-hour route window | 48 | Only 40 also meet a token-frequency prefilter and have an absent pair. |
| Shared entity only beyond 48 hours | 39 | Wider windows could retrieve pairs, with a collision cost. |
| Shared technique | 128 | Technique alone can be broad. |
| Shared technique only beyond the 1-hour route window | 126 | A larger window could create many unrelated pairs. |
| At least one route-prefilter-eligible pair absent from graph | 40 | Consistent with the nearest-five-per-posting candidate limit. |
| Shared detector / shared category | 244 / 290 | Common descriptors are available, but coincidence is a major concern. |

The rows overlap; they are **not** additive root-cause partitions. The candidate generator keeps frozen descriptor proposals, adds organization-scoped shared entity within 48 hours or shared technique within one hour, drops postings over 500, and considers only five subsequent neighbors per token ([source](src/submission_full_entity_time.py)). The 40 eligible-but-absent cases are a concrete retrieval-limit target. The 159 without either shared entity or technique suggest a harder signal or annotation problem. A shared detector/category or time proximity alone is insufficient evidence that two alerts belong to one incident. No proposed missing pair was automatically treated as a true operational link.

## Candidate-connected but incomplete incidents: 1,451

**1,244/1,451** contain 2–10 alerts; **158** contain 11–100 and **49** exceed 100. The number of predicted fragments containing each incident's alerts is **2: 714; 3: 230; 4: 115; 5: 89; at least 6: 303**. In **1,143** incidents, even the largest predicted fragment holds just one gold alert. This is a dispersed-fragment problem, not merely a single missing bridge between two large halves.

All 1,451 have at least one same-incident candidate edge crossing predicted fragments; **827** have at least two such edges. These are evaluator-known positive edges, not observable ground truth at inference. The best frozen-v2 cross-fragment edge score per incident falls in: **below 0.25: 138; 0.25–<0.50: 639; 0.50–<0.65: 430; 0.65–<0.75: 238; at least 0.75 but blocked by the component limit: 6**. Therefore simple threshold lowering would expose many candidate-positive links, but says nothing about simultaneous false merges.

For the strongest cross-fragment edge, **1,402/1,451** incident labels have a shared entity and **1,378** use an entity candidate route; **1,177** share category and **829** share detector. The strongest link may still be too weak or coincidental. Entity equality is especially double-edged: it is common in both true split relationships and false merges below. The prior [adaptive lower-link control](submission/ADAPTIVE_LINKS_NEGATIVE_CONTROL_20261114.md), [learned group-merge control](submission/GROUP_MERGE_MODEL_STUDY_20261114.md), and [Phase 3 fragment study](PHASE3_FRAGMENT_AWARE_GROUPING_REPORT.md) already tested related ideas. The Phase 3 variant raised the oracle total by only **6** labels while increasing mixed groups and false-positive pairs. Another blanket lower threshold or the same merge rule is not justified by these diagnostics.

## Complete but impure groups: 218

**138** affected expert incidents are singletons, **77** have 2–10 alerts, and **3** have 11–100. The selected complete group contains **636 unrelated alert memberships in total** across these label-level cases; the count can repeat an alert if multiple expert labels select the same mixed group. Every one of the 218 selected groups contains at least one direct v2-accepted candidate edge connecting *different* expert incidents; **125** have exactly one such high-score false edge, and there are **916** such direct edges overall within the selected groups. The strongest false edge uses an entity route in **215/218** cases and shares an entity within 48 hours in **218/218**; only **138** share category, **77** share detector, and **90** share technique. These are observed associations, not proof that the entity route alone caused every merge.

This explains why more merging is risky. A shared entity may be a common device, account, address, or reused indicator rather than a unique incident identifier. A future rule should consider token rarity, independent corroboration, conflicting detector/category/time evidence, group size, and whether one bridge edge would contaminate an otherwise pure group. The **218** count is top-20 *label-level impurity*, not the all-incident count of mixed predicted groups or the count of false-positive alert pairs; those must be reported separately in a Phase 7 evaluation.

## Representative anonymized cases

These deterministic examples are drawn from the verified diagnostic. Sizes and rounded scores are retained; identifiers and raw feature values are omitted.

1. **No current entity/technique bridge:** a five-alert expert incident has candidate components of sizes **3 and 2**. Cross-component alerts share detector and category, but no entity or technique; its span exceeds 48 hours. A detector/category route might find it, but needs hard-negative controls.
2. **Candidate posting limit:** a ten-alert incident has oracle candidate components **6, 1, 1, 1, 1**. A cross-component pair shares an eligible entity within 48 hours yet is absent from the graph, consistent with the nearest-five rule. The existing predicted fragments are single alerts.
3. **Connected but split:** an eight-alert incident forms one oracle candidate component but eight singleton predicted fragments. There are **22** positive cross-fragment candidate edges; the strongest v2 score is **0.4957**, via an entity route. The label does not tell us how many negative fragment pairs would also pass a new rule.
4. **False merge:** a one-alert incident is placed in a two-alert group with one unrelated alert through a direct high-score false edge, **0.8328**, on an entity route. A higher recall setting that accepts similar edges would harm purity.

## Organization patterns and feature availability

| Failure | Organizations with ≥1 label | Median labels/organization | 90th percentile | Maximum in one | Share in 50 most affected organizations |
|---|---:|---:|---:|---:|---:|
| Candidate-disconnected (487) | 198/499 | 0 | 3 | 18 | 58.3% |
| Incomplete (1,451) | 408/499 | 2 | 7 | 17 | 31.6% |
| Impure (218) | 107/499 | 0 | 2 | 10 | 69.3% |

Splits are widespread; candidate disconnection and impurity are more concentrated. In the historical **334 train / 67 validation / 68 holdout / 30 unassigned** organization split, incomplete counts are **993 / 188 / 171 / 99**, candidate-disconnected **342 / 66 / 47 / 32**, and impure **155 / 20 / 26 / 17**. These are descriptive counts, not independent validation: GUIDE_Test labels in all groups were previously accessed.

Among all 400,039 alert projections, **12,549** have no usable entity and **240,440** have no technique. Detector, category, entity type, and evidence role are populated in these projections, but populated does not mean discriminative or available at queue-entry time. In incident-level terms, **203/487** disconnected, **440/1,451** incomplete, and **58/218** impure labels have no technique on any of their alerts; the corresponding all-alerts-no-entity counts are **40**, **14**, and **0**. All feature observations use the [local sensitivity policy](configs/entity_time_sensitivity_policy.yaml). The official [operational field allowlist](configs/field_policy.yaml) is empty, and the [point-in-time assessment](submission/POINT_IN_TIME_EVIDENCE_STATUS_20261114.md) does not establish when entity evidence became available. These features are **local research inputs, not approved production inputs**. `IncidentId`, expert rank/grade, and outcome fields were used only by the evaluator.

## Offline ML opportunities and limits

| Task | Feasible local approach | Legitimate training signal | Main limitation |
|---|---|---|---|
| Candidate retrieval | Token/character similarity or TF-IDF over **model-eligible** descriptors, plus bounded entity/time routes | Historical training-organization incident memberships could label retrieved pairs for exploratory fitting if that use is authorized | Retrieval can multiply candidate volume and false merges; text richness and timing approval need checking. |
| Pair relationship scoring | Calibrated gradient-boosted tree using overlap, rarity, time, route, and conflict features | Training-organization same/different incident pairs, subject to the GUIDE_Test label restriction | The existing v2 model already does this; a new score alone may repeat threshold failures. |
| Fragment-to-fragment matching | Supervised group-pair score using independent cross-edge support, rarity, within/between-group consistency, and conflict vetoes | Existing prior study had **16,876 positive and 26,257 negative** sampled training group-pair examples across 334 training organizations ([study](submission/GROUP_MERGE_MODEL_STUDY_20261114.md)) | Prior learned merge failed development gates; pairwise group labels do not directly optimize incident coverage or guard cascading false merges. |
| Merge confidence | Organization-calibrated probability plus explicit abstention/review band | Same training queues, with validation queues used for selection only | Calibration shifts by organization and alert mix; current labels are already exposed and no operational approval exists. |

These approaches would use incident membership **only to construct offline training targets**; they cannot use `IncidentId`, rank, grade, or outcome as a prediction feature. The available historical split is inside previously accessed GUIDE_Test. It shows that supervised fitting is technically possible, **not** that a new GUIDE_Test-tuned model is authorized or confirmatory. If the earlier no-GUIDE_Test-fitting/tuning restriction remains in force for Phase 7, a new independently labeled development set is required for supervised fitting; a prespecified label-free rule can be evaluated meanwhile. Any model experiment must keep organization boundaries, freeze predictions before evaluator access, and report development results separately. No approach in this table was fitted or selected in Phase 6.

## Ceiling impact and Phase 7 recommendation

The **487** disconnected labels represent at most **4.88 percentage points** of the total Recall@20 denominator if candidate retrieval alone could make every one connectable, before grouping and ranking losses. The **1,451** incomplete labels represent at most **14.54 points** under a perfect, purity-preserving grouping fix; the **218** impure labels represent another **2.18 points**. Fixing only the 1,451 splits would move the *oracle fixed-group ceiling* from **69.83% to at most 84.37%**; fixing splits and impurity would reach the current graph's **86.55% oracle bound**. These are deliberately optimistic arithmetic ceilings, not predicted gains.

**Address candidate-connected fragmentation first.** It is nearly three times the disconnected label count, spans 408 organizations, and has existing cross-fragment candidates, especially among 2–10-alert incidents. Phase 7 should implement **one isolated fragment-boundary decision experiment** on the frozen graph. A supervised version would use train-organization fragment pairs, hard negatives from high-scoring *different-incident* neighboring groups, independent cross-edge supports, rarity/consistency/conflict features, and a false-merge veto, **only after its label-use prerequisite is resolved**. Under the earlier no-GUIDE_Test-fitting/tuning rule, use a prespecified label-free boundary rule or obtain independent training labels first. Either version should account for the existing 100-alert component limit and target incident-level split and false-merge errors rather than sampled group-pair accuracy alone. This is a **proposed experiment**, not a claim of improved performance.

Prespecify the rule and its decision gate **before looking at further outcome comparisons**; select parameters only on an independently authorized development cohort. Then freeze a new versioned prediction. Compare with the exact frozen v2+v7 reference on identical **499 queues, 400,039 alerts, 1,942,648 candidate pairs, and 9,980 labels**, recalculating group features and scores with the **same fitted v7 ranker** for changed groups. A useful development gate, if such a cohort becomes available, is **at least 10 additional pure/complete top-20 labels per 840-label, 42-queue cohort**, with **no increase in label-level impurity, mixed predicted groups, or false-positive pairs**, **no loss of pair precision or P@10**, and runtime and peak memory at most **25%** above the matched baseline. These thresholds are prospective decision criteria, **not achieved values**. Report pair precision/recall, false-positive pairs, false splits, group purity, false merges, oracle recoverability, Recall@20, P@10, nDCG@20, paired organization differences, and resources. Do not promote a variant solely for recall. Preserve v2 if the gates fail. The previously exposed GUIDE_Test labels make any comparison on the 499 queues exploratory; a fresh untouched ranked cohort is still necessary to confirm generalization.

Candidate-route expansion is a **separate later experiment**. The 40 small disconnected incidents with prefilter-eligible but missing cross-component pairs give a focused test of neighbor-budget expansion. Other disconnected incidents may require evidence not present in the current projection, and broad category/time retrieval has an unquantified false-merge cost. Change only candidate generation in that later ablation and report added pair volume, incident connectivity, purity, end-to-end recall, and resource cost.

## Final decisions and required external evidence

1. **First failure type:** candidate-connected, incompletely grouped incidents, especially the 1,244 with 2–10 alerts.
2. **Stronger opportunity:** fragment decisions on the existing graph have the larger optimistic label opportunity (**1,451 versus 487**), with a serious purity risk. Candidate retrieval remains a separate, narrower target.
3. **Feasible offline ML:** a calibrated fragment-pair gradient-boosted model is technically feasible with historical training-organization labels and local research features, but those labels are GUIDE_Test and their permitted use for new fitting must be settled first. The earlier negative merge study means benefit is unproven; TF-IDF or other retrieval should be considered only after a bounded feature/volume audit.
4. **Phase 7:** one controlled fragment-boundary experiment with independent support, conflict safeguards, a prespecified gate, frozen predictions, and matched v2+v7 evaluation. Add supervised fitting and hard negatives only with an authorized training-label source; otherwise use a fixed label-free rule and report it as exploratory. No algorithm was implemented in this phase.
5. **Additional evidence:** expert adjudication of ambiguous alert-to-incident assignments (the 855 absent labels), audited evidence-arrival times and operational field approval, expert review of borderline true/false fragment links and high-degree shared entities, and a genuinely new untouched expert-ranked organization cohort. A later shadow-mode SOC study is needed for analyst-workload or live-operations claims.

### Reproduction

From the repository root, with the existing local derived GUIDE data and Python environment present:

```powershell
.\.venv\Scripts\python.exe -m submission.diagnose_phase6_grouping_failures
```

The diagnostic refuses to overwrite its versioned aggregate output. For a new rerun, first change only its `OUTPUT` name to a fresh version, then run the command and compare category totals and source hashes. The completed evaluator-only pass took **95.0 seconds** and peaked at **721 MB process RSS** on this machine; these are audit costs, not SOC decision latency. The current [aggregate JSON](outputs/phase6_grouping_failure_analysis_20261115_v4.json) is the reproducibility record.
