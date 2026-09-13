# Phase 1 - Literature Review and Research Gap Identification

## Selection-Compliance Checkpoint

The three selected PDFs are 2026 journal research articles and contain identifiable methodologies, data sources, and evaluations. The PDFs do not establish journal quartile. Their Q1 status must therefore be confirmed using the instructor's accepted ranking source before submission. **[Verification required]**

## 1. Proposed Research Topic and Current Research Direction

### Development of the topic

The project began within the broad area of a **multi-agent Security Operations Centre (SOC)**. However, “multi-agent SOC” describes a possible application or system architecture; it does not identify a research problem by itself. A project that only connects multiple agents to alerts, retrieval tools, and a dashboard would demonstrate implementation, but it would not necessarily produce generalizable research evidence.

The selected literature points toward a narrower problem. Zhang et al. examine causal constraints, adversarial policy review, and explainable escalation in autonomous cyber defense. Agrawal et al. examine adaptive attacker-defender interaction and automated response in a cyber range. Zhao et al. use source-grounded extraction, critic agents, adjudication, and retrieval-assisted validation for CTI-based APT profiling. These studies address different tasks, but together they motivate a possible decision process:

> **alert -> retrieved evidence -> specialized reasoning -> evidence verification/criticism -> adjudication -> decision or abstention**

This combination is an architectural synthesis, not a demonstrated novelty claim. The empirical question is whether its verification and adjudication mechanisms improve alert decisions under controlled evidence conditions.

### Current research direction

- **Research area:** Evidence-Grounded Multi-Agent Reasoning for Security Alert Triage
- **Research problem:** Reliable security-alert decision-making when evidence is incomplete, contradictory, or uncertain.
- **Candidate research question:** **Does explicit evidence verification and multi-agent adjudication improve the reliability of security-alert triage compared with a matched single-agent RAG baseline, particularly when evidence is incomplete or contradictory?**

In this question, **reliability is not represented by one metric**. It refers to a combination of correct alert disposition, reasoning supported by the supplied evidence, confidence that corresponds to observed correctness, and appropriate abstention when the evidence is insufficient or conflicting.

This question is a candidate direction emerging from the Phase 1 comparison. It is not permanently fixed, and the reviewed papers do not establish its novelty across the wider literature. A broader literature search is required before making a final novelty claim.

### Scope boundaries

The proposed work is currently limited to:

- security-alert triage or disposition;
- traceable evidence grounding;
- explicit verification and adjudication;
- uncertainty-aware abstention or escalation; and
- comparison under matched evidence and computational conditions.

It does **not** currently claim to solve full autonomous SOC operation, complete incident response, cyberattack generation, zero-day detection, APT attribution, or general-purpose autonomous cyber defense. These are related domains, not interchangeable project objectives.

### Why this is a research question

“Build a multi-agent SOC” is primarily a construction objective. In contrast, testing whether explicit evidence verification and adjudication improve triage reliability defines:

- a **baseline**: a matched single-agent retrieval-augmented generation (RAG) triager;
- an **intervention**: proposer, critic, and adjudicator roles with explicit evidence checks;
- **controlled conditions**: complete, incomplete, and contradictory evidence;
- **measurable outcomes**: decision performance, grounding errors, calibration, abstention behavior, latency, and cost; and
- a **falsifiable proposition**: the multi-agent mechanism may improve, fail to improve, or reduce reliability under the stated conditions.

The second formulation is therefore research-oriented because it evaluates a mechanism rather than assuming that a multi-agent architecture is beneficial.

## 2. Paper 1 - Zhang et al.

**Bibliographic record:** Yiyao Zhang, Diksha Goel, and Hussain Ahmad, “Explainable Autonomous Cyber Defense Using Adversarial Multi-Agent Reinforcement Learning,” *Expert Systems with Applications*, 326, 132741, 2026. DOI: 10.1016/j.eswa.2026.132741.

### A. What the paper does

Zhang, Goel, and Ahmad propose the Causal Multi-Agent Decision Framework (C-MADF) for autonomous cyber defense under ambiguous or manipulated telemetry. The system is intended to reduce unsafe or unnecessary mitigation caused by correlation-based decisions. [Zhang, Sections 1 and 5, pp. 1-14]

### B. Methodology

