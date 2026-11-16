"""Render FINAL_REPORT.md as a portable submission PDF with aggregate figures."""

from __future__ import annotations

import html
import hashlib
import json
import re
import argparse
from pathlib import Path

import matplotlib
from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle, XPreformatted,
)


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_fonts() -> None:
    font_dir = Path(matplotlib.get_data_path()) / "fonts/ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", str(font_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(font_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(font_dir / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")


def inline_markup(value: str) -> str:
    tokens = MarkdownIt().parseInline(value)[0].children or []
    parts = []
    link_closers = []
    for token in tokens:
        if token.type == "text":
            parts.append(html.escape(token.content))
        elif token.type == "strong_open":
            parts.append("<b>")
        elif token.type == "strong_close":
            parts.append("</b>")
        elif token.type == "em_open":
            parts.append("<i>")
        elif token.type == "em_close":
            parts.append("</i>")
        elif token.type == "code_inline":
            parts.append(f'<font name="DejaVu" color="#244a63">{html.escape(token.content)}</font>')
        elif token.type == "link_open":
            target = token.attrGet("href") or ""
            if target.startswith(("https://", "http://")):
                parts.append(f'<link href="{html.escape(target, quote=True)}" color="#205a83">')
                link_closers.append("</link>")
            else:
                parts.append('<font color="#205a83">')
                link_closers.append("</font>")
        elif token.type == "link_close":
            parts.append(link_closers.pop())
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append("<br/>")
    return "".join(parts)


def parse_table(lines: list[str], style: ParagraphStyle, width: float) -> Table:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    rows = [row for row in rows if not all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in row)]
    count = max(map(len, rows))
    if count == 2:
        widths = [width * 0.26, width * 0.74]
    elif count == 3:
        widths = [width * 0.43, width * 0.285, width * 0.285]
    elif count == 4:
        widths = [width * 0.34] + [width * 0.22] * 3
    else:
        widths = [width / count] * count
    data = [[Paragraph(inline_markup(cell), style) for cell in row + [""] * (count - len(row))] for row in rows]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe7ef")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#7fa0b5")),
    ]))
    return table


def footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#b9cbd6"))
    canvas.line(1.8 * cm, 1.45 * cm, width - 1.8 * cm, 1.45 * cm)
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#567082"))
    canvas.drawString(1.8 * cm, 1.1 * cm, "Exploratory GUIDE_Test implementation | 2026-11-16")
    canvas.drawRightString(width - 1.8 * cm, 1.1 * cm, str(doc.page))
    canvas.restoreState()


def build(
    source: Path = ROOT / "submission/FINAL_REPORT.md",
    output: Path = ROOT / "submission/PHASE3_IMPLEMENTATION_REPORT.pdf",
    manifest: Path = ROOT / "submission/PHASE3_REPORT_PDF_MANIFEST.json",
) -> None:
    register_fonts()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["Normal"], fontName="DejaVu", fontSize=8.8, leading=11.5, textColor=colors.HexColor("#1d2933"), spaceAfter=4)
    heading1 = ParagraphStyle("H1", parent=body, fontName="DejaVu-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#153b53"), spaceBefore=10, spaceAfter=5)
    heading2 = ParagraphStyle("H2", parent=body, fontName="DejaVu-Bold", fontSize=11.5, leading=15, textColor=colors.HexColor("#20506b"), spaceBefore=10, spaceAfter=5)
    title = ParagraphStyle("Title", parent=body, fontName="DejaVu-Bold", fontSize=20, leading=27, textColor=colors.HexColor("#122e42"), alignment=TA_CENTER, spaceAfter=16)
    table_cell = ParagraphStyle("Cell", parent=body, fontSize=7.3, leading=10.2, spaceAfter=0)
    caption = ParagraphStyle("Caption", parent=body, fontSize=8, leading=11.5, textColor=colors.HexColor("#4b5d68"), alignment=TA_LEFT, spaceBefore=5, spaceAfter=9)
    code = ParagraphStyle("Code", parent=body, fontName="DejaVu", fontSize=7.2, leading=10.5, textColor=colors.HexColor("#273d4c"), leftIndent=8, spaceAfter=9)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.3 * cm, bottomMargin=1.45 * cm, title="GUIDE_Test Research Performance Report", author="CNET Research")
    usable = A4[0] - doc.leftMargin - doc.rightMargin
    lines = source.read_text(encoding="utf-8").splitlines()
    story = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), title))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#8db3c7"), spaceAfter=12))
            i += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), heading1))
            i += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), heading2))
            i += 1
            continue
        if line.startswith("!["):
            match = re.match(r"!\[[^]]*\]\(([^)]+)\)", line)
            if match:
                path = (source.parent / match.group(1)).resolve()
                image = Image(str(path))
                scale = min(usable / image.imageWidth, 9.0 * cm / image.imageHeight, 1.0)
                image.drawWidth *= scale
                image.drawHeight *= scale
                story.append(image)
                story.append(Spacer(1, 5))
            i += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            story.append(parse_table(table_lines, table_cell, usable))
            story.append(Spacer(1, 10))
            continue
        if line.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            story.append(XPreformatted("\n".join(html.escape(x) for x in code_lines), code))
            i += 1
            continue
        if line.startswith("- "):
            story.append(Paragraph("&#8226; " + inline_markup(line[2:]), body))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("#", "|", "![", "- ", "```", "<!--")):
            paragraph.append(lines[i].strip())
            i += 1
        combined = " ".join(paragraph)
        story.append(Paragraph(inline_markup(combined), caption if combined.startswith("**Figure ") else body))
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    record = {
        "classification": "exploratory_phase3_report_pdf",
        "command": r".\.venv\Scripts\python.exe -m submission.build_report_pdf",
        "sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): digest(path)
            for path in (
                source,
                Path(__file__),
                output,
            )
        },
    }
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a Markdown research report as PDF.")
    parser.add_argument("--source", type=Path, default=ROOT / "submission/FINAL_REPORT.md")
    parser.add_argument("--output", type=Path, default=ROOT / "submission/PHASE3_IMPLEMENTATION_REPORT.pdf")
    parser.add_argument("--manifest", type=Path, default=ROOT / "submission/PHASE3_REPORT_PDF_MANIFEST.json")
    args = parser.parse_args()
    build(
        source=args.source.resolve(),
        output=args.output.resolve(),
        manifest=args.manifest.resolve(),
    )
