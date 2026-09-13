# Research Relevance

## What Debapt contributes

### AUTHOR CLAIM

Debapt operationalizes evidence grounding through source checks, deterministic validation, RAG verification, ontology constraints, reviewer feedback, adjudication, moderator-controlled termination, and cross-source confidence adjustment. [Debapt, Sections 3-4.3, pp. 3-7]

### OUR OBSERVATION

For **Evidence-Grounded Multi-Agent Reasoning for Security Alert Triage**, Debapt provides the most transferable role design:

- specialized extractors gather different evidence categories;
- critics check provenance, coverage, semantic validity, redundancy, and conflict;
- adjudicators decide whether evidence is sufficient;
- a moderator limits unproductive iteration;
- RAG and a vector database retain supporting sources;
- cross-source corroboration/conflict changes confidence.

This pattern could be adapted to alerts if VICTOR is replaced with a triage schema covering alert identity, rule provenance, affected assets/users, event timeline, corroborating telemetry, CTI, severity, disposition, and recommended next action.

## What Debapt does not address

### OUR OBSERVATION

- It does not ingest SIEM/EDR/NDR alerts or prioritize alert queues.
- It does not determine true/false positive disposition or incident severity.
- It does not reconstruct incidents from heterogeneous alert streams.
- It does not select or evaluate response actions.
- It does not measure analyst time, queue reduction, missed critical alerts, or triage calibration.
- It does not test noisy, contradictory, incomplete, or adversarial operational telemetry beyond CTI-text extraction errors.

## Domain distinction

Debapt performs **cyber threat intelligence extraction and APT adversary profiling**. Those profiles may enrich an investigation, but profiling an actor from reports is not the same task as triaging security alerts. Its evidence-review architecture is relevant; its reported F1 scores do not transfer directly to alert-triage effectiveness.