C-MADF learns a Structural Causal Model (SCM) from historical telemetry and converts it into an investigation-level MDP-DAG. This graph restricts the transitions available to the decision policies. A threat-optimizing Blue-Team policy proposes actions, while a conservatively rewarded Red-Team policy challenges actions that lack sufficient support. Policy divergence contributes to an Explainability-Transparency Score (ETS), which governs autonomous action, further evidence collection, or human escalation. [Zhang, Sections 1 and 5, pp. 1-14]

Both policies use a three-layer MLP with Double DQN, prioritized replay, target networks, and separately learned weights. The action space contains 18 high-level investigation and mitigation actions. Training uses 1.5 million steps per agent and three random seeds. [Zhang, Section 5.3.1 and Table 10, pp. 10-12]

### C. Dataset and experimental setup

Evaluation uses CICIoT2023. The study maps multiple attack categories to a binary attack/benign decision space. Records are transformed into alert-summary, host, flow, and investigation-context features. Scenario-level train/validation/test separation is used, and scaling parameters are learned from training data only. Exact sample counts and split proportions are not clearly reported. The external baselines are DUGAT-LSTM, BiLSTM IDS, and Hybrid Weighted-XGBoost. [Zhang, Section 7.1, p. 17]

### D. Main results

C-MADF reports precision **0.997**, recall **0.961**, F1 **0.979**, and FPR **1.8%**. The baseline FPRs are **11.2%**, **9.7%**, and **8.4%**. In the ablation study, removing the causal SCM produces precision **0.903**, recall **0.959**, F1 **0.930**, and FPR **59.4%**. Removing the Red Team produces **0.963**, **0.963**, **0.963**, and **21.2%**, respectively; removing the Blue Team produces **0.957**, **0.972**, **0.964**, and **25.1%**. Results are means over three seeds, with reported standard deviations below 0.02. [Zhang, Tables 12-13, pp. 18-19]

The paper reports that higher ETS values align with stronger causal support and lower policy disagreement, while lower values align with weaker evidence and greater disagreement. Exact correlation or calibration coefficients are not clearly reported. [Zhang, Section 7.5, p. 19]

### E. Author-stated limitations

The authors state that causal discovery depends on representative historical telemetry and that sustained poisoning requires further empirical study. They acknowledge additional inference overhead, possible shared blind spots between the two policies, dependence on a predefined investigation ontology, and the absence of human-factor and live operational validation for ETS. They also state that one laboratory benchmark is insufficient to establish deployment readiness. [Zhang, Sections 8-8.3, pp. 19-20]

### F. Our critical observations

The paper is a strong conceptual match to the proposed direction, but its empirical scope is narrower than its framing. CICIoT2023 is a benchmark dataset rather than an operational SOC alert queue. The binary attack/benign formulation removes distinctions that may matter for alert severity, priority, and next-step investigation. The external baselines are primarily intrusion-detection models, not competing triage systems with comparable evidence verification, action constraints, or escalation logic. No analyst study, cross-dataset evaluation, cross-organization test, throughput measurement, or exact ETS calibration analysis is reported.

### G. Relevance to the proposed topic

Zhang contributes three useful ideas: evidence prerequisites can constrain investigation actions; a second policy can challenge premature decisions; and disagreement can trigger evidence collection or human escalation. These ideas support the verification and uncertainty components of the candidate research direction.

### H. What the paper does not establish

The reported detection and FPR results do not establish that C-MADF improves prioritization or disposition within a heterogeneous SOC alert queue. They also do not establish that ETS improves analyst decisions. Triage-specific data, baselines, and outcomes would be required for those claims.

## 3. Paper 2 - Agrawal et al.

**Bibliographic record:** Alka Agrawal, Mohd Nadeem, Ahmed Al Nuaim, and Abdullah Al Nuaim, “Artificial Intelligence Driven Multi Agent Framework for Adaptive Cyber Attack Simulation and Automated Incident Response in Cyber Range Environments,” *Scientific Reports*, 16, 11673, 2026. DOI: 10.1038/s41598-026-45937-9.

### A. What the paper does

Agrawal et al. address cyber-range simulations that rely on static attack scripts or fixed rules. They propose an AI-driven multi-agent framework for adaptive attack simulation, network-attack detection, and automated response in CyDER 2.0. [Agrawal, Abstract and “Research objectives and hypothesis,” pp. 1, 6]

