# Adaptive small-component links: development control

This exploratory offline study tested whether lower-probability pair links could join only small incident components, while preserving every high-confidence v2 link. The [development script](development_adaptive_links_v9.py) used the frozen v2 pair model and v7 ranking method on the same 42 historical development queues of at most 500 alerts. It tested six fixed lower-threshold and component-cap settings against the base 0.75 threshold. The source, model, and split hashes and full [metric table](../outputs/submission_development_adaptive_links_v9_20261114_v1.json) are frozen.

| Setting on 42 development queues | Recall@20 | P@10 | Pair precision | False positive pairs | Recoverable top-20 labels / 840 |
|---|---:|---:|---:|---:|---:|
| Base v2 groups + v7 ranking | 47.74% | 58.33% | 87.53% | 340 | 610 |
| Lower floor 0.60, cap lower-confidence merges at 5 alerts | 47.98% | 57.14% | 84.55% | 520 | 597 |
| Lower floor 0.65, cap lower-confidence merges at 5 alerts | 47.62% | 58.33% | 86.91% | 414 | 604 |
| Lower floor 0.50, cap lower-confidence merges at 5 alerts | 45.60% | 55.00% | 75.75% | 1,052 | 572 |

The 0.60 setting raised development Recall@20 by only 0.24 percentage points while reducing P@10 and the number of labels that even ideal ordering could recover. Looser settings improved selected pair F1 but joined unrelated alerts and reduced end-to-end utility. The prespecified rule required pair precision of at least 80%, P@10 at least the base value, and a strict Recall@20 gain. **Base v2 grouping was selected.** No new all-499 prediction run was needed, because that selection reproduces the already frozen v2 groups and v7 scores.

The best all-499 offline result therefore remains the exploratory v7 **49.82% Recall@20** and **61.58% P@10** on v2 groups. Its fixed-group oracle-order ceiling remains **69.83%**. These values can be listed in a paper as retrospective exploratory findings with matching denominators and limitations, but they cannot be presented as an untouched test or operational SOC result. GUIDE_Test labels were previously accessed, and point-in-time evidence approval and a fresh ranked cohort are still unresolved. The final report and PDF were not changed.
