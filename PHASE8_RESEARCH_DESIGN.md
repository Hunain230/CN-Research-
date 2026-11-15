# Phase 8: small-incident recovery research design

**Status (15 November 2026): proposed, read-only.** This report investigates the **1,244** expert top-20 incidents with **2–10 alerts** that are candidate-connected but incomplete under frozen v2 grouping. It proposes a future experiment; **no Phase 8 model was fitted, rule implemented, prediction generated, configuration changed, or existing artifact rewritten**. All GUIDE_Test labels have been accessed previously, so these observations are exploratory. The aim is **more complete, pure incidents reaching the top 20**, not simply more correct alert pairs.

## Scope, sources, and evaluator boundary

The frozen reference is the [Phase 6 loss audit](PHASE6_GROUPING_FAILURE_ANALYSIS.md), [v2 candidate generator](src/submission_full_entity_time.py), [v2 grouping](src/submission_entity_time_pair_v2.py), [100-alert union limit](src/submission_full_guide.py), and [v7 ranking reference](PHASE7_FRAGMENT_MATCHING_ML_REPORT.md). The [Phase 7 corrected metrics](outputs/submission_fragment_matching_ml_v1_20261115_v2/metrics_corrected.json) report **49.82% incident Recall@20**, **90.4148% grouped alert-pair precision**, **28,606 false-positive grouped pairs**, **4,841 mixed predicted groups**, **218 impure top-20 labels**, and **69.83% existing-group oracle recoverability**. The [Phase 7 prediction freeze](outputs/submission_fragment_matching_ml_v1_20261115_v2/prediction_freeze.json) hashes all 499 private decision files. The read-only audit checked those decision hashes and the frozen candidate/group file hashes before aggregating evidence. It exported no incident, organization, alert, or entity identifier and wrote no diagnostic file.

The evaluator selected a label only when it had **2–10 in-scope alerts**, at least one same-incident candidate component covering **80%** of them, and **no** frozen v2 group covering 80%. Incident membership and expert rank were used **only for this retrospective selection and for assessing hypothetical recovery**. They are never proposed as inference features. The 499 queues, **400,039** alerts, **1,942,648** candidates, and **9,980** top-20 labels remain unchanged. Candidate-pair recall, grouped-pair recall, group recoverability, and end-to-end Recall@20 are distinct measures.

## Observed failure taxonomy

The following counts are incident-label counts unless called edges or proposals. Rows overlap unless a partition is stated.

| Observed property of the 1,244 small incomplete incidents | Count | What it establishes |
|---|---:|---|
| At least one same-incident candidate edge crosses v2 fragments | **1,244** | None is wholly blocked by the current candidate graph under the 80% connectivity criterion. |
| Exactly one cross-fragment candidate edge | **624** | A two-edge automatic-merge rule cannot directly address these cases. |
| At least two cross-fragment candidate edges | **620** | Multiple edges exist, though they may reuse the same alert or entity. |
| At least two distinct fragment boundaries with candidate edges | **531** | Evidence is distributed over more than one group pair. |
| At least one gold-bearing fragment has no cross-fragment candidate edge | **27** | A subset of each incident remains unretrievable by cross-group linking, even though an 80%-complete subset may be connected. |
| At least one Phase 7 fragment proposal, requiring v2 pair score ≥0.40 | **815** | The Phase 7 proposal floor exposed a potentially scoreable boundary. |
| No Phase 7 proposal at that floor | **429** | Existing graph edges were present, but no same-incident fragment boundary entered that scorer. This is a **score-floor/proposal limitation**, not total candidate disconnection. |
| Multiple Phase 7 fragment proposals | **319** | More than one boundary was available to that model. |

The cross-edge count partitions the 1,244 as **624 with one; 267 with 2–3; 238 with 4–10; and 115 with more than 10**. Of the 624 single-edge incidents, **272** had no Phase 7 proposal at score ≥0.40 and **352** had at least one. Of the 620 multi-edge incidents, **157** had no such proposal. The number of predicted fragments containing a small incident's alerts was **2: 711; 3: 225; 4: 112; 5: 84; 6: 42; 7: 29; 8: 24; 9: 8; 10: 9**. A large number of singletons is therefore part of the challenge; requiring two touched alerts on a side excludes many real small incidents by construction.

### Evidence strength and safeguard conflicts

Among the **815** incidents with a Phase 7 proposal, the best-scored fragment boundary had **two or more candidate edges in 99** cases, and both that edge support and **at least two of four descriptor families** (rare shared entity, category, technique, detector) in **75**. A narrower profile—rare shared entity, shared category or technique, and at least two edges—appeared in **69**. In contrast, **716/815** best boundaries depended on only one candidate edge; **156** had one edge and at most one of those four descriptor families. These are *corroboration proxies*: two candidate edges can reuse a single alert or entity, and category/detector overlap can be common across unrelated incidents. They are not independent expert evidence.

