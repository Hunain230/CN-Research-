# Research Gaps

## Scope statement

The claims below are limited to the three reviewed papers. They do **not** establish that the wider literature has no solution. The defensible wording is: **the three reviewed papers do not directly address** the stated gap.

## Evidence table

| Research Gap | Evidence from Paper 1 | Evidence from Paper 2 | Evidence from Paper 3 | Proposed Research Opportunity |
|---|---|---|---|---|
| 🟢 **Strong - Operational evidence-grounded alert triage is not directly evaluated** | Binary CICIoT2023 detection plus abstract decision states; no alert queue/case benchmark. [Zhang, Section 7.1, p. 17] | Traffic detection and cyber-range response; no analyst alert dispositions. [Agrawal, pp. 14-17] | CTI entity/relation extraction and APT profiles; no SIEM/EDR alerts. [Debapt, Sections 5.1-5.7, pp. 7-13] | Build a bounded triage task where agents must rank/disposition alerts and cite the exact evidence used. Compare against single-agent and rule baselines. |
| 🟢 **Strong - Multi-agent disagreement is not calibrated against analyst decisions or operational harm** | ETS is aligned with internal evidence/policy signals, but human factors and downstream outcomes are future work. [Zhang, Section 8.3, p. 20] | Expert acceptance is summarized, while explanations, overrides, and response correctness are not measured. [Agrawal, Table 13, p. 17] | No analyst evaluation; F1 measures extraction match, not whether profiles improve decisions. [Debapt, Sections 5-6, pp. 7-16] | Test whether critic disagreement predicts triage errors and whether escalation improves analyst accuracy/time without excessive handoffs. |
| 🟢 **Strong - CTI evidence is not linked end-to-end to alert disposition and safe response** | Causal telemetry constrains actions, but CTI enrichment/provenance is not used. | Detection triggers predefined response rules; evidence provenance and CTI-based reasoning are absent. [Agrawal, p. 17] | CTI facts are grounded and aggregated, but are not connected to alert severity, disposition, or response. | Evaluate a provenance-preserving bridge from CTI facts and local telemetry to alert decisions, with abstention when sources conflict. |
| 🟢 **Strong - Generalization is not tested across organizations, time, and alert-generation systems** | One laboratory IoT benchmark; authors call external validity open. [Zhang, pp. 19-20] | Two old traffic datasets are merged into one cyber range; scenarios confound size and complexity. | Three CTI datasets broaden text types but remain under one ontology and task; actor/source-disjoint testing is unreported. | Use time- or environment-separated evaluation and report performance/calibration decay under new rules, assets, and attack distributions. |
| 🟡 **Needs refinement - Quality/latency trade-off of multi-agent reasoning is undermeasured** | Deliberation overhead is acknowledged, but throughput/latency are not reported. [Zhang, Sections 8.2-8.3, p. 20] | Response latency is reported, but the defender does not use a comparable debate workflow. | Five-round debate is bounded, but token cost, wall time, and marginal quality per round are not reported. | Measure accuracy, grounding, latency, token/compute cost, and escalation rate by agent count and debate rounds under a fixed budget. |

## Why each gap matters

### 1. Operational evidence-grounded triage - 🟢 Strong

### OUR OBSERVATION

Alert triage is the proposed topic's central task. Detection, CTI extraction, and response are adjacent but cannot substitute for evaluating prioritization, disposition, and investigation decisions. A triage-specific benchmark makes the project research rather than a loose integration of the three papers.

### 2. Analyst-calibrated disagreement - 🟢 Strong

### OUR OBSERVATION

Multi-agent disagreement is only useful if it identifies risky decisions better than ordinary confidence measures and if escalation improves outcomes. Otherwise, debate may add cost and produce persuasive but unhelpful explanations.

### 3. CTI-to-alert provenance chain - 🟢 Strong

### OUR OBSERVATION

Debapt demonstrates source-grounded CTI extraction, while Zhang demonstrates constrained action reasoning. Connecting these carefully could test whether external intelligence materially improves alert triage while preserving traceability and abstaining on conflict.

### 4. Cross-environment generalization - 🟢 Strong

### OUR OBSERVATION

SOC data changes across organizations, tools, rules, and time. A system that memorizes dataset-specific patterns can look strong on random splits while failing on the next environment. This is a methodological gap, not a claim that the wider literature lacks generalization studies.

### 5. Quality/cost frontier - 🟡 Needs refinement

### OUR OBSERVATION

This matters operationally, but it becomes a research gap only if tied to a precise hypothesis, such as whether evidence-specialized critics improve grounded triage accuracy per unit latency more than additional single-agent sampling.

