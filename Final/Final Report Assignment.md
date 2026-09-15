# Final Report Assignment

## Phase 1 — Literature Review and Research Gap Identification

### Assignment-purpose and selection checkpoint

The purpose of Phase 1 is to critically analyze recent research related to the proposed topic by identifying established methodologies, data sources, models, evaluation strategies, reported findings, limitations, and potential research gaps. The assignment requires exactly three directly relevant journal research articles published in 2026. Each paper must contain an identifiable methodology, experimental setup, or analytical framework and sufficient information about data, methods, and evaluation for critical analysis. The three papers must also be published in Q1-ranked journals. [Phase 1 assignment PDF, “Paper Selection”]

The three papers used in this report are 2026 journal research articles with identifiable frameworks and evaluations. However, journal quartile depends on the ranking system and category used. *Expert Systems with Applications* and *Computers & Security* still require confirmation in the instructor's accepted ranking source. More importantly, the publisher's [journal statistics](https://www.mdpi.com/journal/applsci/stats) currently list *Applied Sciences* as JCR Q2 in Engineering (Multidisciplinary), while reporting CiteScore Q1 in some categories. Therefore, the MCP paper satisfies the assignment's Q1 condition only if the instructor accepts the applicable Scopus/CiteScore category. **[Verification required before submission]**

## 1. Proposed Research Topic

### Development of the topic

The initial area was a **multi-agent Security Operations Centre (SOC)**. That phrase describes an application area and possible architecture, but it does not by itself state a research problem. Building agents that connect to a SIEM, retrieval tools, and response functions would demonstrate system integration; it would not necessarily provide evidence about whether a particular mechanism improves security decisions.

The selected papers narrow the problem in three complementary ways:

- Simões et al. provide a concrete MCP-based SOC pipeline and show why tool access, inter-agent handoffs, memory, and external outputs require explicit security controls.
- Zhang et al. examine causal constraints, evidence-sensitive escalation, and adversarial policy review in autonomous cyber defense.
- Zhao et al. demonstrate source-grounded extraction, criticism, adjudication, and retrieval-assisted validation in CTI-based APT profiling.

These studies motivate the following decision process:

> **alert → retrieved evidence → specialized reasoning → evidence verification/criticism → adjudication → decision or abstention**

This architecture is a synthesis of ideas from the selected literature, not a claim of novelty. The research interest is whether its explicit verification and adjudication mechanisms improve alert decisions under controlled evidence conditions.

### Current research direction

- **Research area:** Evidence-Grounded Multi-Agent Reasoning for Security Alert Triage
- **Research problem:** Reliable security-alert decision-making when evidence is incomplete, contradictory, or uncertain.
- **Candidate research question:** **Does explicit evidence verification and multi-agent adjudication improve the reliability of security-alert triage compared with a matched single-agent RAG baseline, particularly when evidence is incomplete or contradictory?**

Here, **reliability** refers to several measurable properties: correct alert disposition, reasoning that is supported by the supplied evidence, confidence that corresponds to observed correctness, and appropriate abstention when evidence is insufficient or conflicting. No single metric represents all of these properties.

This question is a candidate direction emerging from Phase 1. The three selected studies motivate it but do not establish its novelty across the wider literature. A broader literature review is required before any novelty claim is made.

### Scope boundaries

The proposed project is limited to security-alert triage or disposition, traceable evidence grounding, explicit verification and adjudication, and uncertainty-aware abstention or escalation. It does not claim to solve full SOC automation, complete incident response, cyberattack generation, zero-day detection, APT attribution, or general-purpose autonomous cyber defense.

### Why this is a research question

“Build a multi-agent SOC” is primarily a construction objective. In contrast, the candidate question defines:

- a **baseline**: a matched single-agent retrieval-augmented generation (RAG) triager;
- an **intervention**: explicit proposer, critic, and adjudicator roles;
- a **task**: security-alert disposition;
- **controlled conditions**: complete, incomplete, and contradictory evidence;
- **measurable outcomes**: decision quality, grounding, uncertainty handling, and operational cost; and
- a **falsifiable proposition**: the proposed mechanism may improve performance, have no effect, or make performance worse.

The research contribution would therefore be the empirical evaluation of a mechanism, not the existence of multiple agents.

## 2. Paper 1 — Simões et al.

**Bibliographic record:** Rodrigo Tavares de Pina Simões, Xavier Larriva-Novo, Carmen Sánchez-Zas, Victor A. Villagrá, and Andrés I. Marín López, “Design of a Security Framework for Multi-Agent Systems Based on Model Context Protocol in SOC Environments,” *Applied Sciences*, 16, 7915, 2026. DOI: 10.3390/app16167915.

### A. What the paper does

Simões et al. address the security risks created when LLM-based agents in a SOC can discover and invoke tools through the Model Context Protocol (MCP). The paper presents a security framework placed between agents and MCP servers. Its purpose is to constrain tool use and detect attacks such as tool-description poisoning, tool shadowing, indirect prompt injection, and confused-deputy behavior. [Simões, Abstract and Sections 1–3, pp. 1–15]

The operational example is a three-agent **triage–enrichment–response** pipeline connected to Wazuh. This makes the paper directly relevant to agentic SOC architecture. However, its principal research outcome is the security of MCP-mediated interactions, not the accuracy or reliability of alert disposition.

### B. Methodology

The architecture contains three sequential agents, persistent shared memory, a legitimate Wazuh MCP server, and a purpose-built malicious server. Each agent has a dedicated prompt, tool allowlist, and output schema. The response agent can propose a Wazuh rule, but cannot apply it without analyst review. [Simões, Section 3.1, pp. 5–7]

A unified middleware gateway examines tool registration and then enforces five execution layers: role-based access control, rate limiting, input validation, output validation, and audit logging. Session identifiers and namespaced memory reduce cross-session contamination. All agents use GPT-4o mini with temperature **0.1**. Wazuh 4.14.0, the framework, and the two MCP servers run in an isolated Vagrant/Docker laboratory. [Simões, Sections 3.2–3.3 and Table 4, pp. 7–17]

### C. Dataset and experimental setup

The study does not use a conventional machine-learning dataset. It derives **35** relevant attack vectors from agentic-AI and MCP taxonomies; **29** are addressed by the middleware. Six test suites contain **25 unique attack instances** and **30 block decisions per trial**. Twenty repetitions produce **600** block decisions, with attack cases paired to legitimate cases. A pipeline demonstration uses one live Wazuh alert and one synthetic SSH brute-force alert. Conventional training splits are not applicable because this is a deterministic security-control evaluation. [Simões, Sections 3.2.8, 3.4–3.5 and Tables 2, 5–11, pp. 12–23]

### D. Evaluation and main results

Every evaluated attack instance was blocked in all repetitions: **600/600** block decisions, **0** bypasses, and **0** false blocks among the paired legitimate cases. [Simões, Section 4.1 and Table 12, p. 23]

The authors separately test important boundary cases. All four obfuscation methods—base64 encoding, homoglyph substitution, Spanish translation, and paraphrase—evade the Layer 3 lexical scan: **0 of 4** payloads remain blocked under each method. In a test of eight benign SOC inputs containing attack-like text, **7 of 8** are incorrectly blocked. These results limit the earlier zero-false-block result to the harness's simpler legitimate cases. [Simões, Sections 4.4–4.5 and Tables 14–15, pp. 25–26]

The combined local cost of Layers 1–4 is below **0.6 ms**, or below **30 µs** with schema precompilation; these measurements exclude network and model-inference latency. The two-alert demonstration preserves decision-relevant outputs between secured and unsecured conditions, but does not establish whether those outputs are correct dispositions. [Simões, Sections 4.2–4.3 and Table 13, pp. 23–24]

### E. Author-stated limitations

The authors limit the findings to fixed, non-adaptive, clear-text payloads from one malicious server. The evaluation uses a sequential topology, one LLM, and a file-based memory store unsuitable for production concurrency. Six vectors remain uncovered, and the DNS-rebinding application check was inactive in the evaluated deployment. Proposed future work includes semantic detection, adaptive attacks, non-sequential topologies, more models, scalable memory, and stronger audit integrity. [Simões, Sections 4.4–6, pp. 25–29]

### F. Our critical observations

The explicit threat model and separate negative tests make the evaluation transparent. However, the repetitions reuse fixed deterministic payloads and are reproducibility checks, not independent evidence over a diverse attack population. A changed manifest is also counted as successful detection although the control raises a warning rather than rejecting it. The pipeline contains only two alert examples and has no labelled triage outcomes, competing triage baselines, evidence-quality manipulation, analyst evaluation, end-to-end latency, or token-cost analysis.

### G. Relevance to the proposed topic

The paper establishes that an agentic SOC pipeline needs controlled tool registration, least-privilege access, validated inputs and outputs, isolated memory, auditable provenance, and human approval for externally actionable proposals. These controls are relevant infrastructure for a safe evidence-grounded triage experiment.

### H. What the paper does not establish

The paper does not establish that three agents make more accurate alert decisions than one agent, that its triage output is evidence-grounded, or that criticism and adjudication improve decisions under incomplete or contradictory evidence. “Triage” is the first stage of the demonstrated pipeline, but the evaluation measures middleware attack blocking rather than triage reliability.

## 3. Paper 2 — Zhang et al.

**Bibliographic record:** Yiyao Zhang, Diksha Goel, and Hussain Ahmad, “Explainable Autonomous Cyber Defense Using Adversarial Multi-Agent Reinforcement Learning,” *Expert Systems with Applications*, 326, 132741, 2026. DOI: 10.1016/j.eswa.2026.132741.

### A. What the paper does

Zhang et al. propose the Causal Multi-Agent Decision Framework (C-MADF) for autonomous cyber defense under ambiguous or manipulated telemetry. The framework is intended to reduce unsafe or unnecessary mitigation caused by correlation-based decisions. [Zhang, Sections 1 and 5, pp. 1–14]

### B. Methodology

C-MADF learns a Structural Causal Model (SCM) from historical telemetry and converts it into an investigation-level MDP-DAG that restricts policy transitions. A threat-optimizing Blue-Team policy proposes actions, while a conservatively rewarded Red-Team policy challenges actions with insufficient support. Policy divergence contributes to an Explainability-Transparency Score (ETS), which governs autonomous action, further evidence collection, or human escalation. [Zhang, Sections 1 and 5, pp. 1–14]

Both policies use three-layer multilayer perceptrons with Double DQN, prioritized replay, target networks, and separately learned weights. The action space contains **18** high-level investigation and mitigation actions. Training uses **1.5 million steps per agent** and three random seeds. [Zhang, Section 5.3.1 and Table 10, pp. 10–12]

### C. Dataset and experimental setup

Evaluation uses CICIoT2023. The study maps several attack categories into a binary attack/benign decision space. Records are transformed into alert-summary, host, flow, and investigation-context features. Scenario-level train/validation/test separation is used, and scaling parameters are learned from training data only. Exact sample counts and split proportions are not clearly reported. The external baselines are DUGAT-LSTM, BiLSTM IDS, and Hybrid Weighted-XGBoost. [Zhang, Section 7.1, p. 17]

### D. Evaluation and main results

C-MADF reports precision **0.997**, recall **0.961**, F1 **0.979**, and FPR **1.8%**. The baseline FPRs are **11.2%**, **9.7%**, and **8.4%**. In the ablation study, removing the causal SCM produces precision **0.903**, recall **0.959**, F1 **0.930**, and FPR **59.4%**. Removing the Red Team produces **0.963**, **0.963**, **0.963**, and **21.2%**, respectively; removing the Blue Team produces **0.957**, **0.972**, **0.964**, and **25.1%**. Results are means over three seeds, with reported standard deviations below 0.02. [Zhang, Tables 12–13, pp. 18–19]

The paper reports that higher ETS values align with stronger causal support and lower policy disagreement, while lower values align with weaker evidence and greater disagreement. Exact correlation or calibration coefficients are not clearly reported. [Zhang, Section 7.5, p. 19]

### E. Author-stated limitations

The authors state that causal discovery depends on representative historical telemetry and that sustained poisoning requires further empirical study. They acknowledge additional inference overhead, possible shared blind spots between the policies, dependence on a predefined investigation ontology, and the absence of human-factor and live operational validation for ETS. They also state that one laboratory benchmark is insufficient to establish deployment readiness. [Zhang, Sections 8–8.3, pp. 19–20]

### F. Our critical observations

The paper is a strong conceptual match to the proposed direction, but its empirical scope is narrower than its framing. CICIoT2023 is a benchmark rather than an operational SOC alert queue. The binary attack/benign formulation removes distinctions that may matter for severity, priority, disposition, and investigative next steps. The external baselines are mainly intrusion-detection models, not competing triage systems with matched evidence access, verification, action constraints, and escalation logic. No analyst study, cross-dataset evaluation, cross-organization test, throughput measurement, or exact ETS calibration analysis is reported.

### G. Relevance to the proposed topic

Zhang contributes three useful ideas: evidence prerequisites can constrain investigation actions; a second policy can challenge premature decisions; and disagreement can trigger evidence collection or human escalation. These ideas support the verification and uncertainty components of the candidate direction.

### H. What the paper does not establish

The reported detection and FPR results do not establish improved prioritization or disposition in a heterogeneous SOC alert queue. They also do not establish that ETS improves analyst decisions. Triage-specific data, matched baselines, and triage outcomes would be required for those claims.

## 4. Paper 3 — Zhao et al. (Debapt)

**Bibliographic record:** Xinyun Zhao, Lanlan Qi, Yongheng Zhang, Yingxiao Guan, Guozheng Yang, Yuliang Lu, and Xiang Wang, “Debapt: Ontology-Driven Multi-Agent Debate for APT Adversary Profile Construction from Cyber Threat Intelligence,” *Computers & Security*, 170, 104988, 2026. DOI: 10.1016/j.cose.2026.104988.

### A. What the paper does

Zhao et al. study APT adversary-profile construction from unstructured cyber threat intelligence (CTI). They address omission, semantic drift, and hallucination when profile-relevant facts are distributed across long reports. The authors define the VICTOR ontology and implement Debapt as a two-phase entity- and relation-extraction workflow. [Debapt, Sections 1 and 4.2, pp. 1–6]

### B. Methodology

VICTOR organizes information into Victim, Infrastructure, Capability, TTPs, Originator, and Record. Entity extraction uses six ontology-aligned prompts. CritEn checks source-text support, ontology compliance, coverage, and structured identifiers. Regex validates IP, MAC, and CVE formats, while RAG validates ATT&CK identifier/name consistency. JdgEn accepts the entity set or requests targeted revision. ExtRe, CritRe, and JdgRe then propose, verify, and adjudicate STIX-compatible relations among verified entities. A moderator ends each phase after acceptance, absence of a valid correction, or a five-round limit. [Debapt, Sections 4.2–4.3.3, pp. 4–7]

A vector database and RAG support cross-report aggregation. Corroborating evidence raises a candidate fact's confidence, whereas conflicting evidence lowers confidence and marks the fact as risky. [Debapt, Section 4.3.4, p. 7]

### C. Dataset and experimental setup

The authors re-annotate CTINexus, STIXnet, and LLM4CTI under VICTOR. Three graduate annotators generate LLM-assisted drafts and manually review, correct, and complete them; a fourth graduate researcher arbitrates disagreements. Fleiss's kappa is **0.79**. The resulting annotations contain **4,915 deduplicated entities** and **5,736 relations**. Each dataset is divided **6:2:2** into training, validation, and test sets. The total document count and per-dataset label distributions are not clearly reported. [Debapt, Section 5.1.1, p. 8]

### D. Evaluation and main results

Using thinking-enabled qwen-plus by default, Debapt reports entity F1-micro values of **0.8213**, **0.7684**, and **0.8007** for CTINexus, STIXnet, and LLM4CTI. Relation F1-micro values are **0.8197**, **0.8886**, and **0.8286**. [Debapt, Tables 1–2, p. 9]

Removing CritEn reduces entity F1-micro from **0.8213** to **0.5897**, entity F1-macro from **0.7986** to **0.5398**, relation F1-micro from **0.8197** to **0.7435**, and relation F1-macro from **0.7944** to **0.6450**. [Debapt, Table 4, p. 11]

Across five rounds, the hallucination count falls from **107** to **13**, an approximately **87.9%** reduction. The hallucination ratio falls from **0.1080** to **0.0124**, an approximately **88.5%** reduction. [Debapt, Section 5.6.1, pp. 11–12]

### E. Author-stated limitations

The authors identify reports describing multiple APT actors as a future challenge. [Debapt, Section 6, p. 16] The paper does not provide a dedicated limitations section.

### F. Our critical observations

Debapt's gold annotations are reconstructed under VICTOR, which also guides the proposed method. This is not inherently a methodological error, but it means the results establish performance on a VICTOR-aligned task rather than performance independent of that ontology. Document counts, per-dataset class distributions, actor- or source-disjoint testing, repeated-run uncertainty, inference latency, and token cost are not clearly reported. LLM-assisted annotation and an LLM-based weak semantic matcher may introduce model-mediated bias. Most roles use the same underlying model family, so prompt specialization does not guarantee independent failure modes. The termination study also shows an operational boundary: relation extraction reaches the five-round maximum for three of five long excerpts. [Debapt, Table 6, p. 12]

### G. Relevance to the proposed topic

Debapt provides the strongest methodological inspiration for explicit evidence verification. Its extractor–critic–adjudicator separation, source-text checks, deterministic validation, retrieval-assisted verification, bounded iteration, and conflict-aware aggregation show how checking can be made a visible stage rather than left inside one model response.

### H. What the paper does not establish

Debapt evaluates CTI entity/relation extraction and APT profiling, not security-alert triage. Its extraction F1 and hallucination reductions do not establish more accurate alert disposition, prioritization, useful abstention, or better analyst decisions. Those outcomes require a triage-specific evaluation.

## 5. Cross-Paper Comparison

| # | Title | Year of Publication | Dataset Used | Preprocessing Techniques | Models / Techniques Used | Evaluation Metrics Used | Results | Limitations / Research Gap |
|---:|---|---:|---|---|---|---|---|---|
| 1 | Simões et al., *Design of a Security Framework for Multi-Agent Systems Based on Model Context Protocol in SOC Environments* | 2026 | No conventional ML dataset; 35-vector threat model, six suites, 25 attack instances, 600 block decisions; one live Wazuh alert and one synthetic SSH alert | Threat-vector selection and control mapping; attack-payload catalog; JSON Schema validation; trust-domain isolation | Sequential triage, enrichment, and response agents; GPT-4o mini; Wazuh; MCP gateway; registration validation; RBAC; rate limiting; input/output validation; audit logging | Attacks blocked/passed; false blocks; legitimate calls passed; local processing time; obfuscation detection | 600/600 decisions blocked, 0 bypasses, 0 false blocks in paired harness cases; all tested obfuscations reduced Layer 3 detection to 0/4; 7/8 attack-like benign inputs falsely blocked | Fixed non-adaptive payloads; lexical evasion and false positives; one LLM; sequential topology; two-alert demonstration; no labelled alert-triage accuracy or adjudication comparison |
| 2 | Zhang et al., *Explainable Autonomous Cyber Defense Using Adversarial Multi-Agent Reinforcement Learning* | 2026 | CICIoT2023; exact sample count and split ratios not clearly reported | Scenario-separated partitions; alert/host/flow/context aggregation; training-only scaling; binary attack/benign mapping | SCM; MDP-DAG; Double-DQN Blue/Red policies; policy divergence; ETS | Precision, recall, F1, FPR; three-seed variation; ETS behavior | C-MADF: 0.997 precision, 0.961 recall, 0.979 F1, 1.8% FPR; ablations increase FPR to 59.4%, 21.2%, and 25.1% | Single IoT benchmark; binary task; IDS-style baselines; no direct operational alert-triage or analyst evaluation |
| 3 | Zhao et al., *Debapt: Ontology-Driven Multi-Agent Debate for APT Adversary Profile Construction from Cyber Threat Intelligence* | 2026 | Re-annotated CTINexus, STIXnet, and LLM4CTI; 4,915 entities and 5,736 relations; document count not clearly reported | VICTOR mapping/filtering; annotation completion; mention merging; JSON triples; 6:2:2 split; BIO conversion | VICTOR; entity/relation extractors, critics, adjudicators, moderator; regex; RAG/vector database | Entity/relation micro, macro, and weighted F1; hallucination count/ratio; ablation; length and termination analysis | Entity F1-micro: 0.8213/0.7684/0.8007; relation F1-micro: 0.8197/0.8886/0.8286; hallucination count 107 to 13 | VICTOR-aligned ground truth; CTI profiling rather than alert triage; no analyst outcomes, repeated-run uncertainty, or cost/latency analysis |

### What is common?

All three papers organize cyber-defense work across specialized components or agents, impose some form of constraint on model or policy behavior, and evaluate a defined implementation rather than presenting only a conceptual architecture. Each also acknowledges that laboratory evidence does not establish production-wide generalizability.

### What is different?

The studies evaluate different tasks and their metrics are not interchangeable. Simões evaluates the security of MCP tool mediation in a SOC pipeline. Zhang evaluates binary IoT intrusion decisions and autonomous policy constraints. Debapt evaluates CTI entity/relation extraction and APT profiling. Only Simões operates in an explicitly labelled SOC pipeline, but its “triage” stage is not evaluated with ground-truth alert dispositions. Zhang provides evidence-sensitive decision constraints but uses IDS-style benchmarks and baselines. Debapt directly evaluates criticism and adjudication, but only for ontology-guided CTI extraction.

### What is well studied within these papers?

The selected papers provide substantial evidence for component-level mechanisms: middleware security controls against fixed MCP attacks, causal/adversarial policy constraints for binary intrusion decisions, and critic/adjudicator roles for source-grounded CTI extraction.

### What is only partially studied?

Evidence validation, disagreement, human escalation, operational cost, and generalization are each considered in at least one paper, but not as a unified alert-triage evaluation. The evidence is therefore transferable as design motivation, not as direct proof that the proposed triage mechanism will work.

### What is missing from the selected literature?

The three reviewed studies do not directly compare a single-agent RAG triager with a matched proposer–critic–adjudicator triager under controlled complete, incomplete, and contradictory evidence. This is a gap in the selected literature only. It is not yet a proven gap in the broader field.

## 6. Research-Gap Synthesis

The following gaps are derived from the three selected papers. A difference in research task is not automatically a defect in a paper; it limits what that paper's results can establish for the proposed alert-triage problem.

| Research Gap | Evidence from Paper 1 | Evidence from Paper 2 | Evidence from Paper 3 | Proposed Research Opportunity |
|---|---|---|---|---|
| **1. Evidence-grounded alert disposition is not directly evaluated in the three studies.** | Uses a SOC triage stage, but evaluates MCP attack blocking and output preservation rather than labelled alert dispositions or evidence support. | Evaluates binary IoT attack/benign decisions and abstract investigation actions rather than an operational alert queue. | Evaluates CTI extraction and APT profiling rather than alert disposition. | Evaluate disposition or abstention on labelled alert cases with traceable supporting evidence. |
| **2. Incomplete and contradictory evidence is not controlled as an experimental factor in alert decisions.** | Tests malicious tool content and memory isolation, not systematic evidence removal or contradiction in triage cases. | Relates ETS to causal support and disagreement, but does not compare triage outcomes across controlled evidence-completeness conditions. | Marks conflicting CTI facts as risky, but does not measure their effect on alert disposition. | Construct complete, incomplete, and contradictory evidence conditions and measure errors, contradiction detection, confidence, and abstention. |
| **3. Explicit criticism and adjudication are not evaluated as mechanisms for improving alert-disposition reliability.** | Uses sequential functional agents and deterministic security checks, not a critic and adjudicator comparing alert conclusions. | Uses an adversarial policy and role ablations, but outcomes are benchmark detection rather than matched alert triage. | Ablates critics and adjudicators for CTI extraction, not security-alert decisions. | Compare matched single-agent RAG, proposer-only, and proposer–critic–adjudicator variants on the same alert cases and evidence. |
| **4. Decision quality, grounding, uncertainty, and operational cost are not jointly evaluated.** | Reports security blocking and middleware overhead, but not disposition correctness, grounding, calibration, or full agent cost. | Reports detection metrics and policy behavior, but no citation correctness, unsupported-claim rate, or calibrated abstention analysis. | Reports extraction F1 and hallucination counts, but not triage correctness, calibration, latency, or token cost. | Evaluate a limited set of complementary decision, grounding, uncertainty, and cost measures rather than treating F1 alone as reliability. |

The first gap defines the target task. The second defines the controlled evidence conditions. The third identifies the mechanism to be tested. The fourth specifies why several outcome categories are needed. Together they lead to one bounded empirical opportunity rather than four unrelated projects.

## 7. Proposed Research Opportunity

### Empirical question, not architectural novelty

The proposed contribution is an empirical test of explicit evidence verification and adjudication. The architecture itself is not presented as novel.

**Matched baseline**

> Alert → same retrieval → single-agent RAG → disposition + cited evidence

**Proposed mechanism**

> Alert → same retrieval → proposer → critic → adjudicator → disposition or abstention

Both systems should receive the same alert fields, evidence-retrieval process, retrieval corpus, and evidence budget. The underlying language model should be identical or comparable where practical. Model calls, token use, retrieved context, latency, and other computational differences must be reported. Without these controls, an apparent improvement might result from giving the multi-agent system more computation rather than from verification or adjudication.

### Candidate Phase 2 evidence conditions

1. **Complete evidence:** all case evidence defined by the experimental protocol is available.
2. **Incomplete evidence:** relevant items are withheld according to a documented rule.
3. **Contradictory evidence:** mutually inconsistent items are introduced while their provenance remains visible.

These are proposed experimental conditions, not a validated methodology. Their construction, realism, and labelling procedure must be defined in Phase 2.

### Candidate evaluation measures

The final experiment need not implement every measure. A feasible subset should be chosen after the alert dataset and annotation scheme are confirmed.

**Decision quality**

- Disposition F1, precision, recall, and false-positive rate measure whether alert decisions are correct and how often benign activity is unnecessarily escalated.

**Grounding quality**

- Evidence-citation correctness measures whether a cited item supports the associated claim.
- Unsupported-claim rate measures conclusions not justified by the supplied evidence.
- Contradiction detection measures whether incompatible evidence is recognized rather than silently ignored.

**Uncertainty handling**

- Calibration measures whether stated confidence corresponds to observed correctness.
- Abstention and risk–coverage measure the trade-off between deciding more cases and limiting error among decided cases.

**Operational cost**

- End-to-end latency and token or computational cost measure the overhead of verification and adjudication.

Decision metrics alone cannot identify unsupported reasoning. Grounding metrics alone cannot determine whether the final disposition is correct. Calibration and abstention matter because a system should defer when evidence is insufficient. Cost measures are necessary because the proposed system makes more model calls than the baseline.

### Candidate hypotheses

These hypotheses are provisional and should be refined after selecting the dataset, disposition labels, and primary metrics.

- **H1:** Explicit evidence verification and multi-agent adjudication improve security-alert disposition performance compared with a matched single-agent RAG baseline.
- **H2:** Explicit evidence verification reduces unsupported or incorrectly grounded reasoning.
- **H3:** Adjudication improves calibration or appropriate abstention when evidence is incomplete or contradictory.
- **H4:** The proposer–critic–adjudicator mechanism introduces measurable latency and token-cost overhead relative to the matched single-agent baseline.

The hypotheses are falsifiable. A finding of no improvement, worse performance, or an unfavorable reliability–cost trade-off would still answer the research question.

### Broader literature check required before final novelty claim

The three selected papers motivate this mechanism-focused question but do not represent the complete literature on SOC alert triage, agentic RAG, evidence verification, debate, or selective prediction. Before Phase 2, a targeted literature search must determine whether equivalent matched comparisons already exist and refine the claimed contribution accordingly.

## 8. Short Conclusion

The comparison shows why the project should move from the broad idea of a multi-agent SOC to a narrower empirical question. Simões et al. demonstrate a secured MCP-based triage–enrichment–response pipeline, but their evaluation concerns middleware attacks rather than triage accuracy. Zhang et al. demonstrate causal constraints, adversarial policy review, and evidence-sensitive escalation, but evaluate a binary intrusion task on one IoT benchmark. Debapt demonstrates source grounding, criticism, adjudication, and RAG-assisted validation, but evaluates CTI extraction and APT profiling under the VICTOR ontology.

The papers therefore establish useful components, not proof that multi-agent adjudication improves alert triage. The defensible Phase 1 outcome is a candidate question: whether explicit evidence verification and adjudication improve reliable alert disposition over a matched single-agent RAG baseline, especially when evidence is incomplete or contradictory. The question is bounded, measurable, and falsifiable. It remains feasible for a semester project only if Phase 2 restricts the alert type, evidence corpus, manipulation protocol, and primary metrics.

## 9. Pre-Submission Verification Items

1. **Journal quartiles:** confirm all three journals in the ranking system and category accepted by the instructor. The MCP paper's journal is currently JCR Q2 but CiteScore Q1 in selected categories; written instructor approval may be necessary. **[Verification required]**
2. **Page references:** verify the displayed PDF page numbers against the copies submitted with the report. **[Verification required]**
3. **Final Phase 2 choices:** the alert dataset, evidence corpus, manipulation protocol, disposition labels, and primary metrics are proposals and are not yet established by the reviewed papers.

## 10. Change Note

- Rebuilt the report around Simões et al., Zhang et al., and Zhao et al. in the assignment's required three-paper pattern.
- Kept intrusion detection, MCP security, CTI extraction, APT profiling, and SOC alert triage conceptually distinct.
- Reconstructed the comparison table with the exact required columns and the research-gap table with evidence from each selected paper.
- Framed the proposed contribution as a matched empirical comparison rather than a novel architecture.
- Preserved uncertainty about Q1 compliance instead of asserting unsupported status.
