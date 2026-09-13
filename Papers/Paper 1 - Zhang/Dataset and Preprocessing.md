# Dataset and Preprocessing

## Dataset

### AUTHOR CLAIM

- **Dataset:** CICIoT2023.
- **Source/type:** public IoT intrusion-detection benchmark containing benign IoT traffic and modern attack categories including DDoS, DoS, reconnaissance, and web-based attacks.
- **Use in this study:** records are mapped to a binary attack/benign decision space for C-MADF and all baselines.

[Zhang, Section 7.1, p. 17]

## Size, labels, and split

### AUTHOR CLAIM

- **Dataset size used:** Not clearly specified in the paper.
- **Labels/classes used:** binary attack versus benign; the original benchmark includes multiple attack categories, but these are not evaluated as a multiclass task here.
- **Split proportions/counts:** Not clearly specified in the paper.
- **Split policy:** fixed train/validation/test splits at scenario level so correlated records from the same scenario family do not cross splits.

[Zhang, Section 7.1, p. 17]

## Preprocessing

### AUTHOR CLAIM

Records are transformed into a structured state schema containing an alert summary, host indicators, and flow statistics. Host- and network-level statistics are aggregated over sliding windows, while investigation context includes the roadmap node, evidence flags, mitigation history, and escalation indicators. Per-feature standardization uses parameters estimated from a held-out calibration dataset. Normalization and scaling statistics are learned on the training split and applied unchanged to validation and test data. [Zhang, Sections 5.3.1 and 7.1, pp. 11-12, 17]

The causal-discovery algorithm additionally specifies time alignment, missing-value handling, and normalization/aggregation. [Zhang, Algorithm 1, p. 10]

## Dataset limitations

### AUTHOR CLAIM

The authors state that a single benchmark is insufficient for claiming dependable or verifiable autonomous response in real operating conditions, and that CICIoT2023 was collected in a laboratory rather than from an operational deployment. [Zhang, Sections 8 and 8.1, pp. 19-20]

### OUR OBSERVATION

- No sample counts, class distribution, exact split ratios, or final feature count are provided, limiting reproduction and assessment of imbalance.
- Binary label mapping discards attack-family distinctions that could matter for alert prioritization and response selection.
- CICIoT2023 network flows are not equivalent to a SOC alert corpus containing alert provenance, analyst dispositions, case links, asset criticality, and investigation outcomes.
- The held-out “calibration dataset” is mentioned, but its relationship to train/validation/test partitions is not clearly specified.

