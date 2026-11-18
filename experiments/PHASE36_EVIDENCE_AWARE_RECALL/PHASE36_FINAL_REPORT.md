# Phase 36 final report — NO-GO on fresh development

Phase 36 targeted **270/300 (90%) official Incident Recall@20** with evidence-aware prioritization and the Phase 32 endpoint-fallback +1 reconstruction/verifier frozen. The Phase 33 untouched synthetic holdout result, **260/300 (86.67%)**, remains the strongest confirmed generalization result. Historical cohorts were never combined.

The prerequisite Phase 35 offline diagnostic found 42 misses: **15 recoverable but below the top 20** and **27 fragmented/unrecoverable**. Of the fragmented misses, 14 had insufficient independent visible support, 12 had late related claims, and one lacked a visible evidence family. These categories describe observable patterns; they do not prove a single cause. The existing receiver-visible evidence supported a bounded ranking test but did not justify new unions. Shared context and future observations were not used to merge incidents.

One predeclared Candidate A was fitted on a fresh eight-queue train split. It combined the Phase 34 visible group features with counts of timely original observations, distinct accepted-claim roots, accepted evidence families, verified alert coverage, and mean claim availability delay. It preserved the frozen group partition and first ten ranks, then reordered groups below rank ten. No Candidate B or C was fitted after development evaluation.

| New 15-queue development cohort | Frozen matched baseline | Candidate A | Gate |
|---|---:|---:|---:|
| Incident Recall@20 | **265/300 (88.33%)** | **262/300 (87.33%)** | ≥270/300 and above baseline |
| Group recoverability | 277/300 (92.33%) | 277/300 (92.33%) | Non-inferior; 95% preferred |
| P@10 | 115/150 (76.67%) | 115/150 (76.67%) | Non-inferior |
| Grouped-pair precision | 100% | 100% | ≥99% |
| False grouped pairs | 0 | 0 | No increase |
| Mixed groups | 0 | 0 | No increase |

Candidate A newly recalled four incidents and lost seven relative to the matched baseline, a net decline of three. Three queues declined in recall; no queue regressed on recoverability, P@10, false pairs, or mixed groups. Its 277/300 recoverability leaves **23 unrecoverable** oracle top-20 incidents, and its 262/300 recall leaves **15 recoverable but unranked**. The 90% recall and baseline-improvement gates failed. **Phase 36 is NO-GO; no holdout was generated or opened.** Candidate B (hard-negative discrimination) and C (conservative recoverability-aware priority) were not run because the predeclared single evidence-aware test failed and further tuning on this development cohort would compromise the selection protocol.

The original evaluator, metric definitions, temporal cutoff, eligibility, and C/V decisions were unchanged. A 497-file historical hash inventory, train/development split isolation, generator validation, prediction seals, per-queue group and safety checks, and post-evaluation leakage audit passed. Results are specific to this controlled synthetic generator; distinct root IDs alone cannot establish real-world controller independence, and synthetic safety does not imply production readiness.
