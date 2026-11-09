# Module 6E — Robustness and generalization checks

**Status:** exploratory ablation and masking analysis is available; it does not establish generalization to new organizations.

## Existing robustness evidence

The saved tie-aware BM25 report contains one primary condition, five leave-one-field-family-out conditions, and 10 masking conditions (20% and 40%, five seeds each). On the 30 previously accessed organizations, primary macro Recall@20 was 0.3392 with a 95% organization-bootstrap interval of [0.2492, 0.4284]; primary-direction nDCG@20 was 0.3924 [0.2857, 0.5016]. Under the opposite QueueRank direction, nDCG@20 was 0.1153 [0.0676, 0.1680].

Across the five 20% masking seeds, mean Recall@20 was 0.2820; across the five 40% masks it was 0.2391. These are descriptive stress-test outputs on an already accessed test cohort. They must not be used to select fields or tune the final configuration. No causal feature-importance conclusion follows from ablations.

## Generalization and overfit limits

Organization bootstrap intervals describe variation across the sampled organizations under this local task proxy; they do not replace an untouched confirmatory cohort. Because the test results were accessed, there is no clean estimate of post-selection generalization and no defensible “does not overfit” claim. No fresh cohort could be frozen from repository evidence. Correlation coverage remains poor, so joint recovery was not evaluated.

## Acceptance status

- Saved robustness conditions and intervals disclosed: **pass**.
- New method choices made from test results: **no**.
- Fresh confirmatory generalization assessment: **unavailable**.
- 95% Recall@20 or no-overfit guarantee: **not established**.

