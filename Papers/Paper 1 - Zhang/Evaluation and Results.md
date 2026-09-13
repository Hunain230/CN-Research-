# Evaluation and Results

## Evaluation design

### AUTHOR CLAIM

The paper evaluates precision, recall, F1-score, and FPR, plus ETS behavior relative to evidentiary sufficiency and policy agreement. All reported metrics are averaged over three seeds; standard deviations are below 0.02. Baselines use shared splits and features, validation-only hyperparameter calibration, and no post-hoc test threshold adjustment. [Zhang, Section 7.1 and Section 7.3, pp. 17-18]

## Main results

### AUTHOR CLAIM

| Framework | Precision | Recall | F1-score | FPR |
|---|---:|---:|---:|---:|
| DUGAT-LSTM | 0.979 | 0.905 | 0.941 | 11.2% |
| BiLSTM IDS | 0.982 | 0.915 | 0.947 | 9.7% |
| Hybrid Weighted-XGBoost | 0.985 | 0.941 | 0.962 | 8.4% |
| C-MADF | **0.997** | **0.961** | **0.979** | **1.8%** |

Source: [Zhang, Table 12, p. 18]

The authors calculate relative FPR reductions of approximately 83.9%, 81.4%, and 78.6% against DUGAT-LSTM, BiLSTM IDS, and Hybrid Weighted-XGBoost, respectively. [Zhang, Section 7.2, p. 18]

## Ablation results

### AUTHOR CLAIM

| Configuration | Precision | Recall | F1-score | FPR |
|---|---:|---:|---:|---:|
| C-MADF full | 0.997 | 0.961 | 0.979 | 1.8% |
| Without causal SCM | 0.903 | 0.959 | 0.930 | 59.4% |
| Without Red Team | 0.963 | 0.963 | 0.963 | 21.2% |
| Without Blue Team | 0.957 | 0.972 | 0.964 | 25.1% |

Source: [Zhang, Table 13, p. 19]

## ETS findings

### AUTHOR CLAIM

Higher ETS values align with stronger causal support and lower policy divergence; lower ETS values align with weaker evidence and more disagreement. The authors present this as preliminary support for ETS-based gating. Exact correlation coefficients, calibration error values, or human-study outcomes are not clearly reported. [Zhang, Section 7.5, p. 19]

## Statistical testing and robustness

### AUTHOR CLAIM

- Three independent seeds are used, with standard deviations reported only as being below 0.02.
- The paper describes formal bounded-violation and temporal-safety properties and discusses model checking over a finite abstraction.
- It analyzes a bounded telemetry-manipulation adversary.

[Zhang, Sections 6-7, pp. 14-18]

### OUR OBSERVATION

- No confidence intervals or hypothesis-test results are reported for model-to-model differences.
- Robustness is framed through formal analysis and the Shadow-Jitter construction, but the principal numeric table is still a single-dataset detection comparison.
- The three external baselines are classifiers, not multi-agent alert-triage or autonomous-response systems, so they do not isolate the value of the full decision workflow against like-for-like alternatives.
- ETS lacks a user study and exact quantitative calibration results, limiting claims about actual analyst trust, workload, or decision quality.

