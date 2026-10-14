#!/usr/bin/env python3
"""Build and visually-verifiable V2 paper and one-page summary PDFs."""
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
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _ascii(text: str) -> str:
    replacements = {
        "–": "-", "—": "-", "−": "-", "‑": "-", "“": '"', "”": '"',
        "‘": "'", "’": "'", "…": "...", "×": "x", "Δ": "Delta", "↑": "up", "↓": "down",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _inline(text: str) -> str:
    text = html.escape(_ascii(text), quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(
        r"(https?://[^\s<]+)", r"<link href='\1' color='#155E75'>\1</link>", text
    )
    return text


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("V2Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=17, leading=20.5, alignment=TA_CENTER, textColor=colors.HexColor("#102A43"), spaceAfter=8),
        "meta": ParagraphStyle("V2Meta", parent=sample["Normal"], fontName="Helvetica", fontSize=7.8, leading=9.7, alignment=TA_CENTER, textColor=colors.HexColor("#52606D"), spaceAfter=4),
        "h1": ParagraphStyle("V2H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=colors.HexColor("#0F4C5C"), spaceBefore=9, spaceAfter=4, keepWithNext=True),
        "h2": ParagraphStyle("V2H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=10.2, leading=12, textColor=colors.HexColor("#16697A"), spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "body": ParagraphStyle("V2Body", parent=sample["BodyText"], fontName="Times-Roman", fontSize=8.65, leading=10.8, alignment=TA_JUSTIFY, spaceAfter=5, allowWidows=0, allowOrphans=0),
        "abstract": ParagraphStyle("V2Abstract", parent=sample["BodyText"], fontName="Times-Roman", fontSize=8.25, leading=10.3, alignment=TA_JUSTIFY, leftIndent=15, rightIndent=15, borderColor=colors.HexColor("#BCCCDC"), borderWidth=.55, borderPadding=7, backColor=colors.HexColor("#F5F7FA"), spaceAfter=8),
        "bullet": ParagraphStyle("V2Bullet", parent=sample["BodyText"], fontName="Times-Roman", fontSize=8.5, leading=10.5, leftIndent=14, firstLineIndent=-8, spaceAfter=2.5),
        "small": ParagraphStyle("V2Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.3, leading=8.8, alignment=TA_LEFT),
        "caption": ParagraphStyle("V2Caption", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.2, leading=8.7, alignment=TA_JUSTIFY, textColor=colors.HexColor("#52606D"), leftIndent=8, rightIndent=8, spaceAfter=7),
    }


def _page_decor(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#BCCCDC"))
    canvas.setLineWidth(.4)
    canvas.line(doc.leftMargin, height - .39 * inch, width - doc.rightMargin, height - .39 * inch)
    canvas.setFont("Helvetica", 6.9)
    canvas.setFillColor(colors.HexColor("#7B8794"))
    canvas.drawString(doc.leftMargin, height - .30 * inch, "Trustworthy AI Research Lab - V2 Final Correction")
    canvas.drawRightString(width - doc.rightMargin, .29 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _table(lines: list[str], style: dict[str, ParagraphStyle], width: float) -> Table:
    rows = []
    for line in lines:
        values = [value.strip() for value in line.strip().strip("|").split("|")]
        if values and all(set(value) <= {"-", ":"} for value in values):
            continue
        rows.append([Paragraph(_inline(value), style["small"]) for value in values])
    columns = len(rows[0])
    table = Table(rows, colWidths=[width / columns] * columns, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2EC")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102A43")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#BCCCDC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _figure(path: Path, width: float, caption: str, style: dict[str, ParagraphStyle]) -> list[object]:
    from PIL import Image as PILImage

    with PILImage.open(path) as source:
        image_width, image_height = source.size
    target_width = min(width, 6.55 * inch)
    target_height = target_width * image_height / image_width
    return [
        Spacer(1, 4),
        Image(str(path), width=target_width, height=target_height),
        Spacer(1, 2),
        Paragraph(_inline(caption), style["caption"]),
    ]


def _markdown_story(
    source: Path,
    style: dict[str, ParagraphStyle],
    available: float,
    figure_dir: Path,
) -> list[object]:
    lines = source.read_text(encoding="utf-8").splitlines()
    figure_after = {
        "### 8.2 SciFact Dev matched comparison": (
            "dev_ablation_aurc.png",
            "Figure 1. Corrective replay of the matched SciFact Dev ablation. Lower AURC is better; the paired intervals, reported in text, cross zero.",
        ),
        "### 10.1 E1 errors": (
            "dev_e1_confusion_matrix.png",
            "Figure 2. Eligible SciFact Dev confusion matrix. The pronounced SUPPORT recall deficit is visible in the off-diagonal counts.",
        ),
        "### 10.4 Evidence perturbations and calibration": (
            "perturbation_rank_stability.png",
            "Figure 3. Rank stability under prespecified synthetic perturbations. The sampled-document condition does not establish semantic irrelevance.",
        ),
    }
    story: list[object] = []
    index = 0
    abstract_next = False
    pending_figure: tuple[str, str] | None = None
    while index < len(lines):
        raw = lines[index].strip()
        if not raw:
            index += 1
            continue
        if raw.startswith("# "):
            story.append(Paragraph(_inline(raw[2:]), style["title"]))
        elif raw.startswith("**Research chronology:") or raw.startswith("**Protocol status:") or raw.startswith("**Latest scientific correction:"):
            story.append(Paragraph(_inline(raw), style["meta"]))
        elif raw.startswith("## "):
            heading = raw[3:]
            story.append(Paragraph(_inline(heading), style["h1"]))
            abstract_next = heading == "Abstract"
        elif raw.startswith("### "):
            story.append(Paragraph(_inline(raw[4:]), style["h2"]))
            pending_figure = figure_after.get(raw)
        elif raw.startswith("| "):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            story.extend([Spacer(1, 3), _table(table_lines, style, available), Spacer(1, 5)])
            if pending_figure:
                story.extend(_figure(figure_dir / pending_figure[0], available, pending_figure[1], style))
                pending_figure = None
            continue
        elif re.match(r"^[0-9]+\. ", raw):
            story.append(Paragraph(_inline(raw), style["bullet"]))
        elif raw.startswith("- "):
            story.append(Paragraph("- " + _inline(raw[2:]), style["bullet"]))
        else:
            story.append(Paragraph(_inline(raw), style["abstract"] if abstract_next else style["body"]))
            abstract_next = False
            if pending_figure:
                story.extend(_figure(figure_dir / pending_figure[0], available, pending_figure[1], style))
                pending_figure = None
        index += 1
    return story


def build_paper(root: Path, output: Path) -> None:
    style = _styles()
    doc = SimpleDocTemplate(
        str(output), pagesize=letter, leftMargin=.57 * inch, rightMargin=.57 * inch,
        topMargin=.54 * inch, bottomMargin=.50 * inch,
        title="Evidence-Aware Risk Scoring for Scientific Claim Verification - V2 Final",
        author="Human owner review pending; AI-assisted research artifact",
        subject="Corrected V2 scientific manuscript",
    )
    available = letter[0] - doc.leftMargin - doc.rightMargin
    story = _markdown_story(
        root / "paper/Trustworthy_AI_Research_Lab_V2_Final.md",
        style,
        available,
        root / "reports/research_upgrade_v2/corrections/2026-10-14/results/figures",
    )
    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)


def build_summary(root: Path, output: Path) -> None:
    style = _styles()
    doc = SimpleDocTemplate(
        str(output), pagesize=letter, leftMargin=.58 * inch, rightMargin=.58 * inch,
        topMargin=.48 * inch, bottomMargin=.44 * inch,
        title="Evidence-Aware Risk Scoring - One-Page Summary",
        author="Human owner review pending; AI-assisted research artifact",
        subject="Corrected one-page undergraduate research summary",
    )
    story: list[object] = [
        Paragraph("Evidence-Aware Risk Scoring for Scientific Claim Verification", style["title"]),
        Paragraph("Corrected V2 One-Page Academic Summary - 14 October 2026", style["meta"]),
        HRFlowable(width="100%", thickness=.7, color=colors.HexColor("#0F4C5C")),
        Spacer(1, 6),
    ]
    summary_style = ParagraphStyle(
        "SummaryBody", parent=style["body"], fontSize=8.25, leading=10.0, spaceAfter=4.1
    )
    for line in (root / "reports/research_upgrade_v2/RESEARCH_ONE_PAGE_SUMMARY.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        story.append(Paragraph(_inline(line), summary_style))
    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    build_paper(root, root / "paper/Trustworthy_AI_Research_Lab_V2_Final.pdf")
    build_summary(root, root / "paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf")


if __name__ == "__main__":
    main()
