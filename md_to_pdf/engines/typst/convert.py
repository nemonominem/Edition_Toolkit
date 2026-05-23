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

# Shared frontmatter parser (engines/__init__.py)
# Insert the md_to_pdf root so `engines` package is importable from anywhere.
_MD2PDF_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_MD2PDF_ROOT) not in sys.path:
    sys.path.insert(0, str(_MD2PDF_ROOT))
from engines import parse_frontmatter, load_style_defaults, load_sidecar, load_typst_overrides  # noqa: E402


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
    # # introduces function calls / headings in code mode
    text = text.replace("#", "\\#")
    # * and _ are emphasis markers — escape stray ones not consumed by bold/italic
    text = text.replace("*", "\\*")
    text = text.replace("_", "\\_")
    # [ opens a content block in Typst; ] closes one — both must be escaped in plain text
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text


# Pattern: ***bold+italic*** (must be matched BEFORE bold and italic separately)
_BOLD_ITALIC_RE = re.compile(r'\*\*\*(.+?)\*\*\*', re.DOTALL)
# Pattern: **bold** or __bold__ (word-boundary anchored to avoid false matches)
_BOLD_RE   = re.compile(r'\*\*(.+?)\*\*|(?<!\w)__(.+?)__(?!\w)', re.DOTALL)
# Pattern: *italic* or _italic_ (single, word-boundary anchored)
_ITALIC_RE = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!\w)_(?!_)(.+?)(?<!_)_(?!\w)')
# Pattern: `inline code`
_CODE_RE   = re.compile(r'`([^`]+)`')
# Pattern: [text](url)
_LINK_RE   = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
# Pattern: [^key] footnote reference (not definition)
_FNREF_RE  = re.compile(r'\[\^([^\]]+)\](?!:)')
# Pattern: ~~strikethrough~~
_STRIKE_RE = re.compile(r'~~(.+?)~~')

# Styles that use endnotes (collected at end of document) instead of page footnotes
_ENDNOTE_STYLES = {'intelligence', 'academic'}

