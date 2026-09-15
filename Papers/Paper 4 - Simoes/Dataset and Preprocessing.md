# Dataset and Preprocessing

## Data sources

### AUTHOR CLAIM

The study does not use a conventional labelled machine-learning dataset. Its evaluation material consists of:

- a literature-derived threat model containing **35** middleware-addressable vectors;
- six test suites with **25** unique attack instances;
- **30** block decisions per trial, repeated for **20** trials, producing **600** decisions;
- paired legitimate operations for each tested surface;
- one alert retrieved live from Wazuh; and
- one synthetic SSH brute-force alert used in the full-pipeline demonstration.

[Simões, Sections 3.2.8, 3.4-3.5 and 4.2, pp. 12-24]

## Attack-payload preparation

### AUTHOR CLAIM

Threat vectors are selected for architectural relevance, empirical grounding, and SOC applicability, then mapped to specific framework controls and test-harness subtests. Payloads are described by structure and intent. They cover malicious tool metadata, name collisions, manifest or binary changes, unauthorized tool calls, request bursts, poisoned arguments or memory, invalid handoffs, malicious response content, trust manipulation, and cross-session access. [Simões, Sections 3.2.8 and 3.5, Tables 5-11, pp. 12-23]

The main harness uses fixed, literal payloads. A separate robustness test transforms four injection payloads using base64 encoding, Cyrillic homoglyphs, Spanish translation, and paraphrase. Another test supplies eight benign SOC strings containing attack-like surface patterns. [Simões, Sections 4.4-4.5 and Tables 14-15, pp. 25-26]

## Validation and splitting

### AUTHOR CLAIM

JSON Schema validation is configured for all 16 Wazuh tools. Agent inputs and server outputs are scanned using channel-specific lexical patterns. Because the framework controls are deterministic and no model is trained on the attack cases, train/validation/test splits and class labels are not applicable. The 20 repetitions test decision stability and expose legitimate cases to model variation; the authors explicitly state that repetitions are not independent samples and do not increase statistical power. [Simões, Sections 3.3-3.4, pp. 16-18]

## Data limitations

### AUTHOR CLAIM

- The malicious server is purpose-built and does not capture the variability of adaptive real-world attackers.
- The clear-text payload catalog does not establish robustness to mutation or iterative evasion.
- The paired legitimate cases in the main harness do not represent arbitrary SOC traffic.

[Simões, Sections 3.4, 4.4-4.5, and 5, pp. 18, 25-28]

### OUR OBSERVATION

- The evaluation corpus is a curated security test catalog rather than a distribution of real SOC attacks and normal operations.
- Only two alerts exercise the full pipeline, so alert-type, rule, product, and organizational diversity are not evaluated.
- No labelled alert dispositions, analyst decisions, evidence-quality labels, or controlled missing/contradictory evidence conditions are included.
- The fixed cases enable reproducibility but cannot support population-level claims about detection rates or false-positive rates in production SOC traffic.