The best Phase 7 model probability was **below 0.70 for 745/815** and **0.70–<0.95 for 70/815**; **none** reached 0.95. Across any proposal for a given incident, **40** encountered the fixed `abstain_review` band, **119** had at least one common-entity veto, **568** at least one single-bridge veto, and **145** at least one no-descriptor-corroboration veto. These incident counts overlap. The **2,216** same-incident fragment-pair proposals carried **1,383** single-bridge, **487** common-entity, **240** no-descriptor, **52** review, **51** low-confidence, and **3** insufficient-touched-alert decisions. No proposed pair for these 1,244 was accepted. A review-band score is **not** proof that a merge is safe.

The negative-control comparison shows why the safeguards matter. Among **178,851** Phase 7 proposals between distinct, at least 80%-majority expert incidents, **529** nevertheless had the *same rare-entity + category/technique + multi-edge profile*; **92** also scored at least 0.70. None reached the fixed 0.95 acceptance threshold or was accepted. The **69** incident-level positive profiles and **529** negative *pair-level* profiles have different denominators and cannot be interpreted as precision. They show that this feature combination is **not a perfect separator**. Lowering the model threshold to reach the 40 review-band incidents would expose negative lookalikes; the existing data do not justify doing that.

### Exact merge-only oracle bound for the 1,244

An evaluator-only enumeration considered every subset of the frozen v2 groups containing each incident's alerts (at most **2^10 − 1** subsets per incident). A subset was eligible only if its groups were connected by **existing same-incident candidate edges across groups**, contained at least **80%** of the incident's in-scope alerts, contained no more than **100 alerts total**, and had at least **80% purity** after merging the *whole* predicted groups. The evaluator used expert membership to choose the best subset; no model can do that at inference.

| Optimistic merge-only condition | Incidents / 1,244 |
|---|---:|
| At least one connected subset reaches 80% completeness within cap 100, ignoring purity | **1,244** |
| At least one connected subset reaches **both** 80% completeness and 80% purity within cap 100 | **1,209** |
| No whole-group merge subset meets both criteria | **35** |

Among the 1,209 oracle-feasible incidents, the *minimum* number of whole-group merges is **1: 712; 2: 210; 3: 177; 4: 40; 5: 30; 6: 23; 7: 17**. Thus there is a substantial one-merge opportunity in theory. The **35** remaining cases need splitting, reassignment, improved underlying groups, or a changed evidence scope; merging existing whole groups cannot make them pure and complete under this criterion. **1,209 is an optimistic group-recoverability ceiling for this subset, not an attainable model result or a Recall@20 forecast.** Newly complete groups would still need ranking into the top 20, and false merges elsewhere could reduce net recovery.

## Evidence-supported opportunity versus hypotheses

**Observed:** Phase 7 accepted only **three** merges in all 499 queues, all on historical training queues, joining already recoverable large-incident fragments. It added **1,082** true grouped alert pairs with **no** new false grouped pairs, but changed **zero** top-20 recoverable labels and **zero** Recall@20. The [Phase 3 rule study](PHASE3_FRAGMENT_AWARE_GROUPING_REPORT.md) made **428** merges, gained only **6** recoverable labels, and added **852** false pairs and **39** mixed groups. The [adaptive-link](submission/ADAPTIVE_LINKS_NEGATIVE_CONTROL_20261114.md) and [learned group-merge](submission/GROUP_MERGE_MODEL_STUDY_20261114.md) studies likewise failed their development purity/recoverability gates. Broad threshold relaxation and undirected component joining have already shown poor trade-offs.

**Hypothesis 1:** A boundary model trained against *incident recovery* rather than pair correctness could identify some of the **712** one-merge oracle cases that Phase 7 missed, provided it learns when a merge changes the 80% recovery status and when it contaminates other incidents. This requires training labels available only during fitting; the recovery target cannot be an inference feature.

**Hypothesis 2:** Some of the **429** score-floor misses could be exposed by scoring existing graph boundaries below 0.40, with a strict per-group and per-queue budget. The frozen graph already contains cross-fragment edges; broadening the *candidate graph* is not the first step for this 1,244-label subset. A second independent signal would still be needed for automatic merging of the 624 single-edge cases.

**Hypothesis 3:** Separating *automatic merge* from *analyst review* is necessary. The 40 review-band cases may be useful for expert annotation, but the 92 negative lookalikes at score ≥0.70 show that the review band cannot be treated as automatic acceptance.

## Candidate feature proposal for a future experiment