# Per-document endnote state — reset by convert_md_to_typ() before each run
_fn_endnote_mode: bool = False          # True for intelligence/academic styles
_fn_index: dict[str, int] = {}         # key → note number (1-based)
_fn_notes: list[tuple[str, str]] = []  # ordered [(key, definition), ...]


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
        # Escape specials in link text (@ triggers label refs, # triggers calls, etc.)
        # Respect already-stashed placeholders from step 1 (inline code, HTML imgs).
        segs = re.split(r'(\x00PH\d+\x00)', link_text)
        escaped_link = ''.join(
            seg if re.match(r'\x00PH\d+\x00', seg) else _escape_typst(seg)
            for seg in segs
        )
        return stash(f'#link("{url}")[{escaped_link}]')
    text = _LINK_RE.sub(replace_link, text)

    # 3. Footnote references  [^key]
    def replace_fnref(m: re.Match) -> str:
        global _fn_endnote_mode, _fn_index, _fn_notes
        key = m.group(1)
        if _fn_endnote_mode:
            # Endnote mode: assign sequential number, record definition once
            if key not in _fn_index:
                n = len(_fn_notes) + 1
                _fn_index[key] = n
                defn = footnotes.get(key, key)
                _fn_notes.append((key, defn))
            n = _fn_index[key]
            # Inline: superscript linking to endnote anchor.
            # Label names use hyphens (Typst rejects underscores in labels).
            safe_key = key.replace('_', '-')
            return stash(f'#link(<en-{safe_key}>)[#super(size: 6.5pt, baseline: 2pt)[{n}]]')
        else:
            # Page-footnote mode (magazine, thinktank)
            defn = footnotes.get(key, "")
            if defn:
                inner = convert_inline(defn, {})
                return stash(f"#footnote[{inner}]")
            return stash(f"#footnote[{key}]")
    text = _FNREF_RE.sub(replace_fnref, text)

    def _escape_inner(s: str) -> str:
        """Escape the inner text of a bold/italic/strike span.
        Placeholders (already-stashed inline elements) pass through untouched;
        raw text segments are escaped so stray Typst specials don't leak out."""
        segs = re.split(r'(\x00PH\d+\x00)', s)
        return ''.join(
            seg if re.match(r'\x00PH\d+\x00', seg) else _escape_typst(seg)
            for seg in segs
        )

    # 4. Bold+italic ***text*** (must come before bold and italic separately)
    def replace_bold_italic(m: re.Match) -> str:
        return stash(f"*_{_escape_inner(m.group(1))}_*")
    text = _BOLD_ITALIC_RE.sub(replace_bold_italic, text)

    # 5. Bold **text**
    def replace_bold(m: re.Match) -> str:
        inner = m.group(1) or m.group(2)
        return stash(f"*{_escape_inner(inner)}*")
    text = _BOLD_RE.sub(replace_bold, text)

    # 6. Italic *text*
    def replace_italic(m: re.Match) -> str:
        inner = m.group(1) or m.group(2)
        return stash(f"_{_escape_inner(inner)}_")
    text = _ITALIC_RE.sub(replace_italic, text)

    # 7. Strikethrough ~~text~~
    def replace_strike(m: re.Match) -> str:
        return stash(f"#strike[{_escape_inner(m.group(1))}]")
    text = _STRIKE_RE.sub(replace_strike, text)

    # 8. Escape remaining special Typst characters
    # (do it per-segment between placeholders so we don't corrupt them)
    parts = re.split(r'(\x00PH\d+\x00)', text)
    escaped_parts = []
    for part in parts:
        if re.match(r'\x00PH\d+\x00', part):
            escaped_parts.append(part)
        else:
            escaped_parts.append(_escape_typst(part))
    text = ''.join(escaped_parts)

    # 9. Restore placeholders in reverse order so nested stashes resolve correctly.
    # (A later stash may contain the token of an earlier one inside its content;
    #  restoring outermost-last ensures inner tokens are already resolved first.)
    for i in range(len(placeholders) - 1, -1, -1):
        text = text.replace(f"\x00PH{i}\x00", placeholders[i])

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

    # Column width heuristic:
    #   2-col tables: narrow label col (0.28fr) + wide content col (1fr).
    #   3-col tables: if the first column header is short (≤ 12 chars) AND
    #     the first-column data cells are all short (≤ 20 chars), treat it as
    #     a label/date column and use 0.28fr + 1fr + 1fr.  Otherwise equal.
    #   4+ col tables: always equal 1fr each.
    def _first_col_is_narrow() -> bool:
        """Return True if col 0 looks like a label/date column.
        Strips basic Markdown bold/italic markers before measuring."""
        def _plain(s: str) -> str:
            return re.sub(r'\*+', '', s).strip()
        hdr = _plain(header_row[0]) if header_row else ''
        if len(hdr) > 12:
            return False
        for row in data_rows:
            cell = _plain(row[0]) if row else ''
            if len(cell) > 25:
                return False
        return True

    if n_cols == 2:
        col_spec = "0.28fr, 1fr"
    elif n_cols == 3 and _first_col_is_narrow():
        col_spec = "0.28fr, 1fr, 1fr"
    else:
        col_spec = ", ".join("1fr" for _ in range(n_cols))

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
    return all(re.match(r'^\|[ \t]?(?!.*\|\s*$)', ln) for ln in lines if ln.strip())


