#!/usr/bin/env python3
"""
md_to_typst/convert.py — Markdown → Typst (.typ) conversion pipeline.

Converts a Markdown article (using the Edition publishing conventions) to a
Typst source file, then optionally compiles it to PDF via `typst compile`.

Pipeline: Markdown → .typ → PDF (via `typst compile`)

Usage:
    python3 convert.py article.md --style intelligence [--output out.pdf] [--compile]

Edition Markdown conventions handled:
  - ATX headings # … ######
  - **bold**, *italic*, `inline code`
  - [text](url) links
  - ![alt](src){width=X%} images
  - Pipe tables  | col | col |
  - Fenced code blocks (``` lang ... ```)
  - ```mermaid``` diagrams → placeholder
  - [^key] / [^key]: footnotes
  - <div class="single-column">  full-width section
  - <div class="full-width">     full-width block (tables)
  - <div class="page-break">     explicit page break
  - <div class="key-takeaways">  highlighted box
  - | pull-quote / | source: ... lines (no trailing |)
  - > [!NOTE] / > [!WARNING]  GFM callouts
  - Horizontal rules ---
  - Ordered and unordered lists
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Inline Markdown → Typst conversion
# ---------------------------------------------------------------------------

def _escape_typst(text: str) -> str:
    """Escape characters that have special meaning in Typst markup."""
    # Order matters: backslash first, then other specials.
    # We do NOT escape inside already-converted #func(...) calls.
    text = text.replace("\\", "\\\\")
    # @ introduces labels/references in Typst
    text = text.replace("@", "\\@")
    # < and > have meaning in links
    text = text.replace("<", "\\<").replace(">", "\\>")
    # $ introduces math
    text = text.replace("$", "\\$")
    # _ and * are emphasis markers in Typst markup mode
    # (we handle bold/italic separately, so escape stray ones)
    return text


# Pattern: **bold** or __bold__
_BOLD_RE   = re.compile(r'\*\*(.+?)\*\*|__(.+?)__', re.DOTALL)
# Pattern: *italic* or _italic_ (single)
_ITALIC_RE = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)')
# Pattern: `inline code`
_CODE_RE   = re.compile(r'`([^`]+)`')
# Pattern: [text](url)
_LINK_RE   = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
# Pattern: [^key] footnote reference (not definition)
_FNREF_RE  = re.compile(r'\[\^([^\]]+)\](?!:)')
# Pattern: ~~strikethrough~~
_STRIKE_RE = re.compile(r'~~(.+?)~~')


def convert_inline(text: str, footnotes: dict[str, str]) -> str:
    """
    Convert inline Markdown within a text fragment to Typst markup.

    Args:
        text:      Raw Markdown inline text.
        footnotes: Mapping of footnote key → definition text (already inline-converted).

    Returns:
        Typst markup string.
    """
    # Process in a specific order to avoid double-substitution.
    # We use placeholder tokens for already-converted spans.

    placeholders: list[str] = []

    def stash(s: str) -> str:
        placeholders.append(s)
        return f"\x00PH{len(placeholders)-1}\x00"

    # 0. Convert/strip HTML tags before escaping.
    #    Raw HTML can appear in div inner content (e.g. <img>, <p>, <em>).
    #    Convert recognised tags; strip the rest.

    # <img src="..." alt="..." style="..."> → #image(...)
    def replace_html_img(m2: re.Match) -> str:
        attrs = m2.group(1)
        src_m = re.search(r'src=["\']([^"\']+)["\']', attrs)
        alt_m = re.search(r'alt=["\']([^"\']*)["\']', attrs)
        if src_m:
            src = _resolve_image_src(src_m.group(1))
            alt = alt_m.group(1) if alt_m else ''
            if alt:
                return stash(
                    f'#figure(image("{src}", width: 100%), caption: [{alt}])'
                )
            return stash(f'#image("{src}", width: 100%)')
        return ''
    text = re.sub(r'<img\s+([^>]+)/?>', replace_html_img, text, flags=re.IGNORECASE)

    # <em>…</em> → _…_
    text = re.sub(r'<em>(.*?)</em>', lambda m2: stash(f'_{m2.group(1)}_'), text, flags=re.IGNORECASE | re.DOTALL)
    # <strong>…</strong> → *…*
    text = re.sub(r'<strong>(.*?)</strong>', lambda m2: stash(f'*{m2.group(1)}*'), text, flags=re.IGNORECASE | re.DOTALL)
    # <br>, <br/> → linebreak
    text = re.sub(r'<br\s*/?>', stash('\\ '), text, flags=re.IGNORECASE)
    # Strip remaining block-level HTML tags (p, div, span, etc.)
    text = re.sub(r'</?(?:p|div|span|figure|figcaption|section|article|header|footer|h[1-6])\b[^>]*>', '', text, flags=re.IGNORECASE)
    # Strip any remaining HTML tags (catch-all)
    text = re.sub(r'<[^>]+>', '', text)

    # 1. Inline code (protect from further processing)
    def replace_code(m: re.Match) -> str:
        return stash(f"`{m.group(1)}`")
    text = _CODE_RE.sub(replace_code, text)

    # 2. Links  [text](url)
    def replace_link(m: re.Match) -> str:
        link_text = m.group(1)
        url       = m.group(2)
        return stash(f'#link("{url}")[{link_text}]')
    text = _LINK_RE.sub(replace_link, text)

    # 3. Footnote references  [^key]
    def replace_fnref(m: re.Match) -> str:
        key = m.group(1)
        defn = footnotes.get(key, "")
        if defn:
            inner = convert_inline(defn, {})   # no nested footnotes
            return stash(f"#footnote[{inner}]")
        return stash(f"#footnote[{key}]")
    text = _FNREF_RE.sub(replace_fnref, text)

    # 4. Bold **text**
    def replace_bold(m: re.Match) -> str:
        inner = m.group(1) or m.group(2)
        return stash(f"*{inner}*")
    text = _BOLD_RE.sub(replace_bold, text)

    # 5. Italic *text*
    def replace_italic(m: re.Match) -> str:
        inner = m.group(1) or m.group(2)
        return stash(f"_{inner}_")
    text = _ITALIC_RE.sub(replace_italic, text)

    # 6. Strikethrough ~~text~~
    def replace_strike(m: re.Match) -> str:
        return stash(f"#strike[{m.group(1)}]")
    text = _STRIKE_RE.sub(replace_strike, text)

    # 7. Escape remaining special Typst characters
    # (do it per-segment between placeholders so we don't corrupt them)
    parts = re.split(r'(\x00PH\d+\x00)', text)
    escaped_parts = []
    for part in parts:
        if re.match(r'\x00PH\d+\x00', part):
            escaped_parts.append(part)
        else:
            escaped_parts.append(_escape_typst(part))
    text = ''.join(escaped_parts)

    # 8. Restore placeholders
    for i, ph in enumerate(placeholders):
        text = text.replace(f"\x00PH{i}\x00", ph)

    return text


# ---------------------------------------------------------------------------
# Table conversion
# ---------------------------------------------------------------------------

_SEP_CELL_RE = re.compile(r'^[ \t]*:?-+:?[ \t]*$')


def _is_sep_row(cells: list[str]) -> bool:
    return bool(cells) and all(_SEP_CELL_RE.match(c) for c in cells)


def _parse_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]


def convert_table(block: str, footnotes: dict[str, str]) -> str:
    """Convert a Markdown pipe table block to a Typst #table()."""
    lines = [ln for ln in block.splitlines() if ln.strip()]
    if len(lines) < 2:
        return block

    rows = [_parse_row(ln) for ln in lines]
    if not _is_sep_row(rows[1]):
        return block   # not a valid GFM table

    sep_cells  = rows[1]
    header_row = rows[0]
    data_rows  = rows[2:]

    n_cols = max(len(header_row), len(sep_cells))

    def align_str(cell: str) -> str:
        c = cell.strip()
        if c.startswith(':') and c.endswith(':'):
            return "center"
        if c.endswith(':'):
            return "right"
        return "left"

    aligns = [align_str(sep_cells[i] if i < len(sep_cells) else '') for i in range(n_cols)]
    col_spec = ", ".join(f"1fr" for _ in range(n_cols))

    lines_out: list[str] = []
    lines_out.append(f"#block(width: 100%)[")
    lines_out.append(f"#set text(size: 8.5pt)  // tables slightly smaller than body")
    lines_out.append(f"#table(")
    lines_out.append(f"  columns: ({col_spec}),")
    lines_out.append(f"  stroke: none,")
    lines_out.append(f"  inset: (x: 0.55em, y: 0.35em),")

    # Header cells
    for i, hdr in enumerate(header_row):
        if i >= n_cols:
            break
        content = convert_inline(hdr, footnotes)
        lines_out.append(
            f"  table.cell(fill: rgb(\"#1d4b7a\"), align: {aligns[i]})"
            f"[#text(fill: white, weight: \"bold\")[{content}]],"
        )

    # Data rows with alternating fill
    for row_idx, row in enumerate(data_rows):
        fill = 'rgb("#e8eef4")' if row_idx % 2 == 1 else "white"
        for col_idx in range(n_cols):
            cell_content = row[col_idx] if col_idx < len(row) else ""
            content = convert_inline(cell_content, footnotes)
            lines_out.append(
                f"  table.cell(fill: {fill}, align: {aligns[col_idx]})[{content}],"
            )

    lines_out.append(")")   # close #table
    lines_out.append("]")   # close #block
    return "\n".join(lines_out)


