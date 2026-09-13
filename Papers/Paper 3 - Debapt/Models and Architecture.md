# Models and Architecture

## Default model configuration

### AUTHOR CLAIM

Debapt uses qwen-plus in thinking-enabled mode by default, with a maximum of five iterations, temperature 0.2, maximum output length 8,192 tokens, and a fixed random seed. Python 3.11.14 is used. Open-source models run on Alibaba Cloud ECS, while commercial models use official Alibaba Cloud APIs. [Debapt, Section 5.1.3, p. 8]

## Model-variation study

### AUTHOR CLAIM

The framework is evaluated with qwen2.5-7b/14b/32b/72b-instruct, qwq-32b, deepseek-r1, qwen-turbo, qwen-plus (non-thinking), qwq-plus, and qwen-plus (thinking-enabled). [Debapt, Table 3, p. 10]

Selected exact aggregate results:

| Backbone | Entity F1 micro/weighted/macro | Relation F1 micro/weighted/macro |
|---|---|---|
| qwen2.5-7b-instruct | 0.6115 / 0.5581 / 0.6123 | 0.7367 / 0.7222 / 0.7185 |
| qwen2.5-72b-instruct | 0.7741 / 0.7545 / 0.7811 | **0.8837 / 0.8666 / 0.8665** |
| qwq-32b | 0.8139 / 0.8004 / 0.8264 | 0.8229 / 0.7910 / 0.8222 |
| deepseek-r1 | 0.8125 / 0.7974 / **0.8275** | 0.8627 / 0.8499 / 0.8653 |
| qwen-plus, thinking | **0.8213 / 0.8186** / 0.7986 | 0.8197 / 0.8199 / 0.7944 |

Source: [Debapt, Table 3, p. 10]

## Evidence controls

### AUTHOR CLAIM

- Source-text evidence is checked for every candidate.
- Regex is used for structured observables and CVE identifiers.
- RAG checks ATT&CK identifier/name consistency.
- Ontology and STIX relation semantics constrain type and relation choices.
- Exact-string requirements reduce mutation of precise indicators.
- Reviewer feedback drives targeted revision; adjudicators gate phase transitions.

[Debapt, Sections 3-4.3, pp. 3-7; Appendix D, p. 18]

## Reasoning structure

### OUR OBSERVATION

The system's “debate” is a structured workflow rather than free-form argument: extractor outputs are tested against evidence and schema by critics, then adjudicated. This makes provenance and validation roles clearer than a group of identical agents voting on an answer.

However, most roles use the same underlying backbone and prompt-defined specialization. Agent diversity therefore reflects role instructions more than independently trained models or evidence sources.