### B. Methodology

DQN attacker agents observe known vulnerabilities, network configuration, and recent defender behavior before selecting actions such as scanning, exploitation, privilege escalation, and evasion. Defender agents combine a Random Forest for labeled attacks with an Autoencoder for anomalous activity. Agents exchange asynchronous JSON messages through ZeroMQ. Detected activity triggers a predefined response library containing actions such as blocking an IP address, quarantining a host, terminating sessions, preserving logs, blocking outbound traffic, or notifying staff. [Agrawal, “Multi-agent system architecture,” pp. 11-12; “Results,” p. 17]

The DQN has hidden layers of 128, 64, and 32 units, a learning rate of **0.001**, discount factor **0.95**, replay capacity of **100,000**, batch size **64**, and epsilon decay from **0.8** to **0.1** over **5,000** episodes. [Agrawal, “Developing an attacker agent model,” p. 13]

### C. Dataset and experimental setup

The study uses CICIDS2017 and UNSW-NB15 traffic data. It reports approximately **80 GB** of raw CICIDS2017 logs, approximately **85** extracted features, fewer than **0.5%** of rows affected by missing data, SMOTE balancing, and a roughly **50,000**-sample balanced dataset divided into **40,000** training and **10,000** test samples. It does not clearly report each source dataset's contribution, final class distribution, feature-alignment procedure, or whether SMOTE is applied only after the split. [Agrawal, Table 4, p. 12; Table 8, p. 15]

Three combined scale/scenario configurations are tested: **50 hosts** with basic attacks, **120 hosts** with a multi-stage attack, and **200 hosts** with concurrent attacks. Each configuration uses two attacker agents and three defender agents. [Agrawal, “Environment configuration,” p. 14]

### D. Main results

The DQN attack success rate rises from **18.7%** at episode 1,000 to **84.5%** at episode 5,000. The weighted Random Forest/Autoencoder ensemble reports **93.0%** accuracy and **91.9%** F1. [Agrawal, Tables 5-6, pp. 13-14]

The AI-driven MAS reports F1 scores of **94.5%**, **89.9%**, and **87.9%** for the small, medium, and large configurations. The rule-based MAS reports **80.1%**, **75.5%**, and **71.8%**; the static system reports **67.8%**, **59.2%**, and **56.1%**. Response latencies for the AI-driven MAS are **4.2**, **5.6**, and **6.1 seconds**. Rule-based latencies are **6.5**, **8.3**, and **9.5 seconds**, while static-system latencies are **12.1**, **15.8**, and **18.4 seconds**. [Agrawal, Tables 9-10, pp. 15-16]

The prose below Table 10 gives **12.6 seconds** for the medium static configuration, whereas the table reports **15.8 seconds**. This draft retains the table value and marks the discrepancy for verification rather than resolving it by assumption. **[Verification required]** [Agrawal, “Average response latency,” p. 16]

### E. Author-stated limitations

The authors explicitly identify deployment on resource-constrained distributed edge devices as difficult because of computing and storage demands. They propose compression, lightweight inference, and hybrid edge-cloud designs as future work. [Agrawal, Conclusion, p. 18] The paper does not contain a dedicated limitations section for its own experimental design.

### F. Our critical observations

The framework combines adaptive attack generation and ML-based detection with response actions that are largely predefined. It therefore does not demonstrate evidence-based deliberation about alternative defender conclusions or responses. Network size and attack complexity change together across the three main configurations, so their separate effects cannot be identified. No ablation isolates the contributions of DQN adaptation, ensemble detection, asynchronous communication, or multi-agent coordination. The paper states that paired t-tests and ANOVA reject null hypotheses at p < 0.05, but the corresponding experimental sample sizes, test statistics, degrees of freedom, confidence intervals, and effect sizes are not clearly reported.

### G. Relevance to the proposed topic

Agrawal contributes an executable attacker-defender environment and shows that latency, resource use, scenario complexity, and scale are necessary operational measures. These concerns should inform any later evaluation of a multi-agent triage mechanism.

### H. What the paper does not establish

The results do not establish improved analyst-facing alert reasoning. Detection, adaptive attack simulation, and rapid rule-triggered response are distinct from deciding whether an alert is credible, citing the evidence for that disposition, identifying contradiction, or abstaining under uncertainty.

