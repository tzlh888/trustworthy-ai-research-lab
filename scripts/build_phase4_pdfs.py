#!/usr/bin/env python3
"""Build the Phase 4 paper and one-page summary PDFs from reviewed Markdown."""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def ascii_safe(text: str) -> str:
    replacements = {
        "–": "-", "—": "-", "−": "-", "‑": "-", "“": '"', "”": '"',
        "‘": "'", "’": "'", "…": "...", "×": "x", "Δ": "Delta",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def inline_markup(text: str) -> str:
    text = ascii_safe(text)
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(https?://[^\s<]+)", r"<link href='\1' color='#1D4ED8'>\1</link>", text)
    return text


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("PaperTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=17, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#111827"), spaceAfter=8),
        "meta": ParagraphStyle("Meta", parent=base["Normal"], fontName="Helvetica", fontSize=8.2, leading=10, alignment=TA_CENTER, textColor=colors.HexColor("#4B5563"), spaceAfter=4),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=12.2, leading=14.2, textColor=colors.HexColor("#0F3D56"), spaceBefore=9, spaceAfter=4, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.3, leading=12.2, textColor=colors.HexColor("#155E75"), spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.65, leading=10.9, alignment=TA_JUSTIFY, spaceAfter=5.2, allowWidows=0, allowOrphans=0),
        "abstract": ParagraphStyle("Abstract", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.35, leading=10.4, alignment=TA_JUSTIFY, leftIndent=16, rightIndent=16, borderColor=colors.HexColor("#CBD5E1"), borderWidth=.5, borderPadding=7, backColor=colors.HexColor("#F8FAFC"), spaceAfter=8),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.5, leading=10.6, leftIndent=13, firstLineIndent=-7, spaceAfter=2.5),
        "caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName="Helvetica", fontSize=7.4, leading=9, alignment=TA_JUSTIFY, textColor=colors.HexColor("#374151"), leftIndent=8, rightIndent=8, spaceAfter=7),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.7, leading=9.4, alignment=TA_LEFT, spaceAfter=3),
    }


