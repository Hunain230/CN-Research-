# Cross-Paper Comparison

## Assignment-required comparison table

| # | Title | Year of Publication | Dataset Used | Preprocessing Techniques | Models / Techniques Used | Evaluation Metrics Used | Results | Limitations / Research Gap |
|---|---|---:|---|---|---|---|---|---|
| 1 | *Explainable autonomous cyber defense using adversarial multi-agent reinforcement learning* | 2026 | CICIoT2023; attack categories mapped to binary attack/benign | Scenario-level train/validation/test separation; alert/host/flow state aggregation; training-only normalization/scaling; time alignment and missing-value handling for causal discovery | C-MADF; PC/FCI-family SCM; ontology-constrained MDP-DAG; Double-DQN Blue/Red policies; policy-divergence arbitration; ETS human escalation | Precision, recall, F1, FPR; ETS association with evidence/policy agreement; three-seed means | C-MADF: 0.997 precision, 0.961 recall, 0.979 F1, 1.8% FPR; baseline FPR 8.4%-11.2%; removing SCM raises FPR to 59.4% | One lab IoT benchmark; dataset counts/split ratios missing; classifier rather than triage baselines; no analyst study, live SOC evaluation, or cross-dataset transfer. [Zhang, Sections 7-8.3, Tables 12-13, pp. 17-20] |
| 2 | *Artificial intelligence driven multi agent framework for adaptive cyber attack simulation and automated incident response in cyber range environments* | 2026 | CICIDS2017 and UNSW-NB15; combined balanced subset reported as ~50,000 samples | ~85 flow features; removal/imputation; normalization; dimensionality reduction; SMOTE; stratified 80/20 split (40,000/10,000) | DQN attacker; Random Forest + Autoencoder defender; asynchronous ZeroMQ agents; CyDER 2.0; predefined response rules | Precision, recall, F1; response latency; attack complexity; CPU/RAM; expert/acceptance tests; claimed paired t-tests/ANOVA | AI MAS F1: 94.5%, 89.9%, 87.9% across small/medium/large scenarios; latency: 4.2, 5.6, 6.1 s; DQN attack success reaches 84.5% | Combined-data construction and statistics underreported; size is confounded with scenario complexity; response is predefined; no component ablation, evidence trace, or operational-alert evaluation. [Agrawal, Tables 4-13, pp. 12-17] |
| 3 | *Debapt: Ontology-driven multi-agent debate for APT adversary profile construction from cyber threat intelligence* | 2026 | Re-annotated CTINexus, STIXnet, and LLM4CTI; 4,915 deduplicated entities and 5,736 relations | Map/filter to VICTOR; add missed explicit entities; merge co-references; JSON triples; LLM-assisted/manual annotation; 6:2:2 split; BIO conversion; exact and weak semantic matching | VICTOR ontology; ExtEn/CritEn/JdgEn and ExtRe/CritRe/JdgRe; moderator; regex and RAG validation; vector-database aggregation; qwen-plus default | Entity/relation precision, recall, micro/macro/weighted F1; hallucination count/ratio; ablations; length groups; termination rounds | Entity F1-micro: 0.8213/0.7684/0.8007; relation F1-micro: 0.8197/0.8886/0.8286; hallucination count 107 to 13; CritEn removal causes largest entity decline | VICTOR-aligned ground truth; document/distribution counts missing; no uncertainty statistics, cost/latency, independent ontology, analyst utility, or transfer to alerts. [Debapt, Sections 5.1-5.6, Tables 1-6, pp. 8-12] |

## Functional comparison

