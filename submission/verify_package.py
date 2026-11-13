"""Check local submission links and frozen aggregate artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    ROOT / "dashboard/README.md",
    ROOT / "dashboard/SIMULATION_README.md",
    ROOT / "submission/FINAL_REPORT.md",
    ROOT / "submission/REPRODUCE.md",
    ROOT / "submission/KNOWN_LIMITATIONS.md",
    ROOT / "submission/DELIVERY_CHECKLIST.md",
    ROOT / "submission/DASHBOARD_VERIFICATION.md",
    ROOT / "submission/EXPERIMENT_REGISTER.md",
    ROOT / "submission/RESULTS_AND_DISCUSSION.md",
    ROOT / "submission/FULL_SUITE_RUN_20261113.md",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    links = 0
    missing = []
    for doc in DOCS:
        body = doc.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
            if target.startswith(("https://", "http://", "#")):
                continue
            path = (doc.parent / unquote(target.split("#", 1)[0])).resolve()
            links += 1
            if not path.exists():
                missing.append((str(doc.relative_to(ROOT)), target))
    if missing:
        raise ValueError(f"Broken local links: {missing}")
    for name in ("submission_full_guide_20261112_v1", "submission_qwen_20261112_v1", "submission_full_guide_paper_20261113_v1", "submission_qwen_v2_paper_20261113_v1"):
        manifest = json.loads((ROOT / "outputs" / name / "run_manifest.json").read_text(encoding="utf-8"))
        for relative, expected in manifest["sha256"].items():
            source = ROOT / relative
            if digest(source) != expected:
                raise ValueError(f"Run manifest mismatch: {relative}")
    correction = json.loads((ROOT / "outputs/submission_qwen_20261112_v1/correction_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in correction["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Correction manifest mismatch: {relative}")
    figure = json.loads((ROOT / "submission/figures/submission_figure_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in (figure["source_sha256"] | figure["figure_sha256"]).items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Figure manifest mismatch: {relative}")
    qwen_figure = json.loads((ROOT / "submission/figures/qwen_v2_figure_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in (qwen_figure["source_sha256"] | qwen_figure["figure_sha256"]).items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Qwen figure manifest mismatch: {relative}")
    pdf = json.loads((ROOT / "submission/PHASE3_REPORT_PDF_MANIFEST.json").read_text(encoding="utf-8"))
    for relative, expected in pdf["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Report PDF manifest mismatch: {relative}")
    dashboard = json.loads((ROOT / "dashboard/simulation_manifest.json").read_text(encoding="utf-8"))
    if digest(ROOT / "dashboard/simulation.html") != dashboard["output_sha256"]:
        raise ValueError("Dashboard output hash mismatch")
    print(f"Submission verification passed: {links} local links, four run manifests, one correction, two new figures, report PDF, and dashboard hash")


if __name__ == "__main__":
    main()
