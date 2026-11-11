# Phase A progress — coverage and retrieval audit

**Status:** partial audit complete; Phase A exit gate failed. No Groq or Gemini call was needed for this phase.

The same previously accessed 57-organization small-queue cohort used by `offline_joint_v2` has 11,219 unambiguous in-scope alerts and 1,140 expert top-20 labels. The restricted evaluator-ledger audit found 1,066 labels represented by at least one unambiguous alert and **74 labels represented only by ambiguous alert assignments**. Under the existing whole-key exclusion policy, end-to-end Recall@20 cannot exceed 1,066/1,140 = **93.51%** on this cohort. This is an evaluation ceiling, not model performance. It does not justify relabeling or silently removing the 74 labels from the denominator.

The frozen, label-blind candidate generator produced 1,216,600 alert pairs out of 1,510,902 possible within-organization pairs: **80.52% pair coverage**. It retrieved 38,807 of 47,607 positive pairs: **81.52% micro candidate recall**. Mean organization-level recall was **98.12%** (10,000-resample 95% bootstrap interval 96.00–99.70%). The macro/micro gap shows that larger positive-pair populations still suffer substantial candidate misses. The Phase A target of at least 99% micro candidate recall at affordable volume **was not met**; generating most possible pairs is also too expensive as an LLM input strategy.

An evaluator-only miss audit checked all 8,800 omitted positive pairs. Every one shares the generic `EntityType` and `EvidenceRole` descriptors, while only 825 share `Category` and 168 share `DetectorId`; none shares `MitreTechniques` under the parsed feature representation. This is a specificity problem: simply adding a route for either generic shared field would likely produce many more candidate pairs. A point-in-time-safe, privacy-reviewed entity-link transform or other discriminative evidence may be needed; it is not approved by this audit.

Both audits checked the raw-source hashes and prior prediction freeze. They exported only aggregates, no organization/alert/incident identifiers. Reproduce from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m src.phase_a_coverage_audit
.\.venv\Scripts\python.exe -m src.phase_a_candidate_audit
.\.venv\Scripts\python.exe -m src.phase_a_miss_analysis
```

The commands refuse to overwrite existing outputs. Results and source hashes are in `outputs/phase_a/coverage_20261111.json`, `outputs/phase_a/candidate_20261111.json`, and `outputs/phase_a/missed_positive_pairs_20261111.json`. This is an exploratory audit of an already evaluated cohort, not a new confirmatory run.

**Next Phase A work:** establish source semantics for conflicting alerts and the exact local queue mapping, verify field timing/data-use, improve retrieval without near-exhaustive pair volume, and obtain an independently untouched organization cohort or external release. Phase B live model calls should wait until the data contract and candidate workload are suitable; API keys alone do not clear these gates.

**Production readiness:** no.
