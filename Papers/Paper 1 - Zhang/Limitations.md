# Limitations

## Author-stated limitations

### AUTHOR CLAIM

- The causal-discovery module depends on representative historical telemetry; poisoning and persistent distribution shift may corrupt the learned structure. Empirical robustness under sustained poisoning remains future work. [Zhang, Section 8.3, p. 20]
- Adversarial deliberation adds inference overhead and assumes sufficiently diverse Blue/Red policies; shared blind spots can defeat arbitration. [Zhang, Section 8.3, p. 20]
- The MDP-DAG uses a predefined investigation ontology, which restricts adaptation to unforeseen workflows. [Zhang, Section 8.3, p. 20]
- ETS is validated with benchmark-grounded internal reliability criteria, not human-factors outcomes or live operational outcomes. [Zhang, Section 8.3, p. 20]
- Evidence from one laboratory benchmark cannot establish field generalization or deployment readiness. Production logs, operational red-team exercises, and newer corpora are required. [Zhang, Sections 8-8.3, pp. 19-20]
- Constraint-based causal discovery and deliberation may become computationally expensive in large enterprise state/action spaces. [Zhang, Section 8.2, p. 20]
- Formal verification applies to the induced finite MDP-DAG abstraction and does not exhaustively verify the underlying cyber-physical environment. [Zhang, Section 6.2, p. 17]

## Our critical observations

### OUR OBSERVATION - Dataset

- Dataset size, class distribution, feature count, and split ratios are not specified.
- Collapsing multiple attack types into attack/benign labels removes task detail needed for prioritization and response selection.
- Network-flow records are not equivalent to operational alerts or analyst cases.

### OUR OBSERVATION - Methodology

- The accuracy of the causal graph is foundational, but there is no ground-truth causal graph against which structural recovery is evaluated.
- Blue and Red policies share a model family, making correlated failure modes plausible.
- The roadmap ontology is predefined, so apparent safety may partly reflect manual workflow design rather than learned reasoning.

### OUR OBSERVATION - Evaluation

- Classifier baselines do not provide a like-for-like comparison for causal planning, adversarial deliberation, human escalation, or response decisions.
- No live or replayed SOC workflow evaluates queue prioritization, case grouping, analyst time, escalation quality, or action utility.
- ETS is not validated with analysts, and exact calibration statistics are absent.
- No cross-dataset, cross-organization, or cross-telemetry transfer experiment is reported.
- Formal properties are conditional on abstraction correctness; empirical model-checking results are not clearly presented.

## Missing experiments

### OUR OBSERVATION

- Cross-dataset external validation.
- Operational alert-triage benchmark with alert-level and case-level labels.
- Human analyst study measuring override rate, time-to-decision, cognitive load, and explanation usefulness.
- Comparison against a single-agent version of the same causal decision system and against a non-causal multi-agent triage system.
- Latency, compute cost, and throughput under realistic alert volumes.
- Sustained poisoning and concept-drift stress tests.

