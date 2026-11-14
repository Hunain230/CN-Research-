# Matched controls for the bounded local-Qwen study

**Status:** exploratory retrospective re-evaluation, 2026-11-14. The 20 GUIDE_Test queues and their labels were previously accessed. No new model calls or changes to frozen Qwen predictions were made. This is a bounded comparison, not the complete B0–B4/C/P/V experiment or a new publication test.

The earlier [local-Qwen prediction freeze](../outputs/submission_qwen_v2_paper_20261113_v1/prediction_freeze.json) selected **20 queues, 240 exact descriptor-match candidate pairs, and 391 distinct alerts** without labels. Every comparison below uses those same selected alerts and keeps all **4,668 unambiguous alerts** in the organizations for incident-completeness scoring and all **400 expert top-20 labels** in Recall@20 denominators.

The [offline-control analysis](../outputs/submission_qwen_matched_offline_controls_20261114_v1.json) replays the frozen Qwen C groups and P scores against no-link singletons and all-exact-pair links, using local count or rarity ranking. The [frozen five-descriptor pair model](../outputs/submission_qwen_matched_statistical_20261114_v1/prediction_freeze.json) was trained on separate historical training organizations and applied at its development-selected 0.995 threshold to the same 240 pairs, with the same five descriptor fields visible to Qwen. It accepted **zero** selected edges, so its groups equal the singleton control. The [separate evaluation](../outputs/submission_qwen_matched_statistical_20261114_v1/metrics.json) confirms the matched scores.

| Same 20 queues and 240-pair budget | Macro end-to-end Recall@20 | Macro P@10 | Macro nDCG@20 |
|---|---:|---:|---:|
| Qwen C groups + Qwen P scores | 0.1443 | 0.1848 | 0.0281 |
| Same Qwen C groups + local rarity ranking | 0.1450 | 0.2310 | 0.0478 |
| No-link singletons + local rarity ranking | **0.1600** | **0.2383** | **0.0508** |
| Frozen five-descriptor statistical links + local rarity ranking | **0.1600** | **0.2383** | **0.0508** |
| Link every selected exact-match pair + local rarity ranking | 0.0000 | 0.0000 | 0.0000 |

The paired Qwen C+P minus singleton/rarity Recall@20 difference is **-0.0157**, with descriptive 95% interval **[-0.0400, 0]** over 20 organizations. The all-link control shows how exact descriptor agreement can destroy group purity. Qwen C linked only 1 of 22 positive selected pairs in the original study, and the repeated single-model B3 group-priority comparator was never run. V produced review flags but did not revise groups or scores; therefore C/P/V and C+P have identical ranking metrics in this frozen run.

**Decision:** These matched controls do not support a Qwen C/P/V superiority claim. They strengthen the bounded baseline table by adding a fair local statistical comparator and a trivial singleton control. The 20-queue candidate sample is too narrow to stand in for the full 499-queue offline study. A new untouched ranked cohort, an authoritative ambiguous-alert assignment rule, point-in-time field approval, and complete matched model budgets remain required for a confirmatory paper. The [baseline-paper contract](BASELINE_PAPER_STUDY_CONTRACT_20261114.md) records those gates.
