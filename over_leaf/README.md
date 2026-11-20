# Springer Nature Overleaf manuscript

Upload the contents of this folder (or the accompanying ZIP) to Overleaf. Set `main.tex` as the main document, select pdfLaTeX, and compile with BibTeX. This uses Springer Nature `sn-jnl.cls` template version 3.1 in its two-column layout with numbered math/physical-sciences references. Keep `sn-jnl.cls`, `sn-mathphys-num.bst`, `references.bib`, and `figures/` alongside `main.tex`.

`main.tex` is a complete single-file manuscript, as the template requests. The editable section sources and `build_manuscript.py` are included for future revision; after editing a section, run `python build_manuscript.py` and upload the regenerated `main.tex`. The vector architecture diagrams can be rebuilt with `python figure_source/redraw.py`.

The title is **A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization**. The manuscript distinguishes the bounded local LLM prototype and retrospective GUIDE work from the deterministic fresh synthetic holdout. The latter is the measured 260/300 result; it is not presented as an LLM performance result.

The primary base paper is Hmimou et al., *A Multi-Agent System for Cybersecurity Threat Detection and Correlation Using Large Language Models* (IEEE Access, 2025, DOI: 10.1109/ACCESS.2025.3602681). Guo et al. and AgentSOC are related prioritization comparisons. Published metrics are explicitly distinguished from the project's own metrics; they are not claimed to be results on the same dataset.

The source includes base-paper comparison, ablation, reproducibility, declarations, and explicit evidence boundaries. The local pdfLaTeX/BibTeX build is 12 A4 pages. No margin, type-size, or spacing override was added to the Springer class. Author metadata and declarations should be checked by the authors.

The accompanying ZIP includes the generated `main.tex`, bibliography, Springer class and bibliography style, and every referenced vector figure. Editable section sources and chart-generation code are included; Python is only needed if you edit sections or regenerate figures.

The package includes `analysis/holdout_queue_results.csv` and `analysis/paired_queue_bootstrap.py` for the paired 10,000-resample intervals quoted in the Results. Run `python analysis/paired_queue_bootstrap.py` from the project folder to verify them. From the repository root, `python over_leaf/analysis/replay_frozen_holdout.py` regenerates the same-seed controlled cohort in a temporary directory and checks both frozen arms against all 15 archived queues. It does not overwrite the original experiment or create an independent new holdout. `RUBRIC_REVIEW.md` maps the paper to the teacher's criteria and records author checks; it does not appear in the compiled manuscript.

The main text uses the two-column Springer layout. Five archived-data graphics show paired bootstrap intervals, cumulative and interval-based rank retrieval, incident outcomes and transitions, per-queue metric changes, and the matched development ablation; two additional figures explain the architecture and verifier workflow. The verifier's confusion matrix is a centered table. Matplotlib and Seaborn source is in `figure_source/metrics_charts.py`. The principal numeric results are bolded.

Local pdfLaTeX and BibTeX compiled the final 12-page PDF. The final log has no overfull boxes, unresolved citations, or unresolved cross-references. The rendered pages were checked for float placement and column alignment.
