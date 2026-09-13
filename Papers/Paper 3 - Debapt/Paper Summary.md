# Paper 3 - Critical Summary

## Bibliographic information

- **Title:** *Debapt: Ontology-driven multi-agent debate for APT adversary profile construction from cyber threat intelligence*
- **Authors:** Xinyun Zhao, Lanlan Qi, Yongheng Zhang, Yingxiao Guan, Guozheng Yang, Yuliang Lu, and Xiang Wang
- **Journal:** *Computers & Security*, volume 170, article 104988
- **Year:** 2026
- **DOI:** 10.1016/j.cose.2026.104988

Source: [Debapt, title page, p. 1]

## Research problem

### AUTHOR CLAIM

Long, fragmented CTI reports contain profile-relevant facts about APT actors, but rule-based/deep-learning extraction and single-LLM prompting can omit long-range information, drift outside profile semantics, and hallucinate precise cyber facts. [Debapt, Abstract and Section 1, pp. 1-2]

## Research objective

### AUTHOR CLAIM

The authors formulate APT profile construction as ontology-constrained entity and relation extraction. They develop the six-dimension VICTOR ontology and the Debapt multi-agent framework to extract, review, adjudicate, and aggregate evidence-supported facts without task-specific fine-tuning. [Debapt, Sections 1, 3, and 4, pp. 2-7]

## Main findings

### AUTHOR CLAIM

Across CTINexus, STIXnet, and LLM4CTI, Debapt ranks in the top two for every dataset/metric combination and reports the best value in 15 combinations. It reports entity F1-micro values of 0.8213, 0.7684, and 0.8007 and relation F1-micro values of 0.8197, 0.8886, and 0.8286 for the three datasets. [Debapt, Section 5.2, Tables 1-2, p. 9]

Hallucination count falls from 107 in round 1 to 13 in round 5 (approximately 87.9%), while hallucination ratio falls from 0.1080 to 0.0124 (about 88.5%). [Debapt, Section 5.6.1, Fig. 5, pp. 11-12]

## Critical assessment

### OUR OBSERVATION

Debapt offers the strongest process-level evidence for source-grounded multi-agent review among the three papers. It separates extraction, criticism, adjudication, and orchestration and tests component removals. Yet its task is structured CTI extraction and APT profiling, not operational alert prioritization. Its metrics reward matching a VICTOR-aligned gold schema, and the study does not show whether analysts make better or faster security decisions using the profiles. Thus, its mechanisms are highly transferable in principle, while its outcome evidence is task-specific.

See [[Methodology]], [[Dataset and Preprocessing]], [[Models and Architecture]], [[Evaluation and Results]], [[Limitations]], and [[Research Relevance]].