# ---------------------------------------------------------------------------
# Pull-quote detection and conversion
# ---------------------------------------------------------------------------

_PULLQUOTE_LINE_RE = re.compile(r'^(?:\| )(?!.*\|\s*$)(.+)$', re.MULTILINE)


def _is_pullquote_block(lines: list[str]) -> bool:
    """Return True if every line in the block starts with '| ' and has no trailing |."""
    return all(re.match(r'^\| (?!.*\|\s*$)', ln) for ln in lines if ln.strip())


def convert_pullquote_block(lines: list[str], footnotes: dict[str, str]) -> str:
    """Convert a pull-quote block to a Typst #pull-quote() call."""
    stripped = [ln[2:] if ln.startswith('| ') else ln for ln in lines]

    source = None
    if stripped and re.match(r'^source:\s*', stripped[-1], re.IGNORECASE):
        source = re.sub(r'^source:\s*', '', stripped[-1], flags=re.IGNORECASE).strip()
        stripped = stripped[:-1]

    body_text = ' '.join(stripped).strip()
    body_typst = convert_inline(body_text, footnotes)

    if source:
        src_typst = convert_inline(source, footnotes)
        return f'#pull-quote(source: [{src_typst}])[{body_typst}]'
    return f'#pull-quote[{body_typst}]'