def convert_pullquote_block(lines: list[str], footnotes: dict[str, str]) -> str:
    """Convert a pull-quote block to a Typst #pull-quote() call."""
    stripped = [re.sub(r'^\|[ \t]?', '', ln) for ln in lines]

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
    """Convert a list block to Typst, preserving nesting up to any depth.

    Markdown uses 2- or 4-space indent per level.  We detect the indent unit
    from the first indented item and map indent depth → Typst nesting via
    repeated list markers (Typst nests lists by simply indenting the marker).

    Each item may span multiple continuation lines (indented but no marker).
    """
    marker_re = re.compile(r'^(\s*)(\d+\.|[-*+])\s+(.*)$')

    # ── Parse into a flat list of (raw_indent, text) tuples ──────────────
    raw_parsed: list[tuple[int, str]] = []   # (raw_indent, text)

    i = 0
    while i < len(lines):
        ln = lines[i]
        m = marker_re.match(ln)
        if m:
            raw_indent = len(m.group(1))
            text = m.group(3)
            # Collect continuation lines (indented, no marker)
            i += 1
            while i < len(lines) and not marker_re.match(lines[i]) and lines[i].strip():
                text += ' ' + lines[i].strip()
                i += 1
            raw_parsed.append((raw_indent, text))
        else:
            i += 1  # blank or unrecognised — skip

    # ── Normalise indent to 0-based levels ────────────────────────────────
    # Determine indent unit from the smallest non-zero indent seen.
    # Then shift so the minimum indent maps to level 0.
    parsed: list[tuple[int, str]] = []
    if raw_parsed:
        all_indents = sorted({ri for ri, _ in raw_parsed})
        min_indent  = all_indents[0]
        # Detect indent unit: smallest gap between consecutive distinct indents
        indent_unit = 2  # default
        for a, b in zip(all_indents, all_indents[1:]):
            indent_unit = b - a
            break  # first gap is enough
        for ri, text in raw_parsed:
            level = (ri - min_indent) // indent_unit if indent_unit else 0
            parsed.append((level, text))

    # ── Emit Typst list syntax ─────────────────────────────────────────────
    # Typst nesting: indent child items inside the parent with a nested list.
    # We do this by emitting indented `- ` / `+ ` markers; Typst treats
    # indented markers as nested lists automatically.
    def _render(items: list[tuple[int, str]], base_level: int, list_type: str) -> list[str]:
        out: list[str] = []
        idx = 0
        while idx < len(items):
            lvl, text = items[idx]
            if lvl < base_level:
                break   # back up to parent caller
            if lvl == base_level:
                content = convert_inline(text, footnotes)
                # Peek ahead: does the next item go deeper?
                child_items = []
                j = idx + 1
                while j < len(items) and items[j][0] > base_level:
                    child_items.append(items[j])
                    j += 1
                if child_items:
                    child_typst = '\n'.join(_render(child_items, base_level + 1, list_type))
                    out.append(f"{list_type} {content}\n  {child_typst.replace(chr(10), chr(10) + '  ')}")
                    idx = j
                else:
                    out.append(f"{list_type} {content}")
                    idx += 1
            else:
                # Deeper item with no parent at this base_level — promote
                content = convert_inline(text, footnotes)
                out.append(f"{list_type} {content}")
                idx += 1
        return out

    list_type = "+" if ordered else "-"
    return '\n'.join(_render(parsed, 0, list_type))


# ---------------------------------------------------------------------------
# Mermaid placeholder
# ---------------------------------------------------------------------------

_mermaid_counter = 0
_mermaid_images_dir: Path | None = None  # set per-document in convert_md_to_typ
_md_dir: Path | None = None              # directory of the source .md file; used to resolve relative image paths


