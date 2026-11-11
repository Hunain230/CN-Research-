# Offline predicted-group comparison

**Exploratory, not a complete LLM-agent comparison.** All four runnable methods use the same small complete GUIDE_Test organization queues and frozen correlation candidate edges. Ranking consumes predicted groups, never oracle incident groups. The offline CP/CPV rows are deterministic proxies, not the proposed LLM agents.

Organizations: 57; alerts: 11219; candidate pairs: 1216600; expert top-20 labels: 1140.

| Method | Pair F1 micro | Pair F1 macro | P@10 macro | End-to-end Recall@20 macro | nDCG@20 rank 1 high |
|---|---:|---:|---:|---:|---:|
| B0_rule_count | 0.1364 | 0.0684 | 0.0684 | 0.0746 | 0.0364 |
| B1_rule_bm25 | 0.1364 | 0.0684 | 0.1649 | 0.1395 | 0.0840 |
| offline_CP_proxy | 0.0811 | 0.0409 | 0.0421 | 0.0211 | 0.0395 |
| offline_CPV_proxy | 0.0872 | 0.0588 | 0.2105 | 0.1175 | 0.1859 |

B2, B3, B4, and the proposed LLM C/P/V have no empirical scores in this offline run. Do not substitute synthetic stubs or deterministic proxies for them.

Pair F1 is computed from all within-queue alert pairs implied by predicted components. End-to-end recovery requires a predicted top-20 component to contain at least 80% of a gold incident's in-scope alerts and at least 80% of its own alerts to belong to that incident. A missing gold incident has zero recovery. Precision@10 counts recovered expert incidents in the first ten predicted components divided by ten. nDCG uses the implemented exponential gain; reverse direction is in metrics.json.

The original 30 organizations were excluded; the 68 rerun holdout organizations have already been evaluated and are exploratory. This comparison restricts further to complete queues with at most 500 unambiguous alerts, selected without outcome labels. It cannot establish performance on larger queues or a confirmatory holdout.

Source artifacts and their hashes are in prediction_freeze.json. Private predictions remain under ignored data/derived/offline_joint_v1/; only aggregate results are under outputs/offline_joint_v1/.
