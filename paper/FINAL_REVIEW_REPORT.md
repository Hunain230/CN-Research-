# Final manuscript review

**Result:** the revised 8-page, two-column LaTeX article compiles successfully to `research_paper.pdf`. It is a research manuscript, not an accepted, submitted or peer-reviewed publication. No institution or author contribution was invented.

## Completed checks

| Check | Outcome |
|---|---|
| Authors | PDF and source use exactly **Hunain Shahid** and **Hammad Ullah Khan**; no affiliations, emails or credentials were added. |
| Phase 33 metrics | Rechecked against `HOLDOUT_SUMMARY.json`: Recall@20 250/300 vs 260/300, recoverability 263/300 vs 281/300, P@10 107/150 vs 113/150, zero candidate false pairs/mixed groups and 100% pair precision. |
| Post-truth union audit | `POST_EVALUATION_AUDIT.json` reports 28/28 true fallback unions, 711/711 true accepted unions, 150 false tokens rejected, 35 true tokens withheld, zero temporal/private-feature violations and a valid seal. |
| Metric definitions | Checked against the original Phase 15 evaluator: 80% completeness and purity, 20 priority targets per queue, first 20 groups for recall, first ten groups and ten targets for P@10, all within-group pairs for pair precision, and mixed groups by distinct incident IDs. |
| Evidence levels | Phase 33 is labeled a frozen synthetic holdout; Phase 31--32 and 34--38 are identified as development or stress studies. Phase 34's 89% is not presented as a confirmed holdout result. |
| External data | Phase 39 is described as stopped before prediction, with no real-world Recall@20 or shadow deployment. GUIDE counts are attributed to prior local validation whose input-file hashes Phase 39 confirmed. |
| Frozen artifacts | Eight important code/configuration/evaluator/result hashes matched the Phase 39 audit. Both Phase 33 prediction hashes also matched `HOLDOUT_SUMMARY.json`. No historical research file was edited. |
| Citations | All 23 cited BibTeX keys resolve. The three user-supplied papers were checked against their PDFs and primary publisher or author records; details are in `REFERENCES_VERIFICATION.md`. |
| LaTeX and visuals | `pdflatex`/`bibtex`/`pdflatex`/`pdflatex` completed. Final log has no undefined citations/references, overfull boxes or LaTeX warnings. The two-column layout, diagrams, matched-result plot, tables, equations and references were rendered and inspected. |
| Claim traceability | `CLAIMS_EVIDENCE_LEDGER.csv` has 36 entries, including the derived 21/19 missed-incident breakdown and the three added external sources. |
| Change scope | Final working-tree audit found no changes to historical experiment files or frozen artifacts. |

## Remaining limits before a real-data claim

- A single 15-queue controlled synthetic holdout does not measure generalization to a real SOC. No Phase 33 holdout confidence interval or significance test was available, so none was invented.
- The simulator supplies trust roots and evidence-availability metadata that the available GUIDE export lacks. An authorized, independently adjudicated, point-in-time SOC export is required for external validation.
- Phase 29 and Phase 40 experiment directories were not present in this workspace; no results were inferred for them.
- Author affiliations, funding, acknowledgments, target venue and author contributions were not supplied, so they were omitted. Any future submission should be reviewed and approved by the named authors.
- LaTeX build files and temporary reference renderings remain inside `paper/`. Automatic approval review rejected recursive cleanup of the temporary renderings as blocked by policy, without a more specific reason. They do not affect the manuscript or final PDF.