def page_decor(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#CBD5E1")); canvas.setLineWidth(.4)
    canvas.line(doc.leftMargin, height - .40*inch, width-doc.rightMargin, height-.40*inch)
    canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(doc.leftMargin, height-.31*inch, "Evidence-Aware Risk Scoring for Scientific Claim Verification")
    canvas.drawRightString(width-doc.rightMargin, .31*inch, f"Page {doc.page}")
    canvas.restoreState()


def image_flow(path: Path, width: float, caption: str, sty: dict[str, ParagraphStyle]) -> list:
    from PIL import Image as PILImage
    with PILImage.open(path) as source:
        iw, ih = source.size
    height = width * ih / iw
    return [Spacer(1, 4), Image(str(path), width=width, height=height), Spacer(1, 3), Paragraph(inline_markup(caption), sty["caption"])]


def parse_table(lines: list[str], sty: dict[str, ParagraphStyle], available_width: float) -> Table:
    cells = []
    for line in lines:
        values = [value.strip() for value in line.strip().strip("|").split("|")]
        if all(set(value) <= {"-", ":"} for value in values):
            continue
        cells.append([Paragraph(inline_markup(value), sty["small"]) for value in values])
    column_count = len(cells[0])
    if column_count == 6:
        widths = [available_width*.13, available_width*.12, available_width*.14, available_width*.13, available_width*.23, available_width*.25]
    else:
        widths = [available_width/column_count] * column_count
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#0F172A")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return table


def build_paper(root: Path, output: Path) -> None:
    sty = styles()
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=.58*inch, rightMargin=.58*inch, topMargin=.55*inch, bottomMargin=.52*inch, title="Evidence-Aware Risk Scoring for Scientific Claim Verification", author="Independent student research project")
    available = letter[0] - doc.leftMargin - doc.rightMargin
    source = (root / "paper/EARS_selective_prediction_paper.md").read_text(encoding="utf-8").splitlines()
    figures = root / "reports/phase4/figures"
    insert_before = {
        "## 8. Statistical Analysis": [
            ("figure_1_risk_coverage_fit_vs_test.png", "Figure 1. Fit-only out-of-fold and frozen Internal Test risk-coverage curves. Every discrete prefix is shown without smoothing; lower is better."),
            ("figure_2_aurc_and_r80_comparison.png", "Figure 2. Independent-test AURC and R80 error counts. All R80 methods accept the same 70 of 88 eligible claims."),
        ],
        "## 9. Error Analysis": [
            ("figure_3_primary_bootstrap_intervals.png", "Figure 3. EARS-minus-B1 paired differences with 95% intervals from 10,000 connected-group bootstrap replicates. Negative values favor EARS."),
        ],
        "## 10. Discussion": [
            ("figure_4_no_relation_sensitivity.png", "Figure 4. Secondary NO_RELATION sensitivity. The six eligible NO_RELATION predictions were all errors; existing scores were reranked without retraining."),
            ("table_1_representative_failure_cases.png", "Table 2. Deterministically selected cases include false reassurance, unnecessary rejection, and outcomes both favorable and unfavorable to EARS. Diagnostics are descriptive, not causal."),
        ],
    }
    story = []
    index = 0
    abstract_next = False
    while index < len(source):
        raw = source[index].strip()
        if raw in insert_before:
            for filename, caption in insert_before[raw]:
                story.extend(image_flow(figures / filename, available, caption, sty))
        if not raw:
            index += 1; continue
        if raw.startswith("# "):
            story.append(Paragraph(inline_markup(raw[2:]), sty["title"]))
        elif raw.startswith("**Independent") or raw.startswith("**Study period") or raw.startswith("**Protocol"):
            story.append(Paragraph(inline_markup(raw), sty["meta"]))
        elif raw.startswith("## "):
            heading = raw[3:]
            story.append(Paragraph(inline_markup(heading), sty["h1"]))
            abstract_next = heading == "Abstract"
        elif raw.startswith("### "):
            story.append(Paragraph(inline_markup(raw[4:]), sty["h2"]))
        elif raw.startswith("- "):
            story.append(Paragraph("- " + inline_markup(raw[2:]), sty["bullet"]))
        elif raw.startswith("|"):
            table_lines = []
            while index < len(source) and source[index].strip().startswith("|"):
                table_lines.append(source[index].strip()); index += 1
            story.append(Spacer(1, 3)); story.append(parse_table(table_lines, sty, available)); story.append(Spacer(1, 5))
            continue
        else:
            story.append(Paragraph(inline_markup(raw), sty["abstract"] if abstract_next else sty["body"]))
            abstract_next = False
        index += 1
    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


def build_summary(root: Path, output: Path) -> None:
    sty = styles()
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=.58*inch, rightMargin=.58*inch, topMargin=.48*inch, bottomMargin=.45*inch, title="One-Page Research Summary", author="Independent student research project")
    story = [Paragraph("Evidence-Aware Risk Scoring for Scientific Claim Verification", sty["title"]), Paragraph("One-Page Research Summary", sty["meta"]), HRFlowable(width="100%", thickness=.7, color=colors.HexColor("#0F3D56")), Spacer(1, 6)]
    lines = (root / "application/ONE_PAGE_RESEARCH_SUMMARY.md").read_text(encoding="utf-8").splitlines()
    for raw in lines:
        raw = raw.strip()
        if not raw: continue
        if raw.startswith("#"):
            continue
        story.append(Paragraph(inline_markup(raw), ParagraphStyle("SummaryBody", parent=sty["body"], fontSize=8.25, leading=10.2, spaceAfter=4.3)))
    doc.build(story, onFirstPage=page_decor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    build_paper(root, output / "EARS_selective_prediction_paper.pdf")
    build_summary(root, output / "EARS_one_page_research_summary.pdf")


if __name__ == "__main__":
    main()
