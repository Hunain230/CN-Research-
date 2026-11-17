# Phase 24 target status

| Metric | Target | Best aggregate development candidate | Status |
| --- | ---: | ---: | --- |
| Group recoverability | ≥85% | 165/320 = 51.56% | Miss |
| Incident Recall@20 | ≥80% | 155/320 = 48.44% | Miss |
| P@10 | ≥63.88% | 70/160 = 43.75% | Miss |
| Grouped-pair precision | ≥90% | 99.11% | Pass |
| False grouped pairs | No same-cohort increase | 120 vs 1,001 aggregate; **120 vs 63 in queue q014** | Fail queue gate |
| Mixed groups | No same-cohort increase | 1 vs 30 aggregate; 1 vs 1 in q014 | Pass |

The candidate is `coherent_rare` reconstruction plus blended ranking on the final Phase 24 development cohort. All percentages use this cohort's denominators. The Phase 16 selected result remains the historical scoreboard; no locked Phase 24 evaluation exists.
