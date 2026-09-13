# Dataset and Preprocessing

## Datasets

### AUTHOR CLAIM

- **DS1 - CTINexus:** cybersecurity news briefs and security-bulletin summaries; relatively short CTI reports.
- **DS2 - STIXnet:** descriptions of APT groups and threat actors; organization-centered CTI.
- **DS3 - LLM4CTI:** complete technical-analysis blogs and threat-analysis reports; longer context and cross-sentence associations.

All are public datasets derived from real-world CTI reports. [Debapt, Section 5.1.1, pp. 7-8]

## Annotation and preprocessing

### AUTHOR CLAIM

Because the original labels do not match VICTOR, the authors reconstruct a unified ground truth:

1. map original entities/relations to VICTOR and remove out-of-scope items;
2. add explicitly stated entities missed by original annotations;
3. group by type and merge mentions of the same concept; and
4. annotate semantic relations as JSON triples.

[Debapt, Section 5.1.1, p. 8]

Three graduate annotators (two master's students and one PhD student) independently use LLM-assisted pre-annotation and manually review/correct/complete their drafts. A fourth PhD student arbitrates disagreements. Fleiss's kappa is 0.79. The resulting corpus contains 4,915 deduplicated entities and 5,736 relations. [Debapt, Section 5.1.1, p. 8]

Each dataset is split 6:2:2 into train, validation, and test and converted to BIO format for supervised baselines. LLM-based methods use the common test set; test labels are excluded from training, tuning, prompts, and exemplar selection. [Debapt, Sections 5.1.1 and 5.1.3, p. 8]

## Dataset size and labels

### AUTHOR CLAIM

- The total number of source documents and per-dataset entity/relation counts are **not clearly specified**.
- Entity types and relation types follow VICTOR and STIX-compatible semantic guidance; full definitions appear in the appendices.

[Debapt, Section 5.1.1, p. 8; Appendices A-C, pp. 16-19]

## Evaluation matching

### AUTHOR CLAIM

Entity evaluation first uses case-insensitive exact matching and then a weak semantic-matching prompt for equivalent expressions; uncertain cases are non-matches. Relation labels use case-insensitive exact matching only. Metrics are computed per document and aggregated as micro, macro, and weighted F1. [Debapt, Appendix E, pp. 18-19]

## Dataset limitations

### OUR OBSERVATION

- Gold labels are reconstructed specifically under VICTOR, so the evaluation favors compliance with the ontology being proposed; an independent alternative schema is not tested.
- LLM-assisted draft annotation and an LLM-based semantic matcher may introduce model-mediated bias even though humans verify labels.
- The paper reports aggregate entity/relation totals but not document counts or per-dataset distributions, limiting assessment of class imbalance and statistical power.
- A random 6:2:2 split may allow documents from related actors, campaigns, or publishers to occur across partitions; actor/source-disjoint splitting is not reported.
- All three datasets are CTI text corpora, so results do not establish transfer to SIEM/EDR alerts, telemetry timelines, or incident tickets.

