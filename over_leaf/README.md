# Springer Nature Overleaf manuscript

Upload the contents of this folder (or the accompanying ZIP) to Overleaf. Set `main.tex` as the main document, select pdfLaTeX, and compile with BibTeX. This is Springer Nature `sn-jnl.cls` template version 3.1 using the numbered math/physical-sciences reference style. Keep `sn-jnl.cls`, `sn-mathphys-num.bst`, `references.bib`, and `figures/` alongside `main.tex`.

`main.tex` is a complete single-file manuscript, as the template requests. The editable section sources and `build_manuscript.py` are included for future revision; after editing a section, run `python build_manuscript.py` and upload the regenerated `main.tex`. The vector architecture diagrams can be rebuilt with `python figure_source/redraw.py`.

The title is **A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization**. The manuscript distinguishes the bounded local LLM prototype and retrospective GUIDE work from the deterministic fresh synthetic holdout. The latter is the measured 260/300 result; it is not presented as an LLM performance result.

The primary base paper is Hmimou et al., *A Multi-Agent System for Cybersecurity Threat Detection and Correlation Using Large Language Models* (IEEE Access, 2025, DOI: 10.1109/ACCESS.2025.3602681). Guo et al. and AgentSOC are related prioritization comparisons. Published metrics are explicitly distinguished from the project's own metrics; they are not claimed to be results on the same dataset.

The teacher's Phase 4 brief requires a roughly 8–12 page venue-appropriate paper, explicit base-paper comparison, ablation, reproducibility, declarations, and honest evidence boundaries. This source includes those elements, but the exact page count and visual layout must be checked after Overleaf compilation. No margin, type-size or spacing overrides were added to the Springer class. Author metadata, funding/competing-interest declarations, repository URL, and target venue requirements require author confirmation.

The accompanying ZIP is curated for direct Overleaf upload: it includes the generated `main.tex`, bibliography, Springer class and bibliography style, and the six referenced vector figures. It also includes editable section sources and diagram-generation code. Python is only needed if you later regenerate `main.tex` or redraw a diagram; Overleaf compiles the supplied `main.tex` directly.

The package includes `analysis/holdout_queue_results.csv` and `analysis/paired_queue_bootstrap.py` for the paired 10,000-resample intervals quoted in the Results. Run `python analysis/paired_queue_bootstrap.py` from the project folder to verify them. `RUBRIC_REVIEW.md` maps the paper to the teacher's criteria and records author checks; it does not appear in the compiled manuscript.

Local command-line LaTeX could not be used for a final typeset check in this environment: MiKTeX was blocked by Windows registry access, and Tectonic could not fetch its uncached bundle. Static checks found no missing figure, citation key, or cross-reference.
