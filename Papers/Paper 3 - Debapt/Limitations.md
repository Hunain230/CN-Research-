# Limitations

## Author-stated limitations and future work

### AUTHOR CLAIM

- The authors identify multi-actor reports as a future challenge: reports organized around shared TTPs may describe multiple APT groups in one narrative, requiring multiple concurrent profile states and finer-grained attribution. [Debapt, Section 6, p. 16]
- The termination study shows that relation extraction is more demanding than entity extraction: three of five long excerpts reach the five-round maximum with unresolved or minimally changing relations. [Debapt, Section 5.6.2, Table 6, p. 12]
- Multi-agent debate introduces computational cost as agent and round counts grow; this is acknowledged in the related-work motivation for bounded termination. [Debapt, Sections 2.3 and 4.3.3, pp. 3, 7]

The paper does not provide a dedicated limitations section.

## Our critical observations

### OUR OBSERVATION - Dataset and annotation

- The ground truth is reconstructed using VICTOR, the same ontology that constrains Debapt. This tests schema-aligned extraction well but may overstate advantage over methods not designed around VICTOR.
- LLM-assisted annotation and LLM-based weak semantic matching can share biases with LLM-based evaluated systems.
- Document counts and per-dataset label distributions are missing.
- Actor-disjoint, campaign-disjoint, publisher-disjoint, and chronological splits are not reported.

### OUR OBSERVATION - Methodology

- VICTOR's coverage and boundary choices determine what can be extracted; facts outside the ontology may be systematically omitted.
- Most agents appear to use the same backbone, so prompt-role diversity may not prevent correlated errors.
- RAG verifies selected structured facts and supports aggregation, but retrieval quality, vector-store configuration, and retrieval-specific ablations are not reported.
- Confidence updates in profile aggregation are illustrated with fixed scores, but calibration against factual correctness is not evaluated.

### OUR OBSERVATION - Evaluation and generalizability

- All three datasets are textual CTI, not alerts, cases, or raw telemetry.
- No human analyst study measures profile correctness, time saved, decision quality, or cognitive burden.
- No cost, token-use, wall-clock latency, or throughput comparison quantifies the price of multi-round debate.
- No statistical uncertainty is reported.
- Long-context groups top out near 2,033 average tokens in the plotted experiment, while the separate termination excerpts average about 3,000 tokens; this does not test very long reports near the 8,192-token output limit or larger input context windows.

## Missing experiments

### OUR OBSERVATION

- Evaluation under an ontology not authored for Debapt or against an ontology-free gold standard.
- Actor/source/time-disjoint generalization.
- Retrieval ablation and retrieval-error stress testing.
- Comparison with independent backbones per role versus a shared backbone.
- Cost/latency/quality trade-off by round count.
- Blind analyst evaluation of profile usefulness and evidence traceability.
- Transfer from CTI facts to alert enrichment, triage, or incident investigation.

