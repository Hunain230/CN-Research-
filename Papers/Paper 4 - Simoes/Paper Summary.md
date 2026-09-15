# Paper 4 - Critical Summary

## Bibliographic information

- **Title:** *Design of a Security Framework for Multi-Agent Systems Based on Model Context Protocol in SOC Environments*
- **Authors:** Rodrigo Tavares de Pina Simões, Xavier Larriva-Novo, Carmen Sánchez-Zas, Victor A. Villagrá, and Andrés I. Marín López
- **Journal:** *Applied Sciences*, volume 16, article 7915
- **Year:** 2026
- **DOI:** 10.3390/app16167915
- **Publication date:** 8 August 2026

Source: [Simões, title page, p. 1]

## Research problem

### AUTHOR CLAIM

MCP-based multi-agent SOC systems expose security risks at tool registration, tool invocation, server responses, shared memory, and inter-agent handoffs. Agents with broad tool access may be affected by tool-description poisoning, tool shadowing, indirect prompt injection, confused-deputy behavior, and related attacks. Existing architectural proposals do not by themselves provide an implemented and experimentally evaluated middleware defense for this setting. [Simões, Abstract and Sections 1-2, pp. 1-5]

## Research objective

### AUTHOR CLAIM

The authors design and evaluate a model-independent security gateway for MCP-based multi-agent SOC deployments. It combines connection-time tool validation with five runtime layers: access control, rate limiting, input validation, output validation, and audit logging. The framework is demonstrated in a Wazuh-connected triage-enrichment-response pipeline. [Simões, Abstract and Sections 3-4, pp. 1, 5-26]

## Main findings

### AUTHOR CLAIM

Across six suites containing 25 unique attack instances repeated 20 times, the framework records **600/600** correct block decisions, **0** attack bypasses, and **0** false blocks among the harness's paired legitimate cases. [Simões, Section 4.1 and Table 12, p. 23]

The result is deliberately bounded. Four tested obfuscation methods reduce Layer 3 detection from **4/4** clear-form payloads to **0/4** under each method. Seven of eight benign SOC inputs containing attack-like substrings are falsely blocked. [Simões, Sections 4.4-4.5 and Tables 14-15, pp. 25-26]

## Critical assessment

### OUR OBSERVATION

The paper provides a concrete and security-conscious agentic SOC implementation, with an explicit threat model and useful negative tests. However, its evaluation concerns middleware enforcement, not the correctness of SOC alert dispositions. The full pipeline is demonstrated with only one live Wazuh alert and one synthetic SSH alert, without ground-truth triage labels or competing triage systems. Therefore, the paper directly informs how a future triage experiment should protect tools, memory, and handoffs, but it does not establish that multiple agents improve alert-triage reliability.

## Q1 selection warning

The paper is a 2026 journal research article. The publisher currently lists *Applied Sciences* as JCR Q2 in Engineering (Multidisciplinary), while reporting CiteScore Q1 in selected categories. Whether it satisfies the assignment depends on the ranking system and category accepted by the instructor. **[Verification required]**

See [[Methodology]], [[Dataset and Preprocessing]], [[Models and Architecture]], [[Evaluation and Results]], [[Limitations]], and [[Research Relevance]].

