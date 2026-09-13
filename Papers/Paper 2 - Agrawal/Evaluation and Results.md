# Evaluation and Results

## Defender validation

### AUTHOR CLAIM

| Model | Accuracy | Precision | Recall | F1-score |
|---|---:|---:|---:|---:|
| Random Forest | 91.2% | 89.8% | 90.5% | 90.1% |
| Autoencoder | 87.5% | 85.3% | 86.0% | 85.6% |
| Weighted ensemble | **93.0%** | **91.7%** | **92.1%** | **91.9%** |

Source: [Agrawal, Table 6, p. 14]

## Attacker training

### AUTHOR CLAIM

| Episode | Average reward | Attack success rate | Epsilon |
|---:|---:|---:|---:|
| 1000 | 25.3 | 18.7% | 0.8 |
| 2500 | 56.1 | 46.4% | 0.6 |
| 4000 | 92.7 | 79.1% | 0.3 |
| 5000 | 101.4 | 84.5% | 0.1 |

Source: [Agrawal, Table 5, p. 13]

## Detection by scenario and scale

### AUTHOR CLAIM

| Network/scenario | Model | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| Small (50), A | AI-driven MAS | 95.8% | 93.2% | 94.5% |
|  | Rule-based MAS | 81.3% | 78.9% | 80.1% |
|  | Static | 70.2% | 65.5% | 67.8% |
| Medium (120), B | AI-driven MAS | 91.2% | 88.7% | 89.9% |
|  | Rule-based MAS | 77.4% | 73.8% | 75.5% |
|  | Static | 61.5% | 57.1% | 59.2% |
| Large (200), C | AI-driven MAS | 89.6% | 86.3% | 87.9% |
|  | Rule-based MAS | 73.1% | 70.5% | 71.8% |
|  | Static | 58.4% | 54.0% | 56.1% |

Source: [Agrawal, Table 9, p. 15]

## Response latency

### AUTHOR CLAIM

| Network/scenario | AI-driven MAS | Rule-based MAS | Static cyber range |
|---|---:|---:|---:|
| Small (50), A | 4.2 s | 6.5 s | 12.1 s |
| Medium (120), B | 5.6 s | 8.3 s | 15.8 s |
| Large (200), C | 6.1 s | 9.5 s | 18.4 s |

Source of authoritative values: [Agrawal, Table 10, p. 16]

### OUR OBSERVATION

The paragraph below Table 10 says the static system rises from 12.1 to “12.6” to 18.4 seconds, whereas Table 10 reports 15.8 seconds for the medium setting. This vault uses the table value and records the inconsistency rather than silently reconciling it. [Agrawal, “Average response latency,” p. 16]

## Complexity and resource results

### AUTHOR CLAIM

- Attack-complexity scores for AI/rule/static are 5/3/2 (small), 12/7/4 (medium), and 15/9/5 (large). [Agrawal, Table 11, p. 16]
- Average per-agent resource use is 35 +/- 5% CPU and 140 +/- 15 MB for attackers, and 30 +/- 4% CPU and 130 +/- 12 MB for defenders. [Agrawal, Table 12, p. 16]
- Integration testing reports 85 +/- 15 ms agent action execution, 99.8% message delivery, 35% CPU and 140 MB RAM per agent, and 95% correct scripted-step execution. [Agrawal, Table 7, p. 14]
- Simulations reportedly take about 30 minutes for a small network and two hours or longer for larger, more complex scenarios. [Agrawal, “Observations,” p. 17]

## Statistical testing, robustness, and generalization

### AUTHOR CLAIM

The paper states that paired t-tests and ANOVA rejected null hypotheses at p < 0.05, and reports acceptance testing for defender consistency, attacker convergence, scenario fidelity, performance, fault tolerance, and scalability. [Agrawal, Table 13 and “Comparative analysis,” pp. 17-18]

### OUR OBSERVATION

The paper does not report the experimental sample sizes, test statistics, degrees of freedom, effect sizes, confidence intervals, or detailed ANOVA results behind the p < 0.05 statement. “Robustness” and “generalizability” acceptance outcomes are summarized qualitatively without enough protocol detail for independent assessment.

