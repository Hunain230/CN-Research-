# Evidence-aware incident reconstruction paper

Manuscript source: `main.tex`; primary results: `figure_data/holdout_metrics.csv`; original immutable outputs in `../experiments/PHASE33_FROZEN_GENERALIZATION/`.

From repository root: `python paper/build_paper.py` verifies the sealed prediction SHA-256 hashes and metric sums and regenerates the seven vector figures. `python paper/audit_paper.py` refreshes claim and source audits without changing experiment files. To compile from `paper/` after a working TeX distribution is installed: `pdflatex main.tex`, `bibtex main`, `pdflatex main.tex` twice; copy `main.pdf` to `research_paper.pdf`. Required packages: geometry, lmodern, microtype, ragged2e, setspace, graphicx, booktabs, tabularx, array, amsmath, amssymb, caption, subcaption, float, xcolor, hyperref, natbib.

The final manuscript uses “frozen synthetic holdout” rather than internal phase identifiers. Internal audit paths retain phase names. The currently installed MiKTeX fails on registry access and initial setup in this sandbox; a compiled PDF requires a functioning LaTeX installation. Do not substitute a rendered non-LaTeX PDF for a claimed LaTeX compilation.
