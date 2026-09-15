# Evaluation and Results

## Evaluation protocol

### AUTHOR CLAIM

Six suites isolate framework components:

| Suite | Component | Unique instances | Block decisions |
|---|---|---:|---:|
| T00 | Tool-registration validator | 4 | 100 |
| T01 | Layer 1: access control | 5 | 120 |
| T02 | Layer 2: rate limiter | 2 | 40 |
| T03 | Layer 3: input validator | 5 | 100 |
| T04 | Layer 4: output validator | 7 | 160 |
| T05 | Session controls | 2 | 80 |
| **Total** |  | **25** | **600** |

Each unique instance is repeated 20 times. The repetitions verify deterministic stability and expose paired legitimate cases to non-zero-temperature model behavior; they are not independent samples. [Simões, Sections 3.4-3.5 and Table 12, pp. 18-23]

## Main security results

### AUTHOR CLAIM

- Correct block decisions: **600/600**
- Attack decisions passed: **0**
- Legitimate calls falsely blocked in the main paired harness: **0**

[Simões, Section 4.1 and Table 12, p. 23]

## Full-pipeline demonstration

### AUTHOR CLAIM

The system processes one live Wazuh alert and one synthetic SSH brute-force alert under unsecured and secured conditions. The registration validator removes the malicious name-collision and description-poisoning tools. Runtime layers handle malicious response content and unauthorized tool use. Decision-relevant response fields are identical between conditions for both alerts. Two unsupported wildcard arguments are rejected by schema validation and are independently rejected by Wazuh. [Simões, Section 4.2, pp. 23-24]

## Performance overhead

### AUTHOR CLAIM

Controls are measured in isolation after 200 warm-up iterations followed by **10,000** timed iterations. All controls except unoptimized JSON Schema validation complete in under **20 µs**. Schema validation averages **546.6 µs** because the schema is recompiled on every call; precompilation reduces it to **11.4 µs**. The summed local overhead for Layers 1-4 is below **0.6 ms**, or below **30 µs** with precompilation. Network and LLM latency are excluded. [Simões, Section 4.3 and Table 13, p. 24]

## Robustness and false-positive probes

### AUTHOR CLAIM

| Condition | Layer 3 payloads blocked |
|---|---:|
| Clear form | 4/4 |
| Base64 | 0/4 |
| Homoglyph substitution | 0/4 |
| Spanish translation | 0/4 |
| Paraphrase | 0/4 |

[Simões, Section 4.4 and Table 14, p. 25]

Seven of eight benign SOC inputs containing attack-like substrings are blocked by the Layer 3 injection scan. The authors therefore restrict the zero-false-block result to the paired legitimate cases in the original harness. [Simões, Section 4.5 and Table 15, pp. 25-26]

## Our evaluation assessment

### OUR OBSERVATION

- The separate robustness and benign-text probes materially qualify the headline 600/600 result.
- No statistical test is appropriate for the repeated fixed deterministic decisions; the paper correctly avoids treating repetitions as increased statistical power.
- The unsecured pipeline is a useful demonstration baseline, but the study does not compare alternative security frameworks or remove individual controls in an end-to-end ablation.
- The evaluation does not measure alert-disposition correctness, evidence-citation correctness, calibration, abstention, analyst utility, end-to-end latency, or token cost.
- A detected manifest change is counted as a successful outcome even though the implementation warns rather than blocks; detection and prevention should be distinguished.

