# Phase 3 implementation report: GUIDE_Test hybrid evaluation

**Updated:** 2026-11-14. **Status:** exploratory implementation and evaluation. The raw GUIDE_Test export is retrospective SOC research data, not a live SOC feed. This report separates the full offline run, bounded local Qwen model runs, and the fictional dashboard simulation.

## Abstract

This project implements alert correlation, group prioritization, and evidence review for the Microsoft GUIDE research export. A full offline pass covers 4,147,992 evidence rows and the 499 ranked organizations, while a bounded local `qwen2.5:3b` pass exercises C/P/V roles and a single-model pair baseline on 240 frozen candidate pairs from 20 organizations. Predictions were frozen before evaluator truth was opened. The full offline result exposes a severe candidate-retrieval bottleneck: 37,018 of 159,186,107 positive alert pairs reached the candidate set. In the paired model sample, C found 1/22 positive pairs and B2 found 2/22. The work demonstrates a reproducible pipeline and local model integration; it does not establish the proposed performance target or a confirmatory advantage over baselines.

## Problem, method, and data

The research question is whether a correlate–prioritize–verify (C/P/V) workflow can group related alerts and recover expert-prioritized incidents. The supplied `GUIDE_Test.csv` is an evidence-row export; multiple rows can describe one alert. Its queue file has 499 organizations and 20 expert labels per organization. The project uses `(OrgId, AlertId)` and `(OrgId, IncidentId)` composite identities. All 70,702 conflicting alert keys are excluded from model and offline truth scoring while all expert labels remain in end-to-end denominators. The five descriptor fields are local-only assumptions; the official field allowlist remains empty. Time, raw entity identifiers, and external model transmission remain outside the approved field boundary. The [data and claim audit](DATA_AND_CLAIM_AUDIT.md) documents these constraints.