# ---------------------------------------------------------------------------
# GFM callout conversion  > [!NOTE] etc.
# ---------------------------------------------------------------------------

_CALLOUT_LABELS = {
    'NOTE': 'Note', 'TIP': 'Tip', 'IMPORTANT': 'Important',
    'WARNING': 'Warning', 'CAUTION': 'Caution',
}
_NOTE_STYLES   = {'note', 'tip'}
_WARN_STYLES   = {'warning', 'caution', 'important'}


def convert_gfm_callout(kind: str, body_lines: list[str], footnotes: dict[str, str]) -> str:
    """Convert a GFM callout block to a Typst #callout() call."""
    label = _CALLOUT_LABELS.get(kind.upper(), kind.capitalize())
    style = kind.lower()
    body_text = '\n'.join(body_lines).strip()
    body_typst = convert_paragraph_text(body_text, footnotes)

    return f'#callout(label-text: "{label}", style: "{style}")[{body_typst}]'


# ---------------------------------------------------------------------------
# Footnote extraction
# ---------------------------------------------------------------------------

_FN_DEF_RE = re.compile(
    r'^\[\^([^\]]+)\]:\s*(.+?)(?=\n\[\^|\n\n|\Z)',
    re.MULTILINE | re.DOTALL,
)


def extract_footnotes(text: str) -> tuple[str, dict[str, str]]:
    """
    Extract [^key]: definition blocks from Markdown text.

    Returns:
        (text_without_definitions, {key: definition_text})
    """
    footnotes: dict[str, str] = {}

    def collect(m: re.Match) -> str:
        key  = m.group(1)
        defn = m.group(2).strip()
        # Collapse continuation lines (indented lines belong to the same definition)
        defn = re.sub(r'\n[ \t]+', ' ', defn)
        footnotes[key] = defn
        return ''

    cleaned = _FN_DEF_RE.sub(collect, text)
    return cleaned, footnotes


# ---------------------------------------------------------------------------
# Image conversion
# ---------------------------------------------------------------------------

_IMG_RE = re.compile(
    r'!\[([^\]]*)\]\(([^)]+)\)(?:\{width=([^}]+)\})?'
)


def _resolve_image_src(src: str) -> str:
    """Resolve a relative image src to an absolute path using _md_dir.
    Absolute paths and URLs are returned unchanged."""
    if src.startswith(('/', 'http://', 'https://', 'data:')):
        return src
    if _md_dir is not None:
        resolved = (_md_dir / src).resolve()
        if resolved.exists():
            return str(resolved)
    return src


def convert_image(m: re.Match) -> str:
    alt   = m.group(1)
    src   = _resolve_image_src(m.group(2))
    width = m.group(3)

    # Convert percentage width
    if width:
        w = width.strip().rstrip('%')
        try:
            frac = float(w) / 100.0
            width_arg = f"width: {frac:.0%}"
        except ValueError:
            width_arg = "width: 100%"
    else:
        width_arg = "width: 100%"

    alt_escaped = alt.replace('"', '\\"')
    if alt:
        return (
            f'#figure(\n'
            f'  image("{src}", {width_arg}),\n'
            f'  caption: [{alt_escaped}],\n'
            f')'
        )
    return f'#image("{src}", {width_arg})'


# ---------------------------------------------------------------------------
# Block-level text processing (paragraphs within a section)
# ---------------------------------------------------------------------------

def convert_paragraph_text(text: str, footnotes: dict[str, str]) -> str:
    """
    Convert a block of Markdown-formatted text (possibly multiple paragraphs)
    to Typst inline markup.  Paragraph breaks become blank lines in Typst.
    """
    paras = re.split(r'\n{2,}', text.strip())
    result_paras = []
    for para in paras:
        # Inline images within paragraph text
        para = _IMG_RE.sub(convert_image, para)
        result_paras.append(convert_inline(para, footnotes))
    return '\n\n'.join(result_paras)