## 4. Paper 3 - Zhao et al. (Debapt)

**Bibliographic record:** Xinyun Zhao, Lanlan Qi, Yongheng Zhang, Yingxiao Guan, Guozheng Yang, Yuliang Lu, and Xiang Wang, “Debapt: Ontology-Driven Multi-Agent Debate for APT Adversary Profile Construction from Cyber Threat Intelligence,” *Computers & Security*, 170, 104988, 2026. DOI: 10.1016/j.cose.2026.104988.

### A. What the paper does

Zhao et al. study APT adversary-profile construction from unstructured cyber threat intelligence. They address omission, semantic drift, and hallucination when profile-relevant facts are distributed across long CTI reports. The authors define the VICTOR ontology and implement Debapt as a two-phase entity- and relation-extraction workflow. [Debapt, Sections 1 and 4.2, pp. 1-6]

### B. Methodology

VICTOR organizes information into Victim, Infrastructure, Capability, TTPs, Originator, and Record. Entity extraction uses six ontology-aligned prompts. CritEn checks source-text support, ontology compliance, coverage, and structured identifiers. Regex validates IP, MAC, and CVE forms, while RAG validates ATT&CK identifier/name consistency. JdgEn accepts the entity set or requests targeted revision. ExtRe, CritRe, and JdgRe then propose, verify, and adjudicate STIX-compatible relations among verified entities. A moderator stops each phase following acceptance, absence of a valid correction, or a five-round cap. [Debapt, Sections 4.2-4.3.3, pp. 4-7]

A vector database and RAG support cross-report aggregation. Corroborating evidence raises a candidate fact's confidence, whereas conflicting evidence lowers confidence and marks the fact as risky. [Debapt, Section 4.3.4, p. 7]

### C. Dataset and experimental setup

The authors re-annotate CTINexus, STIXnet, and LLM4CTI under VICTOR. Three graduate annotators produce LLM-assisted drafts and manually review, correct, and complete them; a fourth graduate researcher arbitrates disagreements. Fleiss's kappa is **0.79**. The resulting annotations contain **4,915 deduplicated entities** and **5,736 relations**. Each dataset is divided **6:2:2** into training, validation, and test sets. The total document count and per-dataset label distributions are not clearly reported. [Debapt, Section 5.1.1, p. 8]

### D. Main results

Using thinking-enabled qwen-plus by default, Debapt reports entity F1-micro values of **0.8213**, **0.7684**, and **0.8007** for CTINexus, STIXnet, and LLM4CTI. Relation F1-micro values are **0.8197**, **0.8886**, and **0.8286**. [Debapt, Tables 1-2, p. 9]

Removing CritEn reduces entity F1-micro from **0.8213** to **0.5897**, entity F1-macro from **0.7986** to **0.5398**, relation F1-micro from **0.8197** to **0.7435**, and relation F1-macro from **0.7944** to **0.6450**. [Debapt, Table 4, p. 11]

Across five rounds, the hallucination count falls from **107** to **13**, an approximately **87.9%** reduction. The hallucination ratio falls from **0.1080** to **0.0124**, an approximately **88.5%** reduction. [Debapt, Section 5.6.1, pp. 11-12]

### E. Author-stated limitations

The authors identify reports describing multiple APT actors as a future challenge. [Debapt, Section 6, p. 16] The paper does not provide a dedicated limitations section.

### F. Our critical observations

Debapt's gold annotations are reconstructed under VICTOR, which is also the ontology guiding the proposed method. This is not inherently an error, but it means the results establish performance on a VICTOR-aligned task rather than performance independent of that ontology. Document counts, per-dataset class distributions, actor- or source-disjoint testing, repeated-run uncertainty, inference latency, and token cost are not clearly reported. LLM-assisted annotation and an LLM-based weak semantic matcher may also introduce model-mediated bias. Most roles use the same underlying backbone, so prompt specialization does not guarantee independent failure modes. The termination study further shows an operational boundary: relation extraction reaches the five-round maximum for three of five long excerpts. [Debapt, Table 6, p. 12]

### G. Relevance to the proposed topic

Debapt provides the strongest methodological inspiration for the current direction. Its extractor-critic-adjudicator separation, source-text checks, deterministic validation, retrieval-assisted verification, bounded iteration, and conflict-aware aggregation show how evidence checking can be made an explicit stage rather than left inside one model response.

