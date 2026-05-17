#!/usr/bin/env python3
"""
etk_md2pdf.convert — Markdown → PDF conversion pipeline.

Entry point: main()  (registered as console_script 'md2pdf' in pyproject.toml)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import resources as _res
from pathlib import Path

# ---------------------------------------------------------------------------
# Bundled style resolution
# ---------------------------------------------------------------------------

def _styles_dir() -> Path:
    """
    Return the Path to the package's bundled styles/ directory.
    Works for editable installs, regular installs, and zipimport (wheels).
    """
    # importlib.resources.files() is the canonical API (Python 3.9+).
    # It returns a Traversable; we convert to a real Path via as_posix /
    # a temporary extraction if necessary (wheels store files in a zip).
    pkg_files = _res.files('etk_md2pdf')
    styles = pkg_files / 'styles'
    # If styles is already a real directory (editable / regular install),
    # return it directly.  Otherwise materialise it with as_file().
    try:
        p = Path(str(styles))
        if p.is_dir():
            return p
    except TypeError:
        pass
    # Fallback: extract to a temp dir (zip-based installs)
    import atexit, tempfile as _tf
    tmp = Path(_tf.mkdtemp(prefix='etk_md2pdf_styles_'))
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    for item in styles.iterdir():
        dest = tmp / item.name
        dest.write_bytes(item.read_bytes())
    return tmp


def resolve_css(spec: str | None) -> Path:
    """
    Resolve a --css argument to an absolute Path.

    Resolution order for a given spec string:
      1. Exact path that exists on disk           → use as-is
      2. Relative path from cwd that exists       → resolve to absolute
      3. Exact filename in bundled styles/         → use bundled
      4. 'style_<spec>.css' in bundled styles/    → use bundled
      5. '<spec>.css' in bundled styles/           → use bundled
      6. Strip leading 'style_' / trailing '.css' and retry 4+5

    If spec is None, returns the default bundled style (style_thinktank.css).
    """
    styles = _styles_dir()
    default = styles / 'style_thinktank.css'

    if spec is None:
        return default

    # 1 & 2: real filesystem path
    p = Path(spec)
    if p.exists():
        return p.resolve()
    abs_p = Path.cwd() / p
    if abs_p.exists():
        return abs_p.resolve()

    # Normalise: strip path separators (user typed a bare name)
    name = Path(spec).name  # drop any directory component

    # Build candidate filenames to try against the bundled styles dir
    stem = name
    if stem.endswith('.css'):
        stem = stem[:-4]             # strip extension
    if stem.startswith('style_'):
        bare = stem[len('style_'):]  # e.g. 'intelligence'
    else:
        bare = stem

    candidates = [
        f'{name}',                   # exact as given
        f'{stem}.css',               # with extension if missing
        f'style_{bare}.css',         # style_<bare>.css
        f'{bare}.css',               # <bare>.css
    ]

    for c in candidates:
        hit = styles / c
        if hit.exists():
            return hit.resolve()

    # Nothing found — let the caller fail with a clear message
    return Path(spec).resolve()


# Default (used in legacy md_to_pdf.py shim and --css display)
DEFAULT_CSS_PATH = resolve_css(None)


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------

def find_mmdc() -> str | None:
    """Return path to mmdc CLI if available, else None."""
    found = shutil.which('mmdc')
    if found:
        return found
    for candidate in [
        os.path.expanduser('~/.npm/bin/mmdc'),
        os.path.expanduser('~/.npm-global/bin/mmdc'),
        '/usr/local/bin/mmdc',
        '/opt/homebrew/bin/mmdc',
    ]:
        if os.path.isfile(candidate):
            return candidate
    return None


def render_mermaid_blocks(text: str, out_dir: Path) -> str:
    """
    Replace ```mermaid...``` fenced blocks with either:
    - An <img> tag pointing at a rendered PNG (when mmdc is available), or
    - A styled <div class="mermaid-placeholder"> notice.
    PNG files are written into out_dir (typically the document's images/ folder).
    """
    mmdc = find_mmdc()
    counter = [0]

    def replace_block(m: re.Match) -> str:
        diagram_src = m.group(1).strip()
        counter[0] += 1
        idx = counter[0]

        if not mmdc:
            return (
                f'<div class="mermaid-placeholder">'
                f'[Diagram {idx} — install mmdc to render: '
                f'npm install -g @mermaid-js/mermaid-cli]'
                f'</div>'
            )

        with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w',
                                         delete=False, encoding='utf-8') as f:
            f.write(diagram_src)
            mmd_path = f.name

        png_name = f'_mermaid_{idx}.png'
        png_path = out_dir / png_name

        try:
            result = subprocess.run(
                [mmdc, '-i', mmd_path, '-o', str(png_path),
                 '-b', 'white', '--width', '1200'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0 or not png_path.exists():
                print(f"  [mermaid] Warning: diagram {idx} failed: {result.stderr[:200]}",
                      file=sys.stderr)
                return (
                    f'<div class="mermaid-placeholder">'
                    f'[Diagram {idx} rendering failed]'
                    f'</div>'
                )
            print(f"  [mermaid] Rendered diagram {idx} → {png_name}")
            return (
                f'<p class="img-block"><img src="{png_path}" alt="Diagram {idx}" '
                f'style="max-width:100%;display:block;margin:1em auto;"></p>'
            )
        except Exception as e:
            print(f"  [mermaid] Exception on diagram {idx}: {e}", file=sys.stderr)
            return (
                f'<div class="mermaid-placeholder">'
                f'[Diagram {idx} — rendering error]'
                f'</div>'
            )
        finally:
            os.unlink(mmd_path)

    return re.sub(r'```mermaid\n(.*?)```', replace_block, text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# GFM callout conversion  (> [!NOTE], > [!WARNING], etc.)
# ---------------------------------------------------------------------------

def md_inline(src: str) -> str:
    """
    Convert a Markdown fragment to HTML, preserving footnote refs ([^key])
    so the outer document-level footnote pass can resolve them with correct
    numbering.
    """
    import markdown

    refs = []
    def stash_ref(m):
        refs.append(m.group(0))
        return f'\x00FNREF{len(refs)-1}\x00'

    src_stashed = re.sub(r'\[\^[^\]]+\](?!:)', stash_ref, src)
    html = markdown.markdown(
        src_stashed,
        extensions=['tables', 'fenced_code', 'attr_list', 'def_list', 'abbr', 'smarty'],
    )
    for i, ref in enumerate(refs):
        html = html.replace(f'\x00FNREF{i}\x00', ref)
    return html


def convert_gfm_callouts(text: str) -> str:
    """Convert > [!NOTE] / [!WARNING] etc. blocks to styled HTML divs."""
    LABELS = {
        'NOTE': 'Note', 'TIP': 'Tip', 'IMPORTANT': 'Important',
        'WARNING': 'Warning', 'CAUTION': 'Caution',
    }

    def replace_callout(m: re.Match) -> str:
        kind = m.group(1).upper()
        label = LABELS.get(kind, kind.capitalize())
        css_class = kind.lower()
        body_lines = []
        for line in m.group(2).splitlines():
            if line.startswith('> '):
                body_lines.append(line[2:])
            elif line == '>':
                body_lines.append('')
            else:
                body_lines.append(line)
        body_html = md_inline('\n'.join(body_lines).strip())
        return (
            f'<div class="callout callout-{css_class}">\n'
            f'<p class="callout-label">{label}</p>\n'
            f'{body_html}\n'
            f'</div>'
        )

    return re.sub(
        r'> \[!(' + '|'.join(LABELS) + r')\]\n((?:>[ \t]?.*\n?)*)',
        replace_callout, text, flags=re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Pull-quote conversion
# ---------------------------------------------------------------------------

def convert_pullquotes(text: str) -> str:
    """
    Convert pipe-prefixed pull-quote blocks to HTML blockquotes.

        | "Quote text."[^fn]
        | source: Attribution line.
    """
    def replace_block(m: re.Match) -> str:
        lines = [l[2:] for l in m.group(0).splitlines()]
        if lines and lines[-1].lower().startswith('source:'):
            body_lines, source = lines[:-1], lines[-1][len('source:'):].strip()
        else:
            body_lines, source = lines, ''

        body_html = md_inline(' '.join(body_lines).strip())
        body_html = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1', body_html, flags=re.DOTALL)

        if source:
            source_html = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1',
                                  md_inline(source).strip(), flags=re.DOTALL)
            return (
                f'<div class="pull-quote">'
                f'<blockquote><p>{body_html}</p></blockquote>'
                f'<cite class="pull-source">{source_html}</cite>'
                f'</div>\n'
            )
        return (
            f'<div class="pull-quote">'
            f'<blockquote><p>{body_html}</p></blockquote>'
            f'</div>\n'
        )

    return re.sub(
        r'(?m)^(?:\| (?!.*\|\s*$)[^\n]+\n?)+',
        replace_block, text,
    )


# ---------------------------------------------------------------------------
# Annex page breaks
# ---------------------------------------------------------------------------

def inject_annex_breaks(text: str) -> str:
    """Insert CSS page-break divs before ## Annex N / Further Reading / Notes."""
    BREAK = '<div class="annex-break"></div>\n\n'
    return re.sub(
        r'(?m)^(## (?:Annex \d+|Further Reading|Notes)\b)',
        BREAK + r'\1', text,
    )


# ---------------------------------------------------------------------------
# Markdown image pre-processing
# ---------------------------------------------------------------------------

def convert_md_images(text: str) -> str:
    """
    Pre-convert Markdown image syntax to raw HTML before python-markdown
    processes the document.

    Python-Markdown does not parse ![]() inside raw HTML blocks (e.g.
    <div class="single-column">), so images inside those divs render as plain
    text.  Converting them to <img> tags first fixes this for both wrapped and
    unwrapped images.

    Two cases are distinguished:

    Standalone image — ![]() is the only non-whitespace content on its line:
        Emitted as <p><img ...></p> so it forms its own block and never appears
        as inline content inside a paragraph.  This avoids the WeasyPrint crash
        (assert BlockReplacedBox) that occurs when a block-level img lands inside
        a paragraph that also triggers a ::first-letter float (e.g. drop caps in
        column layouts).

    Inline image — ![]() appears within a line of other text:
        Emitted as a bare <img> with display:inline so it flows with surrounding
        text.

    Handles optional width attribute:
        ![alt](path){width=60%}  →  max-width:60%
        ![alt](path)             →  max-width:100%

    resolve_image_paths() later rewrites relative src values to file:// URIs
    and continues to work correctly on the output of this step.
    """
    # One image token: ![alt](src) optionally followed by {width=VALUE}
    IMG_TOKEN = re.compile(
        r'!\[([^\]]*)\]\(([^)]+)\)(?:\{width=([^}]+)\})?'
    )

    def make_block(alt: str, src: str, width: str | None) -> str:
        max_w = width if width else '100%'
        return (
            f'<p class="img-block"><img src="{src}" alt="{alt}" '
            f'style="max-width:{max_w};display:block;margin:0.5em auto;"></p>'
        )

    def make_inline(alt: str, src: str, width: str | None) -> str:
        max_w = width if width else '100%'
        return (
            f'<img src="{src}" alt="{alt}" '
            f'style="max-width:{max_w};display:inline;vertical-align:middle;">'
        )

    def replace_line(m: re.Match) -> str:
        """
        Called for lines whose *entire non-whitespace content* is one or more
        image tokens (possibly chained: ![a](x)![b](y)![c](z)).
        Each token becomes its own <p class="img-block"> block.
        """
        blocks = []
        for tok in IMG_TOKEN.finditer(m.group(0)):
            blocks.append(make_block(tok.group(1), tok.group(2), tok.group(3)))
        return '\n'.join(blocks)

    # A "standalone image line" is a line whose non-whitespace content consists
    # entirely of image tokens (one or more, possibly chained without spaces).
    STANDALONE_LINE = re.compile(
        r'^[ \t]*(?:!\[[^\]]*\]\([^)]+\)(?:\{width=[^}]+\})?)+[ \t]*$',
        re.MULTILINE,
    )

    text = STANDALONE_LINE.sub(replace_line, text)

    # Remaining ![]() tokens are genuinely inline (within a sentence).
    text = IMG_TOKEN.sub(
        lambda m: make_inline(m.group(1), m.group(2), m.group(3)),
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Markdown table pre-processing
# ---------------------------------------------------------------------------

def convert_md_tables(text: str) -> str:
    """
    Pre-convert Markdown pipe-table syntax to raw HTML <table> elements before
    python-markdown processes the document.

    Python-Markdown's TableExtension does not parse tables inside raw HTML
    blocks (e.g. <div class="full-width">).  This pre-processor runs before
    python-markdown and converts every pipe-table — whether inside a raw HTML
    block or in normal Markdown flow — to a <table> element.

    Pipe tables that python-markdown would have handled are converted here
    instead; the TableExtension never sees them (they're already HTML), which
    is harmless.

    Format recognised:
        | col1 | col2 | col3 |
        | ---- | ---- | ---- |   ← separator row: cells contain only [-:| ]
        | val  | val  | val  |
        ...

    A separator row must be the second row; tables without one are left alone
    (they are not valid GFM tables).

    Inline Markdown within cells is converted with md_inline().
    """
    # Detect a separator row: each cell contains only dashes, colons, spaces
    SEP_CELL = re.compile(r'^[ \t]*:?-+:?[ \t]*$')

    def is_separator_row(cells: list[str]) -> bool:
        return bool(cells) and all(SEP_CELL.match(c) for c in cells)

    def parse_row(line: str) -> list[str]:
        """Split a pipe-table row into cell strings (stripped)."""
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        return [c.strip() for c in line.split('|')]

    def align_from_sep(cell: str) -> str:
        c = cell.strip()
        left = c.startswith(':')
        right = c.endswith(':')
        if left and right:
            return ' style="text-align:center"'
        if right:
            return ' style="text-align:right"'
        return ''  # left-align is default

    def render_table(block: str) -> str:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            return block

        rows = [parse_row(l) for l in lines]
        # Validate: row[1] must be separator
        if not is_separator_row(rows[1]):
            return block

        header_cells = rows[0]
        sep_cells = rows[1]
        data_rows = rows[2:]

        # Derive column count and alignments from the separator row
        n_cols = max(len(header_cells), len(sep_cells))
        aligns = []
        for i in range(n_cols):
            c = sep_cells[i] if i < len(sep_cells) else ''
            aligns.append(align_from_sep(c))

        def cell_html(content: str) -> str:
            """Convert inline Markdown in a cell to HTML, unwrapping outer <p>."""
            h = md_inline(content)
            # md_inline wraps in <p>...</p>; strip that for table cells
            h = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1', h.strip(), flags=re.DOTALL)
            return h

        parts = ['<table>']

        # Header
        parts.append('<thead><tr>')
        for i, hdr in enumerate(header_cells):
            al = aligns[i] if i < len(aligns) else ''
            parts.append(f'<th{al}>{cell_html(hdr)}</th>')
        parts.append('</tr></thead>')

        # Body
        if data_rows:
            parts.append('<tbody>')
            for row in data_rows:
                parts.append('<tr>')
                for i in range(n_cols):
                    content = row[i] if i < len(row) else ''
                    al = aligns[i] if i < len(aligns) else ''
                    parts.append(f'<td{al}>{cell_html(content)}</td>')
                parts.append('</tr>')
            parts.append('</tbody>')

        parts.append('</table>')
        return '\n'.join(parts)

    # Match a run of consecutive pipe-table lines (lines starting with |).
    # We allow blank lines between table and surrounding text but not within.
    TABLE_BLOCK = re.compile(
        r'(?m)^(?:\|[^\n]*\n)+',
    )

    return TABLE_BLOCK.sub(lambda m: render_table(m.group(0)), text)


# ---------------------------------------------------------------------------
# HTML conversion
# ---------------------------------------------------------------------------

def resolve_image_paths(html: str, base_dir: Path) -> str:
    """Rewrite relative img src attributes to absolute file:// URIs."""
    def rewrite(m):
        src = m.group(1)
        if src.startswith(('http://', 'https://', 'data:', 'file://')):
            return m.group(0)
        return f'src="file://{(base_dir / src).resolve()}"'
    return re.sub(r'src="([^"]+)"', rewrite, html)


def md_to_html(md_path: Path) -> str:
    """Run all pre-processing steps and convert Markdown to a full HTML document."""
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.footnotes import FootnoteExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.toc import TocExtension
    from markdown.extensions.attr_list import AttrListExtension
    from markdown.extensions.def_list import DefListExtension
    from markdown.extensions.abbr import AbbrExtension
    from markdown.extensions.smarty import SmartyExtension

    text = md_path.read_text(encoding='utf-8')
    text = convert_gfm_callouts(text)
    text = convert_md_images(text)
    text = convert_md_tables(text)
    text = render_mermaid_blocks(text, md_path.parent / 'images')
    text = convert_pullquotes(text)
    text = inject_annex_breaks(text)

    extensions = [
        TableExtension(), FootnoteExtension(UNIQUE_IDS=True),
        FencedCodeExtension(), TocExtension(permalink=False),
        AttrListExtension(), DefListExtension(), AbbrExtension(), SmartyExtension(),
    ]
    try:
        from markdown.extensions.codehilite import CodeHiliteExtension
        extensions.append(CodeHiliteExtension(guess_lang=False))
    except Exception:
        pass

    md = markdown.Markdown(extensions=extensions)
    body_html = md.convert(text)

    # Resolve raw [^key] tokens that survived inside raw HTML islands
    fn_anchors = {}
    for m in re.finditer(
        r'<sup id="fnref:(\d+-)?([^"]+)"><a[^>]+href="(#fn:[^"]+)"\s*>(\d+)</a></sup>',
        body_html
    ):
        key, href, num = m.group(2), m.group(3), m.group(4)
        if key not in fn_anchors:
            fn_anchors[key] = f'<sup><a class="footnote-ref" href="{href}">{num}</a></sup>'

    for m in re.finditer(
        r'<li id="fn:(\d+-)?([^"]+)">\s*<p>.*?<a[^>]+href="#fnref:(\d+-)?[^"]*"',
        body_html, flags=re.DOTALL
    ):
        key = m.group(2)
        if key not in fn_anchors:
            fn_id = m.group(0).split('"')[1]
            all_fn_ids = re.findall(r'<li id="(fn:[^"]+)">', body_html)
            try:
                num = str(all_fn_ids.index(fn_id) + 1)
                fn_anchors[key] = f'<sup><a class="footnote-ref" href="#{fn_id}">{num}</a></sup>'
            except ValueError:
                continue

    body_html = re.sub(
        r'\[\^([^\]]+)\]',
        lambda m: fn_anchors.get(m.group(1), m.group(0)),
        body_html,
    )

    # width= attribute → inline style (WeasyPrint honours inline over stylesheet)
    def apply_width_attr(html: str) -> str:
        def rewrite(m: re.Match) -> str:
            tag = re.sub(r'\s*width="[^"]*"', '', m.group(0))
            w = m.group(1)
            return re.sub(r'\s*/?>$',
                           f' style="max-width:min({w}, 100%);width:min({w}, 100%);">', tag)
        return re.sub(r'<img\b[^>]*\bwidth="([\d.]+(?:px|%))"[^>]*/?>',
                       rewrite, html)
    body_html = apply_width_attr(body_html)

    # Wrap adjacent bare <img> tags in <p> blocks so WeasyPrint sizes them correctly
    def isolate_images(html: str) -> str:
        def wrap_run(m: re.Match) -> str:
            imgs = re.findall(r'<img\b[^>]*/?>',  m.group(0))
            return '\n'.join(f'<p>{img}</p>' for img in imgs) + '\n'
        return re.sub(r'(?:<img\b[^>]*/?>[ \t]*\n?){2,}', wrap_run, html)
    body_html = isolate_images(body_html)

    # Tag image captions: <p><em>…</em></p> immediately after <img>
    body_html = re.sub(
        r'(<img\b[^>]*/?>)\s*(<p>(<em>.*?</em>)\s*</p>)',
        lambda m: m.group(1) + '\n' + m.group(2).replace('<p>', '<p class="img-caption">'),
        body_html, flags=re.DOTALL,
    )

    title = md_path.stem.replace('_', ' ').replace('-', ' ')
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{title}</title>\n'
        f'</head>\n<body>\n{body_html}\n</body>\n</html>'
    )


# ---------------------------------------------------------------------------
# Conversion engines
# ---------------------------------------------------------------------------

def _mark_oversized_spans(
    html: str,
    div_char_threshold: int = 20_000,
    table_row_threshold: int = 25,
) -> tuple[str, int]:
    """
    Pre-mark spanning elements that are too tall for WeasyPrint to handle with
    column-span:all (raises ``assert not page_is_empty``).

    Two element types are checked:

    div.single-column — marked when inner HTML exceeds *div_char_threshold*
        characters.  At 8.5pt body text a single-column page holds roughly
        7,000–8,000 chars; 20,000 chars (~2.5 pages) is a safe threshold.
        div.full-width is intentionally excluded: its tables are already
        protected by 'div.full-width table { column-span: none }' in CSS,
        and marking the div itself would strip its own column-span:all.

    Standalone <table> elements — marked when the table has more than
        *table_row_threshold* <tr> rows.  These tables sit directly in the
        two-column flow with column-span:all; if they exceed one page WeasyPrint
        crashes.  Marking adds class 'no-span' which the CSS turns into
        column-span:none, letting the table flow inside a single column instead.
        Tables already inside div.full-width or div.single-column are excluded
        (their column-span is already suppressed by the CSS rules).

    Returns (patched_html, count_marked).
    """
    marked = 0

    # ── 1. div.single-column ────────────────────────────────────────────────
    OPEN_DIV = re.compile(r'<div\s+class="(single-column[^"]*)"')
    out = []
    pos = 0
    for m in OPEN_DIV.finditer(html):
        tag_start = m.start()
        tag_end = m.end()
        gt = html.index('>', tag_end)
        inner_start = gt + 1

        depth = 1
        scan = inner_start
        inner_end = len(html)
        while depth > 0 and scan < len(html):
            next_open = html.find('<div', scan)
            next_close = html.find('</div>', scan)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                scan = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    inner_end = next_close
                else:
                    scan = next_close + 6

        inner_html = html[inner_start:inner_end]
        if len(inner_html) > div_char_threshold:
            classes = m.group(1)
            out.append(html[pos:tag_start])
            out.append(f'<div class="{classes} no-span"')
            pos = tag_end
            marked += 1
            print(
                f"  [weasyprint] Marking div.single-column as no-span "
                f"({len(inner_html):,} chars > threshold {div_char_threshold:,})",
                file=sys.stderr,
            )
    out.append(html[pos:])
    html = ''.join(out)

    # ── 2. Standalone <table> elements (not inside a spanning div) ──────────
    # Build a set of character ranges covered by div.full-width and
    # div.single-column so we can skip tables nested inside them.
    SPANNING_DIV = re.compile(r'<div\s+class="(?:full-width|single-column)[^"]*"')
    spanning_ranges: list[tuple[int, int]] = []
    for dm in SPANNING_DIV.finditer(html):
        gt = html.index('>', dm.end())
        inner_start = gt + 1
        depth = 1
        scan = inner_start
        inner_end = len(html)
        while depth > 0 and scan < len(html):
            nopen = html.find('<div', scan)
            nclose = html.find('</div>', scan)
            if nclose == -1:
                break
            if nopen != -1 and nopen < nclose:
                depth += 1
                scan = nopen + 4
            else:
                depth -= 1
                if depth == 0:
                    inner_end = nclose
                else:
                    scan = nclose + 6
        spanning_ranges.append((dm.start(), inner_end))

    def inside_spanning_div(pos: int) -> bool:
        return any(start <= pos <= end for start, end in spanning_ranges)

    TABLE_OPEN = re.compile(r'<table\b([^>]*)>')
    out = []
    pos = 0
    for tm in TABLE_OPEN.finditer(html):
        if inside_spanning_div(tm.start()):
            continue  # already protected by CSS
        # Count <tr> tags inside this table
        table_start = tm.start()
        # Find </table>
        table_end = html.find('</table>', tm.end())
        if table_end == -1:
            continue
        table_end += len('</table>')
        inner = html[tm.end():table_end - len('</table>')]
        row_count = inner.count('<tr')
        if row_count > table_row_threshold:
            attrs = tm.group(1)
            # Add no-span to existing class or as new attribute
            if 'class="' in attrs:
                new_attrs = re.sub(r'class="([^"]*)"', r'class="\1 no-span"', attrs)
            else:
                new_attrs = attrs + ' class="no-span"'
            out.append(html[pos:table_start])
            out.append(f'<table{new_attrs}>')
            pos = tm.end()
            marked += 1
            print(
                f"  [weasyprint] Marking standalone <table> as no-span "
                f"({row_count} rows > threshold {table_row_threshold})",
                file=sys.stderr,
            )
    out.append(html[pos:])
    html = ''.join(out)

    return html, marked


def convert_weasyprint(md_path: Path, pdf_path: Path, css_path: Path,
                       custom_css_path: Path | None = None) -> None:
    """Primary pipeline: Markdown → HTML → PDF via WeasyPrint."""
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    mmdc = find_mmdc()
    if mmdc:
        print(f"  [mermaid] mmdc found at {mmdc} — diagrams will render as PNG")
    else:
        print("  [mermaid] mmdc not found — diagrams will show as placeholders")
        print("            Install: npm install -g @mermaid-js/mermaid-cli")

    print(f"  [weasyprint] Converting {md_path.name} ...")

    html_str = md_to_html(md_path)
    html_str = resolve_image_paths(html_str, md_path.parent)

    # Pre-mark spanning elements whose content exceeds one page worth of text.
    # Those elements get class 'no-span'; the fallback CSS targets only them,
    # leaving normal-sized single-column and full-width elements intact.
    html_str, n_marked = _mark_oversized_spans(html_str)

    font_config = FontConfiguration()
    sheets = [CSS(filename=str(css_path), font_config=font_config)]
    if custom_css_path and custom_css_path.exists():
        sheets.append(CSS(filename=str(custom_css_path), font_config=font_config))
        print(f"  [weasyprint] Custom CSS: {custom_css_path}")

    doc = HTML(string=html_str, base_url=str(md_path.parent))

    # WeasyPrint uses bare asserts internally; the most common triggers are:
    #   - an image taller than a blank page
    #   - a table cell with a very long unbreakable token (e.g. long URL or
    #     a run of dashes) that exceeds the column/page width
    # We cascade through progressively more aggressive fallback CSS overrides
    # so that as much of the document as possible is still rendered.
    #
    # Shared word-break override applied in all fallback passes.
    _WORDBREAK = (
        'td, th, p, li, blockquote, pre, code { '
        '  overflow-wrap: break-word !important; '
        '  word-break: break-all !important; '
        '} '
    )
    # Target only pre-marked oversized elements — normal column-spanning divs
    # (div.single-column, div.full-width without 'no-span') keep their layout.
    _NO_SPAN = (
        'div.no-span { '
        '  column-span: none !important; '
        '} '
    )
    # Last-resort: strip column-span from ALL spanning elements
    _NO_SPAN_ALL = (
        'div.full-width, div.single-column, table, div.footnote { '
        '  column-span: none !important; '
        '} '
    )

    FALLBACKS = [
        # Pass 1 — force word-breaking everywhere (catches long tokens in cells)
        (
            'word-break everywhere',
            CSS(string=_WORDBREAK + 'img { max-width:100% !important; max-height:80vh !important; }'),
        ),
        # Pass 2 — remove column-span only from oversized (pre-marked) elements
        (
            'oversized spans removed',
            CSS(string=_WORDBREAK + _NO_SPAN),
        ),
        # Pass 3 — remove column-span from ALL spanning elements (nuclear option)
        (
            'all column-spans removed',
            CSS(string=_WORDBREAK + _NO_SPAN_ALL),
        ),
        # Pass 4 — also hide images
        (
            'all column-spans removed, images hidden',
            CSS(string=_WORDBREAK + _NO_SPAN_ALL + 'img { display: none !important; }'),
        ),
        # Pass 5 — also hide tables (last resort)
        (
            'all column-spans removed, images and tables hidden',
            CSS(string=_WORDBREAK + _NO_SPAN_ALL + 'img, table { display: none !important; }'),
        ),
    ]

    last_err = None
    for label, fallback_css in [(None, None)] + [(l, c) for l, c in FALLBACKS]:
        extra = [fallback_css] if fallback_css else []
        try:
            doc.write_pdf(str(pdf_path), stylesheets=sheets + extra,
                          font_config=font_config)
            if label:
                print(f"  [weasyprint] Written ({label}) to {pdf_path}")
                print(f"  [weasyprint] Warning: layout required fallback — {label}.",
                      file=sys.stderr)
                print("               Review oversized images or tables in the source.",
                      file=sys.stderr)
            else:
                print(f"  [weasyprint] Written to {pdf_path}")
            return
        except (AssertionError, Exception) as e:
            last_err = e
            print(f"  [weasyprint] Attempt ({label or 'normal'}) failed: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
            if label is None:
                print(f"  [weasyprint] Trying fallbacks ...", file=sys.stderr)
            continue

    raise RuntimeError(
        f"WeasyPrint failed on all fallback attempts. Last error: {last_err}"
    ) from last_err


def convert_pandoc(md_path: Path, pdf_path: Path, css_path: Path) -> None:
    """Fallback pipeline: Markdown → PDF via pandoc + wkhtmltopdf."""
    import pypandoc

    print(f"  [pandoc] Converting {md_path.name} ...")
    extra_args = [
        '--standalone', '--pdf-engine=wkhtmltopdf',
        '--variable', 'margin-top=2.5cm',
        '--variable', 'margin-bottom=2.5cm',
        '--variable', 'margin-left=2.8cm',
        '--variable', 'margin-right=2.8cm',
        '--variable', 'fontsize=10pt',
        '--variable', 'papersize=a4',
    ]
    if css_path.exists():
        extra_args += ['--css', str(css_path)]

    pypandoc.convert_file(str(md_path), 'pdf',
                           outputfile=str(pdf_path), extra_args=extra_args)
    print(f"  [pandoc] Written to {pdf_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _list_bundled_styles() -> list[str]:
    """Return sorted list of bundled style names (bare names, no prefix/ext)."""
    styles_dir = _styles_dir()
    names = []
    for p in sorted(styles_dir.glob('style_*.css')):
        names.append(p.stem[len('style_'):])   # strip 'style_' prefix
    return names


def main():
    parser = argparse.ArgumentParser(
        prog='md2pdf',
        description=(
            'Edition ToolKit — Convert Markdown to PDF.\n\n'
            'Bundled styles: ' + ', '.join(_list_bundled_styles())
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input',
                        help='Input Markdown file (.md)')
    parser.add_argument('output', nargs='?',
                        help='Output PDF path (default: same name as input, .pdf)')
    parser.add_argument(
        '--css',
        metavar='STYLE',
        default=None,
        help=(
            'Style to apply. Accepts: a bare name (thinktank, academic, magazine, '
            'intelligence), style_<name>, style_<name>.css, or a full path to '
            'any .css file. Default: thinktank.'
        ),
    )
    parser.add_argument(
        '--custom',
        metavar='CSS',
        default=None,
        help=(
            'Path to a project-specific CSS file applied after the core style. '
            'Use it to set author name, title slot text, font overrides, or any '
            'other per-project customisation. Overrides anything in the core style.'
        ),
    )
    parser.add_argument('--engine',
                        choices=['weasyprint', 'pandoc', 'auto'],
                        default='auto',
                        help='Rendering engine (default: auto)')
    parser.add_argument('--list-styles', action='store_true',
                        help='List available bundled styles and exit.')
    args = parser.parse_args()

    if args.list_styles:
        print("Bundled styles:")
        for name in _list_bundled_styles():
            print(f"  {name}")
        return

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found.", file=sys.stderr)
        sys.exit(1)

    pdf_path = (Path(args.output).resolve()
                if args.output else md_path.with_suffix('.pdf'))

    css_path = resolve_css(args.css)
    if not css_path.exists():
        print(f"Error: CSS not found: '{args.css}'", file=sys.stderr)
        print(f"  Bundled styles: {', '.join(_list_bundled_styles())}", file=sys.stderr)
        sys.exit(1)

    custom_css_path = None
    if args.custom:
        # Resolution order: exact path, relative to cwd, with .css appended
        _c = Path(args.custom)
        for candidate in [_c, Path.cwd() / _c,
                          _c.with_suffix('.css'), Path.cwd() / _c.with_suffix('.css')]:
            if candidate.exists():
                custom_css_path = candidate.resolve()
                break
        if custom_css_path is None:
            print(f"Error: --custom CSS not found: '{args.custom}'", file=sys.stderr)
            sys.exit(1)

    print(f"Input  : {md_path}")
    print(f"Output : {pdf_path}")
    print(f"Style  : {css_path}")
    if custom_css_path:
        print(f"Custom : {custom_css_path}")

    engine = args.engine

    if engine in ('weasyprint', 'auto'):
        try:
            convert_weasyprint(md_path, pdf_path, css_path, custom_css_path)
            return
        except ImportError:
            if engine == 'weasyprint':
                print("WeasyPrint not installed.", file=sys.stderr)
                print("  conda install markdown weasyprint pygments", file=sys.stderr)
                sys.exit(1)
            print("  WeasyPrint not available, trying pandoc...")

    if engine in ('pandoc', 'auto'):
        try:
            convert_pandoc(md_path, pdf_path, css_path)
        except ImportError:
            print("Neither WeasyPrint nor pypandoc is installed.", file=sys.stderr)
            print("  conda install markdown weasyprint pygments", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
