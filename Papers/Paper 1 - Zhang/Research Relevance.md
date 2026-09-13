# Research Relevance

## What Zhang contributes

### AUTHOR CLAIM

Zhang provides a concrete architecture for grounding autonomous security decisions in learned causal structure, constraining action sequences, using an adversarial second policy to challenge proposed actions, and escalating uncertainty with an interpretable score. [Zhang, Sections 1 and 5, pp. 1-14]

### OUR OBSERVATION

For **Evidence-Grounded Multi-Agent Reasoning for Security Alert Triage**, the most useful foundations are:

- evidence prerequisites encoded as allowed investigation transitions;
- explicit separation between a proposing policy and a skeptical policy;
- disagreement as an uncertainty signal;
- an audit-oriented interface exposing supporting and contradicting evidence;
- a three-way governance pattern: act, collect more evidence, or escalate;
- component ablations that attempt to test whether grounding and internal challenge matter.

These mechanisms could be adapted to alert triage if the states, evidence objects, actions, and evaluation targets are redesigned for SOC alerts rather than network-flow classification.

## What Zhang does not address

### OUR OBSERVATION

- It does not directly evaluate ranking or prioritizing a queue of security alerts.
- It does not group related alerts into incidents or reconstruct an investigation timeline from heterogeneous tools.
- It does not ground decisions in alert provenance, SIEM rules, endpoint evidence, asset/identity context, CTI citations, or analyst case histories.
- It does not measure triage precision, top-k priority quality, analyst agreement, time saved, or missed-high-severity incidents.
- It does not establish transfer from CICIoT2023 to live SOC operations.

## Domain distinction

The evaluated task is principally **network intrusion detection / binary traffic classification with a decision-support layer**. SOC alert triage begins after security controls produce alerts and requires prioritization, contextualization, investigation, and disposition. Therefore, Zhang is methodologically relevant but not direct evidence that multi-agent reasoning improves alert triage.

