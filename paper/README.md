# Evidence-aware incident reconstruction paper

The manuscript has been converted to the IEEEtran conference class. Its
numbered in-text citations link to IEEE-style bibliography entries with
clickable DOI URLs. The PDF files already in this directory predate this
conversion and must be rebuilt before use. Build from the paper directory
with pdflatex main.tex, bibtex main, then pdflatex main.tex twice.
The command-line MiKTeX installation in this sandbox cannot access its
per-user registry settings; a usable TeXworks window was unavailable in
this session. The source has passed a static check of figure paths, citation
keys, and cross-references, but the new PDF has not been typeset here.

Manuscript source: `main.tex`; primary results: `figure_data/holdout_metrics.csv`; original immutable outputs in `../experiments/PHASE33_FROZEN_GENERALIZATION/`.

From repository root: `python paper/build_paper.py` verifies the sealed prediction SHA-256 hashes and metric sums and regenerates the ten vector figures. The layered methodology overview, detailed verifier and provenance diagrams, and two diagnostic charts are sourced in `figure_source/expanded_figures.py`, which the build script runs. `python paper/audit_paper.py` refreshes claim and source audits without changing experiment files. With MiKTeX/TeXworks, open `paper/main.tex`, select `pdfLaTeX+MakeIndex+BibTeX`, and typeset; repeat pdfLaTeX if cross-references remain unresolved. Alternatively, from `paper/` run `pdflatex main.tex`, `bibtex main`, then `pdflatex main.tex` twice. Copy `main.pdf` to `research_paper.pdf`. Required packages: geometry, lmodern, microtype, ragged2e, setspace, graphicx, booktabs, tabularx, array, amsmath, amssymb, caption, subcaption, float, xcolor, hyperref, natbib.

The final manuscript uses "frozen synthetic holdout" rather than internal phase identifiers. Internal audit paths retain phase names. The PDF is compiled with the installed MiKTeX TeXworks user interface. The sandboxed command-line MiKTeX process cannot access its per-user registry configuration, so the UI is used for the final build. Figure source is editable Matplotlib code in `build_paper.py` and `figure_source/expanded_figures.py`; numerical figure data are in `figure_data/`. The original experiment artifacts are never overwritten by this procedure.