| Dimension | Zhang | Agrawal | Debapt |
|---|---|---|---|
| Research problem | Safe autonomous cyber-defense decisions under ambiguous/manipulated telemetry | Adaptive cyberattack simulation and automated defense in a cyber range | Reliable structured APT profiling from long CTI reports |
| Cybersecurity setting | IoT intrusion detection plus constrained investigation/mitigation | Virtualized enterprise-like cyber range | CTI analysis and actor-centric APT profiling |
| Input | Aggregated alert summary, host indicators, flow statistics, investigation context | Flow features, network state, vulnerabilities, defender actions | Unstructured CTI documents |
| Output | Binary detection plus permitted investigation/mitigation action or escalation | Attack action, detection result, and predefined response action | Ontology-typed entities, relation triples, and aggregated actor profile |
| Agent roles | Threat-optimizing Blue policy and conservative Red challenger | Attacker agents and collaborating defender agents | Dimension extractors, critics, adjudicators, and moderator |
| Evidence handling | SCM-derived prerequisites, evidence flags, supporting/contradicting features | Features feed detectors; decision provenance is not represented | Direct source checks, regex, RAG, schema checks, source indexing, corroboration/conflict |
| Reasoning | Causally constrained sequential policy plus disagreement arbitration | RL attack planning; detection ensemble; rule-triggered response | Iterative extract-review-adjudicate loops |
| Explainability | ETS and structured human-in-the-loop artifacts | Real-time monitoring mentioned; no evaluated explanation method | Evidence-backed structured facts; no human-centered explanation study |
| CTI | Not used directly | Mentioned as realistic input in objectives, but evaluated datasets are traffic data | Central input and output domain |
| Alert triage | Mentioned as an application context, not directly benchmarked | Not evaluated | Not evaluated |
| Investigation | Abstract roadmap states and evidence collection | Detection-to-response scenarios | CTI fact extraction and cross-report synthesis |
| Incident response | Constrained high-level actions | Predefined containment/notification actions | Not addressed |
| Baselines | Three intrusion classifiers | Static range and fixed-rule MAS; literature feature table | Seven supervised and five LLM extraction baselines |
| Ablations | Removes SCM, Red, or Blue | None clearly reported | Removes team extractor, critics, or adjudicators |
| Generalizability evidence | One dataset; three seeds | Three sizes but confounded scenarios; two source datasets combined | Three CTI datasets and multiple backbones, all within the same CTI/schema setting |

## What is common?

### AUTHOR CLAIM - Cross-paper synthesis

- All three decompose cybersecurity work among specialized agents.
- All three claim adaptive or iterative behavior is preferable to a single static pipeline.
- All evaluate on public security datasets or reports rather than live production operations.
- Each combines learned components with explicit structure: causal/ontology constraints in Zhang, rules and cyber-range interfaces in Agrawal, and ontology/STIX constraints in Debapt.

### OUR OBSERVATION

The common theme is structured coordination, not a common task. The papers address different points in a security workflow and their metrics are not directly comparable.

## What is different?

### OUR OBSERVATION

- Zhang optimizes **detection and constrained decision execution**.
- Agrawal optimizes **simulation realism/adaptability, detection, and response speed**.
- Debapt optimizes **CTI entity/relation extraction and profile completeness/grounding**.
- “Evidence” is causal telemetry structure for Zhang, detector features for Agrawal, and traceable source text/schema support for Debapt.
- Multi-agent interaction is adversarial policy challenge in Zhang, attacker-defender environment interaction in Agrawal, and cooperative quality control in Debapt.

## What is already well studied in these papers?

### OUR OBSERVATION

- Detection F1/precision/recall on established intrusion datasets.
- Role-specialized multi-agent architectures.
- Structured constraints for narrowing agent actions or outputs.
- Component contribution through ablation in Zhang and Debapt.
- CTI entity/relation extraction against supervised and prompted baselines in Debapt.

This means a semester project that merely combines agents, an intrusion classifier, RAG, and a dashboard would mostly be system integration rather than a research contribution.

## What is only partially studied?

### OUR OBSERVATION

- Human oversight is designed by Zhang, assessed only broadly by experts in Agrawal, and absent as a measured outcome in Debapt.
- Generalization is discussed but not tested on live SOC data.
- Evidence grounding is explicit in Zhang and Debapt but not evaluated as a standalone factor against a triage outcome.
- Incident response is implemented by Agrawal and abstractly constrained by Zhang, but action correctness and operational harm are not rigorously evaluated.
- Long-context robustness is tested for CTI extraction, not for multi-alert incident timelines.

## What is missing from the three-paper evidence base?

### OUR OBSERVATION

- A benchmark of real or realistically replayed security alerts with analyst dispositions and evidence provenance.
- Alert ranking, deduplication, correlation into incidents, and investigation-next-step evaluation.
- A direct comparison of single-agent and multi-agent reasoning under identical evidence and compute budgets.
- Calibrated citations from every triage conclusion to alert/telemetry/CTI evidence.
- Human analyst outcomes and safe-response correctness.
- Cross-organization and temporal generalization under changing alert rules and data distributions.

