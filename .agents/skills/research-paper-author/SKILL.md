---
name: research-paper-author
description: Develop an evidence-traceable academic research paper from a repository, with verified citations, scientific figures, reproducible methods, LaTeX compilation, and an explicit integrity review.
---

# Research paper author

Use this skill when turning completed research artifacts into a scholarly manuscript. Adapt the venue and section order to the study; normally cover abstract, introduction, background/problem, related work, objectives/contributions, methods, experimental design, metrics, results, discussion, threats, limitations, future work, conclusion, and references.

## Evidence before prose

- Audit original code, configs, evaluator, dataset manifests, frozen predictions, metrics, and final reports. Build a claim-to-artifact ledger before drafting results. Record split/cohort, denominator, artifact path, and hash where useful.
- Treat development, holdout, simulator truth, and external data as different evidence levels. Never transfer a metric or safety conclusion across them. Preserve failed experiments and stopping decisions.
- Recompute or cross-check reported numbers from original machine-readable artifacts when possible. If a source is unavailable or contradictory, qualify or omit its claim.

## Terminology and methods

- Define alert, observation, incident, candidate pair, accepted union, false grouped pair, mixed group, recoverability, recall, precision, and abstention using the repository's evaluator semantics. Distinguish incident-level metrics from pair-level metrics.
- Describe implemented cybersecurity and ML components precisely: provenance roots, derivation, point-in-time availability, contradiction checks, split isolation, ranking, and human review. Identify deterministic rules versus trained or agentic models. Never imply an operational deployment from an offline experiment.
- State prediction sealing, truth separation, cohort selection, baselines, gates, and reproducibility limits. Do not invent confidence intervals, significance, author metadata, novelty, or production claims.

## Citations and BibTeX

- Find primary research and official dataset documentation. Verify each reference's authors, exact title, year, venue, DOI or official URL, and support for the sentence citing it. Keep a source-verification note in the paper workspace.
- Use stable BibTeX keys and complete available metadata. Do not pad the bibliography or cite a source solely because its title sounds relevant. Mark preprints as preprints.

## Scientific presentation

- Make figures and tables answer a research question. Use real extracted values, readable labels, numbered captions, source notes, and in-text references. Do not plot percentages from incomparable cohorts as one progression.
- Use a suitable licensed LaTeX class available in the environment; a clean article class is preferable to an unavailable conference template. Compile repeatedly, resolve undefined citations/references, inspect the rendered PDF, and proofread claims, notation, figures, and author names.
- Finish with a publication-readiness check covering claim traceability, citation accuracy, mathematical definitions, cohort boundaries, leakage, negative findings, reproducibility, limitations, and remaining unresolved issues. A successful build is not proof of scientific validity.
