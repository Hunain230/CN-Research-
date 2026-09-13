# Paper 1 - Critical Summary

## Bibliographic information

- **Title:** *Explainable autonomous cyber defense using adversarial multi-agent reinforcement learning*
- **Authors:** Yiyao Zhang, Diksha Goel, and Hussain Ahmad
- **Journal:** *Expert Systems With Applications*, volume 326, article 132741
- **Year:** 2026
- **DOI:** 10.1016/j.eswa.2026.132741

Source: [Zhang, title page, p. 1]

## Research problem

### AUTHOR CLAIM

Autonomous cyber-defense systems operating on correlation-based signals can misclassify benign behavior or take unsafe mitigation actions when telemetry is ambiguous or adversarially manipulated. Existing causal, explainable, and multi-agent approaches provide partial capabilities but do not jointly provide causal grounding, constrained action trajectories, adversarial internal validation, and calibrated human escalation. [Zhang, Abstract and Section 1, pp. 1-2]

## Research objective

### AUTHOR CLAIM

The authors aim to build a dependable autonomous cyber-defense framework in which learned causal structure constrains the allowed investigation/response path, two adversarially shaped policies deliberate over permitted actions, and an explainability score decides when human supervision is required. [Zhang, Section 1, pp. 1-2]

## Proposed contribution

### AUTHOR CLAIM

C-MADF combines four stages: telemetry-based Structural Causal Model (SCM) learning; compilation of the SCM into a constrained MDP-DAG investigation roadmap; Blue-Team/Red-Team deliberation; and Explainability-Transparency Score (ETS)-based execution or escalation. [Zhang, Section 1, pp. 1-2]

## Main findings

### AUTHOR CLAIM

On CICIoT2023, C-MADF reports precision 0.997, recall 0.961, F1 0.979, and false-positive rate 1.8%. Its three baselines report FPRs from 8.4% to 11.2%. All values are means over three seeds, with standard deviations below 0.02. [Zhang, Section 7.2, Table 12, p. 18]

The ablation results show substantial deterioration when the causal SCM, Red Team, or Blue Team is removed. [Zhang, Section 7.4, Table 13, pp. 18-19]

## Critical assessment

### OUR OBSERVATION

The paper closely matches the *reasoning* and *evidence-grounding* parts of the proposed topic, especially its explicit causal constraints, internal challenge process, evidence-sensitive escalation, and action audit trail. However, the experiment primarily measures binary network-intrusion classification on one IoT benchmark. It does not evaluate analyst-facing prioritization across a queue of heterogeneous security alerts, case grouping, investigation quality, or SOC workload outcomes. The paper therefore supplies mechanisms relevant to triage, not direct evidence that they work for end-to-end SOC alert triage.

See [[Methodology]], [[Dataset and Preprocessing]], [[Models and Architecture]], [[Evaluation and Results]], [[Limitations]], and [[Research Relevance]].