def _render_mermaid_to_png(code_lines: list[str]) -> None:
    """
    Render a Mermaid diagram to a PNG using mmdc (mermaid-cli) if available.
    The PNG is written to _mermaid_images_dir/_mermaid_<n+1>.png, where n is
    the current _mermaid_counter (before increment — next_mermaid_placeholder
    will increment it and look for the same file).
    Silently skips if mmdc is not on PATH.
    """
    import shutil, tempfile, os
    if _mermaid_images_dir is None:
        return
    mmdc = shutil.which('mmdc')
    if mmdc is None:
        # Try common npm global install locations
        for candidate in [
            '/usr/local/bin/mmdc',
            '/opt/homebrew/bin/mmdc',
            os.path.expanduser('~/.npm-global/bin/mmdc'),
            os.path.expanduser('~/.nvm/versions/node/current/bin/mmdc'),
        ]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                mmdc = candidate
                break
    if mmdc is None:
        return  # placeholder will be used instead

    n = _mermaid_counter + 1  # next_mermaid_placeholder will use this number
    out_png = _mermaid_images_dir / f'_mermaid_{n}.png'
    if out_png.exists():
        return  # already rendered (e.g. from a previous run)

    _mermaid_images_dir.mkdir(parents=True, exist_ok=True)
    mmd_src = '\n'.join(code_lines)
    with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w', encoding='utf-8', delete=False) as f:
        f.write(mmd_src)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [mmdc, '-i', tmp_path, '-o', str(out_png), '-b', 'white', '-w', '1200'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  mmdc warning (diagram {n}): {result.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"  mmdc error (diagram {n}): {e}", file=sys.stderr)
    finally:
        os.unlink(tmp_path)


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

# A paragraph consisting solely of **bold text** (no other content) is treated
# as an implicit H4 — a common authoring shorthand for informal sub-headings.
_BOLD_ONLY_RE = re.compile(r'^\*\*(.+?)\*\*\.?\s*$')

# Regex patterns for block-level detection
_HEADING_RE        = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$')
_HR_RE             = re.compile(r'^(?:-{3,}|_{3,}|\*{3,})\s*$')
_TABLE_LINE_RE     = re.compile(r'^\|')
_UL_LINE_RE        = re.compile(r'^[ \t]*[-*+]\s+')
_OL_LINE_RE        = re.compile(r'^[ \t]*\d+\.\s+')
_CALLOUT_START_RE  = re.compile(r'^> \[!(' + '|'.join(_CALLOUT_LABELS) + r')\]', re.IGNORECASE)
_PULLQUOTE_RE      = re.compile(r'^\|[ \t]?(?!.*\|\s*$)')   # | or |<space> but not table rows
_FENCED_RE         = re.compile(r'^```(\w*)')
_DIV_OPEN_RE       = re.compile(r'^<div\s+class="([^"]+)">')
_DIV_CLOSE_RE      = re.compile(r'^</div>')
_FN_DEF_LINE_RE    = re.compile(r'^\[\^[^\]]+\]:')
_IMG_STANDALONE_RE = re.compile(r'^!\[')


def convert_md_to_typ(md_text: str, style: str = "intelligence",
                      styles_dir: Path | None = None,
                      justify: bool = True,
                      images_dir: Path | None = None,
                      md_dir: Path | None = None,
                      sidecar: dict[str, str] | None = None,
                      typst_overrides: dict[str, str] | None = None) -> str:
    """
    Convert Markdown text to a complete Typst source file.

    Args:
        md_text:    Raw Markdown source.
        style:      Style name (e.g. "intelligence").
        styles_dir: Absolute path to the styles/ directory.  Used to emit an
                    absolute #import path so the .typ file can be compiled from
                    any working directory.
        sidecar:    Pre-merged metadata overrides (style defaults + sidecar JSON
                    + explicit --meta values).  YAML frontmatter in md_text still
                    wins over sidecar values.

    Returns:
        Typst source string.
    """
    # Reset per-document state
    global _mermaid_counter, _mermaid_images_dir, _md_dir
    global _fn_endnote_mode, _fn_index, _fn_notes
    _mermaid_counter = 0
    _fn_endnote_mode = style in _ENDNOTE_STYLES
    _fn_index = {}
    _fn_notes = []
    endnote_mode = _fn_endnote_mode
    _mermaid_images_dir = images_dir
    # _md_dir is used by convert_image/_resolve_image_src to turn relative paths absolute
    _md_dir = md_dir if md_dir is not None else (images_dir.parent if images_dir is not None else None)

    # 1. Pre-processing passes (order matters)
    # Extract YAML front-matter (if any) — shared parser
    meta, md_text = parse_frontmatter(md_text, sidecar=sidecar)

    # Extract footnote definitions
    md_text, footnotes = extract_footnotes(md_text)
    author   = meta["author"]
    title    = meta["title"]
    pub_name = meta["pub-name"]
    doc_type = meta["doc-type"]

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
    # Per-article Typst variable overrides (from sidecar typst_overrides block).
    # Emitted after #import so they shadow the style's #let definitions.
    if typst_overrides:
        for var_name, typst_val in typst_overrides.items():
            header_lines.append(f'#let {var_name} = {typst_val}')
        header_lines.append(f'')
    justify_val = 'true' if justify else 'false'
    header_lines.append(f'#show: doc.with(')
    header_lines.append(f'  author:   "{author}",')
    header_lines.append(f'  title:    "{title}",')
    header_lines.append(f'  pub-name: "{pub_name}",')
    header_lines.append(f'  doc-type: "{doc_type}",')
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
                _render_mermaid_to_png(code_lines)
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
            bq_lines: list[str] = [line[2:] if line.startswith('> ') else '']
            i += 1
            while i < n and (lines[i].startswith('> ') or lines[i] == '>'):
                bl = lines[i]
                if bl.startswith('> '):
                    bq_lines.append(bl[2:])
                else:
                    bq_lines.append('')
                i += 1
            # Use _convert_block_content so images/figures inside blockquotes
            # are handled correctly, not flattened into inline text.
            bq_text = '\n'.join(bq_lines).strip()
            bq_typst = _convert_block_content(bq_text, footnotes)
            output.append(f'#quote(block: true)[\n{bq_typst}\n]')
            continue

        # ── Pull-quote  | "text" ... ──────────────────────────────────────────
        if _PULLQUOTE_RE.match(line):
            pq_lines: list[str] = [line]
            i += 1
            while i < n and _PULLQUOTE_RE.match(lines[i]):
                pq_lines.append(lines[i])
                i += 1
            output.append(convert_pullquote_block(pq_lines, footnotes))
            continue

        # ── Pipe table ────────────────────────────────────────────────────────
        # Standalone tables always span full width (mirrors CSS column-span:all).
        if _TABLE_LINE_RE.match(line):
            tbl_lines: list[str] = [line]
            i += 1
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
            ul_lines: list[str] = [line]
            i += 1
            while i < n and (_UL_LINE_RE.match(lines[i]) or
                              (ul_lines and lines[i].startswith('  '))):
                ul_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ul_lines, footnotes, ordered=False))
            continue

        # ── Ordered list ──────────────────────────────────────────────────────
        if _OL_LINE_RE.match(line):
            ol_lines: list[str] = [line]
            i += 1
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
                # pagebreak must be at page level, not inside #columns()
                # Use fullwidth sentinels to break out of any column context
                output.append('\x00FULLWIDTH_START\x00')
                output.append('#pagebreak()')
                output.append('\x00FULLWIDTH_END\x00')

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

    # ── Endnotes: append to output before post-processing so sentinels work ────
    if endnote_mode and _fn_notes:
        output.append('\x00FULLWIDTH_START\x00')
        output.append('#pagebreak()')
        output.append('// ── Endnotes ──────────────────────────────────────────────────────────────')
        output.append('#text(size: 11pt, weight: "bold", fill: rgb("#1d4b7a"))[Notes]')
        output.append('#v(2pt)')
        output.append('#line(length: 100%, stroke: 0.8pt + rgb("#1d4b7a"))')
        output.append('#v(0.5em)')
        for key, defn in _fn_notes:
            n = _fn_index[key]
            safe_key = key.replace('_', '-')
            defn_no_xref = _FNREF_RE.sub(
                lambda m2: f'[{_fn_index.get(m2.group(1), "?")}]',
                defn
            )
            defn_typst = convert_inline(defn_no_xref, {})
            output.append(
                f'#block(height: 0pt, above: 0pt, below: 0pt)[] <en-{safe_key}>\n'
                f'#block(below: 1.2em, inset: (left: 1.8em), clip: false)['
                f'#pad(left: -1.8em)[#text(size: 8.5pt)[{n}.#h(0.4em){defn_typst}]]'
                f']'
            )
        output.append('\x00FULLWIDTH_END\x00')

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
                _render_mermaid_to_png(code_lines)
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
            bq_lines: list[str] = [line[2:] if line.startswith('> ') else '']
            i += 1
            while i < n and (lines[i].startswith('> ') or lines[i] == '>'):
                bl = lines[i]
                bq_lines.append(bl[2:] if bl.startswith('> ') else '')
                i += 1
            bq_typst = convert_inline(' '.join(bq_lines).strip(), footnotes)
            output.append(f'#quote(block: true)[{bq_typst}]')
            continue

        if _PULLQUOTE_RE.match(line):
            pq_lines: list[str] = [line]
            i += 1
            while i < n and _PULLQUOTE_RE.match(lines[i]):
                pq_lines.append(lines[i])
                i += 1
            output.append(convert_pullquote_block(pq_lines, footnotes))
            continue

        if _TABLE_LINE_RE.match(line):
            tbl_lines: list[str] = [line]
            i += 1
            while i < n and _TABLE_LINE_RE.match(lines[i]):
                tbl_lines.append(lines[i])
                i += 1
            output.append(convert_table('\n'.join(tbl_lines), footnotes))
            continue

        if _UL_LINE_RE.match(line):
            ul_lines: list[str] = [line]
            i += 1
            while i < n and (_UL_LINE_RE.match(lines[i]) or
                              (ul_lines and lines[i].startswith('  '))):
                ul_lines.append(lines[i])
                i += 1
            output.append(convert_list_block(ul_lines, footnotes, ordered=False))
            continue

        if _OL_LINE_RE.match(line):
            ol_lines: list[str] = [line]
            i += 1
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
    parser.add_argument('--meta', '-m',
                        default=None,
                        metavar='JSON',
                        help='Path to a per-article JSON sidecar file (default: '
                             '<input>.json alongside the .md).  Keys: author, title, '
                             'pub_name / pub-name, doc_type / doc-type, style.')
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

    # Build sidecar metadata: style defaults → auto-detected sidecar → explicit --meta
    sidecar: dict[str, str] = load_style_defaults(args.style)
    sidecar.update(load_sidecar(md_path))
    if args.meta:
        meta_path = Path(args.meta).resolve()
        if not meta_path.exists():
            print(f"Error: --meta file not found: {meta_path}", file=sys.stderr)
            sys.exit(1)
        explicit = load_sidecar(meta_path.with_suffix('').with_name(meta_path.stem))
        # load_sidecar expects a .md path and appends .json; work around by loading directly
        import json as _json
        try:
            raw = _json.loads(meta_path.read_text(encoding='utf-8'))
            _KEY_MAP = {
                "author": "author", "title": "title",
                "pub-name": "pub-name", "pub_name": "pub-name", "pubname": "pub-name",
                "doc-type": "doc-type", "doc_type": "doc-type", "doctype": "doc-type",
            }
            for k, v in raw.items():
                canonical = _KEY_MAP.get(k.lower())
                if canonical and isinstance(v, str):
                    sidecar[canonical] = v
        except Exception as e:
            print(f"Warning: could not load --meta file: {e}", file=sys.stderr)

    if sidecar:
        print(f"Meta   : {sidecar}")

    # Load per-article Typst variable overrides (typst_overrides block in sidecar JSON)
    typst_overrides = load_typst_overrides(md_path)
    if args.meta and not typst_overrides:
        # Also check explicit --meta file for typst_overrides
        import json as _json2
        try:
            raw2 = _json2.loads(Path(args.meta).resolve().read_text(encoding='utf-8'))
            from engines import load_typst_overrides as _lto
            # Re-use the loader logic by temporarily writing to a temp path... simpler:
            # just call _normalise_typst_value directly inline
            from engines import _TYPST_OVERRIDE_VARS, _TYPST_VAR_NAME, _normalise_typst_value
            block = raw2.get("typst_overrides", {})
            for raw_key, raw_val in block.items():
                key = raw_key.lower().replace("-", "_")
                typst_val = _normalise_typst_value(key, raw_val)
                if typst_val is not None:
                    typst_overrides[_TYPST_VAR_NAME[key]] = typst_val
        except Exception:
            pass
    if typst_overrides:
        print(f"Typst  : {typst_overrides}")

    # Convert
    md_text = md_path.read_text(encoding='utf-8')
    # Look for pre-rendered Mermaid PNGs in images/ adjacent to the input file
    images_dir = md_path.parent / 'images'
    if not images_dir.is_dir():
        images_dir = None

    typ_text = convert_md_to_typ(md_text, style=args.style, styles_dir=styles_dir,
                                 justify=not args.no_justify,
                                 images_dir=images_dir,
                                 md_dir=md_path.parent,
                                 sidecar=sidecar,
                                 typst_overrides=typst_overrides)
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
