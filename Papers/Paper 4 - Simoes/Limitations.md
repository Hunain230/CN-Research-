# Limitations

## Author-stated limitations and future work

### AUTHOR CLAIM

- The attack catalog uses a single purpose-built malicious MCP server and fixed, non-adaptive inputs; iterative adversarial probing is not evaluated. [Simões, Section 5, p. 26]
- Lexical, language-specific pattern matching is evaded by base64, homoglyphs, non-English wording, fragmentation, and paraphrase. [Simões, Sections 4.4 and 5, pp. 25-27]
- The same lexical controls reject benign SOC text containing attack-like surface features. [Simões, Sections 4.5 and 5, pp. 25-27]
- Six of 35 threat vectors are not covered. RAG/knowledge-base poisoning, adversarial embeddings, and package hallucination fall outside the middleware; replay needs server-side freshness; consensus manipulation and covert coordination are not tested in the sequential topology. [Simões, Sections 3.2.8 and 5, pp. 13-14, 27]
- The handoff validator supports only a sequential topology. [Simões, Sections 3.3 and 5, pp. 17, 27-28]
- The application-layer DNS-rebinding response check was inactive in the evaluated environment; protection depended on loopback binding and network segmentation. [Simões, Section 5, pp. 27-28]
- Only GPT-4o mini is evaluated, and residual risk may vary with model instruction-following behavior. [Simões, Section 5, pp. 27-28]
- File-based memory is not suitable for concurrent production use at scale. [Simões, Section 5, pp. 27-28]

The authors propose semantic detection, adaptive evaluation, more LLMs, non-sequential topologies, scalable memory, SIEM-integrated audit monitoring, and stronger tamper evidence such as hash-chained or write-once logs. [Simões, Sections 5-6, pp. 26-29]

## Our critical observations

### OUR OBSERVATION - Data and threat coverage

- The 25 cases provide controlled coverage of the authors' threat model, not a representative sample of production attacks.
- The main legitimate set is too simple to estimate operational false-positive rates; the separate benign-text probe demonstrates this boundary.
- Only two alerts exercise the complete SOC pipeline.

### OUR OBSERVATION - Methodology

- All functional agents use the same model, so cross-model effects and model-specific residual behavior are unresolved.
- A linear triage-enrichment-response workflow does not test debate, independent evidence review, or adjudication.
- Regex controls are transparent and deterministic but cannot determine semantic support or contradiction.
- A rug-pull manifest mismatch is logged as successful detection although it does not automatically prevent use; the security consequence of warning-only behavior is not tested.

### OUR OBSERVATION - Evaluation and generalizability

- The evaluation establishes middleware rule enforcement under specified conditions, not accurate alert triage.
- No labelled alert decisions, analyst study, cross-SIEM deployment, long-running workload, concurrency stress test, or adaptive red-team campaign is reported.
- Local microbenchmarks exclude model calls, network time, and total pipeline cost, so production alert throughput is not established.

## Missing experiments

### OUR OBSERVATION

- Adaptive mutation and iterative attacker feedback.
- Semantic detector versus lexical detector, including accuracy, latency, and cost.
- Cross-model and cross-MCP-server replication.
- End-to-end control ablation and comparison with alternative guardrails.
- Representative benign SOC corpus for false-positive measurement.
- Labelled alert-triage benchmark with decision accuracy and evidence-grounding metrics.
- Concurrent and long-duration deployment with production-grade memory and audit storage.