# ---------------------------------------------------------------------------
# List conversion
# ---------------------------------------------------------------------------

def convert_list_block(lines: list[str], footnotes: dict[str, str], ordered: bool) -> str:
    """Convert a list block (already split into item lines) to Typst."""
    items = []
    current: list[str] = []

    marker_re = re.compile(r'^(\s*)(\d+\.|[-*+])\s+(.*)$')

    for ln in lines:
        m = marker_re.match(ln)
        if m:
            if current:
                items.append(' '.join(current))
            current = [m.group(3)]
        elif ln.startswith('  ') and current:
            current.append(ln.strip())
        else:
            if current:
                items.append(' '.join(current))
            current = []
    if current:
        items.append(' '.join(current))

    list_type = "+" if ordered else "-"
    out_lines = []
    for item in items:
        content = convert_inline(item, footnotes)
        out_lines.append(f"{list_type} {content}")
    return '\n'.join(out_lines)


# ---------------------------------------------------------------------------
# Mermaid placeholder
# ---------------------------------------------------------------------------

_mermaid_counter = 0
_mermaid_images_dir: Path | None = None  # set per-document in convert_md_to_typ
_md_dir: Path | None = None              # directory of the source .md file; used to resolve relative image paths


def next_mermaid_placeholder() -> str:
    global _mermaid_counter
    _mermaid_counter += 1
    n = _mermaid_counter
    # If a pre-rendered PNG exists (from a previous md_to_pdf run), use it.
    if _mermaid_images_dir is not None:
        png = _mermaid_images_dir / f'_mermaid_{n}.png'
        if png.exists():
            return (
                f'#figure(\n'
                f'  image("{png}", width: 100%),\n'
                f'  caption: [Diagram {n}],\n'
                f')'
            )
    return f'#mermaid-placeholder({n})'


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

# Regex patterns for block-level detection
_HEADING_RE        = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$')
_HR_RE             = re.compile(r'^(?:-{3,}|_{3,}|\*{3,})\s*$')
_TABLE_LINE_RE     = re.compile(r'^\|')
_UL_LINE_RE        = re.compile(r'^[ \t]*[-*+]\s+')
_OL_LINE_RE        = re.compile(r'^[ \t]*\d+\.\s+')
_CALLOUT_START_RE  = re.compile(r'^> \[!(' + '|'.join(_CALLOUT_LABELS) + r')\]', re.IGNORECASE)
_PULLQUOTE_RE      = re.compile(r'^(?:\| )(?!.*\|\s*$)')
_FENCED_RE         = re.compile(r'^```(\w*)')
_DIV_OPEN_RE       = re.compile(r'^<div\s+class="([^"]+)">')
_DIV_CLOSE_RE      = re.compile(r'^</div>')
_FN_DEF_LINE_RE    = re.compile(r'^\[\^[^\]]+\]:')
_IMG_STANDALONE_RE = re.compile(r'^!\[')


