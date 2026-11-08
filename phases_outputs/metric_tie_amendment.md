# Phase 6 metric amendment: equal-score BM25 ties

**Status:** Adopted for an exploratory re-analysis after the initial Phase 6 test-label access.  
**Date:** 2026-11-08  
**Affected artifact:** `phase6-priority-20261108-v2` frozen predictions.  
**Reason:** A post-run audit found equal BM25 scores within the top-10 and top-20 cutoffs in all 30 primary-condition organizations. The original evaluator serialized such ties by opaque candidate-key order, which can change cutoff metrics even though the predictor scores are identical.

## Amendment

Do not use serialized row order to choose among candidates with exactly equal scores for cutoff metrics. For P@10, Recall@20, and nDCG@20, calculate the expectation over all uniformly random orderings within each equal-score group. For a tied block of size `n` with `m` relevant candidates and `k` occupied evaluation slots, expected relevant selections are `k*m/n`; expected DCG assigns each tied candidate the mean gain across the block at each occupied discount position. The ideal DCG remains the standard descending-gain ordering.

The predictor, fitted corpus, descriptor fields, feature values, scores, seeds, candidate universe, and test labels are unchanged. Opaque candidate keys remain join/serialization identifiers only. The original deterministic reports are retained as a historical evaluator output; use the tie-aware report for interpretation.

## Disclosure

The first evaluator attempt failed during report assembly after test labels were read. The second produced metrics using key-ordered ties. The tie-aware correction was prompted by examining those results and the score tie structure after test-label access. Therefore, the amended output is **exploratory**, not a pristine confirmatory result. Both failed/previous accesses and the byte-identical v1/v2 prediction comparison are recorded in [`test_evaluation_access_log.md`](test_evaluation_access_log.md).

This amendment addresses only metric handling. It does not resolve rank direction, local candidate-universe correspondence, gold-group oracle evaluation, feature provenance, conflicting membership semantics, correlation/joint evaluation, or lack of empirical LLM calls.
