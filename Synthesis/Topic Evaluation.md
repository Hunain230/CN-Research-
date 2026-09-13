# Topic Evaluation

## Topic under review

**Evidence-Grounded Multi-Agent Reasoning for Security Alert Triage**

## Verdict

### OUR OBSERVATION

The topic is promising as a direction but **too broad and underspecified as a research question**. Every key noun hides an unresolved design choice: what counts as evidence, what agents do, what “reasoning” output is evaluated, which alerts are triaged, and what constitutes improvement. In its current form it is more likely to become an AI SOC prototype than a defensible experiment.

## 1. Is the topic too broad?

Yes. It combines evidence retrieval, multi-agent architecture, reasoning, explainability, alert ranking, investigation, and potentially response. A 3-4 month project cannot validate all of these credibly.

## 2. Is it sufficiently specific?

No. It lacks:

- a defined alert source and unit of analysis;
- a fixed triage output (binary disposition, severity, ranking, incident grouping, or next action);
- an evidence schema and provenance rule;
- a comparator;
- an outcome metric; and
- a generalization setting.

## 3. Is it research or merely system implementation?

At present, mostly a system concept. It becomes research only when framed around a falsifiable question, for example: **Does an evidence-specialized critic/adjudicator workflow reduce unsupported alert dispositions and improve top-k triage quality over a single-agent RAG baseline under the same evidence and token budget?**

## 4. Which parts are already crowded?

Within the three papers, the crowded components are intrusion classification, generic multi-agent role decomposition, RAG-based enrichment, explanation dashboards, and automated rule-based response. Combining these components does not by itself establish novelty.

## 5. Which part could constitute a genuine research question?

The strongest candidate is the measurable effect of **evidence-specialized adversarial review** on triage correctness, grounding, calibration, and abstention under incomplete or conflicting evidence. The contribution must be the tested mechanism and evidence, not the existence of multiple agents.

## 6. What would make this an ordinary “AI SOC project”?

- ingest alerts;
- retrieve CTI;
- ask several LLM agents for opinions;
- summarize a verdict;
- show it on a dashboard; and
- report a few illustrative cases without controlled baselines.

That would be useful engineering but weak research.

## 7. What would make it a research contribution?

- a precise hypothesis;
- a reproducible alert/case dataset;
- explicit evidence provenance and unsupported-claim scoring;
- matched single-agent, multi-agent, no-retrieval, and no-critic baselines;
- a component ablation;
- a time/source-separated test;
- uncertainty/calibration and abstention analysis; and
- a clear result, including the possibility that multi-agent debate does not help.

## 8. What methodological risks exist?

### OUR OBSERVATION

- **Dataset mismatch:** public intrusion flows are not SOC alerts.
- **Label ambiguity:** analyst dispositions may be inconsistent or organization-specific.
- **Evidence leakage:** retrieving reports or case notes that contain the label makes evaluation trivial.
- **Shared-model correlation:** several prompted roles may repeat the same error.
- **Judge bias:** using an LLM to grade LLM grounding can inflate results.
- **Cost confounding:** more agents receive more tokens/compute than the baseline.
- **Outcome substitution:** explanation plausibility may be mistaken for correct triage.
- **Automation risk:** false confidence could lead to unsafe response recommendations.
- **Scope creep:** adding simulation, CTI extraction, triage, and response will prevent rigorous evaluation of any one component.

## 9. What claims should we avoid?

- “No one has studied evidence-grounded multi-agent alert triage.”
- “Multi-agent debate eliminates hallucinations.”
- “Causal grounding guarantees safe response.”
- “High extraction/detection F1 proves effective SOC triage.”
- “CICIDS2017, UNSW-NB15, or CICIoT2023 represents real SOC alert workloads.”
- “More agents necessarily improve reasoning.”
- “The system is autonomous” if humans must validate consequential actions.

## 10. What needs to be narrowed?

### RESEARCH OPPORTUNITY

Recommended narrowing:

> **Evaluate whether an evidence-specialized critic and adjudicator improve binary alert disposition and calibrated abstention over a single-agent RAG baseline on a fixed set of security alert cases.**

Keep the scope to triage decisions. Do not include autonomous containment as a primary outcome. Use CTI only as one evidence source, not as a separate extraction research problem. Use two or three agents with explicit roles rather than an open-ended swarm.

## Bottom line

### OUR OBSERVATION

The original title is acceptable as an umbrella, but not yet as a semester-scale research design. The project should be narrowed to one triage decision, one grounding mechanism, one multi-agent mechanism, and one rigorous comparative evaluation.

