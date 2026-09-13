# Methodology

## Overall design

### AUTHOR CLAIM

C-MADF is an end-to-end decision-support architecture with four dependent stages:

1. learn an SCM from historical security telemetry;
2. compile it into an investigation-level MDP-DAG whose edges define admissible transitions;
3. let Blue-Team and Red-Team policies deliberate within that constrained action space; and
4. use policy disagreement and ETS to permit autonomous execution, request more evidence, or escalate to a human.

[Zhang, Sections 1 and 5, pp. 2, 7-14; Algorithms 1-5]

## Causal discovery

### AUTHOR CLAIM

The causal-discovery module uses a constraint-based PC/FCI-family procedure. It preprocesses telemetry through time alignment, missing-value handling, and normalization/aggregation; uses partial-correlation tests for approximately Gaussian continuous variables and kernel- or mutual-information-based tests for mixed/non-Gaussian variables; applies a significance level in the range 0.01-0.05; bounds conditioning sets, for example, to size 2-4; and can incorporate required/forbidden domain edges. FCI is used when latent confounding cannot be excluded. [Zhang, Section 5.1, Algorithm 1 and Table 8, pp. 7-10]

## Decision process

### AUTHOR CLAIM

The variable-level SCM is projected into a separate roadmap DAG over abstract investigation states such as Alert, Evidence Gathering, Containment, and Resolution. A transition is admitted only when it is semantically valid under the investigation ontology and the required causal parents for the destination state are satisfied. The reward combines mitigation success, disruption cost, resource use, and evidential gain. [Zhang, Section 5.2 and Algorithm 2, pp. 8-10]

The action space contains 18 high-level investigation and mitigation actions. Invalid actions are masked before policy evaluation. [Zhang, Section 5.3.1, p. 12]

## Agent roles and training

### AUTHOR CLAIM

- **Blue-Team policy:** optimizes verified threat mitigation while being penalized for disruptive false-positive interventions and inefficient investigation.
- **Red-Team policy:** challenges insufficiently supported mitigation, rewards demands for more evidence under uncertainty, and favors correct escalation.
- **Arbitration:** resolves the policies' proposals; their disagreement is summarized by a Policy Divergence Score and can trigger human escalation.

[Zhang, Section 5.3, Fig. 4, Table 9, p. 11]

Both agents use off-policy deep Q-learning with Double DQN updates, separate prioritized replay buffers, target networks with Polyak averaging, epsilon-greedy exploration, gradient clipping, and self-play. They share the architecture but not learned weights; behavioral differences arise from reward shaping. [Zhang, Section 5.3.1, Algorithm 3, Table 10, pp. 10-12]

## Explainability mechanism

### AUTHOR CLAIM

The human-in-the-loop interface shows competing admissible actions, supporting and contradicting evidence features, policy divergence, and projected operational cost/impact. ETS combines normalized **Clarity**, **Completeness**, and **Confidence** scores and is calibrated against scenario-level correctness, causal-trace consistency, and policy stability. High ETS permits constrained autonomous execution, mid-range ETS requests more evidence, and low ETS triggers human adjudication. [Zhang, Section 5.4, Table 11, Fig. 5, pp. 12-13; Section 7.5, p. 19]

## Baselines and ablations

### AUTHOR CLAIM

External baselines are DUGAT-LSTM, BiLSTM IDS, and Hybrid Weighted-XGBoost, trained with common data splits, telemetry channels, validation-only tuning, and identical test protocol. [Zhang, Section 7.1, p. 17]

Ablations remove the causal SCM, the Red Team, or the Blue Team while retaining the other training conditions. [Zhang, Section 7.4, pp. 18-19]

