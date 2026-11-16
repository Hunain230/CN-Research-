# Phase 16 target status — v4 locked synthetic cohort

The v4 method was selected on 15 development queues and frozen before evaluation on **30 fresh, namespaced test queues**. The corresponding process-only baseline was evaluated on the same 600-label test. The selected pipeline is `lineage_one_context_v` with progression ranking.

| Metric | Target | Selected locked result | Status |
| --- | ---: | ---: | --- |
| Incident Recall@20 | ≥80% | **407/600 = 67.83%** | Fail; needs 73 more labels |
| Group recoverability | ≥85% | **451/600 = 75.17%** | Fail; needs 59 more labels |
| P@10 | ≥63.88% | **189/300 = 63.00%** | Fail; needs 3 more top-10 matches |
| Grouped-pair precision | ≥90% | **31,245/31,685 = 98.61%** | Pass |
| False grouped pairs | ≤ process baseline 2,402 | **440** | Pass |
| Mixed groups | ≤ process baseline 960 | **257** | Pass |

The process-only baseline recovered **0/600** top-20 groups and had 74.90% pair precision; it is a weak but preregistered same-cohort comparator. The selected rule substantially improves C-stage recovery and passes the stated safety gates, but **does not meet the target set**. Its absolute 440 false pairs and 257 mixed groups remain material. No GUIDE or real-world SOC result is implied.
