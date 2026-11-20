"""Check generated manuscript assets and build an Overleaf-ready ZIP."""
import re
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tex = (root / "main.tex").read_text(encoding="utf-8")
bib = (root / "references.bib").read_text(encoding="utf-8")

figures = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", tex)
missing = [x for x in figures if not (root / x).exists()]
labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
refs = set(re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", tex))
keys = set(re.findall(r"@\w+\{\s*([^,]+),", bib))
citations = set(k.strip() for group in re.findall(r"\\cite(?:\[[^]]*\])?\{([^}]+)\}", tex)
                for k in group.split(","))
issues = {"missing figures": missing, "missing labels": sorted(refs-labels),
          "missing bibliography keys": sorted(citations-keys)}
for name, values in issues.items():
    print(f"{name}: {values or 'none'}")
if any(issues.values()):
    raise SystemExit("Package validation failed")

keep = ["main.tex", "main.pdf", "references.bib", "sn-jnl.cls", "sn-mathphys-num.bst", "README.md", "RUBRIC_REVIEW.md", "build_manuscript.py"]
keep += figures
keep += [p.relative_to(root).as_posix() for folder in ("sections", "analysis", "figure_source")
         for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith("ref_page_")]
archive = root.parent / "over_leaf_springer_nature.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
    for item in sorted(set(keep)):
        out.write(root / item, item)
print(f"ZIP: {archive} ({len(set(keep))} files, {len(figures)} referenced figures)")
