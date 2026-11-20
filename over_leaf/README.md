# Overleaf source

Upload the entire `over_leaf` folder contents to a new Overleaf project, or upload `over_leaf.zip` and extract it there. Set `main.tex` as the main document, pdfLaTeX as the compiler, and use Overleaf's normal BibTeX bibliography pass. The PDF figures are vector artwork and must remain in `figures/`.

The tables are each single centered floats; wide tables use the full two-column text width. Numeric results come from `experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json` and `POST_EVALUATION_AUDIT.json`. The token confusion matrix comes from the audit's accepted and rejected decisions. The incident matched table comes from the audit's 15 newly recalled and 5 lost recalled incidents. Development and GUIDE results are presented with separate evidence boundaries.

Before submission, confirm the author metadata and the target IEEE venue's exact template/declaration rules. This project uses the IEEEtran conference template. The local command-line MiKTeX compiler cannot access its Windows user registry in this sandbox, so this source was checked for missing figures, citation keys and references but not freshly compiled here.