### H. What the paper does not establish

Debapt evaluates CTI entity/relation extraction and APT profiling, not security-alert triage. Its extraction F1 and hallucination reductions do not establish more accurate alert disposition, better prioritization, useful abstention, or improved analyst decisions. These outcomes require a triage-specific evaluation.

## 5. Cross-Paper Comparison

| # | Title | Year of Publication | Dataset Used | Preprocessing Techniques | Models / Techniques Used | Evaluation Metrics Used | Results | Limitations / Research Gap |
|---:|---|---:|---|---|---|---|---|---|
| 1 | Zhang et al., *Explainable Autonomous Cyber Defense Using Adversarial Multi-Agent Reinforcement Learning* | 2026 | CICIoT2023; sample count and split ratios not clearly reported | Scenario-separated partitions; alert/host/flow/context aggregation; training-only scaling; binary attack/benign mapping | SCM; MDP-DAG; Double-DQN Blue/Red policies; policy divergence; ETS | Precision, recall, F1, FPR; three-seed variation; ETS behavior | C-MADF: 0.997 precision, 0.961 recall, 0.979 F1, 1.8% FPR; ablations increase FPR to 59.4%, 21.2%, and 25.1% | Single IoT benchmark; binary task; IDS-style baselines; no direct SOC alert-triage or analyst evaluation |
| 2 | Agrawal et al., *Artificial Intelligence Driven Multi Agent Framework for Adaptive Cyber Attack Simulation and Automated Incident Response in Cyber Range Environments* | 2026 | CICIDS2017 and UNSW-NB15; approximately 50,000 balanced samples reported; per-source contribution not clearly reported | Approximately 85 flow features; missing-data handling; normalization; dimensionality reduction; SMOTE; stratified 80/20 split | DQN attacker; Random Forest/Autoencoder defender; CyDER 2.0; ZeroMQ; predefined response rules | Precision, recall, F1; response latency; attack complexity; CPU/RAM; acceptance tests; stated t-tests/ANOVA | AI-MAS F1: 94.5%, 89.9%, 87.9%; latency: 4.2, 5.6, 6.1 s across 50/120/200-host settings | Dataset merge underreported; size and attack complexity confounded; predefined response; no evidence-grounded alert reasoning |
| 3 | Zhao et al., *Debapt: Ontology-Driven Multi-Agent Debate for APT Adversary Profile Construction from Cyber Threat Intelligence* | 2026 | Re-annotated CTINexus, STIXnet, and LLM4CTI; 4,915 entities and 5,736 relations; document count not clearly reported | VICTOR mapping/filtering; annotation completion; mention merging; JSON triples; 6:2:2 split; BIO conversion | VICTOR; entity/relation extractors, critics, adjudicators, moderator; regex; RAG/vector database | Entity/relation micro, macro, and weighted F1; hallucination count/ratio; ablation; length and termination analysis | Entity F1-micro: 0.8213/0.7684/0.8007; relation F1-micro: 0.8197/0.8886/0.8286; hallucination count 107 to 13 | VICTOR-aligned ground truth; no alert dataset, analyst outcomes, repeated-run uncertainty, or cost/latency analysis |

### Cross-paper synthesis

The studies occupy different parts of a broader defensive workflow. Zhang focuses on network intrusion detection and constrained autonomous decisions. Agrawal focuses on cyberattack simulation, network detection, and automated response. Debapt focuses on CTI extraction and APT profiling. Treating their reported metrics as measurements of the same capability would be invalid.

Within the selected literature, Zhang offers causal and uncertainty-aware decision constraints; Agrawal supplies attacker-defender interaction and operational performance considerations; and Debapt supplies explicit evidence review and adjudication. Together they suggest the architecture shown earlier, but none tests whether that architecture improves security-alert disposition. The architectural combination must therefore remain a research proposal rather than a novelty or effectiveness claim.

## 6. Research Gaps Derived from the Three Papers

The gaps below are limited to the selected literature. They do not establish that the wider research field has not addressed them.

