# Rubric review of the Springer manuscript

This is an editorial checklist for the authors. It is not included in `main.tex`.

| Rubric category | Evidence in `main.tex` | Editorial assessment |
|---|---|---|
| Structure and writing | Abstract, introduction with questions/contributions, methods, setup, metrics, results, comparison, ablation, discussion, conclusion, declarations; six captioned figures and six centered tables with text references. | Covered in source. Confirm float placement, legibility, and the requested 8–12 page range after Overleaf compilation. |
| Methodology, experiments, results | Explicit original-root and cutoff rules, endpoint fallback, scoring equation, split seeds and sample counts, baseline/candidate settings, metric formulas, paired holdout, confusion matrix, heatmap, and paired queue bootstrap. | Covered for the frozen synthetic experiment. Bootstrap intervals describe variation across 15 generated queues, not real deployment uncertainty. |
| Base paper, ablation, discussion | Hmimou et al. is the primary base; Guo et al. and AgentSOC supply context. The matched 10-queue development ablation isolates independent evidence and endpoint fallback. Failure cases and scope are discussed. | Published systems were not executed on the same synthetic data and metrics. Only the project's frozen baseline and candidate have a same-data comparison. Do not describe published percentage figures as head-to-head gains. |
| Originality, references, reproducibility | AI use declared; DOI and source links in bibliography; repository URL, Python/dependency versions, parameter settings, freeze files, code locations, queue CSV, and executable bootstrap analysis given. | Source supports an original controlled experiment. External plagiarism/originality assurance requires an actual similarity check and author review. Repository accessibility and final funding/interest disclosures require author confirmation. |

The full claim of LLM-agent superiority, operational SOC validation, and direct same-dataset improvement over the primary base paper is not supported by the archived experiment. These should not be introduced to chase rubric points. The manuscript reports the stronger supported finding: provenance-constrained endpoint fallback improved a frozen matched synthetic baseline.
