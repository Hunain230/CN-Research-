# Phase 10 research design

Status: retrospective exploratory protocol, 16 November 2026. The frozen C/P/V architecture remains intact. The official operational feature allowlist is empty; every GUIDE descriptor, entity, alert timestamp, candidate probability, and group statistic used here is **local retrospective research only**. `IncidentId`, expert rank, grade, and outcome are evaluator only. Alert IDs are lineage only.

## Audit and fixed references

The 499 queues contain 400,039 unambiguous alerts, 1,942,648 candidate edges, and 9,980 expert top-20 labels. Frozen candidate, v2 group, and v7 rank prediction hashes are `eaa81a87b0e639d93671ccc8a128be5ac6270a4d8c4be19e985acb836ffcd4f8`, `819fde15fbf744ee1fd2c0f347c375a40a917bed1dc9b4e`, and `40255fe6061fb9febbfebe0acfc184b4976c2480a29e09264b8ba9d098de9743`. The selected 75% hard40 / 25% v7 ranking blend is frozen separately. The actual implementations are `src/submission_full_entity_time.py`, `src/submission_entity_time_pair_v2.py`, `src/submission_group_merge_v10_v2.py`, `src/submission_ranking_ltr_v1.py`, and `src/sprint_rank_fusion_v1.py`. Prior Phase 7, 9C, 9E, 9F, and 9G findings rule out a simple global threshold change.

## Experimental design

Keep the frozen candidate graph and v2 groups as coherent atomic fragments; no evaluator label influences these. Aggregate **all** cross-fragment frozen candidate edges, including scores below 0.40. E2 uses a single noncascading mutual-best fragment match. E3 uses bounded hierarchical merging with fresh union-level evidence checks. E4 adds a label-free verification veto and uncertainty flag. Cap remains 100 alerts in all primary policies. A larger cap is a separate future sensitivity experiment, not silently mixed into these runs. E0 is v2+v7, E1 v2+blend, and E5 is the selected reconstructed grouping with the same fixed blend and rescored changed groups.

No threshold will be selected on GUIDE_Test outcomes. The fixed choices in the JSON are research hypotheses informed by exposed history, not confirmatory parameter estimates. Run synthetic tests, then a small queue sample, then freeze full predictions before opening evaluator labels. Compare on identical queues, alert scope, and 9,980-label denominator. Report the 334 historical train, 67 validation, 68 holdout, and 30 unassigned queues separately; none is independent confirmation because labels were previously accessed.

## Decision and safety gates

Primary research targets: Recall@20 ≥80%, group recoverability ≥85%, P@10 ≥63.88%, grouped-pair precision ≥90%, mixed groups ≤4,841, and no material increase in false grouped pairs. Secondary gates compare against 50.77% recall and 69.83% recoverability. A changed group's ranking uses the existing fitted models and the selected blend weights. Every proposal records features, score, decision, and rejection reason; raw entity values stay out of exported provenance.
