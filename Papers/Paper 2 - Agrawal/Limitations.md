# Limitations

## Author-stated limitations

### AUTHOR CLAIM

- Running the AI-driven MAS on resource-constrained distributed edge devices is challenging because of compute and storage requirements. The authors propose compression, lightweight inference, and hybrid edge-cloud deployment as future work. [Agrawal, Conclusion, p. 18]
- The literature/dataset discussion acknowledges that benchmark-based validation in isolated environments can limit generalization and that CICIDS2017 and UNSW-NB15 have limitations for realistic agent training, but the paper does not provide a detailed author-stated limitation analysis of its own combined dataset. [Agrawal, “Cybersecurity datasets and validation challenges,” p. 4]

No dedicated limitations section is provided.

## Our critical observations

### OUR OBSERVATION - Dataset

- The combined-dataset construction is underreported: per-source counts, classes, temporal order, duplicate handling, and feature alignment are absent.
- It is unclear whether SMOTE occurs only after the train/test split; if not, synthetic-neighbor leakage is possible.
- The 50,000-sample balanced subset may not preserve operational prevalence, so accuracy and latency-trigger rates may not transfer to real networks.
- Flow records do not constitute SOC alerts or incident cases.

### OUR OBSERVATION - Methodology

- The response layer is a predefined rule/action library, so the system does not demonstrate multi-agent reasoning about competing evidence or alternative response hypotheses.
- Policy Gradient methods are mentioned but not specified or evaluated; reported attacker training is DQN-based.
- The Autoencoder architecture, anomaly threshold, ensemble weights, and fusion rule are missing.
- Scenario A, B, and C are tied to increasing network size, confounding scale with attack complexity; declines cannot be attributed to one factor cleanly.

### OUR OBSERVATION - Evaluation

- The baselines are broad categories (“static” and “rule-based MAS”) with insufficient implementation detail.
- No ablation isolates the effects of DQN adaptation, ensemble detection, asynchronous messaging, multi-agent coordination, or the response library.
- The p < 0.05 claim lacks the underlying statistics and experimental unit definition.
- Table 10 and its explanatory prose conflict on the medium static-system latency (15.8 versus 12.6 seconds).
- Scalability is tested only to 200 hosts in the main scenario table, while Table 14 summarizes support for 25+ agents without a detailed scaling curve.
- Expert realism/usability evaluation lacks participant count in the acceptance-test section, instrument, scoring distribution, and inter-rater analysis.

## Missing experiments

### OUR OBSERVATION

- Same attack scenario held constant while independently varying host and agent count.
- Cross-dataset training/testing and unseen-environment transfer.
- Prevalence-preserving evaluation without SMOTE at test time.
- Ablations of attacker learning, defender components, communication, and response logic.
- Response correctness/safety evaluation, not only response start latency.
- Comparison against modern learning-based cyber-range agents under matched conditions.
- Operational alert-triage evaluation with analyst dispositions and evidence provenance.

