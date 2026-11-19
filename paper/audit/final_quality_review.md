# Final quality review — 19 November 2026

## Manuscript and PDF

- The installed MiKTeX TeXworks compiled `main.tex` to a 17-page PDF. The final copy is `research_paper.pdf`.
- All 14 section inputs are present. The PDF has numbered pages, a single text column, ragged-right body paragraphs, nine original vector figures, seven principal tables, appendices, and a numeric bibliography. Figure 1 is the C/V/P architecture, Figure 2 is the evidence timing/provenance model, and Figure 3 is the detailed verifier flow.
- The compiled PDF text contains all 12 cited bibliography entries and no unresolved `[?]` citation markers. The source citation keys, figure files, and `\\ref` targets were checked against the source files.
- A rendered contact sheet of all 17 pages was inspected. The page text bounding boxes lie within approximately x=76–521 pt on an A4 width of 595 pt; no text crosses page margins in the extracted geometry. The figure-heavy pages, results table, bibliography, and appendix were visually checked at contact-sheet scale. The detailed diagrams and new charts were also inspected separately at higher resolution. This is a layout check, not a specialist copyedit or a printer proof.
- The original `main.log` records one first-pass LaTeX run before bibliography resolution; it is not a reliable final warning report for the later TeXworks chain. No claim of a warning-free build is made. The resulting PDF itself contains resolved citations and cross-references.

## Source and evidence checks

- `build_paper.py` checks the SHA-256 of both sealed prediction files against the pre-evaluation seal and summary, verifies 15 per-queue records and the primary numerator sums, and generates chart CSVs and vector PDFs from the original holdout summary. The added queue-delta heatmap checks column totals (+10/+18/+6) against the archive, and the retrieval decomposition asserts recall no greater than recoverability no greater than 300 in each arm.
- Primary results: Recall@20 250/300 versus 260/300; recoverability 263/300 versus 281/300; P@10 107/150 versus 113/150; zero false pairs and mixed groups in both arms. The development gate miss and subsequent documented protocol adjustment appear in the paper.
- The manuscript calls the primary experiment a frozen synthetic holdout, without using the internal phase number as the paper's research narrative. Development-only and historical cohorts are kept separate. The public GUIDE inspection is explicitly described as a data-readiness audit without a real-world prediction.
- The literature audit records 12 verified references and an 11-paper comparison. This is below the requested aspirational range of 25–40 references; expansion should follow deeper full-text review, not bibliography padding. Several method comparisons relied on publisher records and accessible abstracts, as recorded in `reference_audit.csv`.

## Submission blockers

The manuscript is **not yet journal submission ready**. It lacks authorized real SOC validation, a compatible published-method comparison, stronger evidence on the independence assumption, and author-confirmed affiliations, declarations, and metadata. The 15-queue synthetic holdout and the pre-holdout protocol adjustment are material reviewer concerns. A target journal's live instructions and template must be checked and adopted before submission; the required single-column ragged-right format is an initial manuscript layout, not a claim of journal-template compliance.