The related [GUIDE study](https://arxiv.org/abs/2407.09017) supplies the investigation and triage data context; the [Adaptive Incident Prioritization study](https://arxiv.org/abs/2607.16963) concerns queue-relative expert priority. This implementation examines a further gap: recovery of ranked incidents from **predicted alert groups** when alert membership itself is ambiguous. Its local exported queue and field semantics do not exactly reproduce the published active-queue task, so published headline results are background rather than direct benchmark rows.

The proposed design combines candidate generation, a C correlation decision, P group priority, and V citation review. The implementation here has two explicitly different scopes. The [full offline pipeline](../src/submission_full_guide.py) scans all GUIDE_Test evidence, applies an exact category plus ATT&CK-technique candidate rule, groups linked alerts, and compares a count ranker with a label-free local BM25-like ranker. The [local Qwen v2 pipeline](../src/submission_local_qwen_v2.py) selects 12 exact category-plus-technique pairs per organization in 20 deterministic small queues without labels or model scores. It runs C and a B2 single-model pair baseline on the same pairs, then P and V on C groups through localhost Ollama. This is a batched model prototype, not the complete proposed pair-by-pair protocol. B2 has pair scores only; B3, B4, and a complete component-ranking comparison are not matched in this run. The earlier [two-queue Qwen v1](../src/submission_local_qwen.py) remains a separate historical diagnostic.

Both pipelines split prediction and evaluation. The prediction stages use local descriptors and frozen candidate data. Evaluators alone read incident membership and queue ranks after prediction files and hashes are written. This separation prevents an accidental label join during inference; it does not create an untouched test set because the data and labels were previously accessed. The full offline and Qwen cohorts and candidate policies differ, so their scores must not be compared as a paired model contest.

## Phase 1–4 implementation status

| Phase | Implementation evidence | Evaluation status |
|---|---|---|
| 1 — Data validation | [Dataset audit](DATA_AND_CLAIM_AUDIT.md) and [Phase 1 record](../phases_outputs/Phase1.md) cover schema, evidence-row grain, composite keys, queue joins, and conflicts. | Local real-data validation. |
| 2 — Preprocessing | [Phase 2 record](../phases_outputs/Phase2.md) covers stable source ordinals, restricted evidence ledger, evaluator-only labels, and deny-by-default export. | Ran on real local files; field and split gates remain provisional. |
| 3 — Baselines | [Phase 3 record](../phases_outputs/Phase3.md) documents rule/BM25 and single-model orchestration. The full offline and bounded local-Qwen artifacts extend empirical coverage. | Earlier B2/B3 checks were synthetic; the new B2 result is a local-model pair diagnostic on 240 selected pairs. |
| 4 — C/P/V agents | [Phase 4 record](../phases_outputs/Phase4.md) documents schema and citation plumbing; [MVP runner](MVP_SYNTHETIC_RUN.md) exercises the offline workflow. The local Qwen prototype exercises batched C/P/V on GUIDE descriptors. | Earlier agent checks were synthetic; the new 20-queue model evaluation is exploratory. |

The Phase 5 evaluator supplies the isolated metric functions and the Phase 6 dashboard supplies an aggregate viewer and a distinct fictional simulation. The planned full empirical LLM C/P/V study is still incomplete.

## Experimental setup

Both current runs use the supplied retrospective GUIDE_Test export and versioned output paths. The full offline pass evaluates all 499 ranked organizations after ambiguous-key exclusion and compares two rankers on exactly the same rule-generated groups. The bounded Qwen v2 pass uses 20 deterministic organizations from a previously accessed small-queue holdout, with 12 hash-ordered exact category-plus-technique candidate pairs in each. Selection was label-blind, but this is a convenience sample; it is not a random draw from all within-queue pairs. The local model is pinned by its Ollama digest and called with fixed seeds; C and B2 decide the same 240 pairs, then P and V operate on C groups. The [reproduction guide](REPRODUCE.md) lists commands, source hashes, and output paths. There is no prospective SOC stream, fresh test split, matched full-model budget, or analyst adjudication.

## Full GUIDE_Test offline results

The [paper-run metrics](../outputs/submission_full_guide_paper_20261113_v1/metrics.json), [prediction freeze](../outputs/submission_full_guide_paper_20261113_v1/prediction_freeze.json), and [run manifest](../outputs/submission_full_guide_paper_20261113_v1/run_manifest.json) record 499 ranked organizations, 400,039 unambiguous alerts, 314,576 generated candidates, 3,517,608,736 possible within-queue pairs, 159,186,107 positive pairs, and 9,980 expert top-20 labels. This independent rerun's aggregate metrics SHA-256 exactly matches the earlier full run (`e6ac81358f6d8eef06c23b574055aa194a1b62fa09085fbca5ccbee0e97d3a94`). The 656,408 evidence rows attached to ambiguous keys in those organizations were omitted from prediction; the complete raw input contains 4,147,992 evidence rows. Only 9,125 of the 9,980 expert labels have unambiguous in-scope alert evidence under this rule, a structural coverage ceiling rather than measured recall. All 9,980 remain in the end-to-end denominator.

Candidate recall was **37,018 / 159,186,107 = 0.0233%**, at **314,576 / 3,517,608,736 = 0.00894%** pair coverage. The rule trades an extremely small pair workload for catastrophic recall. It fails the project's 99% candidate-recall target. Both offline rankers share the same grouping, so their micro pair F1 is **0.00910**. Their ranking differs:

| Method | P@10, organization macro | End-to-end Recall@20, organization macro | nDCG@20, rank 1 high |
|---|---:|---:|---:|
| Rule / count | 0.0492 | 0.0543 | 0.0364 |
| Rule / local BM25-like | 0.1714 | 0.1364 | 0.1542 |

The manifest supplies 10,000-resample organization-bootstrap intervals. For BM25-like Recall@20 the descriptive interval is [0.1244, 0.1488]. Scores use a local query universe and rank-1-highest assumption; the metrics also retain reverse-direction sensitivity. Equal-score blocks use expected tie-aware ranking. None of these intervals repairs the selection or protocol limitations.

![Two full-dataset offline baseline ranking metrics](figures/full_guide_offline.png)

**Figure 4.** Aggregate-only view of two rankers sharing the same weak candidate grouping. [Figure source and output hashes](figures/submission_figure_manifest.json).

## Bounded local Qwen evaluation

The new [Qwen v2 metrics](../outputs/submission_qwen_v2_paper_20261113_v1/metrics.json), [prediction freeze](../outputs/submission_qwen_v2_paper_20261113_v1/prediction_freeze.json), and [run manifest](../outputs/submission_qwen_v2_paper_20261113_v1/run_manifest.json) record a completed 20-organization local run. The installed `qwen2.5:3b` digest was `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`. There were **188 localhost calls**, **zero failed calls**, **129,143 prompt tokens**, **49,401 output tokens**, and zero hosted calls. Summed call elapsed time was 5,290.6 seconds; this is local batch processing time, not a production latency benchmark. Only five local-assumption descriptors were model-visible. Prediction was hashed and frozen before the evaluator read incident membership and expert ranks.

Each of the 20 previously accessed small queues contributed 12 label-blind, exact category-plus-technique candidate pairs. The **240 selected pairs contained 22 positives**. C and B2 received the same pair evidence and call budget. Their micro selected-pair results were:

| Local Qwen role | TP | FP | FN | Abstentions | Pair precision | Pair recall | Pair F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| C correlation | 1 | 16 | 21 | 18 | 0.0588 | 0.0455 | 0.0513 |
| B2 single-model baseline | 2 | 20 | 20 | 34 | 0.0909 | 0.0909 | 0.0909 |

These scores apply **only to selected exact-match candidates**, not all positive alert pairs in the queues. The sample has 22 positives, so a difference of one true link materially changes recall. C did not outperform B2 on this paired diagnostic. B2 produced pair decisions only; no B2 component ranking was run.

![Paired C and B2 selected-candidate precision, recall, and F1](figures/qwen_v2_pair_diagnostic.png)

**Figure 5.** Micro pair scores for C and B2 on the same 240 selected exact-match candidates, including 22 positives. This is not full-queue pair recall. [Source and figure hashes](figures/qwen_v2_figure_manifest.json).

C's LINK decisions formed **374 predicted groups** from **391 selected alerts**. P assigned relative, uncalibrated group scores and V checked supplied evidence references; 60.0% of groups were flagged for review. V did not revise the scores or groups, so the ranking metrics measure C+P output with a separate V review flag. The full-organization evaluator counted all **4,668 unambiguous alerts** when testing 80% incident completeness, and kept all **400 expert top-20 labels** in the ranking denominator. It found 58 distinct labels in qualifying predicted groups; tie-aware organization-macro **end-to-end Recall@20 was 0.1443** (descriptive 95% organization-bootstrap interval [0.0800, 0.2118]). P@10 was 0.1848 and rank-1-highest nDCG@20 was 0.0281. Only 358/400 expert labels have any unambiguous alert evidence in these queues. Because most alerts were not selected for model input and many groups are small, these ranking values do not measure full-queue Qwen C/P/V performance or an advantage over B2.

The prior [two-queue Qwen v1 run](../outputs/submission_qwen_20261112_v1/metrics.json) selected 30 pairs containing **zero positives**. Its pair recall is unavailable, and its original selected-alert completeness calculation was superseded by an additive [full-membership correction](../outputs/submission_qwen_20261112_v1/metrics_full_membership_correction.json). It remains historical and is not pooled with the new 20-queue table.

## Baselines, ablations, and earlier evidence

The prior [matched offline proxy analysis](RESULTS_AND_DISCUSSION.md) reports four methods on the same 57 small queues and 1,140 labels. Its offline CP and CPV scores are statistical proxies, not LLM measurements. Earlier oracle-group feature removal and masking measure a separate conditional priority task; the `MitreTechniques` omission reduced oracle-group Recall@20 from 0.3392 to 0.2897 on 30 previously exposed queues. Those figures are useful context but cannot be pooled with this full-run result or the bounded Qwen run. The [experiment register](EXPERIMENT_REGISTER.md) traces method names, cohorts, and unavailable comparisons.

## Error analysis and discussion

The dominant full-run error occurs before model inference: exact category plus technique matching omits more than 159 million positive pairs. Pair grouping consequently reaches only a small fraction of incident membership, and ranking cannot recover omitted groups. BM25-like ranking helps order the limited predicted components but does not cure candidate omission. A broader candidate generator with measured recall and a controlled workload is required before the original target can be evaluated. The Qwen v2 sample demonstrates local model integration and a paired selected-candidate diagnostic; its 22 positives, sampled alerts, and uncalibrated P scores cannot establish an operational improvement. On those selected pairs, C had fewer false links than B2 (16 versus 20) but also fewer true links (1 versus 2) and lower F1.

A later [post-hoc route diagnostic](../outputs/recall_route_diagnostic_20261113_v1/aggregate.json) on the previously exposed 57 small queues examined exact descriptor overlap without neighbor caps. The union of shared `Category`, `MitreTechniques`, or `DetectorId` reached **47.72% of positive pairs** while covering **59.45% of all pairs**. This truth-informed diagnostic is not a frozen candidate benchmark or a model result. It shows that raising the neighbor cap on these exact fields alone is not a supported path to the 99% candidate target.

The original proposed B0 detector-severity baseline is unavailable because severity is absent. The full offline rule/count baseline is an amendment. B2 v2 and the historical B2/B3 v1 runs are pair-only diagnostics; B4 and complete matched C/P/V baselines with equal candidate, evidence, and token budgets remain unavailable. Ambiguous membership, exact queue semantics, rank direction, field timing/privacy approval, fresh evaluation data, analyst judgments, and prospective latency/cost remain unresolved. Only **9,125/9,980 = 91.43%** of full-run top-20 labels have unambiguous in-scope alert evidence; even perfect predictions cannot reach 95% end-to-end recovery under the current exclusion policy. The [known limitations](KNOWN_LIMITATIONS.md) list submission-relevant gaps.

## Dashboard and deliverables

The [aggregate research dashboard](../dashboard/index.html) reads saved metrics; the [fictional simulation](../dashboard/simulation.html) replays synthetic MVP events with Start, Pause, Reset, speed, and scenario controls. The simulation is not a GUIDE data or Qwen result viewer. Its [build manifest](../dashboard/simulation_manifest.json) and [documentation](../dashboard/SIMULATION_README.md) identify the trace and UI boundary. Reproduction commands are in [REPRODUCE.md](REPRODUCE.md); the [delivery checklist](DELIVERY_CHECKLIST.md) maps these artifacts to Phase 3 assignment requirements.

## Conclusion

The hybrid work is runnable and auditable, but the full-data offline rule misses the candidate-recall target by a wide margin, and the local Qwen study is deliberately bounded. The supported conclusion is implementation feasibility with substantial empirical and protocol gaps. No 95% success, confirmatory model gain, operational SOC readiness, or military certification claim is supported.

## References

- [Microsoft GUIDE dataset paper](https://arxiv.org/abs/2407.09017).
- [Adaptive Incident Prioritization paper](https://arxiv.org/abs/2607.16963).
- [Local research protocol and phase index](../PROJECT_CONTEXT.md).
