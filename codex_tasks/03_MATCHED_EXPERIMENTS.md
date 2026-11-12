# Task 3 Matched Experiments

## Goal

Produce the strongest reproducible comparisons that the approved data and existing artifacts actually permit. If a method is blocked, record it as unavailable instead of substituting a proxy under the same name.

## Safety and validity gates

- No hosted or external model calls.
- No access to new test labels for tuning or method selection.
- No use of evaluator-only fields in candidate generation, features, prompts, retrieval, or calibration.
- No claims that the old exposed cohort is fresh or confirmatory.
- No use of restricted/raw entity values in public artifacts.
- Do not claim the proposed C/P/V LLM result from the offline statistical CPV proxy.

## Steps

1. Map each requested method to actual implementation and existing run artifacts: amended rule/count B0, label-free BM25 B1, single LLM B2, repeated single LLM B3, C+P B4, and C/P/V.
2. Check whether methods share the same alert set, candidate pairs, evidence budget, and evaluator denominator. Do not compare scores from mismatched cohorts as if paired.
3. Reuse immutable, versioned existing runs where they answer a valid question. Any new run must use a new run ID/output directory and write a manifest before evaluation.
4. Run only local offline analysis permitted by the current protocol. Keep evaluation truth separate from prediction generation.
5. For unavailable methods, write down the specific missing implementation, authorization, data gate, or comparable artifact. Do not create fake model output or label a deterministic proxy as an LLM.
6. Record prediction hashes, input/config/code hashes, cohort/query universe, exclusions, seed, and exact commands.
7. Report correlation, ranking, and end-to-end metrics separately. Include candidate misses and denominators; distinguish oracle-group ranking from predicted-group end-to-end ranking.

## Required result

Write `submission/EXPERIMENT_REGISTER.md` and place any genuinely new, versioned aggregate outputs under a new `outputs/submission_<run-id>/` directory. Do not overwrite prior experiment artifacts.

The register must include a method matrix showing run status, data/cohort, evidence, whether it is empirical or synthetic, and whether it is comparable. Include all unavailable methods.

## Acceptance checklist

- [ ] Every result can be traced to a run manifest and frozen prediction artifact.
- [ ] Methods are compared only when their data and evaluation conditions match.
- [ ] Any proxy is named as a proxy.
- [ ] Failed, blocked, or missing runs are disclosed.
- [ ] No new test-set tuning occurred.

