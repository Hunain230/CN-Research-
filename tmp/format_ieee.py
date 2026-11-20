from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "paper"
sections = p / "sections"
remove = {
    "introduction.tex": {"fig:overview"},
    "architecture.tex": {"fig:corrarch"},
    "experimental_design.tex": {"fig:expoverview", "fig:devtraj"},
    "results.tex": {"fig:resultcomp", "fig:metrics", "fig:safetyaudit",
                    "fig:safecard", "fig:queuebars", "fig:perqueue"},
}
for f in sections.glob("*.tex"):
    s = f.read_text(encoding="utf-8")
    s = s.replace(r"\citep{", r"\cite{")
    for label in remove.get(f.name, set()):
        blocks = list(re.finditer(r"\\begin\{figure\}\[ht\](?:(?!\\end\{figure\}).)*\\end\{figure\}\s*",
                                  s, flags=re.S))
        selected = [m for m in blocks if r"\label{" + label + "}" in m.group()]
        assert len(selected) == 1, (f.name, label, len(selected))
        m = selected[0]
        s = s[:m.start()] + s[m.end():]
    # All broad comparison tables span the page, with elastic columns and
    # no fixed-width columns that exceed the IEEE column measure.
    if f.name == "related_work.tex":
        s = re.sub(r"\\begin\{table\}\[ht\](.*?)\\begin\{tabularx\}\{\\linewidth\}\{@\{\}p\{27mm\}p\{28mm\}Y Y@\{\}\}",
                   r"\\begin{table*}[t]\1\\begin{tabularx}{\\textwidth}{@{}p{0.16\\textwidth}p{0.19\\textwidth}Y Y@{}}", s, flags=re.S)
        s = s.replace(r"\end{tabularx}\end{table}", r"\end{tabularx}\end{table*}")
    elif f.name in ("experimental_design.tex", "real_world_readiness.tex", "results.tex"):
        s = s.replace(r"\begin{table}[ht]", r"\begin{table*}[t]")
        s = s.replace(r"\end{tabularx}\end{table}", r"\end{tabularx}\end{table*}")
        s = s.replace(r"\begin{tabularx}{\linewidth}", r"\begin{tabularx}{\textwidth}")
        s = s.replace(r"p{32mm}p{27mm}Y", r"p{0.18\textwidth}p{0.21\textwidth}Y")
        s = s.replace(r"p{35mm}Y Y", r"p{0.23\textwidth}Y Y")
        s = s.replace(r"p{29mm}Yrrr", r"p{0.19\textwidth}Yrrr")
    elif f.name == "methodology.tex":
        s = s.replace(r"\begin{table}[ht]", r"\begin{table*}[t]")
        s = s.replace(r"\end{tabularx}\end{table}", r"\end{tabularx}\end{table*}")
        s = s.replace(r"\begin{tabularx}{\linewidth}{@{}p{35mm}Yp{30mm}@{}}",
                      r"\begin{tabularx}{\textwidth}{@{}p{0.25\textwidth}Yp{0.24\textwidth}@{}}")
    s = re.sub(r"\\centering\\small\\caption", r"\\centering\\footnotesize\\caption", s)
    s = s.replace("Figure~\\ref{fig:arch} previews", "Figure~\\ref{fig:arch} previews")
    if f.name == "results.tex":
        s = s.replace(r"Figures~\ref{fig:primary}--\ref{fig:metrics}",
                      r"Fig.~\ref{fig:primary}")
        s = s.replace(r"Figure~\ref{fig:safety}", r"Fig.~\ref{fig:safety}")
    if f.name == "architecture.tex":
        s = s.replace(r"Figure~\ref{fig:arch} shows the deployed computational order and Figure~\ref{fig:pipeline} provides",
                      r"Fig.~\ref{fig:arch} shows the computational order and Fig.~\ref{fig:pipeline} provides")
    if f.name == "experimental_design.tex":
        s = s.replace(r"Figures~\ref{fig:protocol} and~\ref{fig:devtraj} illustrate the experimental separation and development trajectory.",
                      r"Fig.~\ref{fig:protocol} illustrates the experimental separation.")
    f.write_text(s, encoding="utf-8")

bib = p / "references.bib"
s = bib.read_text(encoding="utf-8")
# IEEEtran prints note fields; visible DOI links remain clickable in PDF.
s = re.sub(r"(doi=\{([^}]+)\})(,?)",
           lambda m: m.group(1) + ", note={\\url{https://doi.org/" + m.group(2) + "}}" + m.group(3),
           s)
bib.write_text(s, encoding="utf-8")