def convert_md_to_typ(md_text: str, style: str = "intelligence",
                      styles_dir: Path | None = None,
                      justify: bool = True,
                      images_dir: Path | None = None,
                      md_dir: Path | None = None) -> str:
    """
    Convert Markdown text to a complete Typst source file.

    Args:
        md_text:    Raw Markdown source.
        style:      Style name (e.g. "intelligence").
        styles_dir: Absolute path to the styles/ directory.  Used to emit an
                    absolute #import path so the .typ file can be compiled from
                    any working directory.

    Returns:
        Typst source string.
    """
    # Reset mermaid state for each document
    global _mermaid_counter, _mermaid_images_dir, _md_dir
    _mermaid_counter = 0
    _mermaid_images_dir = images_dir
    # _md_dir is used by convert_image/_resolve_image_src to turn relative paths absolute
    _md_dir = md_dir if md_dir is not None else (images_dir.parent if images_dir is not None else None)

    # 1. Extract footnote definitions
    md_text, footnotes = extract_footnotes(md_text)

    # Extract YAML front-matter (if any) for title/author
    author = "Author Name"
    title  = "Article Title"
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', md_text, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        for key, dest in [('author', 'author'), ('title', 'title')]:
            km = re.search(rf'^{key}:\s*(.+)$', fm, re.MULTILINE | re.IGNORECASE)
            if km:
                if key == 'author':
                    author = km.group(1).strip().strip('"\'')
                else:
                    title = km.group(1).strip().strip('"\'')
        md_text = md_text[fm_match.end():]

    # 2. Split into logical lines for processing
    lines = md_text.splitlines()

    # 3. Build output: header (outside columns) + body (column-segmented)

    # Header: import style and apply template
    # Use absolute path so the .typ file can be compiled from any directory.
    if styles_dir is not None:
        style_path = str(styles_dir / f"{style}.typ")
    else:
        style_path = f"styles/{style}.typ"
    header_lines: list[str] = []
    header_lines.append(f'#import "{style_path}": doc, key-takeaways, insights-box, pull-quote, callout, callout-note, callout-warning, mermaid-placeholder')
    header_lines.append(f'')
    justify_val = 'true' if justify else 'false'
    header_lines.append(f'#show: doc.with(')
    header_lines.append(f'  author:   "{author}",')
    header_lines.append(f'  title:    "{title}",')
    header_lines.append(f'  pub-name: "DRASTIC",')
    header_lines.append(f'  doc-type: "OSINT RESEARCH PRODUCT",')
    header_lines.append(f'  justify:  {justify_val},')
    header_lines.append(f')')
    header_lines.append(f'')

    # Body: processed by state machine, full-width sentinels added inline
    output: list[str] = []

    # State machine
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # ── Skip blank lines (emit as paragraph separator) ──────────────────
        if not line.strip():
            output.append('')
            i += 1
            continue

        # ── Skip footnote definition lines (already extracted) ───────────────
        if _FN_DEF_LINE_RE.match(line):
            i += 1
            continue

        # ── ATX headings ─────────────────────────────────────────────────────
        m = _HEADING_RE.match(line)
        if m:
            level   = len(m.group(1))
            content = m.group(2).strip()
            equals  = '=' * level
            content_typst = convert_inline(content, footnotes)
            if level == 1:
                # h1 must always span full page width — emit as full-width block
                output.append('\x00FULLWIDTH_START\x00')
                output.append(f'{equals} {content_typst}')
                output.append('\x00FULLWIDTH_END\x00')
            else:
                output.append(f'{equals} {content_typst}')
            i += 1
            continue

        # ── Horizontal rule ───────────────────────────────────────────────────
        if _HR_RE.match(line):
            output.append('#line(length: 100%, stroke: 0.8pt + rgb("#1d4b7a"))')
            i += 1
            continue

        # ── Fenced code block ────────────────────────────────────────────────
        fm = _FENCED_RE.match(line)
        if fm:
            lang = fm.group(1)
            i += 1
            code_lines: list[str] = []
            while i < n and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            if lang.lower() == 'mermaid':
                output.append(next_mermaid_placeholder())
            else:
                code_body = '\n'.join(code_lines)
                # Escape backticks in code
                code_body = code_body.replace('`', '\\`')
                if lang:
                    output.append(f'```{lang}')
                else:
                    output.append('```')
                output.append(code_body)
                output.append('```')
            i_continue = i
            i = i_continue
            continue

        # ── GFM callout  > [!NOTE] ────────────────────────────────────────────
        cm = _CALLOUT_START_RE.match(line)
        if cm:
            kind = cm.group(1)
            i += 1
            body_lines: list[str] = []
            while i < n and lines[i].startswith('>'):
                bl = lines[i]
                if bl.startswith('> '):
                    body_lines.append(bl[2:])
                elif bl == '>':
                    body_lines.append('')
                else:
                    body_lines.append(bl[1:])
                i += 1
            output.append(convert_gfm_callout(kind, body_lines, footnotes))
            continue

        # ── Blockquote (plain >)  ─────────────────────────────────────────────
        if line.startswith('> ') or line == '>':
            bq_lines: list[str] = []
            while i < n and (lines[i].startswith('> ') or lines[i] == '>'):
                bl = lines[i]
                if bl.startswith('> '):
                    bq_lines.append(bl[2:])
                else:
                    bq_lines.append('')
                i += 1
            bq_text = ' '.join(bq_lines).strip()
            bq_typst = convert_inline(bq_text, footnotes)
            output.append(f'#quote(block: true)[{bq_typst}]')
            continue

        # ── Pull-quote  | "text" ... ──────────────────────────────────────────
        if _PULLQUOTE_RE.match(line):
            pq_lines: list[str] = []
            while i < n and _PULLQUOTE_RE.match(lines[i]):
                pq_lines.append(lines[i])
                i += 1
            output.append(convert_pullquote_block(pq_lines, footnotes))
            continue

        # ── Pipe table ────────────────────────────────────────────────────────
        # Standalone tables always span full width (mirrors CSS column-span:all).
        if _TABLE_LINE_RE.match(line):
            tbl_lines: list[str] = []
            while i < n and _TABLE_LINE_RE.match(lines[i]):
                tbl_lines.append(lines[i])
                i += 1
            tbl_block = '\n'.join(tbl_lines)
            output.append('\x00FULLWIDTH_START\x00')
            output.append(convert_table(tbl_block, footnotes))
            output.append('\x00FULLWIDTH_END\x00')
            continue

        # ── Unordered list ────────────────────────────────────────────────────
        if _UL_LINE_RE.match(line):
            ul_lines: list[str] = []
            while i < n and (_UL_LINE_RE.match(lines[i]) or
                              (ul_lines and lines[i].startswith('  '))):
                ul_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ul_lines, footnotes, ordered=False))
            continue

        # ── Ordered list ──────────────────────────────────────────────────────
        if _OL_LINE_RE.match(line):
            ol_lines: list[str] = []
            while i < n and (_OL_LINE_RE.match(lines[i]) or
                              (ol_lines and lines[i].startswith('  '))):
                ol_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ol_lines, footnotes, ordered=True))
            continue

        # ── Raw HTML divs ─────────────────────────────────────────────────────
        dm = _DIV_OPEN_RE.match(line)
        if dm:
            div_class = dm.group(1).strip()
            # Check for self-contained single-line div: <div class="..."></div>
            rest_of_line = line[dm.end():]
            if _DIV_CLOSE_RE.match(rest_of_line):
                # e.g. <div class="page-break"></div> — no inner content
                i += 1
                inner_text = ''
            else:
                i += 1
                # Collect content until matching </div>
                div_lines: list[str] = []
                depth = 1
                while i < n and depth > 0:
                    if _DIV_OPEN_RE.match(lines[i]):
                        depth += 1
                        div_lines.append(lines[i])
                    elif _DIV_CLOSE_RE.match(lines[i]):
                        depth -= 1
                        if depth > 0:
                            div_lines.append(lines[i])
                    else:
                        div_lines.append(lines[i])
                    i += 1
                inner_text = '\n'.join(div_lines).strip()

            if div_class == 'page-break':
                output.append('#pagebreak()')

            elif div_class == 'key-takeaways':
                # Detect optional scope note: first paragraph starting with
                # "Scope Note" (bold or plain) becomes the scope-note: argument.
                scope_note_typst = None
                body_text = inner_text
                scope_match = re.match(
                    r'^\*{0,2}Scope Note[:\*]*\*{0,2}[:\s]*(.*?)(?:\n\n|\Z)',
                    inner_text.strip(), re.DOTALL | re.IGNORECASE
                )
                if scope_match:
                    scope_note_typst = convert_inline(scope_match.group(1).strip(), footnotes)
                    body_text = inner_text[scope_match.end():].strip()

                inner_typst = _convert_block_content(body_text, footnotes)
                if scope_note_typst:
                    output.append(f'#key-takeaways(scope-note: [{scope_note_typst}])[')
                else:
                    output.append(f'#key-takeaways[')
                output.append(inner_typst)
                output.append(f']')

            elif div_class in ('insights', 'key-insights', 'insight-box'):
                # Extract optional first heading as the box heading
                heading_match = re.match(r'^#{1,4}\s+(.+?)(?:\s+#+)?\s*$',
                                         inner_text.lstrip(), re.MULTILINE)
                if heading_match:
                    heading_text = convert_inline(heading_match.group(1).strip(), footnotes)
                    # Strip the heading line from inner content
                    inner_no_heading = inner_text[heading_match.end():].strip()
                    inner_typst = _convert_block_content(inner_no_heading, footnotes)
                    output.append(f'#insights-box(heading: [{heading_text}])[')
                else:
                    inner_typst = _convert_block_content(inner_text, footnotes)
                    output.append(f'#insights-box[')
                output.append(inner_typst)
                output.append(f']')

            elif div_class in ('single-column', 'full-width'):
                # Full-width block — use sentinel markers so the post-processing
                # pass can wrap column segments in #columns(2)[...].
                # Content between sentinels runs at full page width.
                inner_typst = _convert_block_content(inner_text, footnotes)
                output.append('\x00FULLWIDTH_START\x00')
                output.append(inner_typst)
                output.append('\x00FULLWIDTH_END\x00')

            else:
                # Unknown div class — emit content as-is
                inner_typst = _convert_block_content(inner_text, footnotes)
                output.append(inner_typst)

            continue

        # ── Standalone image ──────────────────────────────────────────────────
        if _IMG_STANDALONE_RE.match(line):
            # Collect any continuation (unlikely but safe)
            img_m = _IMG_RE.match(line)
            if img_m:
                output.append(convert_image(img_m))
            else:
                output.append(convert_inline(line, footnotes))
            i += 1
            continue

        # ── Default: paragraph text ───────────────────────────────────────────
        # Collect continuation lines (non-blank, non-special)
        para_lines = [line]
        i += 1
        while i < n:
            ln = lines[i]
            if not ln.strip():
                break
            if (_HEADING_RE.match(ln) or _HR_RE.match(ln) or
                    _FENCED_RE.match(ln) or _TABLE_LINE_RE.match(ln) or
                    _UL_LINE_RE.match(ln) or _OL_LINE_RE.match(ln) or
                    _DIV_OPEN_RE.match(ln) or _DIV_CLOSE_RE.match(ln) or
                    _CALLOUT_START_RE.match(ln) or _PULLQUOTE_RE.match(ln) or
                    _FN_DEF_LINE_RE.match(ln)):
                break
            para_lines.append(ln)
            i += 1

        para_text = ' '.join(para_lines)
        # Handle inline images in paragraph
        para_text = _IMG_RE.sub(convert_image, para_text)
        output.append(convert_inline(para_text, footnotes))

    # ── Post-process: wrap column segments in #columns(2)[...] ───────────────
    # Split body on FULLWIDTH sentinels and wrap alternating segments.
    raw = '\n'.join(output)
    parts = re.split(r'\x00FULLWIDTH_START\x00\n?(.*?)\n?\x00FULLWIDTH_END\x00',
                     raw, flags=re.DOTALL)
    # parts alternates: col_segment, fullwidth_content, col_segment, ...
    body_parts: list[str] = []
    for idx, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if idx % 2 == 0:
            # Column segment — wrap in #columns()
            body_parts.append(f'#columns(2, gutter: 0.5cm)[\n{part}\n]')
        else:
            # Full-width content — emit at page width
            body_parts.append(part)

    header = '\n'.join(header_lines)
    body   = '\n\n'.join(body_parts)
    return header + '\n' + body


