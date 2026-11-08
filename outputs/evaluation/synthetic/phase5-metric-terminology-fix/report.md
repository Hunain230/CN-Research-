# Synthetic evaluation report

**SYNTHETIC ONLY — NOT EMPIRICAL.**

````json
{
  "classification": "synthetic_evaluation_only_not_empirical",
  "clustering_diagnostics": {
    "false_merges": 1,
    "false_splits": 0,
    "singleton_components": 1
  },
  "correlation": {
    "abstentions": 1,
    "candidate_count": 4,
    "candidate_generation_coverage": {
      "denominator_full_eligible_pair_count": 6,
      "numerator_candidate_pairs_in_full_universe": 4,
      "value": 0.6666666666666666
    },
    "candidate_generation_coverage_status": "available",
    "candidate_set": {
      "f1": 0.5,
      "fn": 1,
      "fp": 1,
      "precision": 0.5,
      "precision_zero_denominator": false,
      "recall": 0.5,
      "recall_zero_denominator": false,
      "tn": null,
      "tp": 1
    },
    "decision_coverage": 0.5,
    "denominator_policy": "abstention/failure/missing are separate and count as pair FN for positive recall; TN requires an explicit exhaustive universe",
    "failures": 1,
    "full_eligible_pair": {
      "f1": 0.4,
      "fn": 2,
      "fp": 1,
      "precision": 0.5,
      "precision_zero_denominator": false,
      "recall": 0.3333333333333333,
      "recall_zero_denominator": false,
      "tp": 1
    },
    "missing_predictions": 0,
    "pair_false_negatives": {
      "candidate_set": 1,
      "full_eligible_pair": 2
    },
    "pair_false_positives": 1,
    "valid_decision_count": 2
  },
  "end_to_end": {
    "completeness_threshold": 0.8,
    "details": [
      {
        "gold_key": "g1",
        "reason": "recovered",
        "recovered": true
      }
    ],
    "eligible_gold_top20": 1,
    "purity_threshold": 0.8,
    "recall_at_20": 1.0,
    "recovered": 1
  },
  "high_priority_miss_demo": {
    "denominator_high_priority_auto_decided": 2,
    "miss_rate": 0.5,
    "misses": 1,
    "policy": "count only gold high-priority items among auto-decided cases"
  },
  "holm_fixture": {
    "b0": 0.04,
    "b1": 0.06,
    "b2": 0.06,
    "b3": 0.06
  },
  "metric_version": "evaluation-metrics-v1",
  "operational": {
    "failure_fraction": 0.07142857142857142,
    "input_tokens": 245,
    "output_tokens": 50,
    "p50_latency_ms": 50,
    "p95_latency_ms": 100,
    "predictions": 14,
    "review_abstention_fraction": 0.07142857142857142
  },
  "organization_aggregation_demo": {
    "mean": 0.75,
    "median": 0.75,
    "n_organizations": 2,
    "per_organization": {
      "org-syn-1": 0.5,
      "org-syn-2": 1.0
    }
  },
  "paired_bootstrap_fixture": {
    "ci_high": 0.30000000000000004,
    "ci_low": -0.09999999999999998,
    "excluded_unpaired_organizations": 0,
    "mean_difference": 0.10000000000000002,
    "n_organizations": 3,
    "resamples": 10000,
    "seed": 19,
    "unit": "organization"
  },
  "paired_permutation_fixture": {
    "alternative": "two-sided sign-flip paired permutation",
    "effect": 1.0,
    "excluded_unpaired_organizations": 0,
    "n_organizations": 3,
    "p_value": 0.25,
    "permutations": 8,
    "seed": 19,
    "unit": "organization"
  },
  "ranking": {
    "candidate_count": 25,
    "dcg_at_20": 1185864.166351191,
    "idcg_at_20": 1510434.7677107188,
    "judgment_coverage": 1.0,
    "missing_candidates": 15,
    "ndcg_at_20": 0.7851144529389632,
    "precision_at_10": 0.2,
    "precision_at_10_denominator": 10,
    "recall_at_20": 0.6666666666666666,
    "recall_at_20_denominator": 3,
    "relevant_retrieved_at_20": 2,
    "unjudged_policy": "invalid; never map unknown to irrelevant"
  },
  "reviewer_metrics": {
    "agreement": 0.5,
    "citation_support_denominator": 2,
    "citation_support_rate": 0.5,
    "conflict_detection_recall": 0.5,
    "items": 2,
    "kappa": 0.0
  },
  "synthetic_statistical_demos_are_not_significance_evidence": true
}
````
