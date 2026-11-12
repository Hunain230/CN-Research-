# Task 5 Analysis and Figures

## Goal

Turn valid experiment artifacts into clear tables, plots, ablations, and a cautious discussion suitable for a research submission.

## Steps

1. Read the data/claim audit and experiment register before writing interpretations.
2. Use metrics already defined in the current governing protocol and metric amendments. Do not invent new metrics after seeing results to favor a method.
3. For each metric report unit, numerator/denominator where applicable, aggregation (micro or organization macro), exclusions, and uncertainty method.
4. Distinguish candidate recall, pair classification, oracle-group ranking, and end-to-end predicted-group recovery. Never use one as a substitute for another.
5. Create figures only from verified output files, with descriptive titles, axes, units, sample sizes, and exploratory/synthetic labels as appropriate.
6. Use available ablation/masking results as exploratory evidence; clearly state when they reuse previously accessed data. Do not call differences causal unless the design supports that inference.
7. Conduct error analysis from existing aggregate artifacts or approved restricted procedures. Do not print raw identifiers or sensitive examples. If no reviewed error labels exist, report that the error review was not performed.
8. Compare to related papers qualitatively by task, dataset, labels, and metrics. Do not compare headline numbers from different denominators as direct wins/losses.
9. Discuss negative results and constraints, including candidate misses, false merges/splits, ambiguity exclusions, limited queues, and the absence of empirical LLM C/P/V measurements.
10. Keep the synthetic MVP runner results in a separate subsection labeled “Software demonstration only.” Do not include them in empirical comparisons, ablation conclusions, or claims about real data.

## Required result

Create `submission/RESULTS_AND_DISCUSSION.md` plus clean, reproducible figures in `submission/figures/`. Add figure-generation commands and source artifact paths to the document.

## Acceptance checklist

- [ ] Every plot can be regenerated from named aggregate artifacts.
- [ ] Values agree with source metrics/manifests.
- [ ] No unlabeled incident is silently treated as negative.
- [ ] Limitations and failed targets are visible beside relevant results.
- [ ] No dashboard demo data appears in research analysis.
- [ ] Synthetic MVP outputs are clearly separated from empirical research findings.

