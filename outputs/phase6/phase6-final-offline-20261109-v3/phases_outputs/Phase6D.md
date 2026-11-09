# Module 6D — Baseline and system comparisons

**Status:** comparison infrastructure exists; an empirical LLM or multi-agent comparison was not performed.

## Available results

- Phase 3–5 baselines and C/P/V orchestration are synthetic-only implementation plumbing. The offline stub is not a real language model.
- Phase 6 contains an offline BM25 priority retrieval ceiling and a separate ambiguity-excluded ATT&CK/Jaccard pair diagnostic.
- These runs use different tasks, candidate units, and truth boundaries. They are not a matched head-to-head comparison and must not be plotted as competing systems.
- There is no empirical B2/B3 or C/P/V output, no live model latency, and no model cost measurement.

## Decision

Do not claim that BM25, rules, single-LLM, repeated-LLM, or C/P/V wins. No hosted API call was made. The current project protocol disallows external model calls and data transfer, and no local model run is available. Hardware limitations are addressed by leaving inference as an optional remote-provider integration, not by silently transmitting security evidence.

For a future comparison, use the same frozen query set, candidate universe, allowed fields, output schema, and evaluator. Preserve development-only selection and label all old-test results exploratory. A provider key alone does not clear the data handling or test-exposure gates.

## Acceptance status

- Synthetic comparator implementations retained: **pass**.
- Empirical paired comparison on the same frozen cohort and universe: **not available**.
- LLM/multi-agent claims: **not supported**.
- Provider credentials or external data transmission: **not used**.

