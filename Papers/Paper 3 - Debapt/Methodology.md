# Methodology

## Problem formulation

### AUTHOR CLAIM

For each CTI report, Debapt produces a document-level profile consisting of ontology-typed entity instances and semantic relation triples. An entity or relation is retained only if supported by source-text evidence and compatible with VICTOR/STIX semantic guidance. [Debapt, Section 3, pp. 3-4]

## VICTOR ontology

### AUTHOR CLAIM

VICTOR organizes APT profile information into six dimensions:

- **Victim:** targeted entities and attributes;
- **Infrastructure:** resources supporting campaigns;
- **Capability:** attacker tools and technical capabilities;
- **TTPs:** tactical and technical behavior;
- **Originator:** threat actors and background attributes;
- **Record:** temporal information about activity and disclosure.

[Debapt, Section 4.2, Fig. 2, pp. 4-6]

VICTOR aligns fields with representative STIX objects and MITRE ATT&CK concepts. Its type-level relation hints are soft semantic guidance rather than rigid graph constraints. [Debapt, Sections 3 and 4.2, pp. 3-6; Appendices B-C, pp. 16-19]

## Entity debate loop

### AUTHOR CLAIM

- **ExtEn:** six ontology-aligned extraction prompts, one per VICTOR dimension, improve coverage and reduce cross-dimension interference.
- **CritEn:** checks source evidence, ontology compliance, coverage, and formal validity. Regex validates IP/MAC/CVE forms; RAG validates ATT&CK technique identifier legality and name-ID consistency.
- **JdgEn:** accepts the current entity set or returns targeted feedback for another extraction round.

[Debapt, Section 4.3.1, pp. 6-7]

## Relation debate loop

### AUTHOR CLAIM

- **ExtRe:** proposes relations among verified entities using context and STIX relation-schema guidance.
- **CritRe:** checks textual support, relation type/direction, endpoint compatibility, entity coverage, redundancy, and conflicts.
- **JdgRe:** accepts the relation set or returns evidence and feedback for targeted revision.

[Debapt, Section 4.3.2, p. 7]

## Moderator and termination

### AUTHOR CLAIM

The moderator does not extract facts. It passes context, tracks unresolved disputes, controls rounds, and terminates a phase when adjudication accepts, the maximum round count is reached, or further iterations yield no valid/substantive correction. The default maximum is five rounds. [Debapt, Sections 4.3 and 4.3.3, pp. 6-7; Section 5.1.3, p. 8]

## Profile aggregation and RAG/vector database

### AUTHOR CLAIM

Document-level profiles can be aggregated around a threat-actor node. Supporting documents are indexed in a vector database; RAG retrieves semantically related cross-report evidence. Corroboration raises a candidate fact's confidence, while conflict lowers confidence and marks the fact risky. [Debapt, Section 4.3.4, p. 7]

## Baselines

### AUTHOR CLAIM

- **Supervised:** BERT, SecureBERT, BERT-CRF, BERT-BiLSTM-CRF, BiLSTM, BiLSTM-CRF, and Extractor.
- **LLM-based:** ICL, CoT, CTIKG, CTINexus, and AttacKG+.

[Debapt, Section 5.1.2, p. 8]

## Ablations

### AUTHOR CLAIM

The study removes ExtEn-Team, CritEn, CritRe, or both adjudicators (JdgEn and JdgRe) and measures changes to entity and relation F1. [Debapt, Section 5.4, Tables 4, pp. 10-11]

