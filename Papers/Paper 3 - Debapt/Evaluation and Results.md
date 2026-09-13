# Evaluation and Results

## Metrics and protocol

### AUTHOR CLAIM

Entity and relation extraction are evaluated separately with precision, recall, and F1, reported as micro, macro, and weighted F1. All methods use the same matching and post-processing procedures; supervised baselines share train/validation partitions and all methods share the test set. [Debapt, Section 5.1.3, p. 8; Appendix E, pp. 18-19]

## Overall entity results

### AUTHOR CLAIM

| Dataset | Debapt F1-micro | F1-weighted | F1-macro | Strongest comparison noted |
|---|---:|---:|---:|---|
| CTINexus | **0.8213** | **0.8186** | **0.7986** | CoT micro 0.7659; AttacKG+ weighted 0.7491; CoT macro 0.7479 |
| STIXnet | 0.7684 | **0.7903** | **0.8193** | AttacKG+ micro 0.7839 |
| LLM4CTI | **0.8007** | **0.7998** | **0.7243** | CoT micro 0.7380; CoT weighted 0.7285; CoT macro 0.6601 |

Source: [Debapt, Table 1, p. 9]

## Overall relation results

### AUTHOR CLAIM

| Dataset | Debapt F1-micro | F1-weighted | F1-macro | Strongest comparison noted |
|---|---:|---:|---:|---|
| CTINexus | **0.8197** | 0.8199 | **0.7944** | AttacKG+ weighted 0.8256 |
| STIXnet | **0.8886** | 0.8622 | **0.8914** | CTINexus micro 0.8885 and weighted 0.8838 |
| LLM4CTI | **0.8286** | **0.8440** | **0.7553** | CTINexus micro 0.8173; ICL weighted 0.8052; ICL macro 0.6845 |

Source: [Debapt, Table 2, p. 9]

## Ablation results

### AUTHOR CLAIM

| Variant | Entity F1 micro | Entity F1 macro | Relation F1 micro | Relation F1 macro |
|---|---:|---:|---:|---:|
| Full Debapt | 0.8213 | 0.7986 | 0.8197 | 0.7944 |
| Without ExtEn-Team | 0.7008 (-14.7%) | 0.6888 (-13.7%) | 0.7969 (-2.8%) | 0.7927 (-0.2%) |
| Without CritEn | 0.5897 (-28.2%) | 0.5398 (-32.4%) | 0.7435 (-9.3%) | 0.6450 (-18.8%) |
| Without CritRe | 0.7881 (-4.0%) | 0.7947 (-0.5%) | 0.7245 (-11.6%) | 0.6954 (-12.5%) |
| Without adjudicators | 0.6282 (-23.5%) | 0.5734 (-28.2%) | 0.7592 (-7.4%) | 0.7048 (-11.3%) |

Source: [Debapt, Table 4, p. 11]

## Long-context study

### AUTHOR CLAIM

Reports are grouped by average token lengths of 150.75, 324.50, 532.00, 1,217.33, and 2,032.67 tokens. Debapt's entity and relation F1-micro curves are more stable than ICL and CoT, with its advantage more visible in the approximately 1,000- and 2,000-token groups. Exact bar values are shown graphically but not tabulated, so they are not transcribed as exact values here. [Debapt, Section 5.5, Table 5 and Fig. 4, pp. 11-12]

## Hallucination and termination

### AUTHOR CLAIM

- Hallucination count: 107 (round 1) to 13 (round 5), approximately 87.9% reduction.
- Hallucination ratio: 0.1080 to 0.0124, about 88.5% reduction.

[Debapt, Section 5.6.1, Fig. 5, pp. 11-12]

Across five approximately 3,000-token excerpts, entity extraction converges before the cap in four cases, whereas relation extraction converges in two and reaches the five-round maximum in three. [Debapt, Section 5.6.2, Table 6, p. 12]

## Case studies

### AUTHOR CLAIM

The Lazarus study processes 25 reports from 2007-2024 and extracts 3,940 triples and 4,310 entity mentions. The APT28 study processes 22 reports and extracts 2,061 triples and 2,179 entity mentions. [Debapt, Section 5.7, pp. 12-13]

## Statistical testing and robustness

### OUR OBSERVATION

- No confidence intervals, significance tests, repeated-run variance, or model/API nondeterminism analysis is reported.
- The long-context comparison uses only ICL and CoT, not the strongest CTI-specific baselines.
- The hallucination analysis shows within-workflow reduction but does not establish an independent factuality benchmark across systems.
- Case studies demonstrate plausible output, not measured analyst utility or attribution accuracy.

