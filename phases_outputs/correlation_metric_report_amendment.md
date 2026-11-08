# Correlation metric report amendment

**Status:** Adopted after test-label access; aggregate reporting correction only.  
**Affected run:** `phase6-correlation-20261108-v1`.

The original correlation report included a candidate-set recall value for an all-LINK rule. Because every generated candidate pair is predicted LINK, candidate-set decision recall is mechanically 1 when a generated positive exists. Its macro average primarily indicated whether an organization had any generated positive candidate, not recovery of all same-incident alert pairs. It is therefore omitted from the corrected report.

Use candidate-link precision, full-positive-pair recall/F1, and candidate-generation coverage. Full-positive-pair recall treats all same-incident pairs among unambiguous alerts in the held-out organizations as the denominator; positives absent from the candidate set count as missed. The exhaustive same-organization pair universe is reported as the coverage denominator.

No predictions, candidate pairs, labels, or method parameters changed. The correction uses already-computed per-organization evaluator aggregates; it did not re-open source truth. Since the correction follows test access, the result remains exploratory.
