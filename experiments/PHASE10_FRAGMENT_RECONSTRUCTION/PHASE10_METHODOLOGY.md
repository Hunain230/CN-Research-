# Phase 10 fragment reconstruction methodology

## C/P/V architecture

**C:** The immutable v2 groups are atomic, label-free fragments. For each queue, the runner regenerates the frozen entity-enabled candidate graph and fitted v2 pair probabilities, checks the frozen candidate hash, and aggregates cross-fragment edges. It does not remove alerts or split baseline fragments. Alert keys remain in local prediction files; the compressed provenance export contains hashed keys and no entity values.

**P:** E0 and E2–E4 use the frozen fitted v7 ranker. E1 and E5 use the fixed 75% child40 / 25% v7 within-queue percentile blend. Changed groups are rescored with the same fitted v7 and child40 models. No ranking model was fitted or selected here.

**V:** The existing `src/agents/verification.py` provider interface and orchestrator are retained unchanged. Its offline provider works on synthetic evidence IDs; its 34-assertion self-test passes, but GUIDE lacks the source-observation IDs needed to apply it as an empirical provenance verifier. E4/E5 therefore use a new label-free reconstruction veto for weak reciprocal coverage, fewer than two distinct endpoints on either side, more than 24 hours between fragment time intervals, or joint category and technique contradiction. This proxy is operationally unapproved. It cannot infer mixed-incident risk with certainty or establish independent evidence.

## Fragment representation and scoring

For fragment F, store its size, union of normalized typed entity values, category set, technique set, and minimum/maximum alert creation timestamp. For boundary (F,G), aggregate all frozen candidate edges between them: maximum score m, mean score μ, edge count k, touched alert counts, reciprocal coverage c_F and c_G, shared-entity indicator e, category-or-technique agreement d, joint descriptor conflict q, and nonoverlap time gap Δ hours. Only boundaries with a pair score ≥0.55 are materialized because every primary policy requires at least that maximum; all edges on a viable boundary, including scores below 0.40, contribute to μ and k. The threshold is a fixed compute gate, not selected from Phase 10 evaluator outcomes.

The fixed fragment score is

`S(F,G) = 0.20m + 0.20μ + 0.25min(c_F,c_G) + 0.15e + 0.10d + 0.10exp(-Δ/24) - 0.30q`.

Shared entity means normalized value overlap, **not** verified independent corroboration. No raw entity value is exported. Production-permitted feature set is empty; all score terms are research-only. Evaluator incident IDs, grades, ranks, outcomes, and ambiguous membership are never imported by the predictor.

## Reconstruction policies

E2 requires S≥0.68, maximum pair≥0.60, at least three cross edges, minimum reciprocal coverage≥0.5, shared entity, no joint conflict, and mutual-best selection. A fragment is used at most once. E3 relaxes the score to 0.62, maximum pair to 0.55, and edge count to two, then allows hierarchical unions. Each new union requires a direct candidate boundary from **every** fragment on one side to **every** fragment on the other with S≥0.62; at most three original fragments and 100 alerts may be combined. E4 applies the E3 proposal and union rules plus the V veto. All proposals are sorted deterministically by score and fragment index. Every viable proposal records its score, evidence, accepted/rejected state, and reason; boundaries failing the fixed maximum-pair gate are counted only by the graph scan and are not candidate merges.

The hierarchy is conservative in structure, but its score is not calibrated for incident-level purity. A common upstream event can produce multiple shared keys, so distinct alert endpoints do not establish independent evidence. The 100-alert cap is deliberately retained. Oversized >125-alert incidents remain structurally unrecoverable under the 80% completeness rule; a higher cap requires a separate experiment.

## Evaluation

`reconstruct.py` freezes all 499 label-blind predictions with parent and output hashes. `evaluate.py` then opens evaluator labels and applies the existing 80% completeness/purity, tie-aware ranking, pair, and error-cascade definitions. The 499 queues, 400,039 alerts, 1,942,648 candidate edges, and 9,980 expert top-20 labels are identical across E0–E5. The historical train/validation/holdout divisions are reported as exposed retrospective subgroups. No result is confirmatory.
