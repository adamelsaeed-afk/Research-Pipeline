# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx", "markdown-it-py", "linkify-it-py"]
# ///
"""Convert a Markdown research report to a formatted Word (.docx) document.

Parses Markdown with markdown-it-py (never regex) and emits Word elements via
python-docx. Links are emitted as real clickable hyperlinks (python-docx has no
native hyperlink API, so this is done at the XML level). Raw HTML blocks — such
as the agent-instruction comments in the report templates — are skipped.

Usage:
    uv run scripts/export_to_word.py --input report.md --output report.docx --template corporate

The --template flag selects one of three style modules from templates/word/:
corporate, academic, minimal. Dependencies are declared in the PEP 723 block
above, so the first `uv run` installs them automatically.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from markdown_it import MarkdownIt

SCRIPT_DIR = Path(__file__).resolve().parent
WORD_TEMPLATES_DIR = SCRIPT_DIR.parent / "templates" / "word"

LIST_BULLET_STYLES = {1: "List Bullet", 2: "List Bullet 2", 3: "List Bullet 3"}


# ---------------------------------------------------------------------------
# Style loading
# ---------------------------------------------------------------------------

def load_style(name: str) -> dict:
    if str(WORD_TEMPLATES_DIR) not in sys.path:
        sys.path.insert(0, str(WORD_TEMPLATES_DIR))
    module = importlib.import_module(name)
    return module.STYLE


# ---------------------------------------------------------------------------
# Low-level XML helpers
# ---------------------------------------------------------------------------

def _force_style_font(style, font_name: str) -> None:
    """Set the font on a style and strip theme-font overrides, which would
    otherwise take precedence over explicit font names in some renderers."""
    style.font.name = font_name
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.set(qn(attr), font_name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        r_fonts.attrib.pop(qn(attr), None)


def _force_style_color(style, hex_color: str) -> None:
    r_pr = style.element.get_or_add_rPr()
    color = r_pr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        r_pr.append(color)
    color.set(qn("w:val"), hex_color)
    color.attrib.pop(qn("w:themeColor"), None)


def _shade_element(fill: str) -> OxmlElement:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    return shd


def _set_table_borders(table, mode: str, color: str) -> None:
    borders = OxmlElement("w:tblBorders")
    horizontal_only = {"top", "bottom", "insideH"}
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        visible = mode == "all" or (mode == "horizontal" and edge in horizontal_only)
        el.set(qn("w:val"), "single" if visible else "none")
        el.set(qn("w:sz"), "4" if visible else "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color if visible else "auto")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def _shade_cell(cell, fill: str) -> None:
    cell._tc.get_or_add_tcPr().append(_shade_element(fill))


def _mark_header_row(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


# ---------------------------------------------------------------------------
# Document styling
# ---------------------------------------------------------------------------

def apply_document_style(doc: Document, style: dict) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(style["margins_in"]["top"])
    section.bottom_margin = Inches(style["margins_in"]["bottom"])
    section.left_margin = Inches(style["margins_in"]["left"])
    section.right_margin = Inches(style["margins_in"]["right"])

    normal = doc.styles["Normal"]
    _force_style_font(normal, style["body_font"])
    normal.font.size = Pt(style["body_size_pt"])
    pf = normal.paragraph_format
    pf.line_spacing = style["line_spacing"]
    pf.space_before = Pt(0)
    pf.space_after = Pt(style["space_after_pt"])

    for level in range(1, 7):
        heading = doc.styles[f"Heading {level}"]
        size = style["heading_sizes_pt"].get(level, style["body_size_pt"] + (6 - level))
        _force_style_font(heading, style["heading_font"])
        _force_style_color(heading, style["heading_color"])
        heading.font.size = Pt(size)
        heading.font.bold = True
        heading.paragraph_format.keep_with_next = True
        heading.paragraph_format.space_before = Pt(14 if level == 1 else 10)
        heading.paragraph_format.space_after = Pt(6)


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, doc: Document, style: dict):
        self.doc = doc
        self.s = style
        self._heading_counters = [0, 0, 0]  # for Heading 2 / 3 / 4 numbering
        self._in_quote = False
        self._pending_marker = None  # "N." prefix for the next ordered item paragraph

    # -- block walker -------------------------------------------------------

    def render(self, tokens: list, list_stack: list | None = None, depth: int = 0) -> None:
        list_stack = list_stack if list_stack is not None else []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            kind = tok.type

            if kind == "heading_open":
                level = int(tok.tag[1])
                self._add_heading(level, tokens[i + 1])
                i += 3
                continue

            if kind == "paragraph_open":
                self._add_paragraph(tokens[i + 1], list_stack, depth)
                i += 3
                continue

            if kind in ("bullet_list_open", "ordered_list_open"):
                entry = {"kind": "bullet" if kind.startswith("bullet") else "ordered", "n": 1}
                if kind == "ordered_list_open":
                    start = tok.attrGet("start")
                    entry["n"] = int(start) if start else 1
                list_stack.append(entry)
                i += 1
                continue

            if kind in ("bullet_list_close", "ordered_list_close"):
                list_stack.pop()
                i += 1
                continue

            if kind == "list_item_open":
                close = _find_close(tokens, i, "list_item")
                self._add_list_item(tokens[i + 1:close], list_stack, depth)
                i = close + 1
                continue

            if kind == "table_open":
                close = _find_close(tokens, i, "table")
                self._add_table(tokens[i + 1:close])
                i = close + 1
                continue

            if kind == "fence":
                self._add_code_block(tok.content)
                i += 1
                continue

            if kind == "blockquote_open":
                close = _find_close(tokens, i, "blockquote")
                self._in_quote = True
                self.render(tokens[i + 1:close], list_stack, depth)
                self._in_quote = False
                i = close + 1
                continue

            # hr, html_block (template instruction comments), and anything
            # unhandled are skipped gracefully.
            i += 1

    def _add_list_item(self, inner: list, list_stack: list, depth: int) -> None:
        top = list_stack[-1]
        if top["kind"] == "ordered":
            self._pending_marker = f"{top['n']}."
            top["n"] += 1
        self.render(inner, list_stack, depth + 1)

    # -- paragraphs and headings ---------------------------------------------

    def _add_heading(self, level: int, inline_tok) -> None:
        p = self.doc.add_paragraph(style=f"Heading {min(level, 6)}")
        if self.s["heading_numbering"] and 2 <= level <= 4:
            idx = level - 2
            self._heading_counters[idx] += 1
            for k in range(idx + 1, len(self._heading_counters)):
                self._heading_counters[k] = 0
            prefix = ".".join(str(c) for c in self._heading_counters[: idx + 1]) + ". "
            p.add_run(prefix)
        self._render_inline(inline_tok.children, p)

    def _add_paragraph(self, inline_tok, list_stack: list, depth: int) -> None:
        style_name = "Normal"
        pf = None
        if list_stack:
            current = list_stack[-1]["kind"]
            if current == "bullet":
                style_name = LIST_BULLET_STYLES.get(min(depth, 3), "List Bullet 3")
            else:  # ordered item paragraph
                style_name = "List Paragraph"
        if self._in_quote and not list_stack:
            style_name = "Quote"

        p = self.doc.add_paragraph(style=style_name)

        if list_stack and list_stack[-1]["kind"] == "ordered":
            pf = p.paragraph_format
            pf.left_indent = Inches(0.25 * depth + 0.25)
            pf.first_line_indent = Inches(-0.25)
        elif list_stack and depth > 3:
            p.paragraph_format.left_indent = Inches(0.25 * (depth - 3))

        if self._pending_marker is not None:
            marker = p.add_run(self._pending_marker + " ")
            marker.bold = True
            self._pending_marker = None

        self._render_inline(inline_tok.children, p)

    # -- tables ---------------------------------------------------------------

    def _add_table(self, table_tokens: list) -> None:
        rows: list[dict] = []
        in_header = False
        i = 0
        while i < len(table_tokens):
            tok = table_tokens[i]
            if tok.type == "thead_open":
                in_header = True
                i += 1
                continue
            if tok.type == "thead_close":
                in_header = False
                i += 1
                continue
            if tok.type == "tr_open":
                close = _find_close(table_tokens, i, "tr")
                cells = self._parse_row(table_tokens[i + 1:close])
                rows.append({"header": in_header, "cells": cells})
                i = close + 1
                continue
            i += 1

        if not rows:
            return
        ncols = max(len(r["cells"]) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=ncols)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        tcfg = self.s["table"]
        _set_table_borders(table, tcfg["borders"], tcfg["border_color"])

        body_index = 0
        for r_idx, row in enumerate(rows):
            word_row = table.rows[r_idx]
            if row["header"]:
                _mark_header_row(word_row)
            else:
                body_index += 1
            for c_idx in range(ncols):
                cell = word_row.cells[c_idx]
                cell_data = row["cells"][c_idx] if c_idx < len(row["cells"]) else (None, None)
                inline_tok, align = cell_data
                p = cell.paragraphs[0]
                pf = p.paragraph_format
                pf.line_spacing = 1.0
                pf.space_before = Pt(2)
                pf.space_after = Pt(2)
                if align == "right":
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif align == "center":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                is_header = row["header"]
                if is_header and tcfg["header_fill"]:
                    _shade_cell(cell, tcfg["header_fill"])
                if not is_header and tcfg["alt_fill"] and body_index % 2 == 0:
                    _shade_cell(cell, tcfg["alt_fill"])

                color = tcfg["header_text"] if is_header else None
                bold = tcfg["header_bold"] if is_header else False
                if inline_tok is not None:
                    self._render_inline(inline_tok.children, p, bold=bold, color=color)

    def _parse_row(self, row_tokens: list) -> list:
        cells = []
        i = 0
        while i < len(row_tokens):
            tok = row_tokens[i]
            if tok.type in ("th_open", "td_open"):
                close_type = tok.type.replace("_open", "_close")
                j = i + 1
                while row_tokens[j].type != close_type:
                    j += 1
                align = None
                style_attr = tok.attrGet("style") or ""
                if "text-align:right" in style_attr:
                    align = "right"
                elif "text-align:center" in style_attr:
                    align = "center"
                cells.append((row_tokens[i + 1], align))
                i = j + 1
                continue
            i += 1
        return cells

    # -- code blocks -----------------------------------------------------------

    def _add_code_block(self, content: str) -> None:
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = Pt(6)
        pf.space_after = Pt(6)
        p._p.get_or_add_pPr().append(_shade_element("F5F5F5"))
        lines = content[:-1].split("\n") if content.endswith("\n") else content.split("\n")
        for idx, line in enumerate(lines):
            run = p.add_run(line)
            run.font.name = self.s["mono_font"]
            run.font.size = Pt(self.s["body_size_pt"] - 1)
            if idx < len(lines) - 1:
                run.add_break()

    # -- inline rendering -------------------------------------------------------

    def _render_inline(self, children, p, bold: bool = False, color: str | None = None) -> None:
        if not children:
            return
        italic = False
        i = 0
        while i < len(children):
            tok = children[i]
            kind = tok.type
            if kind in ("text", "text_special"):
                self._add_run(p, tok.content, bold, italic, color)
            elif kind == "strong_open":
                bold = True
            elif kind == "strong_close":
                bold = False
            elif kind == "em_open":
                italic = True
            elif kind == "em_close":
                italic = False
            elif kind == "code_inline":
                run = self._add_run(p, tok.content, bold, italic, color)
                run.font.name = self.s["mono_font"]
                run.font.size = Pt(self.s["body_size_pt"] - 1)
                run._element.get_or_add_rPr().append(_shade_element("F2F2F2"))
            elif kind == "softbreak":
                self._add_run(p, " ", bold, italic, color)
            elif kind == "hardbreak":
                p.add_break()
            elif kind == "link_open":
                url = tok.attrGet("href") or ""
                close = _find_inline_close(children, i, "link")
                self._add_hyperlink(p, url, children[i + 1:close], bold, italic, color)
                i = close
            elif kind in ("image", "html_inline", "link_close"):
                pass
            i += 1

    def _add_run(self, p, text: str, bold: bool, italic: bool, color: str | None):
        run = p.add_run(text)
        if bold:
            run.bold = True
        if italic:
            run.italic = True
        if color:
            run.font.color.rgb = RGBColor.from_string(color)
        return run

    def _add_hyperlink(self, p, url: str, inner: list, bold: bool, italic: bool, color) -> None:
        """Clickable hyperlink via raw XML — python-docx has no native API."""
        hyperlink = OxmlElement("w:hyperlink")
        r_id = p.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        hyperlink.set(qn("r:id"), r_id)

        link_color = self.s["link_color"]
        run_color = None if color == link_color else link_color  # header cells keep header color
        segments: list[tuple[str, bool, bool]] = []
        bold_f, italic_f = bold, italic
        for tok in inner:
            if tok.type in ("text", "text_special"):
                segments.append((tok.content, bold_f, italic_f))
            elif tok.type == "strong_open":
                bold_f = True
            elif tok.type == "strong_close":
                bold_f = False
            elif tok.type == "em_open":
                italic_f = True
            elif tok.type == "em_close":
                italic_f = False
            elif tok.type == "softbreak":
                segments.append((" ", bold_f, italic_f))

        for text, seg_bold, seg_italic in segments:
            run = OxmlElement("w:r")
            r_pr = OxmlElement("w:rPr")
            if seg_bold:
                r_pr.append(OxmlElement("w:b"))
            if seg_italic:
                r_pr.append(OxmlElement("w:i"))
            color_el = OxmlElement("w:color")
            color_el.set(qn("w:val"), run_color or link_color)
            r_pr.append(color_el)
            underline = OxmlElement("w:u")
            underline.set(qn("w:val"), "single")
            r_pr.append(underline)
            run.append(r_pr)
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = text
            run.append(t)
            hyperlink.append(run)

        p._p.append(hyperlink)


def _find_close(tokens: list, i: int, base: str) -> int:
    depth = 0
    j = i
    while j < len(tokens):
        if tokens[j].type == base + "_open":
            depth += 1
        elif tokens[j].type == base + "_close":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return len(tokens) - 1


def _find_inline_close(children: list, i: int, base: str) -> int:
    depth = 0
    j = i
    while j < len(children):
        if children[j].type == base + "_open":
            depth += 1
        elif children[j].type == base + "_close":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return len(children) - 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_markdown(source: str) -> list:
    md = MarkdownIt("commonmark", {"html": True, "linkify": True})
    md.enable(["table", "linkify"])
    return md.parse(source)


def convert(input_path: str, output_path: str, template: str) -> None:
    source = Path(input_path).read_text(encoding="utf-8")
    style = load_style(template)
    doc = Document()
    apply_document_style(doc, style)
    Renderer(doc, style).render(parse_markdown(source))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="research-pipeline: convert a Markdown research report to a formatted Word (.docx) document."
    )
    parser.add_argument("--input", required=True, help="Path to the input Markdown (.md) file")
    parser.add_argument("--output", required=True, help="Path for the output Word (.docx) file")
    parser.add_argument(
        "--template",
        default="corporate",
        choices=["corporate", "academic", "minimal"],
        help="Word style template (default: corporate)",
    )
    args = parser.parse_args()
    convert(args.input, args.output, args.template)
    print(f"Saved: {args.output} (template: {args.template})")


if __name__ == "__main__":
    main()
