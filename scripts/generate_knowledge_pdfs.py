from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
DOCS_PDF_ROOT = DOCS_ROOT / "pdf"
OUTPUT_PDF_ROOT = ROOT / "output" / "pdf"


def _register_font(name: str, path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    try:
        pdfmetrics.registerFont(TTFont(name, str(path)))
        return name
    except Exception:
        return fallback


FONT_SERIF = _register_font("PrimeVarSerif", Path("C:/Windows/Fonts/georgia.ttf"), "Times-Roman")
FONT_SERIF_BOLD = _register_font("PrimeVarSerif-Bold", Path("C:/Windows/Fonts/georgiab.ttf"), "Times-Bold")
FONT_SANS = _register_font("PrimeVarSans", Path("C:/Windows/Fonts/arial.ttf"), "Helvetica")
FONT_SANS_BOLD = _register_font("PrimeVarSans-Bold", Path("C:/Windows/Fonts/arialbd.ttf"), "Helvetica-Bold")
FONT_SANS_ITALIC = _register_font("PrimeVarSans-Italic", Path("C:/Windows/Fonts/ariali.ttf"), "Helvetica-Oblique")
FONT_MONO = "Courier"

PDF_SOURCES = {
    "manual": {
        "markdown": DOCS_ROOT / "manual_usuario.md",
        "pdf": DOCS_PDF_ROOT / "manual_usuario.pdf",
        "title": "PrimeVarClass",
        "subtitle": "Manual do usuário",
        "language": "Português-BR",
        "support_label": "Documento de apoio",
        "description": "Pesquisa translacional, validação computacional e interpretação responsável de variantes missense.",
        "page_label": "Página",
    },
    "manual_en": {
        "markdown": DOCS_ROOT / "user_manual_en.md",
        "pdf": DOCS_PDF_ROOT / "user_manual_en.pdf",
        "title": "PrimeVarClass",
        "subtitle": "User Manual",
        "language": "English",
        "support_label": "Support document",
        "description": "Translational research, computational validation, and responsible interpretation of missense variants.",
        "page_label": "Page",
    },
    "glossary": {
        "markdown": DOCS_ROOT / "glossario_primevarclass.md",
        "pdf": DOCS_PDF_ROOT / "glossario_primevarclass.pdf",
        "title": "PrimeVarClass",
        "subtitle": "Glossário",
        "language": "Português-BR",
        "support_label": "Documento de apoio",
        "description": "Pesquisa translacional, validação computacional e interpretação responsável de variantes missense.",
        "page_label": "Página",
    },
    "glossary_en": {
        "markdown": DOCS_ROOT / "glossary_primevarclass_en.md",
        "pdf": DOCS_PDF_ROOT / "glossary_primevarclass_en.pdf",
        "title": "PrimeVarClass",
        "subtitle": "Glossary",
        "language": "English",
        "support_label": "Support document",
        "description": "Translational research, computational validation, and responsible interpretation of missense variants.",
        "page_label": "Page",
    },
}


@dataclass
class BuildResult:
    source: Path
    pdf: Path
    mirror_pdf: Path
    page_count: int


class AccentRule(Flowable):
    def __init__(self, width: float = 160 * mm, height: float = 1.3 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#D77A3D"))
        canvas.roundRect(0, 0, self.width * 0.58, self.height, self.height / 2, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#2A9D8F"))
        canvas.roundRect(self.width * 0.60, 0, self.width * 0.28, self.height, self.height / 2, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#E9C46A"))
        canvas.roundRect(self.width * 0.90, 0, self.width * 0.10, self.height, self.height / 2, stroke=0, fill=1)
        canvas.restoreState()


class SoftBox(Flowable):
    def __init__(self, text: str, style: ParagraphStyle, width: float):
        super().__init__()
        self.text = text
        self.style = style
        self.width = width
        self._paragraph = Paragraph(text, style)

    def wrap(self, availWidth: float, availHeight: float):
        self.width = min(self.width, availWidth)
        _, paragraph_height = self._paragraph.wrap(self.width - 16 * mm, availHeight)
        return self.width, paragraph_height + 12 * mm

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#FFF8ED"))
        canvas.setStrokeColor(colors.HexColor("#EBD6B6"))
        canvas.roundRect(0, 0, self.width, self.height, 8 * mm, stroke=1, fill=1)
        self._paragraph.drawOn(canvas, 8 * mm, 6 * mm)
        canvas.restoreState()


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline_markdown(text: str) -> str:
    escaped = _escape(text)
    escaped = re.sub(r"`([^`]+)`", rf"<font name='{FONT_MONO}'>\1</font>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=FONT_SERIF_BOLD,
            fontSize=34,
            leading=38,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#16323A"),
            spaceAfter=8 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName=FONT_SANS,
            fontSize=15,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#47666A"),
            spaceAfter=18 * mm,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT_SERIF_BOLD,
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#16323A"),
            spaceBefore=10 * mm,
            spaceAfter=5 * mm,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT_SERIF_BOLD,
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#245C63"),
            spaceBefore=7 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=FONT_SANS,
            fontSize=9.6,
            leading=14.2,
            textColor=colors.HexColor("#1F3137"),
            spaceAfter=3.2 * mm,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName=FONT_SANS,
            fontSize=9.4,
            leading=13.4,
            leftIndent=7 * mm,
            firstLineIndent=-3.5 * mm,
            bulletIndent=0,
            textColor=colors.HexColor("#1F3137"),
            spaceAfter=2.2 * mm,
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["Code"],
            fontName=FONT_MONO,
            fontSize=8.2,
            leading=10.8,
            leftIndent=5 * mm,
            rightIndent=5 * mm,
            backColor=colors.HexColor("#F1EFE8"),
            borderColor=colors.HexColor("#D8D0C3"),
            borderWidth=0.5,
            borderPadding=5,
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base["BodyText"],
            fontName=FONT_SANS_ITALIC,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#3D5559"),
            leftIndent=8 * mm,
            rightIndent=5 * mm,
            spaceBefore=2 * mm,
            spaceAfter=4 * mm,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["BodyText"],
            fontName=FONT_SANS,
            fontSize=8.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6C7F80"),
        ),
    }


def _cover_story(config: dict[str, str]) -> list[Flowable]:
    styles = _styles()
    language = config["language"]
    return [
        Spacer(1, 52 * mm),
        Paragraph(config["title"], styles["cover_title"]),
        Paragraph(config["subtitle"], styles["cover_subtitle"]),
        AccentRule(width=120 * mm),
        Spacer(1, 12 * mm),
        Paragraph(f"{config['support_label']} - {language}", styles["meta"]),
        Spacer(1, 4 * mm),
        Paragraph(config["description"], styles["meta"]),
        PageBreak(),
    ]


def _parse_markdown(markdown: str, *, doc_width: float) -> list[Flowable]:
    styles = _styles()
    story: list[Flowable] = []
    code_lines: list[str] = []
    in_code = False
    pending_paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not pending_paragraph:
            return
        text = " ".join(item.strip() for item in pending_paragraph if item.strip())
        pending_paragraph.clear()
        if text:
            story.append(Paragraph(_inline_markdown(text), styles["body"]))

    def flush_code() -> None:
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            code_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                in_code = False
                flush_code()
            else:
                flush_paragraph()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(_inline_markdown(line[2:].strip()), styles["h1"]))
            story.append(AccentRule(width=80 * mm, height=0.9 * mm))
            story.append(Spacer(1, 3 * mm))
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(KeepTogether([Paragraph(_inline_markdown(line[3:].strip()), styles["h2"])]))
            continue
        if line.startswith("> "):
            flush_paragraph()
            story.append(SoftBox(_inline_markdown(line[2:].strip()), styles["quote"], doc_width))
            story.append(Spacer(1, 2 * mm))
            continue
        if line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph(_inline_markdown(line[2:].strip()), styles["bullet"], bulletText="•"))
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            number, text = line.split(". ", 1)
            story.append(Paragraph(_inline_markdown(text), styles["bullet"], bulletText=f"{number}."))
            continue
        pending_paragraph.append(line)
    flush_paragraph()
    flush_code()
    return story


def _draw_page(canvas, document, *, subtitle: str, page_label: str) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D8E1DD"))
    canvas.setLineWidth(0.4)
    canvas.line(document.leftMargin, height - 17 * mm, width - document.rightMargin, height - 17 * mm)
    canvas.setFont(FONT_SANS, 8)
    canvas.setFillColor(colors.HexColor("#647A7C"))
    canvas.drawString(document.leftMargin, height - 13 * mm, "PrimeVarClass")
    canvas.drawRightString(width - document.rightMargin, height - 13 * mm, subtitle)
    canvas.line(document.leftMargin, 15 * mm, width - document.rightMargin, 15 * mm)
    canvas.drawCentredString(width / 2, 9 * mm, f"{page_label} {document.page}")
    canvas.restoreState()


def build_pdf(doc_id: str, config: dict[str, str]) -> BuildResult:
    source = Path(config["markdown"])
    pdf = Path(config["pdf"])
    pdf.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF_ROOT.mkdir(parents=True, exist_ok=True)
    markdown = source.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(pdf),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
        title=f"{config['title']} - {config['subtitle']}",
        author="PrimeVarClass",
    )
    story = _cover_story(config)
    story.extend(_parse_markdown(markdown, doc_width=A4[0] - 36 * mm))
    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_page(c, d, subtitle=config["subtitle"], page_label=config["page_label"]),
        onLaterPages=lambda c, d: _draw_page(c, d, subtitle=config["subtitle"], page_label=config["page_label"]),
    )

    mirror_pdf = OUTPUT_PDF_ROOT / pdf.name
    shutil.copy2(pdf, mirror_pdf)
    try:
        from pypdf import PdfReader

        page_count = len(PdfReader(str(pdf)).pages)
    except Exception:
        page_count = 0
    return BuildResult(source=source, pdf=pdf, mirror_pdf=mirror_pdf, page_count=page_count)


def build_all(doc_ids: Iterable[str] | None = None) -> list[BuildResult]:
    selected_ids = list(doc_ids or PDF_SOURCES.keys())
    return [build_pdf(doc_id, PDF_SOURCES[doc_id]) for doc_id in selected_ids]


def main() -> int:
    results = build_all()
    for result in results:
        print(f"{result.pdf} ({result.page_count} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