| Research Gap | Evidence from Paper 1 | Evidence from Paper 2 | Evidence from Paper 3 | Proposed Research Opportunity |
|---|---|---|---|---|
| **1. Operational evidence-grounded alert triage is not directly evaluated.** | Evaluates binary IoT attack/benign classification and an abstract decision path, not a queue of analyst alerts. | Evaluates traffic detection and cyber-range response rather than alert disposition. | Evaluates CTI extraction and APT profiling rather than alerts. | Evaluate disposition or abstention on alert cases with ground-truth decisions and traceable evidence. |
| **2. Incomplete and contradictory evidence is not controlled as an experimental factor in alert decision-making.** | Models adversarial telemetry and associates ETS with evidence sufficiency, but does not run triage experiments across controlled evidence-completeness conditions. | Does not report systematic removal or contradiction of evidence presented to a defender's decision process. | Detects unsupported and conflicting CTI facts, but not their effect on security-alert disposition. | Compare complete, incomplete, and contradictory evidence conditions while measuring decision errors, contradiction detection, and abstention. |
| **3. Explicit criticism and adjudication are not evaluated as mechanisms for improving alert-disposition reliability.** | Uses an adversarial policy and ablates agent roles, but the outcome is benchmark detection rather than alert disposition. | Uses multiple attacker/defender agents but no explicit evidence critic or adjudicator for defender conclusions. | Ablates critics and adjudicators for CTI extraction, not alert decisions. | Compare a matched single-agent RAG triager with proposer-only and proposer-critic-adjudicator variants. |
| **4. Cross-environment generalization is insufficiently tested for the proposed use.** | Uses one laboratory IoT benchmark and identifies external validity as unresolved. | Combines two traffic datasets in one cyber range; scale and attack complexity vary together. | Uses three CTI corpora under one profiling ontology; actor/source/time-disjoint evaluation is not clearly reported. | Use time-, source-, tool-, or environment-separated evaluation and report performance and calibration changes. |

These gaps are connected. A triage-specific evaluation is necessary before incomplete evidence, adjudication, or generalization can be studied meaningfully. The first gap defines the task; the second and third define controllable mechanisms and conditions; the fourth tests whether any observed effect transfers beyond one data setting.

## 7. Proposed Research Opportunity

### Empirical focus

The proposed contribution is not the construction of another multi-agent architecture. It is an empirical test of whether explicit evidence verification and adjudication improve reliable alert disposition under controlled evidence conditions.

### Candidate comparison

- **Matched baseline:** alert -> evidence retrieval -> single-agent RAG -> disposition plus cited evidence.
- **Proposed mechanism:** alert -> the same evidence retrieval -> proposer -> evidence critic -> adjudicator -> disposition or abstention.

The systems should receive the same alert information, retrieval process, and retrieval corpus. The underlying model should be the same or closely comparable where practical. Model-call counts, retrieved context, token use, latency, and other computational differences must be reported. If equal computational budgets are impractical, the study should present both outcome quality and resource use so that an improvement is not attributed uncritically to additional inference.

### Candidate evidence conditions

1. **Complete evidence:** all evidence defined for the case is available.
2. **Incomplete evidence:** selected relevant evidence is withheld according to a documented rule.
3. **Contradictory evidence:** the case contains mutually inconsistent or conflicting evidence items whose provenance remains visible.

These conditions are proposals for Phase 2 design. Their construction and validity are not established by the reviewed papers.

### Candidate evaluation measures

The final experiment need not implement every measure below. Selection should follow the final task definition and available labels.

**Decision quality**

- **Disposition F1, precision, recall, and false-positive rate:** measure whether alerts receive the correct decision, including the cost of unnecessary escalation or investigation.

**Grounding quality**

- **Evidence-citation correctness:** measures whether cited evidence actually supports the stated decision.
- **Unsupported-claim rate:** measures conclusions that are not justified by the supplied evidence.
- **Contradiction detection:** measures whether the system recognizes incompatible evidence rather than selecting one silently.

**Uncertainty handling**

- **Calibration:** measures whether confidence corresponds to observed correctness.
- **Abstention/selective prediction and risk-coverage:** measure the trade-off between answering more cases and limiting errors on the cases the system chooses to decide.

**Operational cost**

- **Latency and token or computational cost:** measure the operational overhead introduced by verification and adjudication.

Decision metrics alone would miss unsupported reasoning; grounding metrics alone would not show whether the final disposition is correct. Calibration and abstention matter because a triage assistant should defer when its evidence is insufficient. Latency and cost are required because a method that improves accuracy but cannot process alerts at a practical rate may have limited operational value.