def _convert_block_content(text: str, footnotes: dict[str, str]) -> str:
    """
    Recursively convert a block of Markdown content (e.g. inside a div) to Typst.
    Reuses the main state machine by calling convert_md_to_typ on just the body,
    then stripping the template header.
    """
    if not text.strip():
        return ''

    # Process the inner text through the same pipeline but without the header boilerplate.
    # We rebuild just the body conversion by splitting lines and processing them.
    lines = text.splitlines()
    output: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            output.append('')
            i += 1
            continue

        if _FN_DEF_LINE_RE.match(line):
            i += 1
            continue

        m = _HEADING_RE.match(line)
        if m:
            level   = len(m.group(1))
            content = m.group(2).strip()
            equals  = '=' * level
            output.append(f'{equals} {convert_inline(content, footnotes)}')
            i += 1
            continue

        if _HR_RE.match(line):
            output.append('#line(length: 100%, stroke: 0.8pt + rgb("#1d4b7a"))')
            i += 1
            continue

        fm = _FENCED_RE.match(line)
        if fm:
            lang = fm.group(1)
            i += 1
            code_lines: list[str] = []
            while i < n and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            if lang.lower() == 'mermaid':
                output.append(next_mermaid_placeholder())
            else:
                code_body = '\n'.join(code_lines).replace('`', '\\`')
                output.append(f'```{lang}' if lang else '```')
                output.append(code_body)
                output.append('```')
            continue

        cm = _CALLOUT_START_RE.match(line)
        if cm:
            kind = cm.group(1)
            i += 1
            body_lines: list[str] = []
            while i < n and lines[i].startswith('>'):
                bl = lines[i]
                body_lines.append(bl[2:] if bl.startswith('> ') else ('' if bl == '>' else bl[1:]))
                i += 1
            output.append(convert_gfm_callout(kind, body_lines, footnotes))
            continue

        if line.startswith('> ') or line == '>':
            bq_lines: list[str] = []
            while i < n and (lines[i].startswith('> ') or lines[i] == '>'):
                bl = lines[i]
                bq_lines.append(bl[2:] if bl.startswith('> ') else '')
                i += 1
            bq_typst = convert_inline(' '.join(bq_lines).strip(), footnotes)
            output.append(f'#quote(block: true)[{bq_typst}]')
            continue

        if _PULLQUOTE_RE.match(line):
            pq_lines: list[str] = []
            while i < n and _PULLQUOTE_RE.match(lines[i]):
                pq_lines.append(lines[i])
                i += 1
            output.append(convert_pullquote_block(pq_lines, footnotes))
            continue

        if _TABLE_LINE_RE.match(line):
            tbl_lines: list[str] = []
            while i < n and _TABLE_LINE_RE.match(lines[i]):
                tbl_lines.append(lines[i])
                i += 1
            output.append(convert_table('\n'.join(tbl_lines), footnotes))
            continue

        if _UL_LINE_RE.match(line):
            ul_lines: list[str] = []
            while i < n and (_UL_LINE_RE.match(lines[i]) or
                              (ul_lines and lines[i].startswith('  '))):
                ul_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ul_lines, footnotes, ordered=False))
            continue

        if _OL_LINE_RE.match(line):
            ol_lines: list[str] = []
            while i < n and (_OL_LINE_RE.match(lines[i]) or
                              (ol_lines and lines[i].startswith('  '))):
                ol_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ol_lines, footnotes, ordered=True))
            continue

        if _IMG_STANDALONE_RE.match(line):
            img_m = _IMG_RE.match(line)
            if img_m:
                output.append(convert_image(img_m))
            else:
                output.append(convert_inline(line, footnotes))
            i += 1
            continue

        # Paragraph
        para_lines = [line]
        i += 1
        while i < n:
            ln = lines[i]
            if not ln.strip():
                break
            if (_HEADING_RE.match(ln) or _HR_RE.match(ln) or
                    _FENCED_RE.match(ln) or _TABLE_LINE_RE.match(ln) or
                    _UL_LINE_RE.match(ln) or _OL_LINE_RE.match(ln) or
                    _DIV_OPEN_RE.match(ln) or _DIV_CLOSE_RE.match(ln) or
                    _CALLOUT_START_RE.match(ln) or _PULLQUOTE_RE.match(ln) or
                    _FN_DEF_LINE_RE.match(ln)):
                break
            para_lines.append(ln)
            i += 1

        para_text = _IMG_RE.sub(convert_image, ' '.join(para_lines))
        output.append(convert_inline(para_text, footnotes))

    return '\n'.join(output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _list_styles() -> list[str]:
    styles_dir = Path(__file__).parent / 'styles'
    return sorted(p.stem for p in styles_dir.glob('*.typ')) if styles_dir.exists() else []


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='convert',
        description=(
            'Edition md_to_typst — Convert Markdown to Typst (.typ) and optionally to PDF.\n\n'
            'Available styles: ' + ', '.join(_list_styles())
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input',
                        help='Input Markdown file (.md)')
    parser.add_argument('--style', '-s',
                        default='intelligence',
                        help='Style name (default: intelligence). Must exist in styles/.')
    parser.add_argument('--output', '-o',
                        default=None,
                        help='Output path.  If ends in .pdf, derives .typ name from it. '
                             'Default: same stem as input, .typ extension.')
    parser.add_argument('--compile', '-c',
                        action='store_true',
                        help='Compile the .typ file to PDF using `typst compile`.')
    parser.add_argument('--no-justify',
                        action='store_true',
                        help='Disable text justification (ragged right).')
    parser.add_argument('--list-styles',
                        action='store_true',
                        help='List available styles and exit.')
    args = parser.parse_args()

    if args.list_styles:
        styles = _list_styles()
        if styles:
            print("Available styles:")
            for s in styles:
                print(f"  {s}")
        else:
            print("No styles found in styles/")
        return

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found.", file=sys.stderr)
        sys.exit(1)

    # Resolve output paths
    if args.output:
        out = Path(args.output)
        if out.suffix.lower() == '.pdf':
            pdf_path = out.resolve()
            typ_path = pdf_path.with_suffix('.typ')
        else:
            typ_path = out.with_suffix('.typ').resolve()
            pdf_path = typ_path.with_suffix('.pdf')
    else:
        typ_path = md_path.with_suffix('.typ')
        pdf_path = md_path.with_suffix('.pdf')

    # Resolve style
    styles_dir = Path(__file__).parent / 'styles'
    style_file = styles_dir / f'{args.style}.typ'
    if not style_file.exists():
        print(f"Error: style '{args.style}' not found at {style_file}", file=sys.stderr)
        available = _list_styles()
        if available:
            print(f"  Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    print(f"Input  : {md_path}")
    print(f"Output : {typ_path}")
    print(f"Style  : {args.style}")

    # Convert
    md_text = md_path.read_text(encoding='utf-8')
    # Look for pre-rendered Mermaid PNGs in images/ adjacent to the input file
    images_dir = md_path.parent / 'images'
    if not images_dir.is_dir():
        images_dir = None

    typ_text = convert_md_to_typ(md_text, style=args.style, styles_dir=styles_dir,
                                 justify=not args.no_justify,
                                 images_dir=images_dir,
                                 md_dir=md_path.parent)
    typ_path.write_text(typ_text, encoding='utf-8')
    print(f"Written: {typ_path}")

    # Compile
    if args.compile:
        # Resolve typst binary — check common locations so it works even when
        # PATH is minimal (e.g. called from osascript or a GUI launcher).
        import shutil, os
        typst_bin = shutil.which('typst')
        if typst_bin is None:
            for candidate in [
                '/opt/homebrew/bin/typst',
                '/usr/local/bin/typst',
                os.path.expanduser('~/.cargo/bin/typst'),
                '/usr/bin/typst',
            ]:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    typst_bin = candidate
                    break
        if typst_bin is None:
            print("Error: `typst` not found. Install with: brew install typst", file=sys.stderr)
            sys.exit(1)

        # Pass --root / so that absolute paths in the .typ file resolve correctly.
        # Typst treats leading-slash paths as relative to --root, not the filesystem.
        print(f"Compiling: {typst_bin} compile {typ_path} {pdf_path}")
        result = subprocess.run(
            [typst_bin, 'compile', '--root', '/', str(typ_path), str(pdf_path)],
            capture_output=True,
            text=True,
            cwd=str(typ_path.parent),
        )
        if result.returncode == 0:
            print(f"PDF written: {pdf_path}")
        else:
            print(f"typst compile failed (exit {result.returncode}):", file=sys.stderr)
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)


if __name__ == '__main__':
    main()