All proposed features must be computed from the existing **local experimental projection** at prediction time, never from expert incident membership, rank, grade, or outcome. Availability at alert arrival remains unproven, so these are **not production-approved SOC features**. The [official field policy](configs/field_policy.yaml) has an empty approved-model allowlist; the [local sensitivity policy](configs/entity_time_sensitivity_policy.yaml) permits these only for offline research. Obtain evidence-arrival timestamps and authorization before any operational use.

| Feature family | Proposed boundary summaries | Why it may help / risk |
|---|---|---|
| Independent support | Count distinct candidate alert pairs, distinct alerts touched **on each side**, edge-disjoint support paths, and distinct entity **types** supporting those paths | Avoid treating two edges from the same noisy alert as two witnesses. Sparse true incidents may still have one path. |
| Entity quality | Within-organization token frequency, entity type, rarity by group and by alert, agreement across independent paths | Shared devices/accounts/addresses can bridge unrelated incidents; a rare token is not proof. |
| Descriptor consistency | Category, detector, technique, entity-type, and evidence-role overlap and conflict; within-group versus cross-group agreement | A detector/category can be broad; conflicting descriptors need an abstention route. |
| Temporal context | Span and gap from the existing timestamp projection, with explicit missingness and window flags | GUIDE timestamps are noised and evidence-arrival time is unknown. |
| Group state | Observed group sizes, singleton status, internal consistency, cross-to-internal similarity, combined size and proximity to cap 100 | Targets small-fragment recovery without using unavailable gold incident size; large internally coherent groups were Phase 7's only accepted merges. |
| Contamination risk | Number/strength of alternative neighboring groups, mutual-best margin, common-entity degree, one-bridge dependence | High-degree alerts and near-ties are false-merge risks. Gold purity itself is evaluator-only and cannot be used here. |

Use feature ablations on a legitimate development set to check whether added features separate **recovery-changing true boundaries** from **false-merge lookalikes**. Do not select features or thresholds from the exposed 499-queue outcomes.

## Proposed noncascading grouping policy

This is a **design**, not implemented code or a selected parameter setting.

1. Begin with frozen v2 groups and the frozen candidate graph. Consider bounded cross-group boundaries, including a prespecified budget of edges below the historical Phase 7 proposal floor, without changing v2 itself. Limit proposals per original group and per queue; log the number excluded by each budget.
2. Prioritize **small observed fragments** and boundaries whose joining could plausibly change group completeness. Gold incident size and expert rank cannot be known at inference; use only observed group structure, support, and score features. A large-group merge such as Phase 7's three cases should require review unless there is a separately justified benefit.
3. The automatic path requires corroboration from distinct alerts on **both** sides, more than one support path or independently sourced descriptor family, an acceptably rare entity, no strong category/technique conflict, a clear margin over alternative partners, and a combined size ≤100. Proposed numeric cutoffs must be frozen from an authorized development set. Do **not** use the Phase 7 review band as an automatic-merge threshold.
4. Single-edge, common-entity, conflicting, low-margin, and uncertain boundaries **abstain for review**. The 624 one-edge incidents cannot be solved safely by a rule that insists on two graph edges; a future retrieval or expert-evidence route may supply an independent corroboration signal. Review outcomes are measured separately and never silently counted as recovered incidents.
5. Use mutual-best matching and at most one merge per original group per pass. Do not cascade accepted merges or let a newly enlarged group participate again in the same pass. Preserve the 100-alert hard cap and record every proposed, accepted, vetoed, and reviewed boundary with privacy-safe numeric evidence.

The policy should be designed around a **net incident-level objective**, including false-merge cost and top-20 recovery, rather than pair F1 alone. A grouped-pair gain without complete/pure top-20 incidents, as in Phase 7, fails the purpose of this work.

## Evaluation plan and resource constraints

**Before implementation:** Resolve label-use permission, evidence timing, and the independent-development source. Freeze the feature definitions, proposal budget, model, policy, and acceptance gates **before** examining outcomes on a new evaluation cohort. Keep organization boundaries; use incident membership only to construct training targets on authorized historical training organizations. A new independently labeled development set is needed for model and threshold selection if the no-GUIDE_Test-tuning restriction remains binding. The 67 historical validation, 68 historical holdout, and all 499 GUIDE_Test queues are already exposed and cannot become a clean confirmatory test.