### Broader literature check required before final novelty claim

The three selected papers justify this question as a potential opportunity, but they do not represent the complete literature on SOC automation, alert triage, agentic RAG, evidence verification, or selective prediction. Before Phase 2, a targeted literature check should determine whether equivalent matched comparisons already exist and refine the final contribution accordingly.

A result showing no improvement, worse performance, or an unfavorable reliability-cost trade-off would still answer the candidate research question. The value of the study depends on the fairness and transparency of the comparison, not on confirming that multiple agents are superior.

## 8. Proposed Hypotheses

These hypotheses are provisional and should be revised after dataset and metric selection.

- **H1:** Explicit evidence verification and multi-agent adjudication improve security-alert disposition performance compared with a matched single-agent RAG baseline.
- **H2:** Explicit evidence verification reduces unsupported or incorrectly grounded reasoning.
- **H3:** Adjudication improves reliability, calibration, or appropriate abstention when evidence is incomplete or contradictory.
- **H4:** The proposer-critic-adjudicator mechanism introduces measurable latency and token-cost overhead relative to the matched single-agent baseline.

H4 is necessary because an accuracy gain would not be sufficient by itself; the size of the operational cost must also be measured. H1-H3 should not be accepted unless supported by the eventual experiment.

## 9. Short Conclusion

The literature review shows why the project should move from the broad idea of a multi-agent SOC toward a narrower empirical question. Zhang demonstrates causal constraints, adversarial policy review, and evidence-sensitive escalation, but evaluates binary intrusion detection on one IoT benchmark. Agrawal demonstrates adaptive attacker-defender interaction and automated cyber-range response, but does not study analyst-facing evidence reasoning. Debapt demonstrates source-grounded extraction, criticism, adjudication, and RAG-assisted validation, but evaluates CTI extraction and APT profiling under a VICTOR-aligned schema.

The three studies therefore support components of an evidence-grounded decision process, not a claim that multi-agent reasoning already improves security-alert triage. The resulting candidate question asks whether explicit verification and adjudication improve disposition reliability over a matched single-agent RAG baseline, particularly under incomplete or contradictory evidence. This is a suitable direction for further refinement because it defines a baseline, an intervention, controlled conditions, measurable outcomes, and a falsifiable claim. It is also realistically bounded for a semester project if the alert type, dataset, evidence schema, and primary metrics are restricted before implementation.

## 10. Supervisor-Style Quality Check

- **Logical research story:** The progression from multi-agent SOC architecture to a mechanism-focused triage question is explicit.
- **Gap support:** Each gap is tied separately to Zhang, Agrawal, and Debapt; no wider-literature absence is claimed.
- **Domain distinctions:** Intrusion detection, traffic classification, cyber-range response, CTI extraction, APT profiling, and alert triage remain conceptually separate.
- **Numerical integrity:** Previously extracted values are retained. The Agrawal latency discrepancy remains explicitly marked for verification.
- **Novelty discipline:** No claim of complete novelty is made; a broader literature check is required.
- **Falsifiability:** The candidate question compares a defined baseline and intervention under controlled evidence conditions.
- **Semester scope:** The focus is alert disposition, grounding, verification/adjudication, and abstention—not full SOC automation or response.
- **Assignment coverage:** The draft includes the topic, three critical paper analyses, author-stated and reviewer-identified limitations, the required comparison table, four evidence-supported gaps, a proposed opportunity, research question, hypotheses, scope, and conclusion.

## 11. Final Audit Change Log

1. **Major structural changes:** None; the assignment-aligned structure and research direction were retained.
2. **Claims strengthened or weakened:** Defined reliability as a multi-dimensional outcome and clarified that VICTOR alignment limits the scope of Debapt's evidence rather than constituting an automatic methodological error.
3. **Unsupported claims removed:** Reclassified Debapt's five-round convergence result as an observed operational boundary rather than an author-stated limitation.
4. **Research-gap improvements:** Retained the four evidence-supported gaps; no additional gap or novelty claim was introduced.
5. **Remaining verification issues:** Q1 journal status requires an instructor-accepted ranking source; Agrawal's medium static-response latency remains internally inconsistent; the final alert dataset, evidence-condition protocol, and primary metrics remain Phase 2 decisions.
