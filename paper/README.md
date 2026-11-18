# Research paper workspace

**Manuscript:** [research_paper.pdf](research_paper.pdf)  
**Editable source:** [main.tex](main.tex)  
**Authors:** Hunain Shahid and Hammad Ullah Khan

This paper reports the frozen Phase 33 **controlled synthetic** holdout and the failed or blocked follow-up studies. It does not claim a real-world Recall@20 result, a full autonomous multi-agent result, or operational readiness. It uses a clean LaTeX article format because no publisher venue was specified.

## Files

| File | Purpose |
|---|---|
| `main.tex`, `references.bib` | Manuscript and verified bibliography |
| `figures/`, `tables/` | Editable scientific visuals and tables |
| `CLAIMS_EVIDENCE_LEDGER.csv` | Claim-to-original-artifact trace |
| `REFERENCES_VERIFICATION.md` | Source metadata and citation-purpose checks |
| `REPRODUCIBILITY.md` | Build and frozen-artifact verification |
| `LIMITATIONS_AND_THREATS.md` | Study constraints and evidence boundaries |
| `FINAL_REVIEW_REPORT.md` | Editorial, technical and build checks |

## Build

From `paper/`, with MiKTeX available:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
Copy-Item main.pdf research_paper.pdf
```

No historical experiment file was edited to produce the paper. Phase 29 and Phase 40 directories were absent from this workspace during the audit.