**Matched comparison:** Keep the same alerts, candidate graph, fitted v7 ranker, 80% completeness/purity rule, and tie-aware evaluator. Recompute group features and v7 scores for changed groups. Freeze predictions before opening evaluator labels. Report the 334/67/68 and 135 outside-fitting cohorts separately as **exploratory**, plus a **new untouched organization cohort** as the only confirmatory comparison. Report candidate pair volume and recall; grouped-pair TP/FP, precision and recall; complete/pure, incomplete, impure, mixed-group and false-split counts; group oracle recoverability; incident Recall@20, P@10, nDCG@20; singleton, 2–10, and larger incident strata; per-organization paired differences and descriptive intervals. Show how many newly recovered labels were formerly among the 1,244 and how many previously recovered labels were lost. Include reviewer load and abstention count if a review channel exists. Never equate these retrospective batch figures with live analyst workload.

**Batch budgets:** Compare on identical hardware and input verification. The Phase 7 prediction took **138.5 s**, including **48.1 s** of fragment work beyond a **90.4 s** same-pass baseline load, and peaked at **965 MB process RSS**. That exceeded the proposed 25% runtime allowance; its same-process memory comparison was inconclusive. A new method should prespecify a per-queue proposal cap and target **≤25% wall-time overhead** and **≤25% peak-RSS overhead** over a separately measured, matched v2+v7 pass. Measure median and tail per-queue time and memory as well as total cost. If costs exceed those budgets, reject or redesign the method even if a small retrospective recall gain appears. These are batch research limits, not SOC service-level claims.

## Explicit acceptance and rejection criteria

**Prospective development gate:** On an independently authorized **42-queue, 840-top-20-label** development cohort (or a prespecified equivalent rate for a different size), require **at least 10 additional complete-and-pure labels**, a positive paired Recall@20 change, **no increase** in false-positive grouped pairs, mixed groups, or impure labels, **no decrease** in pair precision or P@10, and the batch resource limits above. nDCG@20 must not fall beyond a prespecified tolerance, chosen before outcomes are observed. Count newly recovered **and lost** incidents; a positive pair-TP change alone is not success.

**Independent confirmation:** After development, freeze one method and compare it once on a **new untouched labeled organization cohort**, with the same definitions and a prespecified primary endpoint of paired end-to-end Recall@20 subject to purity and cost constraints. Report uncertainty and incident-size effects. Do not call a positive GUIDE_Test comparison confirmatory, even if it beats the current exposed reference of **4,972/9,980** Recall@20, **28,606** false-positive grouped pairs, **90.4148%** pair precision, **4,841** mixed groups, **218** impure labels, **61.58%** P@10, and **0.4371** nDCG@20.

**Reject or retain v2+v7** if the method recovers no additional complete/pure incidents, moves only pair-level metrics, worsens purity or P@10, exceeds candidate/resource budgets, uses evaluator-only fields at inference, or was selected from exposed GUIDE_Test outcomes. The Phase 3 and Phase 7 results show that a small recall gain accompanied by new false merges does not justify adoption. A model can be scientifically informative while failing these gates.

## Required labels and independent evidence

- **Training labels:** Expert incident membership for organization-disjoint historical training queues, with permission for exploratory fitting and provenance of each alert-to-incident assignment. Resolve ambiguous alert keys with an authoritative source rule; do not infer the **855 absent-scope** labels from evaluator outcomes.
- **Development annotations:** Expert adjudication of borderline fragment pairs, especially single-edge cases, common/high-degree entities, candidate edges below the old 0.40 proposal floor, and review-band cases. Include explicit *different-incident* hard negatives and a reason for ambiguous judgments.
- **Point-in-time contract:** For each entity, descriptor, and time field, obtain when it was available to the SOC, its provenance, privacy approval, and whether it is permitted in a live model. The current operational allowlist is empty.
- **Independent confirmation cohort:** New organization queues with untouched expert incident memberships and top-20 rankings, sealed until the method and gates are frozen. A later shadow-mode study is required for analyst workload, live latency, or operational SOC claims.

### Reproduction of the read-only counts

The audit used the [frozen v2 groups](outputs/submission_entity_time_pair_v2_20261114_v1/prediction_freeze.json), [frozen candidate edges](outputs/submission_full_entity_time_20261114_v1/prediction_freeze.json), [Phase 7 decision hashes](outputs/submission_fragment_matching_ml_v1_20261115_v2/prediction_freeze.json), and the existing evaluator's truth/rank loaders. For each organization, it verified those file hashes; formed same-incident candidate components in evaluator memory; selected top-20 labels with 2–10 in-scope alerts, ≥80% oracle candidate connectivity, and no ≥80%-complete v2 group; counted cross-group same-incident edges; then joined the private Phase 7 decision records **by original frozen group indices**. The merge-only bound enumerated every subset of the selected label's gold-bearing v2 groups and checked candidate-edge connectivity, ≥80% completeness, ≥80% purity, and ≤100 total alerts. No data or output artifact was changed. These calculations are **gold-aware diagnostic bounds**, never model inputs or achieved predictions.
