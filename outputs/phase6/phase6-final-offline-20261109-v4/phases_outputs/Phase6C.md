# Module 6C — High-recall candidate retrieval

**Status:** offline retrieval artifacts exist; the ≥95% target is not met or not validly measurable for the priority candidate path. Results are exploratory.

## Work and evidence

Reused the frozen Phase 6 local BM25 retrieval run (`phase6-priority-20261108-v2`) and its tie-aware evaluator report. It ranked 14,139 candidate incidents across 30 previously accessed test organizations. The candidate universe was formed using evaluator `IncidentId` groups, making the priority result an oracle-group ceiling. It is not an end-to-end candidate generator and its apparent inclusion of the labeled top-20 items cannot be reported as independent candidate-generation recall.

The bounded correlation candidate generator produced 194,296 pairs from a 67,048,813 same-organization pair universe. Its candidate-generation coverage was **0.002898**; full positive-pair recall was **0.008446**. The 95% goal is therefore not achieved for pair retrieval. No test-based parameter changes were made in this module.

## Interpretation and gate

Keep candidate-generation recall separate from Recall@20. A valid priority retrieval recall requires a candidate universe built without evaluator incident membership, plus a defensible query universe and label mapping. Those conditions are not established. All reported values remain exploratory due to prior test-label access. Do not tune against this cohort. The priority, correlation, and ambiguity caveats are recorded in the original [Phase 6 report](Phase6.md).

## Acceptance status

- Existing retrieval outputs and their manifests are preserved: **pass**.
- Candidate-generation coverage denominator stated: **pass**.
- ≥95% candidate recall established on an independent eligible truth universe: **no**.
- Fresh confirmatory cohort available: **no**.
- External model/provider used: **no**.

